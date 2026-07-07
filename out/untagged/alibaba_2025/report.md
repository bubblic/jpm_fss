# Untagged extraction report: alibaba_2025

Source: `previous_llm_extractor\annual_reports\for_financial_statements\alibaba_2025.pdf`  
LLM assist: configured

## balance_sheet

- pages [56, 82, 83] (llm), 27 rows x 7 columns, scale 1
- accepted cells 120, flags 9
- footing: 25 verified groups, FAIL
- A = L + E: N/A (no 'Total assets' row)
- concept mapping: 0 lexical, 0 LLM, 27 unmapped

## income_statement

- pages [56, 65, 69] (llm), 50 rows x 5 columns, scale 1
- accepted cells 54, flags 156
- footing: 49 verified groups, FAIL
- concept mapping: 0 lexical, 0 LLM, 50 unmapped

## cash_flow

- pages [75, 83, 84] (llm), 57 rows x 7 columns, scale 1
- accepted cells 166, flags 77
- footing: 53 verified groups, FAIL
- cash tie: N/A (no beginning/ending cash rows)
- concept mapping: 0 lexical, 0 LLM, 57 unmapped

## Simulation

- skipped: 9 flagged balance-sheet cells; balance_sheet footing unverified; cash_flow footing unverified; income_statement footing unverified (adjudication required before simulation)

LLM calls: 108