"""The declared standard scopes the mapping ladder: wrong-standard lexical
and carried hits fall down the ladder, the signed artifact overlay replays
untouched, the LLM shortlist offers one standard's concepts, and a
document declaring an unsupported framework is refused loudly end to end."""
import json
from types import SimpleNamespace

from test_hard_docs import _STATEMENT_LINES, _build_pdf

from fss.pdfread.llm_assist import LLMAudit
from fss.reconcile import canon_label
from fss.untagged import ConceptInfo, _artifact_overlay, map_rows


def _reconciled(*rows):
    return SimpleNamespace(
        rows=[SimpleNamespace(label=label, section=section) for label, section in rows]
    )


def _info(concept, balance="debit"):
    return ConceptInfo(concept, balance, "instant", True)


def test_wrong_standard_lexical_hit_falls_through_to_scoped_tier():
    lexicon = {
        canon_label("Trade receivables"): _info(
            "ifrs-full:TradeAndOtherCurrentReceivables"
        )
    }
    tier = {canon_label("Trade receivables"): _info("us-gaap:ReceivablesNetCurrent")}
    concepts, stats, sources = map_rows(
        "balance_sheet",
        _reconciled(("Trade receivables", "assets")),
        lexicon,
        {},
        None,
        None,
        taxonomy=tier,
        standard="us-gaap",
    )
    assert concepts[0].concept == "us-gaap:ReceivablesNetCurrent"
    assert sources == {0: "taxonomy"}
    assert stats["lexical"] == 0


def test_without_declared_standard_the_ladder_is_unchanged():
    lexicon = {
        canon_label("Trade receivables"): _info(
            "ifrs-full:TradeAndOtherCurrentReceivables"
        )
    }
    concepts, _, sources = map_rows(
        "balance_sheet",
        _reconciled(("Trade receivables", "assets")),
        lexicon,
        {},
        None,
        None,
    )
    assert concepts[0].concept == "ifrs-full:TradeAndOtherCurrentReceivables"
    assert sources == {0: "lexical"}


def test_carried_wrong_standard_choice_is_vetoed():
    overlay = _artifact_overlay(
        [
            {
                "label": "Trade receivables",
                "concept": "ifrs-full:TradeAndOtherCurrentReceivables",
                "balance": "debit",
                "period_type": "instant",
            }
        ]
    )
    concepts, stats, _ = map_rows(
        "balance_sheet",
        _reconciled(("Trade receivables", "assets")),
        {},
        {},
        None,
        None,
        overlay=overlay,
        overlay_source="carried",
        standard="us-gaap",
    )
    assert concepts == {}
    assert stats["unmapped"] == 1


def test_signed_artifact_overlay_replays_untouched():
    overlay = _artifact_overlay(
        [
            {
                "label": "Trade receivables",
                "concept": "ifrs-full:TradeAndOtherCurrentReceivables",
                "balance": "debit",
                "period_type": "instant",
            }
        ]
    )
    concepts, _, sources = map_rows(
        "balance_sheet",
        _reconciled(("Trade receivables", "assets")),
        {},
        {},
        None,
        None,
        overlay=overlay,
        overlay_source="artifact",
        standard="us-gaap",
    )
    assert concepts[0].concept == "ifrs-full:TradeAndOtherCurrentReceivables"
    assert sources == {0: "artifact"}


class _AbstainingClient:
    def __init__(self):
        self.prompts: list[str] = []

    def ask_json(self, message, prompt, parameters, reasoning):
        self.prompts.append(prompt)
        return {"concept": None}


def test_llm_shortlist_is_scoped_to_the_declared_standard():
    tokens = {
        "us-gaap:InterestExpenseAlpha": {"interest", "expense"},
        "ifrs-full:InterestExpenseBeta": {"interest", "expense"},
    }
    client = _AbstainingClient()
    map_rows(
        "income_statement",
        _reconciled(("Interest expense", "operating expenses")),
        {},
        tokens,
        client,
        LLMAudit(),
        standard="us-gaap",
    )
    assert client.prompts, "the model should have been consulted"
    assert "us-gaap:InterestExpenseAlpha" in client.prompts[0]
    assert "ifrs-full:InterestExpenseBeta" not in client.prompts[0]


