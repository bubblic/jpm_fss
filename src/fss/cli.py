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
    untagged = sub.add_parser(
        "untagged", help="untagged-PDF sweep (annual report PDFs, no XBRL)"
    )
    untagged.add_argument("paths", nargs="*", help="PDF files or folders")
    untagged.add_argument(
        "--merge", action="store_true", help="regenerate the sweep summary only"
    )
    onboard = sub.add_parser(
        "onboard",
        help="BUILD time: ingest with LLM assist and emit a reviewable mapping artifact",
    )
    onboard.add_argument("paths", nargs="*", help="PDF files or folders")
    onboard.add_argument(
        "--rebuild",
        action="store_true",
        help="assemble artifacts from committed build products (no LLM calls)",
    )
    runtime = sub.add_parser(
        "runtime",
        help="RUN time: deterministic replay from the signed mapping artifact; no model access",
    )
    runtime.add_argument("paths", nargs="*", help="PDF files or folders")
    runtime.add_argument(
        "--merge", action="store_true", help="regenerate the sweep summary only"
    )
    sub.add_parser("llm-check", help="verify the Azure LLM endpoint round-trips")
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
    if args.command in ("untagged", "onboard", "runtime"):
        import sys

        from fss import untagged as untagged_module

        flags = []
        if getattr(args, "merge", False):
            flags.append("--merge")
        if getattr(args, "rebuild", False):
            flags.append("--rebuild")
        sys.argv = [args.command, *flags, *args.paths]
        mode = {"untagged": "explore", "onboard": "onboard", "runtime": "runtime"}
        untagged_module.main(mode=mode[args.command])
        return 0
    if args.command == "llm-check":
        from fss import llm

        client = llm.default_client()
        if client is None:
            print("AZURE_DEEPSEEK_ENDPOINT is not set (checked env and .env)")
            return 1
        response = client.ask_json(
            message="gen-ai-response",
            prompt='Health check. Return ONLY JSON: {"ok": true}',
            parameters={},
            reasoning=False,
        )
        print(f"endpoint round-trip response: {response}")
        return 0 if response.get("ok") else 1
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
