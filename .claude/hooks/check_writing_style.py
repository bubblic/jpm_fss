#!/usr/bin/env python
"""PostToolUse(Edit|Write) hook: writing-style gate for the proposal LaTeX sources.

Wired in the committed .claude/settings.json so the gate travels with the
repository and fires deterministically on every assistant edit to a .tex file
under proposal/, instead of relying on the assistant remembering to re-read
WRITING-GUIDE.md. It does two things:

1. MECHANICAL: re-runs the WRITING-GUIDE.md section 4 scans on the edited file
   (em dashes, spaced '--' in prose, retired phrasings, draft references,
   frozen-file protection) and reports violations with line numbers.
2. JUDGMENT: injects the section 1/2/3/5 checklist so the assistant reviews the
   accumulated `git diff` of the document against the guide before moving on.
   A script cannot check first-principles ordering or claim-level consistency;
   the assistant can, and this hook makes that review non-optional.

Contract: reads the PostToolUse JSON on stdin; for governed files it prints
{"decision": "block", "reason": ...} (exit 0), which Claude Code feeds back to
the assistant; for everything else it exits 0 silently. It never blocks the
edit itself (the edit already happened) and it never modifies files.

Portability: stdlib only, any Python 3.9+; invoked as
`python "$CLAUDE_PROJECT_DIR/.claude/hooks/check_writing_style.py"` (Claude
Code runs hook commands via Git Bash on Windows, sh on POSIX, so the same
command string works everywhere). Fails open: any unexpected input exits 0.

KEEP IN SYNC with proposal/WRITING-GUIDE.md section 4: the dash patterns and
the retired-phrasings pattern below duplicate the guide's scans. When a claim
is corrected and a phrasing retires, update the guide's list, its scan
pattern, and RETIRED_PATTERN here, in the same edit.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GOVERNED_DIR = "proposal"
GUIDE_REL = "proposal/WRITING-GUIDE.md"

FULL_PROPOSAL = "Financial_Statement_Simulator_Proposal.tex"
DRAFT_V2 = "Financial_Statement_Simulator_Proposal_Draft_v2.tex"
FROZEN_V1 = "Financial_Statement_Simulator_Proposal_Draft.tex"

# --- Mechanical patterns, mirrored from WRITING-GUIDE.md section 4 -----------
# Dash rule: '---' or a Unicode em dash, on lines that are not pure comments.
EM_DASH = re.compile(r"---|—")
COMMENT_LINE = re.compile(r"^\s*%")
# Spaced '--' doing an em dash's job in prose; TikZ \draw path syntax is fine.
SPACED_DOUBLE_DASH = re.compile(r" -- ")
DRAW_LINE = re.compile(r"\\draw")
# Retired phrasings (full proposal only; Draft_v2 keeps its history by design).
RETIRED_PATTERN = re.compile(
    "one more gated reader|All processing is local|has a text layer"
    "|text-based|prior-year page locations|seed pages|common state space"
    "|standard-neutral state|economic state space|not by hope"
    "|not a sentiment|not aspirations|dressed as|companion disease"
    "|poisoned text",
    re.IGNORECASE,
)
# The full proposal stands alone: no reference to the draft, in any casing.
DRAFT_WORD = re.compile(r"draft", re.IGNORECASE)

MAX_REPORTED = 12
EXCERPT_LEN = 70


def scan_lines(lines: list[str], full_rules: bool) -> list[tuple[int, str, str]]:
    """Return (line_no, rule, excerpt) violations; full_rules adds the
    retired-phrasings and draft-reference scans that apply only to the full
    proposal."""
    hits: list[tuple[int, str, str]] = []
    for no, line in enumerate(lines, 1):
        excerpt = line.strip()[:EXCERPT_LEN]
        if EM_DASH.search(line) and not COMMENT_LINE.search(line):
            hits.append((no, "em dash ('---' or U+2014)", excerpt))
        if SPACED_DOUBLE_DASH.search(line) and not DRAW_LINE.search(line):
            hits.append((no, "spaced '--' in prose", excerpt))
        if full_rules:
            retired = RETIRED_PATTERN.search(line)
            if retired:
                hits.append((no, f"retired phrasing '{retired.group(0)}'", excerpt))
            elif DRAFT_WORD.search(line):
                hits.append((no, "references the draft ('draft')", excerpt))
    return hits


def judgment_checklist(rel_posix: str, is_full: bool, is_draft_v2: bool) -> list[str]:
    lines = [
        f"Now review the accumulated change, not just this edit: run `git diff -- {rel_posix}` "
        f"(for a new file, read it in full) and check every changed line against {GUIDE_REL}:",
        "- Section 1: every new term, symbol, or equation is introduced from first principles, "
        "in words, before it is used; derivations are inline or sketched in one line.",
        "- Section 2: claims stated straight (no grandstanding contrasts, no live metaphors), "
        "slippery distinctions named explicitly.",
        "- Section 3: every number traces to a committed pipeline artifact; never type a value "
        "or count from memory.",
    ]
    if is_full:
        lines.append(
            "- Section 5: if a substantive claim changed, update every summary surface that "
            "restates it (executive summary, success/evidence/robustness surfaces, captions, "
            "risk register, README.md, DEMO.md, docs/DESIGN.md), and add any retired phrasing "
            "to the guide's list, its scan pattern, and this hook's RETIRED_PATTERN."
        )
    if is_draft_v2:
        lines.append(
            "- Draft_v2 policy: corrections, not upgrades. Propagate corrections of claims "
            "since shown wrong; leave its deliberate history (its own dates, its softened "
            "language) in place. The retired-phrasings and draft-word scans do not apply here."
        )
    lines.append(
        "Fix violations now, before other work. Rebuild the PDF (pdflatex twice, from "
        "proposal/) before any commit that includes this file."
    )
    return lines


def build_reason(rel_posix: str, name: str, hits: list[tuple[int, str, str]]) -> str:
    role = {
        FULL_PROPOSAL: "the full proposal (owner of every claim; it stands alone)",
        DRAFT_V2: "the June discussion draft (corrections, not upgrades)",
    }.get(name, "a governed proposal document")
    parts = [f"Writing-style gate: you just edited {rel_posix}, {role}."]
    if hits:
        parts.append(
            f"WRITING-GUIDE.md section 4 scan FAILED ({len(hits)} violation(s)); "
            "fix these in the .tex now:"
        )
        for no, rule, excerpt in hits[:MAX_REPORTED]:
            parts.append(f"- line {no} [{rule}]: {excerpt}")
        if len(hits) > MAX_REPORTED:
            parts.append(f"- ... and {len(hits) - MAX_REPORTED} more.")
    else:
        parts.append("WRITING-GUIDE.md section 4 scans: clean.")
    parts.extend(judgment_checklist(rel_posix, name == FULL_PROPOSAL, name == DRAFT_V2))
    return "\n".join(parts)


def frozen_reason(rel_posix: str) -> str:
    return (
        f"Writing-style gate: you just edited {rel_posix}. WRITING-GUIDE.md says this "
        "file is FROZEN HISTORY (v1 of the draft): do not edit it. Unless the user "
        "explicitly asked for this exact change, restore it (git restore -- "
        f"{rel_posix}) and explain why. If the user did ask, confirm with them that "
        "the frozen draft is really the intended target before continuing."
    )


def relative_to_repo(path: Path) -> Path | None:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT)
    except ValueError:
        pass
    # Windows fallback: tolerate drive-letter or directory case mismatches.
    root = os.path.normcase(str(REPO_ROOT))
    cand = os.path.normcase(str(resolved))
    if cand.startswith(root + os.sep):
        return Path(os.path.relpath(str(resolved), str(REPO_ROOT)))
    return None


def emit(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))


def main() -> int:
    try:
        # utf-8-sig: tolerate a UTF-8 BOM (PowerShell pipes prepend one).
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8-sig", "replace"))
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0
    tool_input = payload.get("tool_input")
    file_path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not file_path:
        return 0

    rel = relative_to_repo(Path(file_path))
    if rel is None or len(rel.parts) < 2 or rel.parts[0] != GOVERNED_DIR:
        return 0
    if rel.suffix.lower() != ".tex":
        return 0
    rel_posix = rel.as_posix()

    if rel.name == FROZEN_V1:
        emit(frozen_reason(rel_posix))
        return 0

    target = REPO_ROOT / rel
    try:
        lines = target.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        lines = []
    hits = scan_lines(lines, full_rules=(rel.name == FULL_PROPOSAL))
    emit(build_reason(rel_posix, rel.name, hits))
    return 0


if __name__ == "__main__":
    sys.exit(main())
