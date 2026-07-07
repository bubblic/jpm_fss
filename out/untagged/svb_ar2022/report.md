# Untagged extraction report: svb_ar2022

Source: `previous_llm_extractor\annual_reports\for_financial_statements\svb\ar2022.pdf`  
LLM assist: configured

## balance_sheet

- pages [111] (deterministic), 25 rows x 2 columns, scale 1000000
- accepted cells 48, flags 0
- footing: 4 verified groups, PASS
- A = L + E: N/A (no combined or component totals)
- concept mapping: 7 lexical, 8 LLM, 10 unmapped

## income_statement

- pages [112] (deterministic), 42 rows x 3 columns, scale 1000000
- accepted cells 121, flags 1
- footing: 4 verified groups, PASS
- concept mapping: 3 lexical, 7 LLM, 32 unmapped

## cash_flow

- pages [117] (deterministic), 49 rows x 3 columns, scale 1000000
- accepted cells 135, flags 1
- footing: 6 verified groups, FAIL
- cash tie: PASS (begin 14586 + change -783 (net-change row, fx added) vs end 13803)
- concept mapping: 4 lexical, 19 LLM, 26 unmapped

## Simulation

- skipped: cash_flow footing unverified (adjudication required before simulation)

LLM calls: 60