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


def _flagged_statement():
    from fss.reconcile import FieldProvenance, ReconciledRow, ReconciledStatement

    def row(label: str, readings: dict[str, str]):
        return ReconciledRow(
            label=label,
            section="",
            printed=[None],
            values=[None],
            dash=[False],
            scale=Decimal(1),
            provenance=[FieldProvenance(label, "", 0, readings, None, "flagged")],
        )

    rows = [
        row("Common stock", {"R1": "944", "R2": "830"}),
        row("Deferred revenue", {"R1": "50", "R2": "61"}),
    ]
    return ReconciledStatement("balance_sheet", [1], 1, rows, [], {})


def test_artifact_adjudication_replays_only_reader_matching_values():
    from fss.untagged import _apply_artifact_adjudications

    statement = _flagged_statement()
    entries = [
        {"label": "Common stock", "column": 0, "value": "944"},  # matches R1
        {"label": "Deferred revenue", "column": 0, "value": "99"},  # nobody read 99
    ]
    resolved = _apply_artifact_adjudications(statement, entries)
    assert resolved == 1
    assert statement.rows[0].provenance[0].rule == "artifact_adjudicated"
    assert statement.rows[0].printed[0] == Decimal(944)
    # the drifted cell stays flagged: the artifact cannot inject numbers
    assert statement.rows[1].provenance[0].rule == "flagged"
    assert statement.rows[1].printed[0] is None


def _build_pdf(objects: list[bytes]) -> bytes:
    header = b"%PDF-1.4\n"
    body = b""
    offsets = []
    for obj in objects:
        offsets.append(len(header) + len(body))
        body += obj
    xref_pos = len(header) + len(body)
    xref = b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        xref += b"%010d 00000 n \n" % offset
    trailer = b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (
        len(objects) + 1,
        xref_pos,
    )
    return header + body + xref + trailer


_STATEMENT_LINES = [
    b"CONSOLIDATED BALANCE SHEET",
    b"(in millions) 2024 2023",
    b"Cash and cash equivalents 100 90",
    b"Accounts receivable 50 45",
    b"Inventories 30 25",
    b"Property and equipment 200 190",
    b"Goodwill 80 80",
    b"Other assets 40 35",
    b"Total assets 500 465",
    b"Accounts payable 60 55",
    b"Long-term debt 140 150",
    b"Total liabilities and stockholders equity 500 465",
]


def _page_pdf(kind: str) -> bytes:
    """A one-page PDF: 'authored' text, bare 'scan', or 'ocr' overlay."""
    image_draw = b"q 612 0 0 792 0 0 cm /Im1 Do Q\n"
    render = b"3 Tr " if kind == "ocr" else b""
    text = b""
    for line_no, line in enumerate(_STATEMENT_LINES):
        y = 720 - 20 * line_no
        text += b"BT /F1 12 Tf %s72 %d Td (%s) Tj ET\n" % (render, y, line)
    content = {"authored": text, "scan": image_draw, "ocr": image_draw + text}[kind]
    return _build_pdf(
        [
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> /XObject << /Im1 5 0 R >> >> "
            b"/Contents 6 0 R >> endobj\n",
            b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
            b"5 0 obj << /Type /XObject /Subtype /Image /Width 1 /Height 1 "
            b"/ColorSpace /DeviceGray /BitsPerComponent 8 /Length 1 >> "
            b"stream\n\xee\nendstream endobj\n",
            b"6 0 obj << /Length %d >> stream\n%s\nendstream endobj\n"
            % (len(content), content),
        ]
    )


def test_authored_text_gate_classifies_page_provenance():
    import io

    import pdfplumber

    from fss.pdfread.locate import authored_text_issues

    with pdfplumber.open(io.BytesIO(_page_pdf("authored"))) as pdf:
        assert authored_text_issues(pdf.pages[0]) == []
    with pdfplumber.open(io.BytesIO(_page_pdf("scan"))) as pdf:
        issues = authored_text_issues(pdf.pages[0])
        assert issues and "scanned" in issues[0]
    with pdfplumber.open(io.BytesIO(_page_pdf("ocr"))) as pdf:
        # the trap: extract_text() sees a full statement, yet the page is
        # a raster with an invisible OCR overlay
        assert (pdf.pages[0].extract_text() or "").count("Total assets") == 1
        issues = authored_text_issues(pdf.pages[0])
        assert issues and "OCR" in issues[0]


def test_seeded_ocr_statement_page_triggers_abstention(tmp_path, monkeypatch):
    """The battery requirement: an OCR'd statement page inside the sweep
    must abstain with the scope error, not extract silently."""
    import fss.untagged as untagged_module

    monkeypatch.setattr(untagged_module, "UNTAGGED_DIR", tmp_path / "out")
    monkeypatch.setattr(untagged_module.llm_module, "default_client", lambda: None)
    pdf_path = tmp_path / "seeded_ocr_filing.pdf"
    pdf_path.write_bytes(_page_pdf("ocr"))
    outcome = untagged_module.analyze_pdf(pdf_path)
    record = outcome["statements"]["balance_sheet"]
    assert "not born-digital" in record.get("error", "")
    assert "OCR" in record["error"]
    assert outcome["simulation"]["status"] == "skipped"


def test_artifact_overlay_maps_by_canonical_and_condensed_label():
    from fss.untagged import _artifact_overlay

    overlay = _artifact_overlay(
        [
            {
                "label": "Notes and loans payable 6",
                "concept": "us-gaap:NotesPayable",
                "balance": "credit",
                "period_type": "instant",
            }
        ]
    )
    from fss.untagged import _condensed

    key = _condensed("Notes and loans payable 6")
    assert overlay[key].concept == "us-gaap:NotesPayable"
