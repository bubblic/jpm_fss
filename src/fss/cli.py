"""FSS command line: python -m fss <command>."""
from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="fss", description="Financial Statement Simulator pipeline"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch", help="acquire filings, warm DTS caches, render PDFs")
    sub.add_parser("extract", help="tag-path extraction of all statements")
    sub.add_parser("measure", help="PDF-only accuracy vs ground truth")
    accept = sub.add_parser("accept", help="full acceptance battery")
    accept.add_argument("--paths", type=int, default=None, help="Monte Carlo paths")
    accept.add_argument("--seed", type=int, default=None, help="random seed")
    accept.add_argument(
        "--company", action="append", default=None, help="run one company (repeatable)"
    )
    accept.add_argument(
        "--merge", action="store_true", help="merge per-company outcomes into the report"
    )
    args = parser.parse_args()

    if args.command == "fetch":
        from fss import edgar

        edgar.main()
        return 0
    if args.command == "extract":
        from fss import tagread

        tagread.main()
        return 0
    if args.command == "measure":
        from fss import measure

        measure.main()
        return 0
    if args.command == "accept":
        from fss import accept as accept_module
        from fss.config import MONTE_CARLO_PATHS, RANDOM_SEED

        ok = accept_module.main(
            paths=args.paths or MONTE_CARLO_PATHS,
            seed=args.seed or RANDOM_SEED,
            companies=args.company,
            merge_only=args.merge,
        )
        return 0 if ok else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
