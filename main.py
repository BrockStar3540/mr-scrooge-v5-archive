#!/usr/bin/env python3
"""mr-scrooge-v5 -- entry point."""
import logging, os, sys
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s  %(message)s")

def main():
    dry_run = "--live" not in sys.argv
    if dry_run:
        logging.info("DRY RUN mode (pass --live to enable order execution)")

    # TODO: wire real feed + broker
    from core.engine import Engine
    engine = Engine(feed=None, broker=None, dry_run=dry_run)
    engine.run_forever()

if __name__ == "__main__":
    main()
