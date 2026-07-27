#!/usr/bin/env python
"""Generate proposal/fig_apple_overlay.tex: Apple's full three-statement overlay.

Draws every face line of Apple's balance sheet, income statement, and cash
flow statement (the validation build's extraction artifacts under
data/extracted/), each line carrying its economic role from the behavior
layer and the law of motion the engine applies to it, with the
cross-statement flows (working capital, debt schedule, capital pool, equity
flows, securities and the liquidity sweep, the cash tie) drawn as colored
trunks between the panels. The picture is laid out landscape; the proposal
rotates it onto its own page. Long labels wrap to a second line (rows have
variable heights); a label is clipped only past two lines.

Nothing here is hand-typed: rows, order, kinds, sections, and dimensions
come from the extracted statements; roles come from the production cascade
(fss.engine.roles.classify_statement); working-capital bindings come from
the production binder (fss.engine.project.Projector._bind_wc_row); the law
chips mirror the dispatch in fss.engine.project.Projector.project (kept in
sync by hand with that function, which the acceptance battery gates).

Regenerate (PowerShell, from the repo root):
    $env:PYTHONPATH = "src"
    python scripts/gen_apple_overlay_figure.py

The output file is committed; do not hand-edit it.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fss.engine import roles as R  # noqa: E402
from fss.engine.project import Projector, _row_key  # noqa: E402
from fss.engine.roles import classify_statement  # noqa: E402
from fss.statements import StructuredStatement  # noqa: E402

OUT = ROOT / "proposal" / "fig_apple_overlay.tex"

# ---- layout constants (cm), landscape ----
ROW_GAP = 0.045  # vertical gap between row boxes
ROW_H1 = 0.26  # single-line row box height
ROW_H2 = 0.56  # two-line row box height
HEAD_H1 = 0.18  # section-header heights (no box)
HEAD_H2 = 0.46
COL_W = 7.0  # width of one statement panel
X_IS = 0.0
X_CF = 7.65
X_BS = 15.55
ART_X = 7.25  # articulation trunk x (income statement -> cash flow gutter)

# trunk x positions in the cash-flow -> balance-sheet gutter, per flow family
TRUNK_X = {
    "wc": 14.73,
    "debt": 14.86,
    "capital": 14.99,
    "equity": 15.12,
    "securities": 15.25,
    "cash": 15.38,
}
TRUNK_COLOR = {
    "wc": "fgreen",
    "debt": "navytwo",
    "capital": "capbrown",
    "equity": "eqplum",
    "securities": "secteal",
    "cash": "gold",
}

# approximate rendered widths (cm per character), used to fit label + chip
CHAR_W = 0.100  # \tiny helvetica text (conservative, for wrap prediction)
ROLE_W = 0.076  # 4pt typewriter role names
MATH_W = 0.105  # law chips, after stripping TeX markup
SEP_W = 0.55  # reserved separation between label block and chip, plus insets
MIN_LABEL = 16

# ---- law chips: the engine dispatch of Projector.project, per role ----
IS_LAW = {
    R.REVENUE: r"$\times(1{+}g_{\mathrm{rev}})$",
    R.COGS: r"$\times(1{+}g_{\mathrm{rev}})(1{+}\Delta m)$",
    R.OPEX_RND: r"$\times(1{+}g_{\mathrm{opex}})$",
    R.OPEX_SELLING: r"$\times(1{+}g_{\mathrm{opex}})$",
    R.OPEX_ADMIN: r"$\times(1{+}g_{\mathrm{opex}})$",
    R.OPEX_OTHER: "held",
    R.RESTRUCTURING: r"$\times$ cycle factor",
    R.INTEREST_INCOME: r"$(y{+}\Delta y_A)\cdot$(cash+sec)",
    R.INTEREST_EXPENSE: r"$(c{+}\Delta c_D)\cdot$debt",
    R.OTHER_INCOME: r"$+\Delta y_A$(cash+sec)$-\Delta c_D$debt",
    R.TAX: r"ETR $\times$ pretax (own arcs)",
    R.EPS: r"parent NI $\div$ shares",
    R.SHARE_COUNT: r"trend $\times$ buyback",
    R.GROSS_PROFIT_ROW: "from rev/cost leaves",
}
CF_LAW = {
    R.CF_NI: "= projected NI",
    R.CF_DA: r"$\times(1{+}g_{\mathrm{rev}})$",
    R.CF_SBC: r"$\times(1{+}g_{\mathrm{rev}})$",
    R.CF_WC: r"$= -\Delta$ stock",
    R.CF_DEFERRED_TAX: "0 (no accrual gap)",
    R.CF_OTHER_NONCASH: "0",
    R.CF_CAPEX: r"$\times(1{+}g_{\mathrm{rev}})$",
    R.CF_INVEST_PURCHASE: "held + sweep",
    R.CF_INVEST_MATURITY: "held (sweep draws)",
    R.CF_INVEST_SALE: "held",
    R.CF_DIVIDENDS: r"$\times(1{+}g_{\mathrm{div}})$",
    R.CF_BUYBACK: r"$\times\,b$",
    R.CF_SBC_TAX_WITHHOLD: r"$\times(1{+}g_{\mathrm{rev}})$",
    R.CF_DEBT_ISSUE: "held schedule",
    R.CF_DEBT_REPAY: "held schedule",
    R.CF_CP_NET: "held schedule",
    R.CF_LEASE_PAYMENT: "held schedule",
    R.CF_STOCK_ISSUE: "held",
    R.CF_FX: "0",
    R.CF_TAX_PAID: "= projected tax",
    R.CF_TAX_ADDBACK: "= projected tax",
    R.CF_INTEREST_RECEIVED: "= finance income",
    R.CF_INTEREST_PAID: "= finance costs",
    R.CF_DIVIDENDS_RECEIVED: "held",
    R.CF_SUPPLEMENTAL: "held",
    R.CF_CASH_BEGIN: "= base cash",
    R.CF_CASH_END: r"= begin $+\,\Delta$",
    R.CF_NET_CHANGE: r"$\Sigma$ (derived)",
    R.CF_ACTIVITY_TOTAL: r"$\Sigma$ (derived)",
}
BS_LAW_FIXED = {
    R.CASH: r"$= +$ net change (CF)",
    R.SECURITIES: "+ net purchases (sweep)",
    R.PPE: r"+ capex $-$ D\&A",
    R.LEASE_ROU: r"+ leases $-$ D\&A",
    R.DEBT: r"+ held schedule $\Delta$",
    R.COMMERCIAL_PAPER: r"+ held schedule $\Delta$",
    R.RETAINED_EARNINGS: r"+ NI $-$ div $-$ buyback",
    R.COMMON_STOCK_APIC: "+ SBC credited",
    R.TREASURY: "+ repurchases",
    R.NCI_EQUITY: r"+ NCI income $-$ NCI div",
    R.COMMITMENTS: "(no amount)",
}
WC_TARGET_LAW = {
    R.INVENTORY: r"$\to\times(1{+}g)(1{+}\Delta m)$",
    R.AP: r"$\to\times(1{+}g)(1{+}\Delta m)$",
}
WC_DEFAULT_LAW = r"$\to\times(1{+}g_{\mathrm{rev}})$ target"

TEX_SPECIALS = {
    "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
    "_": r"\_", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}
ABSTRACT_SUFFIX = re.compile(r"\s*\[abstract\]\s*$", re.IGNORECASE)
TEX_MARKUP = re.compile(r"\\[a-zA-Z]+|[{}$]|\^|_")


def esc(text: str) -> str:
    text = text.replace("\\", "")
    return "".join(TEX_SPECIALS.get(ch, ch) for ch in text)


def chip_width(role: str, law: str) -> float:
    plain = TEX_MARKUP.sub("", law)
    return len(role) * ROLE_W + len(plain) * MATH_W


def layout_label(label: str, width_cm: float) -> tuple[str, int]:
    """Escape and wrap-predict a label for a block of width_cm; two lines at
    most, with a clip only past that."""
    per_line = max(MIN_LABEL, int(width_cm / CHAR_W))
    if len(label) <= per_line:
        return esc(label), 1
    cap = 2 * per_line - 2
    if len(label) <= cap:
        return esc(label), 2
    return esc(label[: cap - 1].rstrip()) + r"\,\ldots", 2


@dataclass
class Slot:
    y: float  # row center
    height: float
    label_tex: str
    label_width: float  # cm, text block width
    chip: str  # "" for section headers
    role: str
    kind: str  # "abstract" | "leaf" | "derived"
    member: bool


def load(kind: str) -> StructuredStatement:
    path = ROOT / "data" / "extracted" / f"apple_{kind}.json"
    return StructuredStatement.from_payload(json.loads(path.read_text(encoding="utf-8")))


def main() -> int:
    stmts = {k: load(k) for k in ("balance_sheet", "income_statement", "cash_flow")}
    projector = Projector("apple", stmts)
    roles = {k: classify_statement(s) for k, s in stmts.items()}

    # working-capital bindings, exactly as the engine binds them
    bs_roles = roles["balance_sheet"]
    wc_edges: list[tuple[tuple, tuple]] = []
    bound: set[tuple] = set()
    for row in stmts["cash_flow"].rows:
        if row.kind != "leaf" or roles["cash_flow"][_row_key(row)].role != R.CF_WC:
            continue
        targets = [k for k in projector._bind_wc_row(row, bs_roles) if k not in bound]
        bound.update(targets)
        for target in targets:
            wc_edges.append((_row_key(row), target))

    # ---- pre-pass: slot geometry per column (variable row heights) ----
    slots: dict[tuple[str, tuple], Slot] = {}
    col_bottom: dict[str, float] = {}
    for kind in ("income_statement", "cash_flow", "balance_sheet"):
        statement = stmts[kind]
        role_map = roles[kind]
        cursor = 0.0  # top edge of the next slot
        for row in statement.rows:
            clean = ABSTRACT_SUFFIX.sub("", row.label)
            if row.kind == "abstract":
                width = COL_W - 0.25
                tex, lines = layout_label(clean.lower(), width)
                height = HEAD_H1 if lines == 1 else HEAD_H2
                chip = ""
                role = ""
                member = False
            else:
                role = role_map[_row_key(row)].role
                chip = law_chip(kind, row, role, bound)
                member = bool(row.dims)
                width = COL_W - chip_width(role, chip) - SEP_W - (0.30 if member else 0.0)
                tex, lines = layout_label(clean, width)
                height = ROW_H1 if lines == 1 else ROW_H2
            y = cursor - height / 2
            slots[(kind, _row_key(row))] = Slot(
                y=y, height=height, label_tex=tex, label_width=width,
                chip=chip, role=role, kind=row.kind, member=member,
            )
            cursor = y - height / 2 - ROW_GAP
        col_bottom[kind] = cursor

    lines_out: list[str] = []
    emit = lines_out.append
    emit("% Generated by scripts/gen_apple_overlay_figure.py from the validation")
    emit("% build's extraction artifacts (data/extracted/apple_*.json).")
    emit("% Do not hand-edit; regenerate instead (see the script header).")
    emit(r"\definecolor{eqplum}{HTML}{8B3A62}")
    emit(r"\definecolor{secteal}{HTML}{0F6E6E}")
    emit(r"\definecolor{capbrown}{HTML}{7A5C00}")
    emit(r"\begin{tikzpicture}[x=1cm, y=1cm, every node/.style={inner sep=1.2pt}]")

    # ---- driver band: one strip across the top ----
    emit(r"\node[draw=navytwo, fill=callfill, rounded corners=2pt, anchor=north west, "
         r"text width=22.25cm, align=left, font=\tiny] at (%.2f, 1.32) "
         r"{\textbf{\scriptsize Scenario} $x=(\Delta g^{\mathrm{GDP}},\ \Delta\pi,\ \Delta r,\ z_c,\ z_d)$, "
         r"six scenarios, 500 Monte Carlo paths each "
         r"$\;\longrightarrow\;$ \textbf{\scriptsize driver draw} (Section 8): "
         r"$g_{\mathrm{rev}}$ revenue growth; $\Delta m$ COGS-ratio shift; "
         r"$g_{\mathrm{opex}}$ opex growth; $\Delta y_A,\ \Delta c_D$ rate shifts; "
         r"$g_{\mathrm{div}}$ dividend growth; $b$ buyback factor; noise "
         r"$\varepsilon_g, \varepsilon_m, \varepsilon_o$. The slate chip on each row "
         r"below names the behavior-layer role, then the law the engine applies to "
         r"that role.};" % X_IS)

    for title, x in (
        ("INCOME STATEMENT: drivers act here", X_IS),
        ("CASH FLOW: articulation and policy", X_CF),
        ("BALANCE SHEET: stocks move only through flows", X_BS),
    ):
        emit(r"\node[anchor=north west, font=\tiny\bfseries\color{navy}] at (%.2f, 0.52) {%s};"
             % (x, title))

    # ---- rows ----
    for kind, x in (("income_statement", X_IS), ("cash_flow", X_CF), ("balance_sheet", X_BS)):
        for row in stmts[kind].rows:
            slot = slots[(kind, _row_key(row))]
            if slot.kind == "abstract":
                emit(r"\node[anchor=west, font=\tiny\scshape\color{slate}, "
                     r"text width=%.2fcm, align=left] at (%.2f, %.2f) {%s};"
                     % (slot.label_width, x + 0.05, slot.y, slot.label_tex))
                continue
            border = "gold" if slot.member else ("navy" if slot.kind == "leaf" else "slate")
            dashing = ", dashed" if slot.kind == "derived" else ""
            emit(r"\node[draw=%s%s, line width=0.3pt, fill=white, rounded corners=1pt, "
                 r"anchor=west, minimum width=%.2fcm, minimum height=%.2fcm] at (%.2f, %.2f) {};"
                 % (border, dashing, COL_W, slot.height, x, slot.y))
            label = ("$\\cdot$ " if slot.member else "") + slot.label_tex
            emit(r"\node[anchor=west, font=\tiny, text width=%.2fcm, align=left] "
                 r"at (%.2f, %.2f) {%s};"
                 % (slot.label_width + (0.30 if slot.member else 0.0), x + 0.06, slot.y, label))
            emit(r"\node[anchor=east, font=\tiny\color{slate}] at (%.2f, %.2f) "
                 r"{{\fontsize{4}{4}\selectfont\ttfamily %s} %s};"
                 % (x + COL_W - 0.05, slot.y, esc(slot.role), slot.chip))

    # ---- edges ----
    def trunk_edge(family: str, y_from: float, y_to: float) -> None:
        tx = TRUNK_X[family]
        emit(r"\draw[-{Stealth[length=1.6mm]}, line width=0.55pt, color=%s, opacity=0.9] "
             r"(%.2f, %.2f) -- (%.2f, %.2f) -- (%.2f, %.2f) -- (%.2f, %.2f);"
             % (TRUNK_COLOR[family], X_CF + COL_W, y_from, tx, y_from, tx, y_to, X_BS, y_to))

    cf_roles = roles["cash_flow"]
    is_roles = roles["income_statement"]

    def cf_rows_with(wanted: set[str]) -> list:
        return [r for r in stmts["cash_flow"].rows
                if r.kind == "leaf" and cf_roles[_row_key(r)].role in wanted]

    def bs_rows_with(wanted: set[str]) -> list:
        return [r for r in stmts["balance_sheet"].rows
                if r.kind == "leaf" and bs_roles[_row_key(r)].role in wanted]

    def y_of(kind: str, key: tuple) -> float:
        return slots[(kind, key)].y

    for cf_key, bs_key in wc_edges:
        trunk_edge("wc", y_of("cash_flow", cf_key), y_of("balance_sheet", bs_key))
    for cf_row in cf_rows_with({R.CF_DEBT_ISSUE, R.CF_DEBT_REPAY, R.CF_CP_NET}):
        for bs_row in bs_rows_with({R.DEBT, R.COMMERCIAL_PAPER}):
            trunk_edge("debt", y_of("cash_flow", _row_key(cf_row)), y_of("balance_sheet", _row_key(bs_row)))
    for cf_row in cf_rows_with({R.CF_CAPEX, R.CF_DA, R.CF_LEASE_PAYMENT}):
        for bs_row in bs_rows_with({R.PPE, R.LEASE_ROU}):
            trunk_edge("capital", y_of("cash_flow", _row_key(cf_row)), y_of("balance_sheet", _row_key(bs_row)))
    re_rows = bs_rows_with({R.RETAINED_EARNINGS})
    apic_rows = bs_rows_with({R.COMMON_STOCK_APIC})
    if re_rows:
        re_y = y_of("balance_sheet", _row_key(re_rows[0]))
        for cf_row in cf_rows_with({R.CF_NI, R.CF_DIVIDENDS, R.CF_BUYBACK, R.CF_SBC_TAX_WITHHOLD}):
            trunk_edge("equity", y_of("cash_flow", _row_key(cf_row)), re_y)
    if apic_rows:
        apic_y = y_of("balance_sheet", _row_key(apic_rows[0]))
        for cf_row in cf_rows_with({R.CF_SBC, R.CF_STOCK_ISSUE}):
            trunk_edge("equity", y_of("cash_flow", _row_key(cf_row)), apic_y)
    for cf_row in cf_rows_with({R.CF_INVEST_PURCHASE, R.CF_INVEST_MATURITY, R.CF_INVEST_SALE}):
        for bs_row in bs_rows_with({R.SECURITIES}):
            trunk_edge("securities", y_of("cash_flow", _row_key(cf_row)), y_of("balance_sheet", _row_key(bs_row)))
    cash_bs = bs_rows_with({R.CASH})
    net_change_rows = [r for r in stmts["cash_flow"].rows
                       if cf_roles[_row_key(r)].role == R.CF_NET_CHANGE]
    if cash_bs and net_change_rows:
        trunk_edge("cash", y_of("cash_flow", _row_key(net_change_rows[0])),
                   y_of("balance_sheet", _row_key(cash_bs[0])))

    # articulation: income statement -> cash flow (dotted slate)
    def art_edge(y_from: float, y_to: float) -> None:
        emit(r"\draw[-{Stealth[length=1.6mm]}, line width=0.5pt, dotted, color=slate] "
             r"(%.2f, %.2f) -- (%.2f, %.2f) -- (%.2f, %.2f) -- (%.2f, %.2f);"
             % (X_IS + COL_W, y_from, ART_X, y_from, ART_X, y_to, X_CF, y_to))

    ni_is = [r for r in stmts["income_statement"].rows
             if r.kind == "derived" and r.concept.endswith("NetIncomeLoss") and not r.dims]
    for cf_row in cf_rows_with({R.CF_NI}):
        if ni_is:
            art_edge(y_of("income_statement", _row_key(ni_is[0])), y_of("cash_flow", _row_key(cf_row)))
    tax_is = [r for r in stmts["income_statement"].rows
              if r.kind == "leaf" and is_roles[_row_key(r)].role == R.TAX]
    for cf_row in cf_rows_with({R.CF_TAX_PAID, R.CF_TAX_ADDBACK}):
        if tax_is:
            art_edge(y_of("income_statement", _row_key(tax_is[0])), y_of("cash_flow", _row_key(cf_row)))

    # ---- legend, in the empty space under the income statement panel ----
    legend_top = col_bottom["income_statement"] - 0.35
    emit(r"\node[anchor=north west, font=\tiny\bfseries\color{navy}] at (%.2f, %.2f) {How to read};"
         % (X_IS, legend_top))
    emit(r"\node[anchor=north west, font=\tiny, text width=6.9cm, align=left] at (%.2f, %.2f) "
         r"{Solid navy box: stored leaf of $z$. Dashed slate box: derived row, recomputed "
         r"through Apple's own calculation arcs on decode. Gold box with $\cdot$: a "
         r"product/service member row (dimensional aggregation). Small-caps lines: the "
         r"filer's section headers. Right chip: \mbox{{\fontsize{4}{4}\selectfont\ttfamily role} law}, "
         r"the behavior layer's role and the engine's law for that line.};"
         % (X_IS, legend_top - 0.22))
    swatches = [
        ("wc", "working-capital stock moves"),
        ("capital", r"capital pool: capex, leases, D\&A"),
        ("debt", "debt at the held schedule"),
        ("equity", "equity flows: close, dividends, buyback, SBC"),
        ("securities", "securities net purchases and the sweep"),
        ("cash", "cash tie: net change into the cash stock"),
    ]
    y_sw = legend_top - 1.95
    for family, text in swatches:
        emit(r"\draw[line width=0.9pt, color=%s] (%.2f, %.2f) -- (%.2f, %.2f);"
             % (TRUNK_COLOR[family], X_IS, y_sw, X_IS + 0.42, y_sw))
        emit(r"\node[anchor=west, font=\tiny] at (%.2f, %.2f) {%s};" % (X_IS + 0.5, y_sw, text))
        y_sw -= 0.26
    emit(r"\draw[line width=0.5pt, dotted, color=slate] (%.2f, %.2f) -- (%.2f, %.2f);"
         % (X_IS, y_sw, X_IS + 0.42, y_sw))
    emit(r"\node[anchor=west, font=\tiny] at (%.2f, %.2f) "
         r"{articulation: a cash-flow row mirrors a projected income line};" % (X_IS + 0.5, y_sw))

    emit(r"\end{tikzpicture}")
    OUT.write_text("\n".join(lines_out) + "\n", encoding="utf-8", newline="\n")
    n_edges = sum(1 for line in lines_out if line.startswith(r"\draw[-{Stealth"))
    wrapped = sum(1 for s in slots.values() if s.height in (ROW_H2, HEAD_H2))
    print(f"wrote {OUT} ({len(lines_out)} lines, {n_edges} edges, "
          f"{sum(len(s.rows) for s in stmts.values())} rows, {wrapped} wrapped)")
    print("column bottoms:", {k: round(v, 2) for k, v in col_bottom.items()})
    return 0


def law_chip(kind: str, row, role: str, bound: set[tuple]) -> str:
    if kind == "income_statement":
        if row.kind == "derived":
            return r"$\Sigma$ (derived)"
        return IS_LAW.get(role, "held")
    if kind == "cash_flow":
        if row.kind == "derived":
            return CF_LAW.get(role, r"$\Sigma$ (derived)")
        return CF_LAW.get(role, "held")
    if row.kind == "derived":
        return r"$\Sigma$ (derived)"
    key = _row_key(row)
    if key in bound:
        return WC_TARGET_LAW.get(role, WC_DEFAULT_LAW)
    return BS_LAW_FIXED.get(role, "held")


if __name__ == "__main__":
    sys.exit(main())
