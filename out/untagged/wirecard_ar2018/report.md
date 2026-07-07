# Untagged extraction report: wirecard_ar2018

Source: `previous_llm_extractor\annual_reports\for_financial_statements\wirecard\ar2018.pdf`  
LLM assist: configured

**Diagnosis:** 104 text-bearing pages (e.g. pages 32-222) extract with ZERO digits: their fonts lack unicode mappings for numerals, so no text engine can read numbers there. If the statements live in that region, any rows extracted elsewhere are condensed summaries, not the statement face; an OCR/vision reader is required.

## balance_sheet

- pages [76] (llm), 6 rows x 2 columns, scale 1000000
- accepted cells 10, flags 1
- footing: 0 verified groups, PASS
- A = L + E: N/A (no 'Total assets' row)
- concept mapping: 1 lexical, 3 LLM, 2 unmapped

## income_statement

- pages [72] (llm), 13 rows x 2 columns, scale 1000000
- accepted cells 20, flags 3, LLM-adjudicated 1
- footing: 1 verified groups, PASS
- concept mapping: 1 lexical, 5 LLM, 7 unmapped

## cash_flow

- pages [72] (llm), 13 rows x 2 columns, scale 1000000
- accepted cells 20, flags 3, LLM-adjudicated 1
- footing: 1 verified groups, PASS
- cash tie: N/A (no beginning/ending cash rows)
- concept mapping: 1 lexical, 5 LLM, 7 unmapped

## Simulation

- skipped: 1 flagged balance-sheet cells (adjudication required before simulation)

LLM calls: 54