# Untagged extraction report: bbby_ar2022

Source: `previous_llm_extractor\annual_reports\for_financial_statements\bbby\ar2022.pdf`  
LLM assist: not configured (deterministic only)

## balance_sheet

- pages [66, 67] (deterministic), 30 rows x 2 columns, scale 1000
- accepted cells 51, flags 0
- footing: 4 verified groups, PASS
- A = L + E: N/A (no combined or component totals)
- concept mapping: 11 lexical, 0 LLM, 19 unmapped

## income_statement

- pages [69] (deterministic), 19 rows x 3 columns, scale 1000
- accepted cells 52, flags 0
- footing: 1 verified groups, PASS
- concept mapping: 3 lexical, 0 LLM, 16 unmapped

## cash_flow

- FAILED: not located (no LLM fallback configured)

## Simulation

- skipped: not all three statements extracted

LLM calls: 0