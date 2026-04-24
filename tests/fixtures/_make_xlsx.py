# -*- coding: utf-8 -*-
"""Generate bank.xlsx from bank.csv using openpyxl.

Run once from the fixtures directory:
    python tests/fixtures/_make_xlsx.py
"""
import csv
import os
from pathlib import Path

try:
    import openpyxl
except ImportError:
    raise SystemExit("ERROR: pip install openpyxl")

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "bank.csv"
XLSX_PATH = HERE / "bank.xlsx"


def main():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            ws.append(row)

    wb.save(XLSX_PATH)
    print(f"Written: {XLSX_PATH}")


if __name__ == "__main__":
    main()
