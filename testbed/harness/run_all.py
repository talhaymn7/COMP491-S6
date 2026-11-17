"""Run every measurement and write results/summary.md."""
import report
import run_change_aware
import run_dtm
import run_fixed
import run_random
import run_static
import validate_truth

if __name__ == "__main__":
    print("== Ground truth =="); validate_truth.main()
    print("\n== Method A: static linters =="); run_static.main()
    print("\n== Method B: fixed-data rollback test =="); run_fixed.main()
    print("\n== Method B': django-test-migrations =="); run_dtm.main()
    print("\n== Method R: random rollback test =="); run_random.main()
    print("\n== Method P: change-aware data generation =="); run_change_aware.main()
    print("\n== Report =="); report.main()
