# Untagged extraction report: alibaba_2025

Source: `previous_llm_extractor\annual_reports\for_financial_statements\alibaba_2025.pdf`  
LLM assist: configured

## balance_sheet

- pages [310] (deterministic), 28 rows x 3 columns, scale 1
- accepted cells 62, flags 0
- footing: 25 verified groups, FAIL
- A = L + E: N/A (no 'Total assets' row)
- concept mapping: 8 lexical, 0 LLM, 20 unmapped

## income_statement

- pages [319, 320] (deterministic), 35 rows x 9 columns, scale 1
- accepted cells 168, flags 18
- footing: 34 verified groups, FAIL
- concept mapping: 14 lexical, 0 LLM, 21 unmapped

## cash_flow

- pages [311, 312, 313, 314, 315] (deterministic), 71 rows x 7 columns, scale 1
- accepted cells 167, flags 46, LLM-adjudicated 1
- footing: 61 verified groups, FAIL
- cash tie: N/A (no beginning/ending cash rows)
- concept mapping: 4 lexical, 0 LLM, 67 unmapped

## Simulation

- skipped: balance_sheet footing unverified; cash_flow footing unverified; income_statement footing unverified (adjudication required before simulation)

LLM calls: 36