# Cross-year carry-forward demonstration

Each experiment onboards a firm's prior-year annual report with and without seeding from the already-onboarded year's mapping artifact, replays the carried artifact at runtime, and scores every mapping choice against the filer's own tags for the onboarded year.

## microsoft_2024 carried from microsoft_2025

Microsoft Corporation 10-K, accession 000095017024087843, filed 2024-07-30, period 2024-06-30 (rendered from the EDGAR primary document). Carried from microsoft_2025 (artifact sha 4793f36c40be9d07..., sign-off: PENDING SIGN-OFF). This is the boundary case: a lexicon firm, so the lexicon should already cover it.

| Statement | located_by | rows | flags | lexical | carried | taxonomy | llm | unmapped |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| balance_sheet (control) | deterministic | 34 | 1 | 34 | 0 | 0 | 0 | 0 |
| balance_sheet (carried) | deterministic | 34 | 1 | 34 | 0 | 0 | 0 | 0 |
| income_statement (control) | deterministic | 19 | 0 | 15 | 0 | 0 | 0 | 4 |
| income_statement (carried) | deterministic | 19 | 0 | 15 | 0 | 0 | 0 | 4 |
| cash_flow (control) | deterministic | 34 | 0 | 31 | 0 | 0 | 3 | 0 |
| cash_flow (carried) | deterministic | 34 | 0 | 31 | 0 | 0 | 3 | 0 |

LLM calls: control 5, carried 5. Simulation: control skipped, carried skipped, runtime replay skipped (runtime model constructed: False).

### Concept accuracy against the filer's own tags

#### Control onboard

| Statement | source | match | mismatch | off-face |
| --- | --- | ---: | ---: | ---: |
| balance_sheet | lexical | 34 | 0 | 0 |
| income_statement | lexical | 13 | 0 | 2 |
| cash_flow | lexical | 31 | 0 | 0 |
| cash_flow | llm | 3 | 0 | 0 |

#### Carried onboard

| Statement | source | match | mismatch | off-face |
| --- | --- | ---: | ---: | ---: |
| balance_sheet | lexical | 34 | 0 | 0 |
| income_statement | lexical | 13 | 0 | 2 |
| cash_flow | lexical | 31 | 0 | 0 |
| cash_flow | llm | 3 | 0 | 0 |

## bbby_2021 carried from bbby_ar2022

Bed Bath & Beyond Inc. 10-K, accession 000088615822000047, filed 2022-04-21, period 2022-02-26 (rendered from the EDGAR primary document). Carried from bbby_ar2022 (artifact sha 1c0493f0331effa2..., sign-off: PENDING SIGN-OFF). This is the payoff case: not a lexicon firm, so firm-specific labels resolve only from the prior artifact or the model.

| Statement | located_by | rows | flags | lexical | carried | taxonomy | llm | unmapped |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| balance_sheet (control) | deterministic | 27 | 0 | 12 | 0 | 0 | 11 | 4 |
| balance_sheet (carried) | deterministic | 27 | 0 | 12 | 12 | 0 | 0 | 3 |
| income_statement (control) | deterministic | 18 | 0 | 3 | 0 | 0 | 7 | 8 |
| income_statement (carried) | deterministic | 18 | 0 | 3 | 6 | 0 | 1 | 8 |
| cash_flow (control) | deterministic | 41 | 0 | 6 | 0 | 1 | 17 | 17 |
| cash_flow (carried) | deterministic | 41 | 0 | 6 | 8 | 1 | 13 | 13 |

LLM calls: control 55, carried 37. Simulation: control ok, carried ok, runtime replay ok (runtime model constructed: False).

### Concept accuracy against the filer's own tags

#### Control onboard

| Statement | source | match | mismatch | off-face |
| --- | --- | ---: | ---: | ---: |
| balance_sheet | lexical | 12 | 0 | 0 |
| balance_sheet | llm | 3 | 8 | 0 |
| income_statement | lexical | 2 | 1 | 0 |
| income_statement | llm | 4 | 3 | 0 |
| cash_flow | lexical | 4 | 2 | 0 |
| cash_flow | llm | 8 | 9 | 0 |
| cash_flow | taxonomy | 1 | 0 | 0 |

