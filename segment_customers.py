import csv
import sys
from datetime import date, datetime, timedelta

INPUT_FILE = "customers.csv"
REQUIRED_COLUMNS = {"first_name", "last_name", "last_purchase_date", "total_spend", "loyalty_points"}

ACTIVE_DAYS = 30
LAPSED_DAYS = 60


def parse_date(value: str) -> date:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: '{value}'")


def load_customers(filepath: str) -> list[dict]:
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not REQUIRED_COLUMNS.issubset(set(reader.fieldnames or [])):
            missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            sys.exit(f"Missing columns in input file: {missing}")
        return list(reader)


def segment(customers: list[dict], today: date) -> tuple[list, list, list]:
    active, lapsed, lost = [], [], []
    for row in customers:
        try:
            purchase_date = parse_date(row["last_purchase_date"])
        except ValueError as e:
            print(f"Skipping row ({row.get('first_name')} {row.get('last_name')}): {e}")
            continue
        days_since = (today - purchase_date).days
        if days_since <= ACTIVE_DAYS:
            active.append(row)
        elif days_since <= LAPSED_DAYS:
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
    customers = load_customers(filepath)

    with open(filepath, newline="", encoding="utf-8") as f:
        fieldnames = csv.DictReader(f).fieldnames

    active, lapsed, lost = segment(customers, today)

    print("Writing segments:")
    write_segment("customers_active.csv", active, fieldnames)
    write_segment("customers_lapsed.csv", lapsed, fieldnames)
    write_segment("customers_lost.csv", lost, fieldnames)

    total = len(active) + len(lapsed) + len(lost)
    print(f"\nDone. {total}/{len(customers)} customer(s) segmented.")


if __name__ == "__main__":
    main()
