# Untagged extraction report: lvmh_dec_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\lvmh_dec_2024.pdf`  
LLM assist: not configured (deterministic only)

## balance_sheet

- pages [26] (deterministic), 32 rows x 3 columns, scale 1
- accepted cells 96, flags 22
- footing: 2 verified groups, FAIL
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 12 lexical, 0 LLM, 20 unmapped

## income_statement

- pages [24] (deterministic), 21 rows x 3 columns, scale 1000000
- accepted cells 63, flags 9
- footing: 2 verified groups, PASS
- concept mapping: 5 lexical, 0 LLM, 16 unmapped

## cash_flow

- FAILED: not located (no LLM fallback configured)

## Simulation

- skipped: not all three statements extracted

LLM calls: 0