Mismatches:
- [llm] 'Prepaid expenses and other current assets': chose us-gaap:OtherAssetsCurrent, filer tags us-gaap:PrepaidExpenseAndOtherAssetsCurrent
- [llm] 'Property and equipment, net': chose us-gaap:PropertyPlantAndEquipmentNet, filer tags us-gaap:PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization
- [llm] 'Other assets': chose us-gaap:OtherAssetsCurrent, filer tags us-gaap:OtherAssetsNoncurrent
- [llm] 'Other liabilities': chose us-gaap:OtherLiabilitiesCurrent, filer tags us-gaap:OtherLiabilitiesNoncurrent
- [llm] 'Income taxes payable': chose us-gaap:AccruedIncomeTaxesCurrent, filer tags us-gaap:AccruedIncomeTaxesNoncurrent
- [llm] 'Common stock - $0.01 par value; authorized - 900,000 shares; issued 344,146 and 343,241, respectively; outstanding 81,979 and 109,621 shares, respectively': chose us-gaap:CommonStocksIncludingAdditionalPaidInCapital, filer tags us-gaap:CommonStockValue
- [llm] 'Additional paid-in capital': chose ifrs-full:AdditionalPaidinCapital, filer tags us-gaap:AdditionalPaidInCapitalCommonStock
- [llm] 'Treasury stock, at cost; 262,167 and 233,620 shares, respectively': chose ifrs-full:TreasuryShares, filer tags us-gaap:TreasuryStockValue
- [lexical] 'Gross profit': chose ifrs-full:GrossProfit, filer tags us-gaap:GrossProfit
- [llm] 'Impairments, including on assets held for sale': chose ck0001639920:AdjustmentForImpairmentChargesOnRealEstateAssets, filer tags us-gaap:AssetImpairmentCharges
- [llm] 'Net loss per share - Basic': chose ifrs-full:BasicEarningsLossPerShare, filer tags us-gaap:EarningsPerShareBasic
- [llm] 'Net loss per share - Diluted': chose ifrs-full:DilutedEarningsLossPerShare, filer tags us-gaap:EarningsPerShareDiluted
- [llm] 'Impairments, including on assets held for sale': chose ck0001639920:AdjustmentForImpairmentChargesOnRealEstateAssets, filer tags us-gaap:GoodwillAndIntangibleAssetImpairment
- [lexical] 'Deferred income taxes': chose us-gaap:DeferredIncomeTaxExpenseBenefit, filer tags bbby:DeferredIncomeTaxNoncashExpenseBenefit
- [llm] 'Other assets': chose us-gaap:IncreaseDecreaseInOtherCurrentAssets, filer tags us-gaap:IncreaseDecreaseInOtherNoncurrentAssets
- [llm] 'Merchandise credit and gift card liabilities': chose us-gaap:IncreaseDecreaseInOtherOperatingLiabilities, filer tags bbby:IncreaseDecreaseInMerchandiseCreditAndGiftCardLiabilities
- [llm] 'Operating lease assets and liabilities, net': chose us-gaap:IncreaseDecreaseInOtherOperatingLiabilities, filer tags bbby:IncreaseDecreaseinOperatingLeaseAssetsandLiabilities
- [llm] 'Other liabilities': chose us-gaap:IncreaseDecreaseInOtherCurrentLiabilities, filer tags us-gaap:IncreaseDecreaseInOtherOperatingLiabilities
- [llm] 'Purchases of held-to-maturity investment securities': chose us-gaap:PaymentsToAcquireInvestments, filer tags us-gaap:PaymentsToAcquireHeldToMaturitySecurities
- [llm] 'Net proceeds from sales of businesses': chose ifrs-full:CashFlowsFromLosingControlOfSubsidiariesOrOtherBusinessesClassifiedAsInvestingActivities, filer tags us-gaap:ProceedsFromDivestitureOfBusinesses
- [llm] 'Net proceeds from sales of property': chose ifrs-full:ProceedsFromDisposalsOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets, filer tags us-gaap:ProceedsFromSaleOfPropertyPlantAndEquipment
- [llm] 'Repayments of finance leases': chose us-gaap:RepaymentsOfLongTermDebt, filer tags us-gaap:FinanceLeasePrincipalPayments
- [lexical] 'Proceeds from exercise of stock options': chose ifrs-full:ProceedsFromExerciseOfOptions, filer tags us-gaap:ProceedsFromStockOptionsExercised

