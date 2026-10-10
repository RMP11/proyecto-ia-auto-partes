"""Start the demo; create the synthetic dataset and model if they are missing."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Run the inventory forecasting demo.")
    parser.add_argument("--rebuild", action="store_true", help="Regenerate data and retrain before starting.")
    parser.add_argument("--port", type=int, default=8981, help="Local HTTP port (default: 8981).")
    args = parser.parse_args()
    data_missing = not (ROOT / "data/sales.csv").exists()
    if args.rebuild or data_missing:
        subprocess.run([sys.executable, "-m", "src.app.data"], cwd=ROOT, check=True)
    if args.rebuild or data_missing or not all((ROOT / "artifacts" / name).exists() for name in ["model.joblib", "metrics.json"]):
        subprocess.run([sys.executable, "-m", "src.app.train"], cwd=ROOT, check=True)
    print(f"Open http://127.0.0.1:{args.port}. Press Ctrl+C to stop.", flush=True)
    subprocess.run([sys.executable, "-m", "uvicorn", "src.app.main:app", "--host", "127.0.0.1", "--port", str(args.port)], cwd=ROOT, check=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDemo stopped.")
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"A step failed with exit code {error.returncode}. See the message above and README.md.") from None
