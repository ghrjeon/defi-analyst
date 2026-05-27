"""
Pipeline orchestrator: fetch → ingest → transform → upload.

Runs steps in sequence, sharing the Supabase client across ingest and
transform to avoid duplicate connections.

Usage:
    python run.py                              # full pipeline
    python run.py --steps fetch,ingest         # specific steps
    python run.py --skip upload                # all except upload
    python run.py --full                       # force full ingest refresh
    python run.py --clear                      # clear Dune tables before upload
    python run.py --dry-run                    # preview without side effects
"""

import argparse
import asyncio
import sys
import time

ALL_STEPS = ["fetch", "ingest", "transform", "upload"]


def main():
    parser = argparse.ArgumentParser(description="Run the defi-analyst pipeline")
    parser.add_argument("--steps", help="Comma-separated steps to run (default: all)")
    parser.add_argument("--skip", help="Comma-separated steps to skip")
    parser.add_argument("--full", action="store_true", help="Force full ingest refresh")
    parser.add_argument("--no-clear", action="store_true", help="Skip clearing Dune tables before upload (append mode)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without side effects")
    args = parser.parse_args()

    if args.steps:
        steps = [s.strip() for s in args.steps.split(",")]
        invalid = [s for s in steps if s not in ALL_STEPS]
        if invalid:
            print(f"unknown steps: {', '.join(invalid)}")
            print(f"available: {', '.join(ALL_STEPS)}")
            sys.exit(1)
    elif args.skip:
        skip = {s.strip() for s in args.skip.split(",")}
        steps = [s for s in ALL_STEPS if s not in skip]
    else:
        steps = list(ALL_STEPS)

    print(f"pipeline: {' → '.join(steps)}")
    if args.dry_run:
        print("[DRY RUN]")
    print()

    t_total = time.time()
    supabase_client = None

    for step in steps:
        t0 = time.time()
        print(f"{'=' * 50}")
        print(f"  {step.upper()}")
        print(f"{'=' * 50}\n")

        if step == "fetch":
            from pipeline.fetch import run as fetch_run
            asyncio.run(fetch_run())

        elif step == "ingest":
            from pipeline.ingest import run as ingest_run
            if supabase_client is None and not args.dry_run:
                from pipeline.db import get_client
                supabase_client = get_client()
            ingest_run(client=supabase_client, full=args.full, dry_run=args.dry_run)

        elif step == "transform":
            from pipeline.transform import run as transform_run
            if supabase_client is None:
                from pipeline.db import get_client
                supabase_client = get_client()
            transform_run(client=supabase_client)

        elif step == "upload":
            from pipeline.upload import run as upload_run
            upload_run(clear=not args.no_clear, dry_run=args.dry_run)

        elapsed = time.time() - t0
        print(f"  [{step} completed in {elapsed:.1f}s]\n")

    total = time.time() - t_total
    print(f"pipeline complete ({total:.1f}s total)")


if __name__ == "__main__":
    main()
