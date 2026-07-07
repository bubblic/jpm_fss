# Untagged extraction report: 2023_general_motors_annual_report

Source: `previous_llm_extractor\annual_reports\for_financial_statements\2023 General Motors Annual Report .pdf`  
LLM assist: configured

## balance_sheet

- pages [62] (deterministic), 37 rows x 2 columns, scale 1000000
- accepted cells 74, flags 0
- footing: 9 verified groups, PASS
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 14 lexical, 12 LLM, 11 unmapped

## income_statement

- pages [61] (deterministic), 21 rows x 3 columns, scale 1000000
- accepted cells 63, flags 0
- footing: 4 verified groups, FAIL
- concept mapping: 2 lexical, 9 LLM, 10 unmapped

## cash_flow

- pages [63] (deterministic), 33 rows x 3 columns, scale 1000000
- accepted cells 97, flags 0
- footing: 5 verified groups, FAIL
- cash tie: PASS (begin 21948 + change -31 (net-change row, fx inside change) vs end 21917)
- concept mapping: 2 lexical, 17 LLM, 14 unmapped

## Simulation

- skipped: cash_flow footing unverified; income_statement footing unverified (adjudication required before simulation)

LLM calls: 62