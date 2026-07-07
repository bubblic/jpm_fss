# Untagged extraction report: evergrande_ar2022

Source: `previous_llm_extractor\annual_reports\for_financial_statements\evergrande\ar2022.pdf`  
LLM assist: not configured (deterministic only)

## balance_sheet

- pages [156] (deterministic), 20 rows x 2 columns, scale 1000000
- accepted cells 38, flags 0
- footing: 7 verified groups, PASS
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 6 lexical, 0 LLM, 14 unmapped

## income_statement

- pages [92, 93, 94] (deterministic), 9 rows x 5 columns, scale 1
- accepted cells 25, flags 0
- footing: 2 verified groups, PASS
- concept mapping: 2 lexical, 0 LLM, 7 unmapped

## cash_flow

- FAILED: not located (no LLM fallback configured)

## Simulation

- skipped: not all three statements extracted

LLM calls: 0