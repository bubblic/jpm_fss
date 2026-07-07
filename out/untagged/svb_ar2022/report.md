# Untagged extraction report: svb_ar2022

Source: `previous_llm_extractor\annual_reports\for_financial_statements\svb\ar2022.pdf`  
LLM assist: configured

## balance_sheet

- pages [111] (deterministic), 26 rows x 2 columns, scale 1000000
- accepted cells 50, flags 0
- footing: 4 verified groups, FAIL
- A = L + E: N/A (no combined or component totals)
- concept mapping: 8 lexical, 8 LLM, 10 unmapped

## income_statement

- pages [112] (deterministic), 41 rows x 3 columns, scale 1000000
- accepted cells 121, flags 0
- footing: 4 verified groups, PASS
- concept mapping: 3 lexical, 8 LLM, 30 unmapped

## cash_flow

- pages [117] (deterministic), 48 rows x 3 columns, scale 1000000
- accepted cells 135, flags 0
- footing: 6 verified groups, FAIL
- cash tie: PASS (begin 14586 + change -783 (net-change row, fx added) vs end 13803)
- concept mapping: 4 lexical, 17 LLM, 27 unmapped

## Simulation

- skipped: balance_sheet footing unverified; cash_flow footing unverified (adjudication required before simulation)

LLM calls: 56