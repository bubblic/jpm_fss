# Untagged extraction report: lehman_ar2007

Source: `previous_llm_extractor\annual_reports\for_financial_statements\lehman\ar2007.pdf`  
LLM assist: not configured (deterministic only)

## balance_sheet

- pages [86, 87] (deterministic), 23 rows x 2 columns, scale 1000000
- accepted cells 46, flags 0
- footing: 2 verified groups, PASS
- A = L + E: N/A (no combined or component totals)
- concept mapping: 3 lexical, 0 LLM, 20 unmapped

## income_statement

- pages [85] (deterministic), 30 rows x 3 columns, scale 1000000
- accepted cells 84, flags 0
- footing: 7 verified groups, FAIL
- concept mapping: 3 lexical, 0 LLM, 27 unmapped

## cash_flow

- FAILED: not located (no LLM fallback configured)

## Simulation

- skipped: not all three statements extracted

LLM calls: 0