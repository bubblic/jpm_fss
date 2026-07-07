"""Hard-document machinery: fusion repair, joint location, the footing
solver, and Chinese-language support."""
from __future__ import annotations

from decimal import Decimal

from fss.pdfread import zh
from fss.pdfread.locate import (
    PageInfo,
    _fusion_score,
    _title_hit,
    assign_statements,
)
from fss.pdfread.textnorm import detect_scale, parse_number
from fss.untagged import _solve_weights


def test_fusion_score_prefers_defused_text():
    fused = "Netincomeincludingnoncontrollinginterests 35,063 37,354"
    spaced = "Net income including noncontrolling interests 35,063 37,354"
    shattered = "N et in co me inc lud ing 35,063 37,354"
    assert _fusion_score(spaced) > _fusion_score(fused)
    assert _fusion_score(spaced) > _fusion_score(shattered)


def test_title_hit_covers_european_singular_and_ligatures():
    page = PageInfo(0, "", ["CONSOLIDATED CASH FLOW STATEMENT", "x 1 2"], 10)
    assert _title_hit(page, "cash_flow")
    ligature = PageInfo(0, "", ["Consolidated cash ﬂow statement"], 10)
    assert _title_hit(ligature, "cash_flow")
    chinese = PageInfo(0, "", ["合併資產負債表"], 10)
    assert _title_hit(chinese, "balance_sheet")


def _page(index: int, title: str | None, value_rows: int, anchor: str = "") -> PageInfo:
    lines = ([title] if title else ["Some heading"]) + [anchor, "alpha 1 2", "beta 3 4"]
    return PageInfo(index, "\n".join(lines), lines, value_rows)


def test_assignment_prefers_colocated_cluster_over_lone_decoy():
    pages = [_page(i, None, 0) for i in range(60)]
    # decoy summary table: income-statement title, very dense, far away
    pages[5] = _page(5, "Consolidated statements of income", 40, "per share")
    # the real, adjacent statements
    pages[48] = _page(48, "Consolidated statements of income", 24, "per share")
    pages[50] = _page(50, "Consolidated balance sheets", 30, "Total assets")
    pages[52] = _page(52, "Consolidated statements of cash flows", 28, "operating activities")
    assigned = assign_statements(pages)
    assert assigned["income_statement"] == [48]
    assert assigned["balance_sheet"] == [50]
    assert assigned["cash_flow"] == [52]


def test_solver_finds_bank_netting_weights():
    # Net revenues = Total revenues - Interest expense, two columns agree
    values = [
        {0: Decimal(100), 1: Decimal(30)},
        {0: Decimal(90), 1: Decimal(25)},
    ]
    totals = [Decimal(70), Decimal(65)]
    weights = _solve_weights(values, [0, 1], totals)
    assert weights == [Decimal(1), Decimal(-1)]


def test_solver_skips_rows_absorbed_by_a_mini_total():
    # Loans, Allowance (negative), Net loans, Premises; the grand total
    # includes Net loans and Premises only (the SVB pattern)
    values = [
        {0: Decimal(74250), 1: Decimal(-636), 2: Decimal(73614), 3: Decimal(394)},
        {0: Decimal(66000), 1: Decimal(-500), 2: Decimal(65500), 3: Decimal(400)},
    ]
    totals = [Decimal(74008), Decimal(65900)]
    weights = _solve_weights(values, [0, 1, 2, 3], totals)
    assert weights == [Decimal(0), Decimal(0), Decimal(1), Decimal(1)]


def test_solver_abstains_without_cross_column_agreement():
    # column 1 admits a numerological subset that column 2 refutes,
    # and no weighting satisfies both
    values = [
        {0: Decimal(40), 1: Decimal(30)},
        {0: Decimal(40), 1: Decimal(30)},
    ]
    totals = [Decimal(70), Decimal(20)]
    assert _solve_weights(values, [0, 1], totals) is None


def test_zh_lookup_maps_face_lines():
    assert zh.lookup("收入")[0] == "Revenues"
    assert zh.lookup("減：購置物業及設備")[0] == "PaymentsToAcquirePropertyPlantAndEquipment"
    assert zh.lookup("經營活動產生的現金流量淨額")[0] == "NetCashProvidedByUsedInOperatingActivities"
    assert zh.lookup("總資產")[0] == "Assets"
    assert zh.lookup("不存在的行項目") is None
    assert zh.has_cjk("收入") and not zh.has_cjk("Revenue")


def test_scale_detection_condensed_and_cjk():
    assert detect_scale("(millionsofdollars)").statement_scale == Decimal(10) ** 6
    assert detect_scale("人民幣百萬元").statement_scale == Decimal(10) ** 6
    assert detect_scale("以億元列示").statement_scale == Decimal(10) ** 8
    assert detect_scale("in millions, except per share").statement_scale == Decimal(10) ** 6


def test_parse_number_fullwidth():
    token = parse_number("（１，２３４）")
    assert token is not None and token.value == Decimal(-1234)
