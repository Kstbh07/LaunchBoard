#!/usr/bin/env python3
"""
LaunchBoard Evaluation Script

Calculates classification accuracy by comparing AI predictions
against manually verified ground truth labels.

Usage:
    python evaluate.py ground_truth_labeled.csv [--output report.json]
"""
import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


VALID_ROLES = [
    "Software Development", "Frontend Development", "Backend Development",
    "Full Stack Development", "AI/ML Engineering", "Data Science",
    "Data Analytics", "DevOps / Cloud", "Cybersecurity",
    "Mobile Development", "QA / Testing", "UI/UX Design",
    "Product Management", "Business Development", "Other",
]


def load_labeled_data(csv_path: str) -> list[dict]:
    """Load labeled CSV data."""
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip rows without manual labels
            if not row.get("manual_role") or not row.get("manual_city"):
                continue
            rows.append(row)
    return rows


def calculate_accuracy(rows: list[dict]) -> dict:
    """Calculate classification accuracy metrics."""
    if not rows:
        return {"error": "No labeled rows found. Please fill in manual_role and manual_city columns."}

    total = len(rows)

    # Role accuracy
    role_correct = sum(
        1 for r in rows
        if r.get("role_correct", "").lower() == "yes"
        or r.get("ai_role_category", "").strip().lower() == r.get("manual_role", "").strip().lower()
    )

    # City accuracy
    city_correct = sum(
        1 for r in rows
        if r.get("city_correct", "").lower() == "yes"
        or r.get("ai_city", "").strip().lower() == r.get("manual_city", "").strip().lower()
    )

    # Combined accuracy
    both_correct = sum(
        1 for r in rows
        if (r.get("both_correct", "").lower() == "yes")
        or (
            (r.get("role_correct", "").lower() == "yes"
             or r.get("ai_role_category", "").strip().lower() == r.get("manual_role", "").strip().lower())
            and
            (r.get("city_correct", "").lower() == "yes"
             or r.get("ai_city", "").strip().lower() == r.get("manual_city", "").strip().lower())
        )
    )

    # Confusion matrix for roles
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        predicted = r.get("ai_role_category", "Unknown").strip()
        actual = r.get("manual_role", "Unknown").strip()
        confusion[actual][predicted] += 1

    # Missing/Unknown counts
    unknown_roles = sum(1 for r in rows if r.get("ai_role_category", "").strip() in ("", "Unknown", "Other"))
    unknown_cities = sum(1 for r in rows if r.get("ai_city", "").strip() in ("", "Unknown"))

    # Per-role accuracy
    role_distribution = Counter(r.get("manual_role", "Unknown").strip() for r in rows)

    return {
        "total_evaluated": total,
        "role_accuracy": {
            "correct": role_correct,
            "total": total,
            "accuracy_pct": round(role_correct / total * 100, 2),
        },
        "city_accuracy": {
            "correct": city_correct,
            "total": total,
            "accuracy_pct": round(city_correct / total * 100, 2),
        },
        "combined_accuracy": {
            "correct": both_correct,
            "total": total,
            "accuracy_pct": round(both_correct / total * 100, 2),
        },
        "unknown_predictions": {
            "unknown_roles": unknown_roles,
            "unknown_cities": unknown_cities,
        },
        "role_distribution": dict(role_distribution),
        "confusion_matrix": {k: dict(v) for k, v in confusion.items()},
    }


def print_report(report: dict) -> None:
    """Print formatted evaluation report."""
    if "error" in report:
        print(f"\n❌ Error: {report['error']}")
        return

    print("\n" + "=" * 60)
    print("  LaunchBoard AI Classification Evaluation Report")
    print("=" * 60)

    print(f"\n📊 Total Jobs Evaluated: {report['total_evaluated']}")

    ra = report["role_accuracy"]
    print(f"\n🏷️  Role Classification Accuracy:")
    print(f"   {ra['correct']}/{ra['total']} = {ra['accuracy_pct']}%")

    ca = report["city_accuracy"]
    print(f"\n📍 City Extraction Accuracy:")
    print(f"   {ca['correct']}/{ca['total']} = {ca['accuracy_pct']}%")

    ba = report["combined_accuracy"]
    print(f"\n✅ Combined Exact-Match Accuracy:")
    print(f"   {ba['correct']}/{ba['total']} = {ba['accuracy_pct']}%")

    up = report["unknown_predictions"]
    print(f"\n❓ Unknown/Missing Predictions:")
    print(f"   Unknown roles: {up['unknown_roles']}")
    print(f"   Unknown cities: {up['unknown_cities']}")

    print(f"\n📈 Role Distribution (Ground Truth):")
    for role, count in sorted(report["role_distribution"].items(), key=lambda x: -x[1]):
        print(f"   {role}: {count}")

    print(f"\n🔀 Confusion Matrix:")
    cm = report["confusion_matrix"]
    if cm:
        all_labels = sorted(set(
            list(cm.keys()) +
            [pred for actual in cm.values() for pred in actual.keys()]
        ))
        # Header
        print(f"   {'Actual \\ Predicted':<30}", end="")
        for label in all_labels:
            print(f"{label[:15]:>16}", end="")
        print()
        # Rows
        for actual in all_labels:
            print(f"   {actual:<30}", end="")
            for predicted in all_labels:
                count = cm.get(actual, {}).get(predicted, 0)
                print(f"{count:>16}", end="")
            print()

    print("\n" + "=" * 60)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Evaluate LaunchBoard AI classification accuracy")

    parser.add_argument("csv_file", help="Path to labeled CSV file")
    parser.add_argument("--output", "-o", help="Output JSON report path", default=None)
    args = parser.parse_args()

    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)

    rows = load_labeled_data(str(csv_path))
    report = calculate_accuracy(rows)
    print_report(report)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to: {args.output}")


if __name__ == "__main__":
    main()
