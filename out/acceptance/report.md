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
| baseline | 117,054 | 108,662 | 113,850 | 116,901 | 120,582 | 124,756 |
| expansion | 122,421 | 113,990 | 119,218 | 122,278 | 125,919 | 130,086 |
| recession | 108,694 | 100,265 | 105,495 | 108,542 | 112,208 | 116,383 |
| competition | 110,647 | 102,462 | 107,529 | 110,491 | 114,078 | 118,161 |
| rate_hike | 117,663 | 109,309 | 114,467 | 117,507 | 121,177 | 125,337 |
| inflation | 114,146 | 105,909 | 110,999 | 113,998 | 117,583 | 121,686 |

| Scenario | mean revenue | p5 | p25 | p50 | p75 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 432,023 | 409,899 | 422,828 | 432,161 | 441,482 | 453,826 |
| expansion | 449,918 | 427,794 | 440,723 | 450,056 | 459,376 | 471,721 |
| recession | 406,637 | 384,513 | 397,443 | 406,775 | 416,096 | 428,440 |
| competition | 422,660 | 400,535 | 413,465 | 422,798 | 432,118 | 444,462 |
| rate_hike | 432,439 | 410,315 | 423,245 | 432,577 | 441,898 | 454,242 |
| inflation | 434,520 | 412,396 | 425,325 | 434,658 | 443,978 | 456,323 |

### Directional battery

- PASS: expansion raises revenue (expansion vs baseline, mean revenue: +17,894,923,000)
- PASS: expansion raises net income (expansion vs baseline, mean net_income: +5,367,290,239)
- PASS: recession lowers revenue (recession vs baseline, mean revenue: -25,385,821,000)
- PASS: recession lowers net income (recession vs baseline, mean net_income: -8,359,816,345)
- PASS: competition lowers net income (competition vs baseline, mean net_income: -6,406,882,057)
- PASS: competition compresses gross margin (competition vs baseline, mean gross_margin_bp: -96bp)
- PASS: inflation lowers net income (inflation vs baseline, mean net_income: -2,907,675,254)
- PASS: rate hike moves income with the firm's net cash position (rate_hike vs baseline, mean net_income: +608,939,208)

### Plausibility (representative and deterministic paths, all scenarios)

- 60 of 60 checks pass; Monte Carlo identity violations: 0

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
| baseline | 113,272 | 106,708 | 110,373 | 113,216 | 115,712 | 120,406 |
| expansion | 118,619 | 112,041 | 115,715 | 118,527 | 121,056 | 125,751 |
| recession | 105,198 | 98,608 | 102,260 | 105,145 | 107,625 | 112,331 |
| competition | 109,015 | 102,525 | 106,136 | 108,974 | 111,424 | 116,073 |
| rate_hike | 113,896 | 107,340 | 111,002 | 113,840 | 116,330 | 121,020 |
| inflation | 112,040 | 105,529 | 109,166 | 111,975 | 114,466 | 119,115 |

| Scenario | mean revenue | p5 | p25 | p50 | p75 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 306,976 | 292,836 | 301,170 | 307,214 | 312,418 | 321,759 |
| expansion | 319,090 | 304,950 | 313,284 | 319,328 | 324,532 | 333,873 |
| recession | 289,791 | 275,651 | 283,985 | 290,028 | 295,232 | 304,574 |
| competition | 300,637 | 286,498 | 294,831 | 300,875 | 306,079 | 315,420 |
| rate_hike | 307,258 | 293,118 | 301,452 | 307,495 | 312,699 | 322,041 |
| inflation | 308,667 | 294,527 | 302,861 | 308,904 | 314,108 | 323,449 |

### Directional battery

- PASS: expansion raises revenue (expansion vs baseline, mean revenue: +12,114,132,000)
- PASS: expansion raises net income (expansion vs baseline, mean net_income: +5,347,251,081)
- PASS: recession lowers revenue (recession vs baseline, mean revenue: -17,185,164,000)
- PASS: recession lowers net income (recession vs baseline, mean net_income: -8,073,929,672)
- PASS: competition lowers net income (competition vs baseline, mean net_income: -4,256,944,526)
- PASS: competition compresses gross margin (competition vs baseline, mean gross_margin_bp: -56bp)
- PASS: inflation lowers net income (inflation vs baseline, mean net_income: -1,231,996,481)
- PASS: rate hike moves income with the firm's net cash position (rate_hike vs baseline, mean net_income: +623,663,016)

### Plausibility (representative and deterministic paths, all scenarios)

