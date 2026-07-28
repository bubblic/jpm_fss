"""The reporting-standard declaration scan: deterministic phrase pack over
condensed text, abstention on ambiguity, other-framework declarations
marked for the pipeline's loud refusal, and the leashed LLM fallback's
verdict normalization."""
from fss.pdfread.llm_assist import LLMAudit, detect_standard
from fss.standards import declaration_candidates, detect, mismatches

OPINION_US = (
    "In our opinion, the financial statements present fairly, in all "
    "material respects, the financial position of the Company in "
    "conformity with accounting principles generally accepted in the "
    "United States of America."
)
BASIS_IFRS_IASB = (
    "The consolidated financial statements have been prepared in "
    "accordance with International Financial Reporting Standards (IFRS) "
    "as issued by the International Accounting Standards Board."
)


def test_us_gaap_opinion_wording_detected():
    detection = detect(["cover page", OPINION_US])
    assert detection.standard == "us-gaap"
    assert detection.evidence and detection.evidence[0].startswith("page 2:")
    assert not detection.ambiguous and not detection.unsupported


def test_ifrs_iasb_wording_detected():
    assert detect([BASIS_IFRS_IASB]).standard == "ifrs"


def test_spacing_noise_is_immaterial():
    fused = "preparedinacc ordancewithInterna tionalFinancial ReportingStandards"
    assert detect([fused]).standard == "ifrs"


def test_eu_uk_and_new_naming_variants_are_ifrs():
    assert (
        detect(["in accordance with IFRSs as adopted by the European Union"]).standard
        == "ifrs"
    )
    assert (
        detect(
            [
                "in accordance with international financial reporting "
                "standards as endorsed by the EU"
            ]
        ).standard
        == "ifrs"
    )
    assert (
        detect(
            ["in accordance with UK-adopted international accounting standards"]
        ).standard
        == "ifrs"
    )
    assert detect(["the group complies with IFRS Accounting Standards"]).standard == "ifrs"


def test_both_supported_standards_is_ambiguous_abstention():
    detection = detect([OPINION_US, BASIS_IFRS_IASB])
    assert detection.standard is None
    assert detection.ambiguous
    assert detection.evidence  # both sides stay on the record for review


def test_no_declaration_abstains_quietly():
    detection = detect(["management discussion", "risk factors"])
    assert detection.standard is None
    assert not detection.ambiguous
    assert not detection.unsupported


def test_hkfrs_alone_is_unsupported_not_ifrs():
    detection = detect(
        ["prepared in accordance with Hong Kong Financial Reporting Standards"]
    )
    assert detection.standard is None
    assert detection.unsupported and "Hong Kong" in detection.unsupported[0]


def test_dual_compliance_with_ifrs_still_resolves_ifrs():
    page = (
        "prepared in accordance with Hong Kong Financial Reporting "
        "Standards and comply with International Financial Reporting Standards"
    )
    detection = detect([page])
    assert detection.standard == "ifrs"
    assert detection.unsupported  # the HKFRS declaration stays on the record


def test_local_adoption_outside_eu_uk_demotes_the_accordance_wording():
    page = (
        "in accordance with International Financial Reporting Standards "
        "as adopted by the Republic of Korea"
    )
    detection = detect([page])
    assert detection.standard is None
    assert any("outside the EU" in item for item in detection.unsupported)


def test_korean_ifrs_full_name_is_unsupported():
    detection = detect(
        ["in accordance with Korean International Financial Reporting Standards"]
    )
    assert detection.standard is None
    assert detection.unsupported


def test_chinese_ifrs_declaration_detected():
    assert detect(["本財務報表乃根據國際財務報告準則編製"]).standard == "ifrs"


def test_chinese_hkfrs_declaration_is_unsupported():
    detection = detect(["本財務報表乃根據香港財務報告準則編製"])
    assert detection.standard is None
    assert detection.unsupported


def test_chinese_comparative_note_prose_is_not_a_declaration():
    # a reconciliation note explaining a treatment difference ("under
    # IFRS, such redeemable equity is classified as a financial
    # liability") must not read as a basis-of-preparation declaration
    detection = detect(["根據國際財務報告準則，該等可贖回股權一般分類為金融負債"])
    assert detection.standard is None
    assert not detection.unsupported


def test_chinese_listing_rule_boilerplate_is_not_a_declaration():
    # listing rules name the acceptable frameworks without declaring one
    detection = detect(["年度帳目須符合香港財務報告準則或國際財務報告準則"])
    assert detection.standard is None
    assert not detection.unsupported


def test_us_gaap_short_form_is_anchored_not_bare():
    assert detect(["in accordance with U.S. GAAP"]).standard == "us-gaap"
    # a bare mention in comparative prose does not anchor a declaration
    assert (
        detect(["differences between IFRS and US GAAP are discussed"]).standard is None
    )


def test_mismatches_is_scoped_to_standard_prefixes():
    assert mismatches("ifrs-full:Assets", "us-gaap")
    assert mismatches("us-gaap:Assets", "ifrs")
    assert not mismatches("us-gaap:Assets", "us-gaap")
    assert not mismatches("aapl:CloudRevenue", "us-gaap")  # extensions pass
    assert not mismatches("doc:TotalAssets_7", "ifrs")
    assert not mismatches("ifrs-full:Assets", None)


def test_declaration_candidates_pick_marker_pages_only():
    pages = [
        "chairman letter",
        "Report of Independent Registered Public Accounting Firm",
        "Notes: basis of preparation and summary of significant accounting policies",
        "another prose page",
    ]
    assert sorted(declaration_candidates(pages)) == [2, 3]


class _Client:
    def __init__(self, payload):
        self.payload = payload
        self.prompts: list[str] = []

    def ask_json(self, message, prompt, parameters, reasoning):
        self.prompts.append(prompt)
        return self.payload


def test_detect_standard_normalizes_the_llm_verdict():
    audit = LLMAudit()
    pages = {5: "auditor's report text"}
    assert detect_standard(_Client({"standard": "US_GAAP"}), audit, pages) == "us-gaap"
    assert detect_standard(_Client({"standard": "ifrs"}), audit, pages) == "ifrs"
    assert detect_standard(_Client({"standard": "other"}), audit, pages) == "other"
    assert detect_standard(_Client({"standard": "K-IFRS"}), audit, pages) is None
    assert detect_standard(_Client({"nonsense": True}), audit, pages) is None
    assert audit.calls == 5
    assert audit.decisions[-1]["kind"] == "detect_standard"
