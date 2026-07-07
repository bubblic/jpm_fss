# FSS acceptance report

Overall verdict: PASS

- PDF-only extraction: 994 of 994 accepted cells match the tag-path ground truth exactly (0 flagged cells abstained). Rule-of-three 95% upper bound on the per-field error rate: 0.30%.
- Monte Carlo: 500 paths per scenario per firm (common random numbers across scenarios), seed 20260706; every path keeps A = L + E and the cash tie exactly, relative to the filer's own printed rounding residual.

## Apple Inc. (us-gaap, 10-K 2025-09-27)

Verdict: PASS

### Extraction (PDF-only mode vs tag path)

| Statement | compared | matches | mismatches | missing | flagged |
| --- | ---: | ---: | ---: | ---: | ---: |
| balance_sheet | 54 | 54 | 0 | 0 | 0 |
| income_statement | 57 | 57 | 0 | 0 | 0 |
| cash_flow | 87 | 87 | 0 | 0 | 0 |

- balance_sheet: 'Common stock, shares outstanding (in shares)': share counts printed inside the equity label, not as table cells
- balance_sheet: 'Common stock, shares issued (in shares)': share counts printed inside the equity label, not as table cells

### Reconstruction and footing

- balance_sheet: exact on 76 cells
- income_statement: exact on 69 cells
- cash_flow: exact on 108 cells
- footing: 49/49 derived cells within the decimals tolerance

### Scenarios (Monte Carlo fan, millions)

| Scenario | mean net income | p5 | p25 | p50 | p75 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 117,297 | 110,009 | 114,552 | 117,237 | 120,094 | 124,356 |
| expansion | 122,665 | 115,307 | 119,854 | 122,593 | 125,472 | 129,797 |
| recession | 108,935 | 101,755 | 106,179 | 108,917 | 111,677 | 115,998 |
| competition | 110,884 | 103,752 | 108,194 | 110,832 | 113,570 | 117,775 |
| rate_hike | 117,905 | 110,631 | 115,164 | 117,844 | 120,668 | 124,950 |
| inflation | 114,385 | 107,177 | 111,662 | 114,304 | 117,090 | 121,356 |

| Scenario | mean revenue | p5 | p25 | p50 | p75 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 432,649 | 411,952 | 424,513 | 432,752 | 440,884 | 452,935 |
| expansion | 450,544 | 429,846 | 442,408 | 450,647 | 458,779 | 470,830 |
| recession | 407,264 | 386,566 | 399,127 | 407,366 | 415,499 | 427,550 |
| competition | 423,286 | 402,588 | 415,149 | 423,388 | 431,521 | 443,572 |
| rate_hike | 433,066 | 412,368 | 424,929 | 433,168 | 441,301 | 453,352 |
| inflation | 435,146 | 414,448 | 427,010 | 435,249 | 443,381 | 455,432 |

### Directional battery

- PASS: expansion raises revenue (expansion vs baseline, mean revenue: +17,894,923,000)
- PASS: expansion raises net income (expansion vs baseline, mean net_income: +5,368,238,681)
- PASS: recession lowers revenue (recession vs baseline, mean revenue: -25,385,821,000)
- PASS: recession lowers net income (recession vs baseline, mean net_income: -8,361,455,385)
- PASS: competition lowers net income (competition vs baseline, mean net_income: -6,412,794,819)
- PASS: competition compresses gross margin (competition vs baseline, mean gross_margin_bp: -96bp)
- PASS: inflation lowers net income (inflation vs baseline, mean net_income: -2,911,652,983)
- PASS: rate hike moves income with the firm's net cash position (rate_hike vs baseline, mean net_income: +608,276,253)

### Plausibility (representative and deterministic paths, all scenarios)

- symbolic closure: PROVEN (flow system cancels for all parameter values; computation DAG acyclic)
- 60 of 60 checks pass; Monte Carlo (TensorFlow) identity violations: 0; max per-path identity residual: 0.00006103515625 (tolerance 1 currency unit)

## Microsoft Corporation (us-gaap, 10-K 2025-06-30)

Verdict: PASS

### Extraction (PDF-only mode vs tag path)

| Statement | compared | matches | mismatches | missing | flagged |
| --- | ---: | ---: | ---: | ---: | ---: |
| balance_sheet | 68 | 68 | 0 | 0 | 0 |
| income_statement | 57 | 57 | 0 | 0 | 0 |
| cash_flow | 102 | 102 | 0 | 0 | 0 |


### Reconstruction and footing

- balance_sheet: exact on 82 cells
- income_statement: exact on 66 cells
- cash_flow: exact on 120 cells
- footing: 44/44 derived cells within the decimals tolerance

