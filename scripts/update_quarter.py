"""
Convert MOPS XLSX files → Parquet for git deployment.

Usage (files in dedicated folder):
  python scripts/update_quarter.py --quarter 2026Q1 --src "C:/path/to/2026Q1_folder"

Usage (all quarters in same folder, distinguished by filename prefix):
  python scripts/update_quarter.py --quarter 2025Q1 --src "C:/path/to/2025財報" --prefix 2025Q1
  python scripts/update_quarter.py --quarter 2025Q2 --src "C:/path/to/2025財報" --prefix 2025Q2

The source folder must contain 6 MOPS xlsx files for each quarter,
named with any pattern containing the market label (上市/上櫃) and
report type (綜合損益表/資產負債表/現金流量表).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.loader import load_quarter_combined

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quarter", required=True, help="e.g. 2025Q1")
    parser.add_argument("--src", required=True, help="folder with MOPS xlsx files")
    parser.add_argument("--prefix", default="", help="filename prefix to filter quarter (e.g. 2025Q1)")
    args = parser.parse_args()

    src = Path(args.src)
    out = Path(__file__).parent.parent / "data" / "processed" / f"{args.quarter}.parquet"

    prefix = args.prefix or ""
    print(f"Reading from: {src}  (prefix filter: '{prefix}')")
    df = load_quarter_combined(src, prefix=prefix)
    print(f"Loaded {len(df)} companies")

    df.to_parquet(out, index=False)
    size_kb = out.stat().st_size / 1024
    print(f"Saved → {out}  ({size_kb:.1f} KB)")

if __name__ == "__main__":
    main()
