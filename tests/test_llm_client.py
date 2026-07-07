"""The adopted LLM calling logic: offline-parseable parts."""
import json
from decimal import Decimal

from fss.llm import extract_json, extract_json_from_text, median_vote


def test_gateway_wrapped_response_unwraps():
    wrapped = json.dumps({"data": {"response": json.dumps({"pages": [3, 4]})}})
    assert extract_json(wrapped) == {"pages": [3, 4]}


def test_prose_with_embedded_json_extracts():
    wrapped = json.dumps(
        {"data": {"response": 'Sure! Here it is: {"value": 123} as requested.'}}
    )
    assert extract_json(wrapped) == {"value": 123}


def test_raw_response_fallback():
    wrapped = json.dumps({"data": {"response": "no json here at all"}})
    assert extract_json(wrapped) == {"raw_response": "no json here at all"}


def test_extract_json_from_text_rejects_non_objects():
    assert extract_json_from_text("[1, 2, 3]") is None


def test_median_vote_keeps_majority():
    voted = median_vote([Decimal(5), Decimal(5), Decimal(7)], runs=3)
    assert voted.value == Decimal(5)
    assert voted.agreement == 2


def test_median_vote_abstains_without_majority():
    voted = median_vote([Decimal(5), None, None], runs=3)
    assert voted.value is None


def test_median_vote_all_none():
    assert median_vote([None, None, None], runs=3).value is None
