"""CLI script to process classification backlog progressively.

Usage:
    python scripts/process_backlog.py [--limit 30] [--delay 4.2] [--retry-failed]
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import async_session_factory
from app.services.classification_backlog import ClassificationBacklogService


async def main():
    parser = argparse.ArgumentParser(description="Process LaunchBoard classification backlog.")
    parser.add_argument("--limit", type=int, default=30, help="Number of jobs to process (default: 30)")
    parser.add_argument("--delay", type=float, default=4.2, help="Delay between requests in seconds (default: 4.2)")
    parser.add_argument("--retry-failed", action="store_true", default=True, help="Include failed jobs in retry")
    args = parser.parse_args()

    print(f"=== LAUNCHBOARD CLASSIFICATION BACKLOG PROCESSOR ===")
    print(f"Batch Limit:       {args.limit}")
    print(f"Pacing Delay:      {args.delay}s (Target: <15 RPM)")
    print(f"Retry Failed:      {args.retry_failed}")
    print("-----------------------------------------------------")

    async with async_session_factory() as session:
        service = ClassificationBacklogService(db=session, rate_limit_delay=args.delay)
        initial_counts = await service.get_backlog_counts()
        print(f"Initial State: Total={initial_counts['total_jobs']} | Classified={initial_counts['classified']} | Pending={initial_counts['pending']} | Failed={initial_counts['failed']}")
        print("Starting classification...")

        res = await service.process_batch(limit=args.limit, retry_failed=args.retry_failed)

        print("\n=== BATCH RESULT ===")
        print(f"Status:            {res.get('status')}")
        print(f"Processed:         {res.get('processed')}")
        print(f"Classified:        {res.get('classified')}")
        print(f"Failed:            {res.get('failed')}")
        print(f"Input Tokens:      {res.get('total_input_tokens')}")
        print(f"Output Tokens:     {res.get('total_output_tokens')}")
        print(f"Estimated Cost:    ${res.get('estimated_cost_usd', 0):.6f}")
        print(f"Remaining Backlog: {res.get('remaining_backlog')}")
        counts = res.get("counts", {})
        print(f"Updated State:     Classified={counts.get('classified')} | Pending={counts.get('pending')} | Failed={counts.get('failed')}")


if __name__ == "__main__":
    asyncio.run(main())
