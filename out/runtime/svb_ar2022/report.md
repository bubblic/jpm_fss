# Runtime report (deterministic inference path): svb_ar2022

Source: `previous_llm_extractor\annual_reports\for_financial_statements\svb\ar2022.pdf`  
Source SHA256: `fb21467d6ddca7dd78f942fd662b106a0a925acf286757f7ae53d57564f55f8c`  
LLM assist: FORBIDDEN in this mode (no model in the inference path)  
Mapping artifact: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\svb_ar2022.json` (approved by: PENDING SIGN-OFF; built at code f798bfc)  

## balance_sheet

- pages [111] (artifact), 25 rows x 2 columns, scale 1000000
- accepted cells 48, flags 0
- footing: 4 verified groups, PASS
- A = L + E: N/A (no combined or component totals)
- concept mapping: 7 lexical, 8 artifact, 0 LLM, 10 unmapped

## income_statement

- pages [112] (artifact), 42 rows x 3 columns, scale 1000000
- accepted cells 121, flags 1
- footing: 4 verified groups, PASS
- concept mapping: 3 lexical, 7 artifact, 0 LLM, 32 unmapped

## cash_flow

- pages [117] (artifact), 49 rows x 3 columns, scale 1000000
- accepted cells 135, flags 1
- footing: 6 verified groups, FAIL
- cash tie: PASS (begin 14586 + change -783 (net-change row, fx added) vs end 13803)
- concept mapping: 4 lexical, 19 artifact, 0 LLM, 26 unmapped

## Simulation

- skipped: cash_flow footing unverified (adjudication required before simulation)

LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)