import csv
import io
import sys
from datetime import date, datetime

INPUT_FILE = "customers.csv"

ACTIVE_DAYS = 30
LAPSED_DAYS = 60

LEGACY_COLUMNS = {"first_name", "last_name", "last_purchase_date", "total_spend", "loyalty_points"}


def parse_date(value: str) -> date:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: '{value}'")


def load_cova_export(filepath: str) -> tuple[list[dict], list[str]]:
    """Load a Cova Customer Activity List, skipping the parameter header block."""
    with open(filepath, newline="", encoding="utf-8") as f:
        lines = f.readlines()

    header_idx = next(
        (i for i, line in enumerate(lines) if line.strip().startswith("Customer,")),
        None,
    )
    if header_idx is None:
        sys.exit("Could not find data header row in Cova export.")

    reader = csv.DictReader(io.StringIO("".join(lines[header_idx:])))
    rows = list(reader)
    return rows, list(reader.fieldnames or [])


def load_customers(filepath: str) -> tuple[list[dict], list[str], str]:
    """Load customers, auto-detecting Cova export vs legacy format."""
    with open(filepath, newline="", encoding="utf-8") as f:
        first_line = f.readline().strip()

    if first_line == "Parameters:":
        rows, fieldnames = load_cova_export(filepath)
        return rows, fieldnames, "cova"

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if not LEGACY_COLUMNS.issubset(set(fieldnames)):
            missing = LEGACY_COLUMNS - set(fieldnames)
            sys.exit(f"Missing columns in input file: {missing}")
        return list(reader), fieldnames, "legacy"


def get_days_since(row: dict, fmt: str, today: date) -> int | None:
    if fmt == "cova":
        try:
            return int(row["Days Since Last Visit"])
        except (ValueError, KeyError):
            print(f"Skipping row ({row.get('Customer')}): invalid 'Days Since Last Visit'")
            return None
    else:
        try:
            return (today - parse_date(row["last_purchase_date"])).days
        except ValueError as e:
            print(f"Skipping row ({row.get('first_name')} {row.get('last_name')}): {e}")
            return None


def segment(customers: list[dict], fmt: str, today: date) -> tuple[list, list, list]:
    active, lapsed, lost = [], [], []
    for row in customers:
        days = get_days_since(row, fmt, today)
        if days is None:
            continue
        if days <= ACTIVE_DAYS:
            active.append(row)
        elif days <= LAPSED_DAYS:
            lapsed.append(row)
        else:
            lost.append(row)
    return active, lapsed, lost


def write_segment(filename: str, rows: list[dict], fieldnames: list[str]) -> None:
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {filename}: {len(rows)} customer(s)")


def main() -> None:
    filepath = sys.argv[1] if len(sys.argv) > 1 else INPUT_FILE
    today = date.today()

    print(f"Reading '{filepath}' (reference date: {today})\n")
    customers, fieldnames, fmt = load_customers(filepath)
    print(f"Format detected: {fmt} ({len(customers)} rows)\n")

    active, lapsed, lost = segment(customers, fmt, today)

    print("Writing segments:")
    write_segment("customers_active.csv", active, fieldnames)
    write_segment("customers_lapsed.csv", lapsed, fieldnames)
    write_segment("customers_lost.csv", lost, fieldnames)

    total = len(active) + len(lapsed) + len(lost)
    print(f"\nDone. {total}/{len(customers)} customer(s) segmented.")


if __name__ == "__main__":
    main()
