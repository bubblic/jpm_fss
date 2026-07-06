"""The shared display grammar."""
from fss.pdfread.rows import parse_text_lines, split_trailing_values


def _rows(lines):
    return parse_text_lines([(0, i, line) for i, line in enumerate(lines)], "T")


def test_glued_currency_terminates_run():
    label, values = split_trailing_values(
        "Accounts receivable, net of allowance of $944 and $830 69,905 56,924".split()
    )
    assert [v.value for v in values] == [69905, 56924]
    assert label[-1] == "$830"


def test_wrapped_label_merges():
    output = _rows(
        [
            "ASSETS:",
            "Cash and cash equivalents $ 35,934 $ 29,943",
            "Common stock and additional paid-in capital, $0.00001 par value: 50,400,000 shares",
            "authorized; 14,773,260 and 15,116,786 shares issued and outstanding 93,568 83,276",
        ]
    )
    data = output.data_rows()
    assert len(data) == 2
    assert data[1].label.startswith("Common stock and additional")
    assert data[1].label.endswith("issued and outstanding")
    assert [v.value for v in data[1].values] == [93568, 83276]


def test_first_row_wrapped_label():
    output = _rows(
        [
            "Cash, cash equivalents, and restricted cash, beginning",
            "balances $ 29,943 30,737 24,977",
        ]
    )
    data = output.data_rows()
    assert len(data) == 1
    assert data[0].label.startswith("Cash, cash equivalents")
    assert [v.value for v in data[0].values] == [29943, 30737, 24977]


def test_unlabeled_section_total_is_a_row():
    output = _rows(
        [
            "Non-current assets",
            "Goodwill 12 1,083 1,201",
            "4,519 3,626",
        ]
    )
    data = output.data_rows()
    assert len(data) == 2
    assert data[1].label == ""
    assert [v.value for v in data[1].values] == [4519, 3626]


def test_bare_line_sets_section():
    output = _rows(
        [
            "Revenue 4 17,186 15,673",
            "Weighted-average ordinary shares outstanding",
            "Basic 9 205,412,951 200,622,518",
        ]
    )
    data = output.data_rows()
    assert data[1].section == "Weighted-average ordinary shares outstanding"


def test_bare_valueless_row_survives():
    output = _rows(
        [
            "Total liabilities 285,508 308,030",
            "Commitments and contingencies",
            "Shareholders' equity:",
            "Common stock 93,568 83,276",
        ]
    )
    kinds = [row.kind for row in output.rows]
    assert "bare" in kinds
    bare = [row for row in output.rows if row.kind == "bare"][0]
    assert bare.label == "Commitments and contingencies"


def test_year_header_lines_dropped():
    output = _rows(
        [
            "€ millions Notes 20253 2024 2023",
            "Cloud 21,023 17,141 13,664",
        ]
    )
    assert len(output.data_rows()) == 1
    assert any("millions" in line for line in output.header_lines)