### Scenarios (Monte Carlo fan, millions)

| Scenario | mean net income | p5 | p25 | p50 | p75 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 113,139 | 106,314 | 110,460 | 113,161 | 115,927 | 119,769 |
| expansion | 118,485 | 111,704 | 115,778 | 118,499 | 121,245 | 125,067 |
| recession | 105,068 | 98,184 | 102,406 | 105,098 | 107,892 | 111,645 |
| competition | 108,885 | 102,125 | 106,244 | 108,908 | 111,642 | 115,437 |
| rate_hike | 113,763 | 106,950 | 111,086 | 113,783 | 116,544 | 120,383 |
| inflation | 111,908 | 105,157 | 109,243 | 111,923 | 114,668 | 118,475 |

| Scenario | mean revenue | p5 | p25 | p50 | p75 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 306,689 | 291,466 | 301,128 | 306,975 | 312,470 | 320,541 |
| expansion | 318,804 | 303,580 | 313,242 | 319,089 | 324,584 | 332,655 |
| recession | 289,504 | 274,281 | 283,943 | 289,790 | 295,285 | 303,355 |
| competition | 300,351 | 285,127 | 294,789 | 300,636 | 306,131 | 314,202 |
| rate_hike | 306,971 | 291,748 | 301,410 | 307,257 | 312,752 | 320,822 |
| inflation | 308,380 | 293,156 | 302,818 | 308,665 | 314,160 | 322,231 |

### Directional battery

- PASS: expansion raises revenue (expansion vs baseline, mean revenue: +12,114,132,000)
- PASS: expansion raises net income (expansion vs baseline, mean net_income: +5,345,887,215)
- PASS: recession lowers revenue (recession vs baseline, mean revenue: -17,185,164,000)
- PASS: recession lowers net income (recession vs baseline, mean net_income: -8,071,917,820)
- PASS: competition lowers net income (competition vs baseline, mean net_income: -4,254,809,023)
- PASS: competition compresses gross margin (competition vs baseline, mean gross_margin_bp: -56bp)
- PASS: inflation lowers net income (inflation vs baseline, mean net_income: -1,231,107,875)
- PASS: rate hike moves income with the firm's net cash position (rate_hike vs baseline, mean net_income: +623,811,117)

### Plausibility (representative and deterministic paths, all scenarios)

- symbolic closure: PROVEN (flow system cancels for all parameter values; computation DAG acyclic)
- 60 of 60 checks pass; Monte Carlo (TensorFlow) identity violations: 0; max per-path identity residual: 0.0000762939453125 (tolerance 1 currency unit)

## SAP SE (ifrs, 20-F 2025-12-31)

Verdict: PASS

### Extraction (PDF-only mode vs tag path)

| Statement | compared | matches | mismatches | missing | flagged |
| --- | ---: | ---: | ---: | ---: | ---: |
| balance_sheet | 82 | 82 | 0 | 0 | 0 |
| income_statement | 111 | 111 | 0 | 0 | 0 |
| cash_flow | 126 | 126 | 0 | 0 | 0 |


### Reconstruction and footing

- balance_sheet: exact on 84 cells, 6 filer-rounded subtotals stored verbatim
- income_statement: exact on 114 cells, 5 filer-rounded subtotals stored verbatim
- cash_flow: exact on 144 cells, 5 filer-rounded subtotals stored verbatim
- footing: 72/72 derived cells within the decimals tolerance

### Scenarios (Monte Carlo fan, millions)

| Scenario | mean net income | p5 | p25 | p50 | p75 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 7,869 | 7,247 | 7,613 | 7,840 | 8,149 | 8,537 |
| expansion | 8,358 | 7,739 | 8,105 | 8,326 | 8,638 | 9,023 |
| recession | 7,101 | 6,475 | 6,847 | 7,076 | 7,384 | 7,773 |
| competition | 7,472 | 6,855 | 7,218 | 7,444 | 7,751 | 8,132 |
| rate_hike | 7,960 | 7,339 | 7,704 | 7,931 | 8,240 | 8,627 |
| inflation | 7,644 | 7,027 | 7,389 | 7,614 | 7,921 | 8,304 |

| Scenario | mean revenue | p5 | p25 | p50 | p75 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 38,532 | 36,541 | 37,774 | 38,563 | 39,298 | 40,427 |
| expansion | 40,114 | 38,123 | 39,357 | 40,146 | 40,881 | 42,009 |
| recession | 36,287 | 34,296 | 35,529 | 36,318 | 37,054 | 38,182 |
| competition | 37,704 | 35,713 | 36,946 | 37,735 | 38,470 | 39,599 |
| rate_hike | 38,569 | 36,577 | 37,811 | 38,600 | 39,335 | 40,463 |
| inflation | 38,753 | 36,761 | 37,995 | 38,784 | 39,519 | 40,647 |

