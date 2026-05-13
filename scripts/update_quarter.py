"""
Convert MOPS XLSX files → Parquet for git deployment.

Usage:
  python scripts/update_quarter.py --quarter 2026Q1 --src "C:/path/to/xlsx/folder"

The source folder must contain these 6 files (rename if needed):
  上市_綜合損益表.xlsx, 上市_資產負債表.xlsx, 上市_現金流量表.xlsx
  上櫃_綜合損益表.xlsx, 上櫃_資產負債表.xlsx, 上櫃_現金流量表.xlsx
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.loader import load_quarter_combined

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quarter", required=True, help="e.g. 2026Q1")
    parser.add_argument("--src", required=True, help="folder with 6 MOPS xlsx files")
    args = parser.parse_args()

    src = Path(args.src)
    out = Path(__file__).parent.parent / "data" / "processed" / f"{args.quarter}.parquet"

    print(f"Reading from: {src}")
    df = load_quarter_combined(src)
    print(f"Loaded {len(df)} companies")

    df.to_parquet(out, index=False)
    size_kb = out.stat().st_size / 1024
    print(f"Saved → {out}  ({size_kb:.1f} KB)")
    print(f"\nNext steps:")
    print(f"  git add data/processed/{args.quarter}.parquet")
    print(f"  git commit -m 'Add {args.quarter} financial data'")
    print(f"  git push")

if __name__ == "__main__":
    main()
