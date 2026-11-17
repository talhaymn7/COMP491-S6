"""Integrity of the digest manifest of method P: Merkle tree + Ed25519 signature.

* Every artifact digest and every field digest of a version is a leaf of a Merkle
  tree. Hashing follows RFC 6962 (Certificate Transparency): leaf = SHA-256(0x00 || data),
  node = SHA-256(0x01 || left || right), split at the largest power of two below n.
  The root represents the whole data contract of the version.
* The root is placed in a small statement (version, scenario, number of leaves, root)
  which is signed with Ed25519 (RFC 8032).
* Before tests are generated, both signed statements are verified and both roots are
  recomputed from the manifests. A manifest that was changed after signing is rejected.
* For every changed element, an inclusion proof against the signed V2 root shows that
  the element is part of the signed contract (log2(n) hashes).
"""
import hashlib
import json
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

LEAF, NODE = b"\x00", b"\x01"


def _h(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _split(n):
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def leaves(manifest):
    """Sorted (key, leaf hash) pairs for every artifact and field digest."""
    items = [(f"artifact:{k}", v) for k, v in manifest["artifacts"].items()] + \
            [(f"field:{k}", v) for k, v in manifest["fields"].items()]
    items.sort()
    return [(key, _h(LEAF + f"{key}={digest}".encode())) for key, digest in items]


def root(hashes):
    n = len(hashes)
    if n == 0:
        return _h(b"")
    if n == 1:
        return hashes[0]
    k = _split(n)
    return _h(NODE + root(hashes[:k]) + root(hashes[k:]))


def inclusion_proof(m, hashes):
    n = len(hashes)
    if n <= 1:
        return []
    k = _split(n)
    if m < k:
        return inclusion_proof(m, hashes[:k]) + [root(hashes[k:])]
    return inclusion_proof(m - k, hashes[k:]) + [root(hashes[:k])]


def verify_inclusion(leaf_hash, m, n, proof, expected_root):
    def rebuild(m, n, proof):
        if n == 1:
            if proof:
                raise ValueError("proof too long")
            return leaf_hash
        k = _split(n)
        if m < k:
            return _h(NODE + rebuild(m, k, proof[:-1]) + proof[-1])
        return _h(NODE + proof[-1] + rebuild(m - k, n - k, proof[:-1]))
    try:
        return rebuild(m, n, list(proof)) == expected_root
    except (ValueError, IndexError):
        return False


def new_key(work_dir):
    """Ephemeral signing key for one run (a CI system would keep this key in a secret store)."""
    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    (work_dir / "signing_public_key.hex").write_text(pub.hex(), encoding="utf-8")
    return key, pub


def statement(manifest, version, scenario):
    hs = [h for _, h in leaves(manifest)]
    return {"version": version, "scenario": scenario, "leaves": len(hs), "merkle_root": root(hs).hex()}


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def sign(key, stmt):
    return key.sign(canonical(stmt)).hex()


def verify(manifest, stmt, signature_hex, public_key: bytes):
    """True if the signature is valid and the manifest still has the signed root."""
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(bytes.fromhex(signature_hex), canonical(stmt))
    except (InvalidSignature, ValueError):
        return False
    hs = [h for _, h in leaves(manifest)]
    return len(hs) == stmt["leaves"] and root(hs).hex() == stmt["merkle_root"]


def protect(m1, m2, scenario, key, pub, work):
    """Sign both manifests, verify them, build inclusion proofs for changed leaves, run tamper tests."""
    t0 = time.perf_counter()
    s1, s2 = statement(m1, "v1", scenario), statement(m2, "v2", scenario)
    sig1, sig2 = sign(key, s1), sign(key, s2)
    t_sign = time.perf_counter() - t0

    t0 = time.perf_counter()
    ok = verify(m1, s1, sig1, pub) and verify(m2, s2, sig2, pub)
    t_verify = time.perf_counter() - t0
    if not ok:
        raise RuntimeError(f"{scenario}: manifest signature or Merkle root verification failed")

    l1, l2 = dict(leaves(m1)), leaves(m2)
    changed = [(i, k, h) for i, (k, h) in enumerate(l2) if l1.get(k) != h]
    removed = sorted(set(l1) - {k for k, _ in l2})
    hashes2 = [h for _, h in l2]
    root2 = bytes.fromhex(s2["merkle_root"])
    proofs = []
    for i, k, h in changed:
        p = inclusion_proof(i, hashes2)
        proofs.append({"leaf": k, "index": i, "proof_hashes": len(p),
                       "verified": verify_inclusion(h, i, len(hashes2), p, root2)})

    # Tamper tests: (1) change one field digest after signing, (2) flip one bit of the signature.
    forged = json.loads(json.dumps(m2))
    first = sorted(forged["fields"])[0]
    forged["fields"][first] = "0" * 64
    bad_sig = format(int(sig2[:2], 16) ^ 1, "02x") + sig2[2:]
    tamper = {"modified_manifest_rejected": not verify(forged, s2, sig2, pub),
              "modified_signature_rejected": not verify(m2, s2, bad_sig, pub)}

    (work / "signed_manifests.json").write_text(json.dumps(
        {"v1": {"statement": s1, "signature": sig1}, "v2": {"statement": s2, "signature": sig2},
         "public_key": pub.hex(), "changed_leaf_proofs": proofs, "removed_leaves": removed},
        indent=1), encoding="utf-8")
    return {
        "leaves_v1": s1["leaves"], "leaves_v2": s2["leaves"],
        "root_v1": s1["merkle_root"], "root_v2": s2["merkle_root"],
        "changed_leaves": [p["leaf"] for p in proofs], "removed_leaves": removed,
        "proof_hashes": [p["proof_hashes"] for p in proofs],
        "proofs_verified": all(p["verified"] for p in proofs),
        "tamper": tamper,
        "ms_sign": round(t_sign * 1000, 2), "ms_verify": round(t_verify * 1000, 2),
    }