#### Carried onboard

| Statement | source | match | mismatch | off-face |
| --- | --- | ---: | ---: | ---: |
| balance_sheet | carried | 3 | 9 | 0 |
| balance_sheet | lexical | 12 | 0 | 0 |
| income_statement | carried | 4 | 2 | 0 |
| income_statement | lexical | 2 | 1 | 0 |
| income_statement | llm | 0 | 1 | 0 |
| cash_flow | carried | 4 | 4 | 0 |
| cash_flow | lexical | 4 | 2 | 0 |
| cash_flow | llm | 9 | 4 | 0 |
| cash_flow | taxonomy | 1 | 0 | 0 |

Mismatches:
- [carried] 'Prepaid expenses and other current assets': chose us-gaap:OtherAssetsCurrent, filer tags us-gaap:PrepaidExpenseAndOtherAssetsCurrent
- [carried] 'Property and equipment, net': chose us-gaap:PropertyPlantAndEquipmentNet, filer tags us-gaap:PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization
- [carried] 'Other assets': chose us-gaap:OtherAssetsCurrent, filer tags us-gaap:OtherAssetsNoncurrent
- [carried] 'Current operating lease liabilities': chose ifrs-full:CurrentFinancialLiabilities, filer tags us-gaap:OperatingLeaseLiabilityCurrent
- [carried] 'Other liabilities': chose us-gaap:OtherLiabilitiesCurrent, filer tags us-gaap:OtherLiabilitiesNoncurrent
- [carried] 'Income taxes payable': chose us-gaap:AccruedIncomeTaxesCurrent, filer tags us-gaap:AccruedIncomeTaxesNoncurrent
- [carried] 'Common stock - $0.01 par value; authorized - 900,000 shares; issued 344,146 and 343,241, respectively; outstanding 81,979 and 109,621 shares, respectively': chose us-gaap:CommonStocksIncludingAdditionalPaidInCapital, filer tags us-gaap:CommonStockValue
- [carried] 'Additional paid-in capital': chose ifrs-full:AdditionalPaidinCapital, filer tags us-gaap:AdditionalPaidInCapitalCommonStock
- [carried] 'Treasury stock, at cost; 262,167 and 233,620 shares, respectively': chose ifrs-full:TreasuryShares, filer tags us-gaap:TreasuryStockValue
- [lexical] 'Gross profit': chose ifrs-full:GrossProfit, filer tags us-gaap:GrossProfit
- [llm] 'Impairments, including on assets held for sale': chose ck0001639920:AdjustmentForImpairmentChargesOnRealEstateAssets, filer tags us-gaap:AssetImpairmentCharges
- [carried] 'Net loss per share - Basic': chose ifrs-full:BasicEarningsLossPerShare, filer tags us-gaap:EarningsPerShareBasic
- [carried] 'Net loss per share - Diluted': chose ifrs-full:DilutedEarningsLossPerShare, filer tags us-gaap:EarningsPerShareDiluted
- [lexical] 'Deferred income taxes': chose us-gaap:DeferredIncomeTaxExpenseBenefit, filer tags bbby:DeferredIncomeTaxNoncashExpenseBenefit
- [llm] 'Other assets': chose us-gaap:IncreaseDecreaseInOtherCurrentAssets, filer tags us-gaap:IncreaseDecreaseInOtherNoncurrentAssets
- [carried] 'Merchandise credit and gift card liabilities': chose us-gaap:IncreaseDecreaseInOtherOperatingLiabilities, filer tags bbby:IncreaseDecreaseInMerchandiseCreditAndGiftCardLiabilities
- [llm] 'Other liabilities': chose us-gaap:IncreaseDecreaseInOtherCurrentLiabilities, filer tags us-gaap:IncreaseDecreaseInOtherOperatingLiabilities
- [carried] 'Purchases of held-to-maturity investment securities': chose us-gaap:PaymentsToAcquireInvestments, filer tags us-gaap:PaymentsToAcquireHeldToMaturitySecurities
- [carried] 'Net proceeds from sales of businesses': chose ifrs-full:CashFlowsFromLosingControlOfSubsidiariesOrOtherBusinessesClassifiedAsInvestingActivities, filer tags us-gaap:ProceedsFromDivestitureOfBusinesses
- [carried] 'Net proceeds from sales of property': chose ifrs-full:ProceedsFromDisposalsOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets, filer tags us-gaap:ProceedsFromSaleOfPropertyPlantAndEquipment
- [llm] 'Repayments of finance leases': chose ifrs-full:RepaymentsOfBorrowingsClassifiedAsFinancingActivities, filer tags us-gaap:FinanceLeasePrincipalPayments
- [lexical] 'Proceeds from exercise of stock options': chose ifrs-full:ProceedsFromExerciseOfOptions, filer tags us-gaap:ProceedsFromStockOptionsExercised
- [llm] 'Effect of exchange rate changes on cash, cash equivalents, and restricted cash': chose us-gaap:EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations, filer tags us-gaap:EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents

