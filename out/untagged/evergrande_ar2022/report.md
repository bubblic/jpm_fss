# Untagged extraction report: evergrande_ar2022

Source: `previous_llm_extractor\annual_reports\for_financial_statements\evergrande\ar2022.pdf`  
LLM assist: configured

## balance_sheet

- pages [156] (deterministic), 20 rows x 2 columns, scale 1000000
- accepted cells 38, flags 0
- footing: 7 verified groups, PASS
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 6 lexical, 7 LLM, 7 unmapped

## income_statement

- pages [92, 93, 94] (deterministic), 9 rows x 5 columns, scale 1
- accepted cells 25, flags 0
- footing: 2 verified groups, PASS
- concept mapping: 2 lexical, 1 LLM, 6 unmapped

## cash_flow

- pages [52, 53, 146] (llm), 59 rows x 2 columns, scale 1000000
- accepted cells 112, flags 1
- footing: 4 verified groups, FAIL
- cash tie: PASS (begin 5435 + change -1103 (net-change row, fx added) vs end 4334)
- concept mapping: 6 lexical, 21 LLM, 32 unmapped

## Simulation

- skipped: cash_flow footing unverified (adjudication required before simulation)

LLM calls: 40