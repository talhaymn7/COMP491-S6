import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import psycopg

from suite import APP_ROOT

ROOT = Path(__file__).resolve().parent.parent
V1_DIR = APP_ROOT / "app_v1"
BUILD = APP_ROOT / "build"
RESULTS = APP_ROOT / "results"
PG = dict(host="db", port=5432, user="rbtest", password="rbtest")


def build_v2(scenario):
    """Copy V1, apply the scenario patches, generate the V2 migration."""
    dst = BUILD / scenario["id"] / "app_v2"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(V1_DIR, dst, ignore=shutil.ignore_patterns("__pycache__", "_*.json"))
    for rel, old, new in scenario.get("patches", []):
        p = dst / rel
        text = p.read_text(encoding="utf-8")
        assert text.count(old) == 1, f"{scenario['id']}: patch anchor missing/not unique in {rel}: {old!r}"
        p.write_text(text.replace(old, new), encoding="utf-8")
    for rel, content in scenario.get("files", {}).items():
        (dst / rel).write_text(content, encoding="utf-8")
    if not scenario.get("files"):
        manage(dst, "makemigrations", "orders", "--noinput", check=True)
    return dst


def manage(app_dir, *args, db="rbtest", check=False):
    env = dict(os.environ, RB_DB=db)
    proc = subprocess.run(["python", "manage.py", *args], cwd=app_dir, env=env,
                          capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"manage.py {' '.join(args)} failed in {app_dir}:\n{proc.stdout}\n{proc.stderr}")
    return proc


def fresh_db(name):
    with psycopg.connect(dbname="rbtest", autocommit=True, **PG) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{name}"')
    return name


def save(name, data):
    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


class Timer:
    def __enter__(self):
        self.t = time.perf_counter()
        return self

    def __exit__(self, *a):
        self.seconds = time.perf_counter() - self.t