### Entries resolved by carry

- balance_sheet: 'Merchandise inventories' -> us-gaap:InventoryNet
- balance_sheet: 'Prepaid expenses and other current assets' -> us-gaap:OtherAssetsCurrent
- balance_sheet: 'Long term investment securities' -> us-gaap:LongTermInvestments
- balance_sheet: 'Property and equipment, net' -> us-gaap:PropertyPlantAndEquipmentNet
- balance_sheet: 'Operating lease assets' -> us-gaap:OperatingLeaseRightOfUseAsset
- balance_sheet: 'Other assets' -> us-gaap:OtherAssetsCurrent
- balance_sheet: 'Current operating lease liabilities' -> ifrs-full:CurrentFinancialLiabilities
- balance_sheet: 'Other liabilities' -> us-gaap:OtherLiabilitiesCurrent
- balance_sheet: 'Income taxes payable' -> us-gaap:AccruedIncomeTaxesCurrent
- balance_sheet: 'Common stock - $0.01 par value; authorized - 900,000 shares; issued 344,146 and 343,241, respectively; outstanding 81,979 and 109,621 shares, respectively' -> us-gaap:CommonStocksIncludingAdditionalPaidInCapital
- balance_sheet: 'Additional paid-in capital' -> ifrs-full:AdditionalPaidinCapital
- balance_sheet: 'Treasury stock, at cost; 262,167 and 233,620 shares, respectively' -> ifrs-full:TreasuryShares
- income_statement: 'Selling, general and administrative expenses' -> us-gaap:SellingGeneralAndAdministrativeExpense
- income_statement: 'Operating loss' -> us-gaap:OperatingIncomeLoss
- income_statement: 'Provision (benefit) from income taxes' -> us-gaap:IncomeTaxExpenseBenefit
- income_statement: 'Net loss' -> us-gaap:NetIncomeLoss
- income_statement: 'Net loss per share - Basic' -> ifrs-full:BasicEarningsLossPerShare
- income_statement: 'Net loss per share - Diluted' -> ifrs-full:DilutedEarningsLossPerShare
- cash_flow: 'Net loss' -> us-gaap:NetIncomeLoss
- cash_flow: 'Stock-based compensation' -> us-gaap:ShareBasedCompensation
- cash_flow: 'Merchandise credit and gift card liabilities' -> us-gaap:IncreaseDecreaseInOtherOperatingLiabilities
- cash_flow: 'Income taxes payable' -> us-gaap:IncreaseDecreaseInAccruedIncomeTaxesPayable
- cash_flow: 'Purchases of held-to-maturity investment securities' -> us-gaap:PaymentsToAcquireInvestments
- cash_flow: 'Net proceeds from sales of businesses' -> ifrs-full:CashFlowsFromLosingControlOfSubsidiariesOrOtherBusinessesClassifiedAsInvestingActivities
- cash_flow: 'Net proceeds from sales of property' -> ifrs-full:ProceedsFromDisposalsOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets
- cash_flow: 'Net cash (used in) provided by investing activities' -> us-gaap:NetCashProvidedByUsedInInvestingActivities