### Directional battery

- PASS: expansion raises revenue (expansion vs baseline, mean revenue: +1,582,400,000)
- PASS: expansion raises net income (expansion vs baseline, mean net_income: +488,731,811)
- PASS: recession lowers revenue (recession vs baseline, mean revenue: -2,244,800,000)
- PASS: recession lowers net income (recession vs baseline, mean net_income: -768,003,541)
- PASS: competition lowers net income (competition vs baseline, mean net_income: -397,501,349)
- PASS: competition compresses gross margin (competition vs baseline, mean gross_margin_bp: -49bp)
- PASS: inflation lowers net income (inflation vs baseline, mean net_income: -225,278,883)
- PASS: rate hike moves income with the firm's net cash position (rate_hike vs baseline, mean net_income: +91,137,716)

### Plausibility (representative and deterministic paths, all scenarios)

- symbolic closure: PROVEN (flow system cancels for all parameter values; computation DAG acyclic)
- 60 of 60 checks pass; Monte Carlo (TensorFlow) identity violations: 0; max per-path identity residual: 0.000004291534423828125 (tolerance 1 currency unit)

## Spotify Technology S.A. (ifrs, 20-F 2025-12-31)

Verdict: PASS

### Extraction (PDF-only mode vs tag path)

| Statement | compared | matches | mismatches | missing | flagged |
| --- | ---: | ---: | ---: | ---: | ---: |
| balance_sheet | 76 | 76 | 0 | 0 | 0 |
| income_statement | 54 | 54 | 0 | 0 | 0 |
| cash_flow | 120 | 120 | 0 | 0 | 0 |


### Reconstruction and footing

- balance_sheet: exact on 92 cells
- income_statement: exact on 63 cells
- cash_flow: exact on 144 cells
- footing: 46/46 derived cells within the decimals tolerance

### Scenarios (Monte Carlo fan, millions)

| Scenario | mean net income | p5 | p25 | p50 | p75 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 2,324 | 2,062 | 2,228 | 2,328 | 2,427 | 2,549 |
| expansion | 2,462 | 2,196 | 2,364 | 2,466 | 2,568 | 2,694 |
| recession | 2,059 | 1,802 | 1,965 | 2,064 | 2,161 | 2,278 |
| competition | 2,041 | 1,789 | 1,950 | 2,046 | 2,140 | 2,262 |
| rate_hike | 2,419 | 2,157 | 2,324 | 2,423 | 2,522 | 2,644 |
| inflation | 2,119 | 1,863 | 2,026 | 2,123 | 2,221 | 2,345 |

| Scenario | mean revenue | p5 | p25 | p50 | p75 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 18,224 | 17,357 | 17,882 | 18,232 | 18,581 | 19,035 |
| expansion | 18,963 | 18,096 | 18,621 | 18,971 | 19,320 | 19,774 |
| recession | 17,175 | 16,309 | 16,834 | 17,184 | 17,533 | 17,987 |
| competition | 17,837 | 16,971 | 17,495 | 17,846 | 18,195 | 18,648 |
| rate_hike | 18,241 | 17,374 | 17,899 | 18,250 | 18,599 | 19,052 |
| inflation | 18,327 | 17,460 | 17,985 | 18,335 | 18,685 | 19,138 |

### Directional battery

- PASS: expansion raises revenue (expansion vs baseline, mean revenue: +738,998,000)
- PASS: expansion raises net income (expansion vs baseline, mean net_income: +137,708,868)
- PASS: recession lowers revenue (recession vs baseline, mean revenue: -1,048,346,000)
- PASS: recession lowers net income (recession vs baseline, mean net_income: -265,198,660)
- PASS: competition lowers net income (competition vs baseline, mean net_income: -282,828,694)
- PASS: competition compresses gross margin (competition vs baseline, mean gross_margin_bp: -122bp)
- PASS: inflation lowers net income (inflation vs baseline, mean net_income: -204,540,863)
- PASS: rate hike moves income with the firm's net cash position (rate_hike vs baseline, mean net_income: +94,680,575)

### Plausibility (representative and deterministic paths, all scenarios)

- symbolic closure: PROVEN (flow system cancels for all parameter values; computation DAG acyclic)
- 60 of 60 checks pass; Monte Carlo (TensorFlow) identity violations: 0; max per-path identity residual: 0.000001430511474609375 (tolerance 1 currency unit)
