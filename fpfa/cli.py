#!/usr/bin/env python3
import argparse
import json
import logging
from .pipeline import run_pipeline
from .db.schema import migrate_quotes_to_json
from .config import load_config
from .scrapers import foreign_affairs as fa
from .scrapers import foreign_policy as fp
from .summarizers.gemini import GeminiSummaryGenerator
from .summarizers.stub import StubSummaryGenerator


def _setup_logging(args):
    if getattr(args, "debug", False):
        level = logging.DEBUG
    elif getattr(args, "verbose", False):
        level = logging.INFO
    elif getattr(args, "log_level", None):
        level = getattr(logging, str(args.log_level).upper(), logging.INFO)
    else:
        level = logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def cmd_crawl(args):
    _setup_logging(args)
    src = args.source.lower()
    if src in ("fa", "foreign_affairs"):
        urls = fa.list_urls(limit=args.limit)
    elif src in ("fp", "foreign_policy"):
        urls = fp.list_urls(limit=args.limit)
    else:
        print(f"Unknown source: {args.source}")
        return 1
    print(json.dumps(urls, indent=2))
    return 0


def cmd_run(args):
    _setup_logging(args)
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    summarizer = StubSummaryGenerator() if (args.dry_run or args.stub) else GeminiSummaryGenerator()
    # If user requested real run but no API key, fail fast with guidance
    if not (args.dry_run or args.stub) and isinstance(summarizer, GeminiSummaryGenerator) and not summarizer.available:
        import sys
        print(
            "Error: GEMINI_API_KEY not set. Set it, or run with --stub or --dry-run.",
            file=sys.stderr,
        )
        return 2
    inserted = run_pipeline(
        sources=sources,
        limit=args.limit,
        summarizer=summarizer,
        persist=not args.dry_run,
    )
    print(f"Inserted {inserted} articles.")
    return 0


def main():
    p = argparse.ArgumentParser(prog="fpfa", description="FP/FA pipeline CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_crawl = sub.add_parser("crawl", help="List latest URLs for a source")
    p_crawl.add_argument("source", help="Source key: fa|fp")
    p_crawl.add_argument("--limit", type=int, default=5)
    p_crawl.add_argument("-v", "--verbose", action="store_true", help="Enable INFO logs")
    p_crawl.add_argument("--debug", action="store_true", help="Enable DEBUG logs")
    p_crawl.add_argument("--log-level", help="Explicit logging level (INFO, DEBUG, WARNING)")
    p_crawl.set_defaults(func=cmd_crawl)

    p_run = sub.add_parser("run", help="Run pipeline for sources")
    p_run.add_argument("--sources", default="fa,fp", help="Comma-separated sources (fa,fp)")
    p_run.add_argument("--limit", type=int, default=3)
    p_run.add_argument("--dry-run", action="store_true", help="Do not write to DB and use stub summarizer")
    p_run.add_argument("--stub", action="store_true", help="Use stub summarizer but persist to DB")
    p_run.add_argument("-v", "--verbose", action="store_true", help="Enable INFO logs")
    p_run.add_argument("--debug", action="store_true", help="Enable DEBUG logs")
    p_run.add_argument("--log-level", help="Explicit logging level (INFO, DEBUG, WARNING)")
    p_run.set_defaults(func=cmd_run)

    p_mig = sub.add_parser("migrate", help="Run migrations")
    p_mig.add_argument("what", choices=["quotes-json"], help="Migration task")
    def _cmd_migrate(args):
        if args.what == "quotes-json":
            updated = migrate_quotes_to_json(load_config().db_path)
            print(f"Updated {updated} rows with quotes_json")
            return 0
        print("Unknown migration")
        return 1
    p_mig.set_defaults(func=_cmd_migrate)

    args = p.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
