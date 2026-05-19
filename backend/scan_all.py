#!/usr/bin/env python3
"""
Orchestrator: scan all MT5 instances.

Usage:
    python scan_all.py
    python scan_all.py --once
    python scan_all.py --instance instance1
    python scan_all.py --dry-run
"""

import argparse
import sys
import time
import logging

from config import Config
from logger import setup_logging
from scan_to_supabase import scan_instance

logger = logging.getLogger("mt5_sync.orch")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MT5 Supabase sync")
    p.add_argument("--once", action="store_true", help="Single scan then exit")
    p.add_argument("--instance", "-i", type=str, default="", help="Scan only this instance")
    p.add_argument("--dry-run", action="store_true", help="Simulate only")
    p.add_argument("--interval", type=int, default=0, help="Override scan interval (s)")
    return p.parse_args()


def run_scan(config: Config, instance_filter: str = "") -> int:
    instances = config.mt5_instances
    if instance_filter:
        inst = config.instance_by_name(instance_filter)
        instances = [inst] if inst else []
        if not instances:
            logger.error("Instance not found: %s", instance_filter)
            return 1

    errors = 0
    for inst in instances:
        result = scan_instance(config, inst)
        if result["status"] != "success":
            logger.error("FAIL %s: %s", inst.name, result.get("error", "?"))
            errors += 1
        else:
            logger.info("OK %s: %d upserted / %d found",
                        inst.name, result["trades_upserted"], result["trades_found"])
    return errors


def main() -> None:
    args = parse_args()
    config = Config.from_env()

    if args.dry_run:
        config.dry_run = True
    if args.interval:
        config.scan_interval_s = args.interval

    setup_logging(log_dir=config.log_dir, level=config.log_level)
    logger.info("Started (dry=%s, interval=%ds)", config.dry_run, config.scan_interval_s)

    if args.once:
        errors = run_scan(config, args.instance)
        sys.exit(1 if errors else 0)

    while True:
        start = time.time()
        errors = run_scan(config, args.instance)
        if errors:
            logger.warning("Cycle done with %d error(s)", errors)

        elapsed = time.time() - start
        sleep = max(10, config.scan_interval_s - int(elapsed))
        logger.info("Sleep %ds...", sleep)
        time.sleep(sleep)


if __name__ == "__main__":
    main()
