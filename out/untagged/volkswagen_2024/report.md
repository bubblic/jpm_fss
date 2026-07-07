# Untagged extraction report: volkswagen_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\volkswagen_2024.pdf`  
LLM assist: not configured (deterministic only)

## balance_sheet

- pages [132] (deterministic), 29 rows x 6 columns, scale 1000000
- accepted cells 162, flags 6
- footing: 2 verified groups, FAIL
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 11 lexical, 0 LLM, 18 unmapped

## income_statement

- pages [472] (deterministic), 16 rows x 2 columns, scale 1000000
- accepted cells 30, flags 7
- footing: 0 verified groups, PASS
- concept mapping: 1 lexical, 0 LLM, 15 unmapped

## cash_flow

- FAILED: not located (no LLM fallback configured)

## Simulation

- skipped: not all three statements extracted

LLM calls: 0