- 60 of 60 checks pass; Monte Carlo identity violations: 0

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
| baseline | 7,881 | 7,264 | 7,627 | 7,866 | 8,132 | 8,530 |
| expansion | 8,370 | 7,753 | 8,115 | 8,357 | 8,617 | 9,020 |
| recession | 7,112 | 6,497 | 6,860 | 7,098 | 7,366 | 7,763 |
| competition | 7,483 | 6,872 | 7,233 | 7,469 | 7,732 | 8,129 |
| rate_hike | 7,972 | 7,356 | 7,719 | 7,957 | 8,223 | 8,621 |
| inflation | 7,655 | 7,043 | 7,404 | 7,643 | 7,902 | 8,302 |

| Scenario | mean revenue | p5 | p25 | p50 | p75 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 38,521 | 36,839 | 37,755 | 38,424 | 39,326 | 40,364 |
| expansion | 40,103 | 38,422 | 39,337 | 40,007 | 40,909 | 41,947 |
| recession | 36,276 | 34,595 | 35,510 | 36,179 | 37,082 | 38,119 |
| competition | 37,693 | 36,011 | 36,927 | 37,596 | 38,498 | 39,536 |
| rate_hike | 38,558 | 36,876 | 37,791 | 38,461 | 39,363 | 40,401 |
| inflation | 38,742 | 37,060 | 37,975 | 38,645 | 39,547 | 40,585 |

### Directional battery

- PASS: expansion raises revenue (expansion vs baseline, mean revenue: +1,582,400,000)
- PASS: expansion raises net income (expansion vs baseline, mean net_income: +489,126,919)
- PASS: recession lowers revenue (recession vs baseline, mean revenue: -2,244,800,000)
- PASS: recession lowers net income (recession vs baseline, mean net_income: -768,561,817)
- PASS: competition lowers net income (competition vs baseline, mean net_income: -397,667,027)
- PASS: competition compresses gross margin (competition vs baseline, mean gross_margin_bp: -49bp)
- PASS: inflation lowers net income (inflation vs baseline, mean net_income: -225,192,592)
- PASS: rate hike moves income with the firm's net cash position (rate_hike vs baseline, mean net_income: +91,152,098)

### Plausibility (representative and deterministic paths, all scenarios)

- 60 of 60 checks pass; Monte Carlo identity violations: 0

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
| baseline | 2,310 | 2,062 | 2,205 | 2,314 | 2,421 | 2,555 |
| expansion | 2,447 | 2,197 | 2,339 | 2,454 | 2,563 | 2,694 |
| recession | 2,046 | 1,805 | 1,941 | 2,052 | 2,155 | 2,285 |
| competition | 2,028 | 1,791 | 1,925 | 2,034 | 2,138 | 2,259 |
| rate_hike | 2,405 | 2,158 | 2,300 | 2,409 | 2,516 | 2,649 |
| inflation | 2,106 | 1,864 | 2,001 | 2,112 | 2,218 | 2,343 |

| Scenario | mean revenue | p5 | p25 | p50 | p75 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 18,212 | 17,354 | 17,836 | 18,219 | 18,581 | 19,070 |
| expansion | 18,951 | 18,093 | 18,575 | 18,958 | 19,320 | 19,809 |
| recession | 17,164 | 16,306 | 16,788 | 17,171 | 17,533 | 18,022 |
| competition | 17,826 | 16,968 | 17,450 | 17,833 | 18,194 | 18,683 |
| rate_hike | 18,230 | 17,371 | 17,853 | 18,236 | 18,598 | 19,087 |
| inflation | 18,316 | 17,457 | 17,939 | 18,322 | 18,684 | 19,173 |

### Directional battery

- PASS: expansion raises revenue (expansion vs baseline, mean revenue: +738,998,000)
- PASS: expansion raises net income (expansion vs baseline, mean net_income: +137,253,388)
- PASS: recession lowers revenue (recession vs baseline, mean revenue: -1,048,346,000)
- PASS: recession lowers net income (recession vs baseline, mean net_income: -264,544,966)
- PASS: competition lowers net income (competition vs baseline, mean net_income: -282,451,092)
- PASS: competition compresses gross margin (competition vs baseline, mean gross_margin_bp: -122bp)
- PASS: inflation lowers net income (inflation vs baseline, mean net_income: -204,498,739)
- PASS: rate hike moves income with the firm's net cash position (rate_hike vs baseline, mean net_income: +94,687,596)

### Plausibility (representative and deterministic paths, all scenarios)

- 60 of 60 checks pass; Monte Carlo identity violations: 0