def test_llm_shortlist_is_unscoped_without_a_declaration():
    tokens = {
        "us-gaap:InterestExpenseAlpha": {"interest", "expense"},
        "ifrs-full:InterestExpenseBeta": {"interest", "expense"},
    }
    client = _AbstainingClient()
    map_rows(
        "income_statement",
        _reconciled(("Interest expense", "operating expenses")),
        {},
        tokens,
        client,
        LLMAudit(),
    )
    assert "us-gaap:InterestExpenseAlpha" in client.prompts[0]
    assert "ifrs-full:InterestExpenseBeta" in client.prompts[0]


def _text_page_pdf(lines: list[bytes]) -> bytes:
    text = b"".join(
        b"BT /F1 12 Tf 72 %d Td (%s) Tj ET\n" % (740 - 20 * index, line)
        for index, line in enumerate(lines)
    )
    return _build_pdf(
        [
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
            b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
            b"5 0 obj << /Length %d >> stream\n%s\nendstream endobj\n"
            % (len(text), text),
        ]
    )


def test_unsupported_framework_document_is_refused(tmp_path, monkeypatch):
    """A report declaring a framework outside us-gaap/ifrs must refuse
    loudly at build time: statements error, simulation refused, and no
    mapping artifact is written."""
    import fss.untagged as untagged_module

    monkeypatch.setattr(untagged_module, "UNTAGGED_DIR", tmp_path / "out")
    monkeypatch.setattr(untagged_module, "ARTIFACTS_DIR", tmp_path / "artifacts")
    monkeypatch.setattr(untagged_module.llm_module, "default_client", lambda: None)
    pdf_path = tmp_path / "tokyo_industries_2025.pdf"
    pdf_path.write_bytes(
        _text_page_pdf(
            [
                b"ANNUAL REPORT",
                b"The consolidated financial statements have been prepared in",
                b"accordance with accounting principles generally accepted in Japan.",
            ]
        )
    )
    outcome = untagged_module.analyze_pdf(pdf_path, mode="onboard")
    assert outcome["simulation"]["status"] == "refused"
    error = outcome["statements"]["balance_sheet"]["error"]
    assert "unsupported reporting standard" in error
    assert "Japanese GAAP" in error
    assert "--standard" in error  # the reviewed override is named
    assert not (tmp_path / "artifacts").exists()
    assert outcome["standard"]["source"] == "unsupported"


def test_detected_us_gaap_document_records_standard_in_artifact(tmp_path, monkeypatch):
    """The declaration is read from the document itself, recorded in the
    outcome and the mapping artifact, and the pipeline proceeds."""
    import fss.untagged as untagged_module

    monkeypatch.setattr(untagged_module, "UNTAGGED_DIR", tmp_path / "out")
    monkeypatch.setattr(untagged_module, "ARTIFACTS_DIR", tmp_path / "artifacts")
    monkeypatch.setattr(untagged_module.llm_module, "default_client", lambda: None)
    opinion = [
        b"in conformity with accounting principles generally accepted",
        b"in the United States of America",
    ]
    pdf_path = tmp_path / "acme_2025.pdf"
    pdf_path.write_bytes(_text_page_pdf(list(_STATEMENT_LINES) + opinion))
    outcome = untagged_module.analyze_pdf(pdf_path, mode="onboard")
    assert outcome["standard"]["value"] == "us-gaap"
    assert outcome["standard"]["source"] == "detected"
    assert outcome["standard"]["evidence"]
    assert "error" not in outcome["statements"]["balance_sheet"]
    artifact = json.loads(
        (tmp_path / "artifacts" / "acme_2025.json").read_text(encoding="utf-8")
    )
    assert artifact["standard"] == "us-gaap"
    assert artifact["standard_source"] == "detected"
    assert artifact["standard_evidence"]


def test_operator_declaration_wins_and_the_conflict_is_recorded(tmp_path, monkeypatch):
    import fss.untagged as untagged_module

    monkeypatch.setattr(untagged_module, "UNTAGGED_DIR", tmp_path / "out")
    monkeypatch.setattr(untagged_module, "ARTIFACTS_DIR", tmp_path / "artifacts")
    monkeypatch.setattr(untagged_module.llm_module, "default_client", lambda: None)
    opinion = [
        b"in conformity with accounting principles generally accepted",
        b"in the United States of America",
    ]
    pdf_path = tmp_path / "acme_2025.pdf"
    pdf_path.write_bytes(_text_page_pdf(list(_STATEMENT_LINES) + opinion))
    outcome = untagged_module.analyze_pdf(
        pdf_path, mode="onboard", declared_standard="ifrs"
    )
    assert outcome["standard"]["value"] == "ifrs"
    assert outcome["standard"]["source"] == "operator"
    assert any("overrides" in item for item in outcome["standard"]["evidence"])
