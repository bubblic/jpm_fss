# Untagged extraction report: bbby_ar2022

Source: `previous_llm_extractor\annual_reports\for_financial_statements\bbby\ar2022.pdf`  
LLM assist: configured

## balance_sheet

- pages [66, 67] (deterministic), 30 rows x 2 columns, scale 1000
- accepted cells 51, flags 0
- footing: 4 verified groups, PASS
- A = L + E: N/A (no combined or component totals)
- concept mapping: 11 lexical, 15 LLM, 4 unmapped

## income_statement

- pages [69] (deterministic), 19 rows x 3 columns, scale 1000
- accepted cells 52, flags 0
- footing: 3 verified groups, FAIL
- concept mapping: 3 lexical, 9 LLM, 7 unmapped

## cash_flow

- pages [74] (llm), 46 rows x 3 columns, scale 1000
- accepted cells 102, flags 0
- footing: 1 verified groups, PASS
- cash tie: N/A (no beginning/ending cash rows)
- concept mapping: 6 lexical, 14 LLM, 26 unmapped

## Simulation

- skipped: income_statement footing unverified (adjudication required before simulation)

LLM calls: 59