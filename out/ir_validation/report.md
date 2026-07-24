# Investor-relations editions scored against their filings' tags

Six untagged-sweep documents are true IR annual reports of filers whose same-fiscal-year filings are tagged on EDGAR. Each document is replayed deterministically from its committed mapping artifact and scored against the filing's tag path: accepted cell values against tagged values (aligned by label and fiscal year), and label-to-concept choices against the filer's own presentation.

## 2023_general_motors_annual_report

General Motors Company 10-K, accession 000146785824000031, period 2023-12-31; document replayed deterministically from its committed artifact (no model constructed).

| Statement | compared | match | mismatch | missing | flagged | gt unmatched |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| balance_sheet | 74 | 74 | 0 | 0 | 0 | 0 |
| income_statement | 54 | 54 | 0 | 0 | 0 | 5 |
| cash_flow | 99 | 98 | 1 | 0 | 0 | 1 |

- income_statement ground-truth rows unmatched: 1 derived (unprinted subtotal), 4 leaf, not extracted
- cash_flow mismatch, 'Issuance (redemption) of subsidiary stock (Note 20)' column 2: filing None, document read 1736000000
- cash_flow ground-truth rows unmatched: 1 leaf, not extracted

#### Concept choices vs the filer's tags

| Statement | source | match | mismatch | off-face |
| --- | --- | ---: | ---: | ---: |
| balance_sheet | build_products | 15 | 10 | 1 |
| income_statement | build_products | 4 | 3 | 3 |
| cash_flow | build_products | 6 | 15 | 0 |

Mismatches:
- [build_products] 'Marketable debt securities (Note 4)': chose us-gaap:MarketableSecuritiesCurrent, filer tags us-gaap:AvailableForSaleSecuritiesDebtSecuritiesCurrent
- [build_products] 'Property, net (Note 9)': chose us-gaap:PropertyPlantAndEquipmentNet, filer tags us-gaap:PropertyPlantAndEquipmentExcludingLessorAssetUnderOperatingLeaseAfterAccumulatedDepreciation
- [build_products] 'Equipment on operating leases, net (Note 7; Note 11 at VIEs)': chose us-gaap:PropertyPlantAndEquipmentNet, filer tags gm:OperatingLeaseRightofuseAssetNoncurrent
- [build_products] 'GM Financial (Note 11 at VIEs)': chose ifrs-full:CurrentFinancialLiabilities, filer tags us-gaap:DebtCurrent|us-gaap:LongTermDebtAndCapitalLeaseObligations|us-gaap:NotesAndLoansReceivableNetCurrent|us-gaap:NotesAndLoansReceivableNetNoncurrent
- [build_products] 'Noncontrolling interest - Cruise stock incentive awards (Note 20)': chose ifrs-full:NoncontrollingInterests, filer tags us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount
- [build_products] 'Common stock, $0.01 par value': chose us-gaap:CommonStockSharesIssued, filer tags us-gaap:CommonStockValue
- [build_products] 'Additional paid-in capital': chose ifrs-full:AdditionalPaidinCapital, filer tags us-gaap:AdditionalPaidInCapital
- [build_products] 'Noncontrolling interests': chose ifrs-full:NoncontrollingInterests, filer tags us-gaap:MinorityInterest
- [build_products] 'Total Equity': chose ifrs-full:Equity, filer tags us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest
- [build_products] 'Total Liabilities and Equity': chose ifrs-full:EquityAndLiabilities, filer tags us-gaap:LiabilitiesAndStockholdersEquity
- [build_products] 'Total net sales and revenue (Note 3)': chose ifrs-full:Revenue, filer tags us-gaap:Revenues
- [build_products] 'Operating income (loss)': chose ifrs-full:ProfitLossFromOperatingActivities, filer tags us-gaap:OperatingIncomeLoss
- [build_products] 'Net income (loss)': chose ifrs-full:ProfitLoss, filer tags us-gaap:ProfitLoss
- [build_products] 'Net income (loss)': chose ifrs-full:ProfitLoss, filer tags us-gaap:ProfitLoss
- [build_products] 'Depreciation and impairment of Equipment on operating leases, net': chose us-gaap:DepreciationDepletionAndAmortization, filer tags gm:DepreciationandImpairmentofEquipmentonOperatingLeasesNet
- [build_products] 'Depreciation, amortization and impairment charges on Property, net': chose us-gaap:DepreciationDepletionAndAmortization, filer tags gm:DepreciationamortizationandimpairmentchargesonProperty
- [build_products] 'Foreign currency remeasurement and transaction (gains) losses': chose ifrs-full:EffectOfExchangeRateChangesOnCashAndCashEquivalents, filer tags gm:ForeignCurrencyRemeasurementandTransactionGainsLosses
- [build_products] 'Pension and OPEB income, net': chose sap:OtherNonOperatingIncomeExpensesNet, filer tags us-gaap:PensionAndOtherPostretirementBenefitExpense
- [build_products] 'Change in other operating assets and liabilities (Note 24)': chose us-gaap:IncreaseDecreaseInOtherOperatingLiabilities, filer tags us-gaap:IncreaseDecreaseInOtherOperatingCapitalNet
- [build_products] 'Other operating activities': chose ifrs-full:OtherOperatingIncomeExpense, filer tags us-gaap:OtherOperatingActivitiesCashFlowStatement
- [build_products] 'Available-for-sale marketable securities, acquisitions': chose us-gaap:PaymentsToAcquireAvailableForSaleSecuritiesDebt, filer tags us-gaap:PaymentsToAcquireMarketableSecurities
- [build_products] 'Available-for-sale marketable securities, liquidations': chose us-gaap:ProceedsFromSaleOfAvailableForSaleSecuritiesDebt, filer tags us-gaap:ProceedsFromSaleAndMaturityOfAvailableForSaleSecurities
- [build_products] 'Purchases of finance receivables': chose us-gaap:PaymentsToAcquireInvestments, filer tags us-gaap:PaymentsToAcquireFinanceReceivables
- [build_products] 'Purchases of leased vehicles': chose ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities, filer tags us-gaap:PaymentsToAcquireLeasesHeldForInvestment
- [build_products] 'Net increase (decrease) in short-term debt': chose us-gaap:CommercialPaper, filer tags us-gaap:ProceedsFromRepaymentsOfShortTermDebtMaturingInThreeMonthsOrLess
- [build_products] 'Proceeds from issuance of debt (original maturities greater than three months)': chose us-gaap:ProceedsFromIssuanceOfLongTermDebt, filer tags us-gaap:ProceedsFromDebtMaturingInMoreThanThreeMonths
- [build_products] 'Issuance (redemption) of subsidiary stock (Note 20)': chose us-gaap:ProceedsFromIssuanceOfCommonStock, filer tags us-gaap:PaymentsForRepurchaseOfPreferredStockAndPreferenceStock|us-gaap:ProceedsFromIssuanceOfPreferredStockAndPreferenceStock
- [build_products] 'Dividends paid': chose ifrs-full:DividendsPaidToEquityHoldersOfParentClassifiedAsFinancingActivities, filer tags us-gaap:PaymentsOfDividends

## exxon_2024

Exxon Mobil Corporation 10-K, accession 000003408825000010, period 2024-12-31; document replayed deterministically from its committed artifact (no model constructed).

| Statement | compared | match | mismatch | missing | flagged | gt unmatched |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| balance_sheet | 21 | 0 | 21 | 11 | 8 | 9 |
| income_statement | 60 | 60 | 0 | 0 | 0 | 0 |
| cash_flow | 105 | 105 | 0 | 0 | 0 | 0 |

- balance_sheet mismatch, 'Cash and cash equivalents' column 1: filing 31539000000, document read 23029000000
- balance_sheet mismatch, 'Cash and cash equivalents – restricted' column 1: filing 29000000, document read 158000000
- balance_sheet mismatch, 'Notes and accounts receivable – net' column 1: filing 38015000000, document read 43681000000
- balance_sheet mismatch, 'Crude oil, products and merchandise' column 1: filing 20528000000, document read 19444000000
- balance_sheet ground-truth rows unmatched: 3 derived (unprinted subtotal), 6 leaf, not extracted

#### Concept choices vs the filer's tags

| Statement | source | match | mismatch | off-face |
| --- | --- | ---: | ---: | ---: |
| balance_sheet | build_products | 8 | 7 | 6 |
| income_statement | build_products | 3 | 6 | 1 |
| cash_flow | build_products | 3 | 12 | 0 |

Mismatches:
- [build_products] 'Cash and cash equivalents – restricted': chose us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents, filer tags us-gaap:RestrictedCashAndCashEquivalentsAtCarryingValue
- [build_products] 'Notes and accounts receivable – net 6': chose us-gaap:AccountsReceivableNetCurrent, filer tags us-gaap:ReceivablesNetCurrent
- [build_products] 'Investments, advances and long-term receivables 8': chose us-gaap:LongTermInvestments, filer tags us-gaap:LongTermInvestmentsAndReceivablesNet
- [build_products] 'Other assets, including intangibles – net': chose us-gaap:FiniteLivedIntangibleAssetsNet, filer tags us-gaap:OtherAssetsNoncurrent
- [build_products] 'Accounts payable and accrued liabilities 6': chose us-gaap:AccountsPayableCurrent, filer tags us-gaap:AccountsPayableAndAccruedLiabilitiesCurrent
- [build_products] 'Long-term debt 14': chose us-gaap:LongTermDebtNoncurrent, filer tags us-gaap:LongTermDebtAndCapitalLeaseObligations
- [build_products] 'Common stock without par value (9,000 million shares authorized, 8,019 million shares issued)': chose us-gaap:CommonStockSharesIssued, filer tags us-gaap:CommonStockValue
- [build_products] 'Sales and other operating revenue 18': chose sap:RevenueFromCloudAndSoftware, filer tags us-gaap:Revenues
- [build_products] 'Income from equity affiliates 7': chose ifrs-full:ProfitLossFromOperatingActivities, filer tags us-gaap:Revenues
- [build_products] 'Other income': chose us-gaap:NonoperatingIncomeExpense, filer tags us-gaap:Revenues
- [build_products] 'Production and manufacturing expenses': chose us-gaap:OperatingExpenses, filer tags xom:ProductionAndManufacturingExpenses
- [build_products] 'Exploration expenses, including dry holes': chose ifrs-full:OperatingExpense, filer tags us-gaap:ExplorationExpense
- [build_products] 'Non-service pension and postretirement benefit expense 17': chose us-gaap:GeneralAndAdministrativeExpense, filer tags us-gaap:NetPeriodicDefinedBenefitsExpenseReversalOfExpenseExcludingServiceCostComponent
- [build_products] 'Net income (loss) including noncontrolling interests': chose us-gaap:NetIncomeLoss, filer tags us-gaap:ProfitLoss
- [build_products] 'Notes and accounts receivable reduction/(increase)': chose us-gaap:IncreaseDecreaseInAccountsReceivable, filer tags us-gaap:IncreaseDecreaseInAccountsAndNotesReceivable
- [build_products] 'Accounts and other payables increase/(reduction)': chose ifrs-full:AdjustmentsForIncreaseDecreaseInTradeAndOtherPayables, filer tags us-gaap:IncreaseDecreaseInAccountsPayable
- [build_products] 'Net (gain)/loss on asset sales 5': chose msft:GainLossOnInvestmentsAndDerivativeInstruments, filer tags us-gaap:GainLossOnDispositionOfAssets1
- [build_products] 'All other items - net': chose sap:OtherNonOperatingIncomeExpensesNet, filer tags us-gaap:IncreaseDecreaseInOtherOperatingCapitalNet
- [build_products] 'Additions to property, plant and equipment': chose ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities, filer tags us-gaap:PaymentsToAcquirePropertyPlantAndEquipment
- [build_products] 'Proceeds from asset sales and returns of investments': chose ifrs-full:OtherCashReceiptsFromSalesOfEquityOrDebtInstrumentsOfOtherEntitiesClassifiedAsInvestingActivities, filer tags us-gaap:ProceedsFromSalesOfBusinessAffiliateAndProductiveAssets
- [build_products] 'Additional investments and advances': chose us-gaap:LongTermInvestments, filer tags xom:AdditionalInvestmentsAndAdvances
- [build_products] 'Cash acquired from mergers and acquisitions': chose msft:AcquisitionsNetOfCashAcquiredAndPurchasesOfIntangibleAndOtherAssets, filer tags us-gaap:CashAcquiredFromAcquisition
- [build_products] 'Net cash used in investing activities': chose ifrs-full:CashFlowsFromUsedInInvestingActivities, filer tags us-gaap:NetCashProvidedByUsedInInvestingActivities
- [build_products] 'Additions to short-term debt': chose us-gaap:CommercialPaper, filer tags us-gaap:ProceedsFromShortTermDebtMaturingInMoreThanThreeMonths
- [build_products] 'Additions/(reductions) in debt with three months or less maturity': chose us-gaap:ProceedsFromRepaymentsOfShortTermDebtMaturingInThreeMonthsOrLess, filer tags us-gaap:ProceedsFromRepaymentsOfOtherDebt

## jpmorgan_2024

JPMorgan Chase & Co. 10-K, accession 000001961725000270, period 2024-12-31; document replayed deterministically from its committed artifact (no model constructed).

| Statement | compared | match | mismatch | missing | flagged | gt unmatched |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| balance_sheet | 0 | 0 | 0 | 0 | 0 | 108 |
| income_statement | 84 | 81 | 3 | 0 | 0 | 3 |
| cash_flow | 138 | 136 | 2 | 0 | 0 | 1 |

- balance_sheet ground-truth rows unmatched: 6 derived (unprinted subtotal), 102 leaf, not extracted
- income_statement mismatch, 'Weighted-average basic shares (in shares)' column 0: filing 2873900000, document read 2873.9
- income_statement mismatch, 'Weighted-average basic shares (in shares)' column 1: filing 2938600000, document read 2938.6
- income_statement mismatch, 'Weighted-average basic shares (in shares)' column 2: filing 2965800000, document read 2965.8
- income_statement ground-truth rows unmatched: 1 derived (unprinted subtotal), 2 leaf, not extracted
- cash_flow mismatch, 'Short-term borrowings' column 1: filing None, document read -1934000000
- cash_flow mismatch, 'Short-term borrowings' column 2: filing None, document read -8984000000
- cash_flow ground-truth rows unmatched: 1 leaf, not extracted

#### Concept choices vs the filer's tags

| Statement | source | match | mismatch | off-face |
| --- | --- | ---: | ---: | ---: |
| balance_sheet | build_products | 0 | 0 | 17 |
| income_statement | build_products | 1 | 12 | 1 |
| cash_flow | build_products | 7 | 13 | 0 |

Mismatches:
- [build_products] 'Mortgage fees and related income': chose ifrs-full:FinanceIncome, filer tags jpm:MortgageFeesAndRelatedIncome
- [build_products] 'Card income': chose ifrs-full:OtherOperatingIncomeExpense, filer tags jpm:FeesAndCommissionsCreditAndDebitCards1
- [build_products] 'Other income': chose us-gaap:NonoperatingIncomeExpense, filer tags us-gaap:NoninterestIncomeOther
- [build_products] 'Noninterest revenue': chose ifrs-full:Revenue, filer tags us-gaap:NoninterestIncome
- [build_products] 'Interest income': chose ifrs-full:FinanceIncome, filer tags us-gaap:InterestIncomeOperating
- [build_products] 'Net interest income': chose ifrs-full:FinanceIncomeCost, filer tags us-gaap:InterestIncomeExpenseNet
- [build_products] 'Total net revenue': chose ifrs-full:Revenue, filer tags us-gaap:RevenuesNetOfInterestExpense
- [build_products] 'Compensation expense': chose us-gaap:GeneralAndAdministrativeExpense, filer tags us-gaap:LaborAndRelatedExpense
- [build_products] 'Occupancy expense': chose us-gaap:GeneralAndAdministrativeExpense, filer tags us-gaap:OccupancyNet
- [build_products] 'Technology, communications and equipment expense': chose us-gaap:GeneralAndAdministrativeExpense, filer tags us-gaap:CommunicationsAndInformationTechnology
- [build_products] 'Total noninterest expense': chose ifrs-full:OperatingExpense, filer tags us-gaap:NoninterestExpense
- [build_products] 'Income tax expense': chose ifrs-full:AdjustmentsForIncomeTaxExpense, filer tags us-gaap:IncomeTaxExpenseBenefit
- [build_products] 'Depreciation and amortization': chose us-gaap:DepreciationDepletionAndAmortization, filer tags us-gaap:DepreciationAmortizationAndAccretionNet
- [build_products] 'Trading assets': chose us-gaap:AssetsCurrent, filer tags us-gaap:IncreaseDecreaseInFinancialInstrumentsUsedInOperatingActivities
- [build_products] 'Securities borrowed': chose us-gaap:MarketableSecuritiesCurrent, filer tags us-gaap:IncreaseDecreaseInCashCollateralForBorrowedSecurities
- [build_products] 'Accrued interest and accounts receivable': chose us-gaap:IncreaseDecreaseInAccountsReceivable, filer tags jpm:IncreaseDecreaseInAccruedInterestsAndAccountsReceivable
- [build_products] 'Trading liabilities': chose us-gaap:LiabilitiesCurrent, filer tags us-gaap:IncreaseDecreaseInTradingLiabilities
- [build_products] 'Accounts payable and other liabilities': chose us-gaap:AccountsPayableCurrent, filer tags jpm:IncreaseDecreaseInAccountsPayableAndOtherLiabilities
- [build_products] 'Other operating adjustments': chose ifrs-full:OtherAdjustmentsForNoncashItems, filer tags us-gaap:OtherOperatingActivitiesCashFlowStatement
- [build_products] 'Purchases': chose us-gaap:PaymentsToAcquireInvestments, filer tags us-gaap:PaymentsToAcquireAvailableForSaleSecuritiesDebt|us-gaap:PaymentsToAcquireHeldToMaturitySecurities
- [build_products] 'Purchases': chose us-gaap:PaymentsToAcquireInvestments, filer tags us-gaap:PaymentsToAcquireAvailableForSaleSecuritiesDebt|us-gaap:PaymentsToAcquireHeldToMaturitySecurities
- [build_products] 'Proceeds from sales and securitizations of loans held-for-investment': chose msft:ProceedsFromInvestments, filer tags us-gaap:ProceedsFromSaleOfFinanceReceivables
- [build_products] 'Net cash used in First Republic Acquisition': chose us-gaap:NetCashProvidedByUsedInInvestingActivities, filer tags us-gaap:PaymentsToAcquireBusinessesNetOfCashAcquired
- [build_products] 'All other investing activities, net': chose us-gaap:NetCashProvidedByUsedInInvestingActivities, filer tags us-gaap:PaymentsForProceedsFromOtherInvestingActivities
- [build_products] 'Dividends paid': chose ifrs-full:DividendsPaidToEquityHoldersOfParentClassifiedAsFinancingActivities, filer tags us-gaap:PaymentsOfDividends

## google_2024

Alphabet Inc. 10-K, accession 000165204425000014, period 2024-12-31; document replayed deterministically from its committed artifact (no model constructed).

| Statement | compared | match | mismatch | missing | flagged | gt unmatched |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| balance_sheet | 48 | 48 | 0 | 0 | 0 | 6 |
| income_statement | 39 | 39 | 0 | 0 | 0 | 0 |
| cash_flow | 99 | 99 | 0 | 0 | 0 | 0 |

- balance_sheet ground-truth rows unmatched: 2 derived (unprinted subtotal), 4 leaf, not extracted

#### Concept choices vs the filer's tags

| Statement | source | match | mismatch | off-face |
| --- | --- | ---: | ---: | ---: |
| balance_sheet | build_products | 18 | 2 | 1 |
| income_statement | build_products | 7 | 2 | 0 |
| cash_flow | build_products | 8 | 21 | 0 |

Mismatches:
- [build_products] 'Long-term debt': chose us-gaap:LongTermDebtNoncurrent, filer tags us-gaap:LongTermDebtAndCapitalLeaseObligations
- [build_products] 'Income taxes payable, non-current': chose ifrs-full:NoncurrentLiabilities, filer tags us-gaap:AccruedIncomeTaxesNoncurrent
- [build_products] 'Cost of revenues': chose ifrs-full:CostOfSales, filer tags us-gaap:CostOfRevenue
- [build_products] 'Total costs and expenses': chose us-gaap:OperatingExpenses, filer tags us-gaap:CostsAndExpenses
- [build_products] 'Depreciation of property and equipment': chose ifrs-full:AdjustmentsForDepreciationExpense, filer tags us-gaap:Depreciation
- [build_products] 'Deferred income taxes': chose us-gaap:DeferredIncomeTaxLiabilitiesNet, filer tags us-gaap:DeferredIncomeTaxesAndTaxCredits
- [build_products] 'Loss (gain) on debt and equity securities, net': chose msft:GainLossOnInvestmentsAndDerivativeInstruments, filer tags us-gaap:DebtAndEquitySecuritiesGainLoss
- [build_products] 'Accounts receivable, net': chose us-gaap:AccountsReceivableNetCurrent, filer tags us-gaap:IncreaseDecreaseInAccountsReceivable
- [build_products] 'Income taxes, net': chose us-gaap:IncomeTaxesPaidNet, filer tags us-gaap:IncreaseDecreaseInIncomeTaxes
- [build_products] 'Accounts payable': chose us-gaap:AccountsPayableCurrent, filer tags us-gaap:IncreaseDecreaseInAccountsPayable
- [build_products] 'Accrued expenses and other liabilities': chose ck0001639920:AccruedExpensesAndOtherNonCurrentLiabilities, filer tags us-gaap:IncreaseDecreaseInAccruedLiabilities
- [build_products] 'Deferred revenue': chose us-gaap:ContractWithCustomerLiabilityCurrent, filer tags us-gaap:IncreaseDecreaseInContractWithCustomerLiability
- [build_products] 'Purchases of property and equipment': chose ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities, filer tags us-gaap:PaymentsToAcquirePropertyPlantAndEquipment
- [build_products] 'Purchases of marketable securities': chose us-gaap:PaymentsToAcquireAvailableForSaleSecuritiesDebt, filer tags us-gaap:PaymentsToAcquireMarketableSecurities
- [build_products] 'Maturities and sales of marketable securities': chose us-gaap:ProceedsFromMaturitiesPrepaymentsAndCallsOfAvailableForSaleSecurities, filer tags us-gaap:ProceedsFromSaleAndMaturityOfMarketableSecurities
- [build_products] 'Purchases of non-marketable securities': chose us-gaap:PaymentsToAcquireInvestments, filer tags us-gaap:PaymentsToAcquireOtherInvestments
- [build_products] 'Acquisitions, net of cash acquired, and purchases of intangible assets': chose msft:AcquisitionsNetOfCashAcquiredAndPurchasesOfIntangibleAndOtherAssets, filer tags goog:AcquisitionsNetOfCashAcquiredAndPurchasesOfIntangibleAndOtherAssets
- [build_products] 'Net payments related to stock-based award activities': chose us-gaap:PaymentsRelatedToTaxWithholdingForShareBasedCompensation, filer tags goog:NetProceedsPaymentsRelatedToStockBasedAwardActivities
- [build_products] 'Proceeds from issuance of debt, net of costs': chose us-gaap:ProceedsFromIssuanceOfLongTermDebt, filer tags us-gaap:ProceedsFromDebtNetOfIssuanceCosts
- [build_products] 'Repayments of debt': chose us-gaap:RepaymentsOfDebtMaturingInMoreThanThreeMonths, filer tags us-gaap:RepaymentsOfDebtAndCapitalLeaseObligations
- [build_products] 'Proceeds from sale of interest in consolidated entities, net': chose msft:ProceedsFromInvestments, filer tags us-gaap:ProceedsFromMinorityShareholders
- [build_products] 'Effect of exchange rate changes on cash and cash equivalents': chose ifrs-full:EffectOfExchangeRateChangesOnCashAndCashEquivalents, filer tags us-gaap:EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents
- [build_products] 'Net increase (decrease) in cash and cash equivalents': chose ifrs-full:IncreaseDecreaseInCashAndCashEquivalents, filer tags us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect
- [build_products] 'Cash and cash equivalents at beginning of period': chose ifrs-full:CashAndCashEquivalents, filer tags us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents
- [build_products] 'Cash and cash equivalents at end of period': chose ifrs-full:CashAndCashEquivalents, filer tags us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents

## svb_ar2022

SVB Financial Group 10-K, accession 000071973923000021, period 2022-12-31; document replayed deterministically from its committed artifact (no model constructed).

| Statement | compared | match | mismatch | missing | flagged | gt unmatched |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| balance_sheet | 0 | 0 | 0 | 0 | 0 | 28 |
| income_statement | 123 | 123 | 0 | 0 | 0 | 0 |
| cash_flow | 144 | 144 | 0 | 0 | 0 | 0 |

- balance_sheet ground-truth rows unmatched: 28 leaf, not extracted

#### Concept choices vs the filer's tags

| Statement | source | match | mismatch | off-face |
| --- | --- | ---: | ---: | ---: |
| balance_sheet | build_products | 0 | 0 | 15 |
| income_statement | build_products | 0 | 10 | 0 |
| cash_flow | build_products | 4 | 19 | 0 |

Mismatches:
- [build_products] 'Federal funds sold, securities purchased under agreements to resell and other short-term investment securities': chose us-gaap:CashCashEquivalentsAndShortTermInvestments, filer tags sivb:InterestIncomeFederalFundsSoldAndSecuritiesPurchasedUnderAgreementsToResellAndOtherShortTermInvestments
- [build_products] 'Total interest income': chose ifrs-full:FinanceIncome, filer tags us-gaap:InterestAndDividendIncomeOperating
- [build_products] 'Total interest expense': chose ifrs-full:OperatingExpense, filer tags us-gaap:InterestExpense
- [build_products] 'Gains (losses) on investment securities, net': chose msft:GainLossOnInvestmentsAndDerivativeInstruments, filer tags us-gaap:GainLossOnInvestments
- [build_products] 'Investment banking revenue': chose ifrs-full:Revenue, filer tags us-gaap:InvestmentBankingRevenue
- [build_products] 'Other': chose us-gaap:OtherNoncashIncomeExpense, filer tags us-gaap:NoninterestIncomeOther|us-gaap:OtherNoninterestExpense
- [build_products] 'Total noninterest income': chose ifrs-full:Revenue, filer tags us-gaap:NoninterestIncome
- [build_products] 'Compensation and benefits': chose us-gaap:GeneralAndAdministrativeExpense, filer tags us-gaap:LaborAndRelatedExpense
- [build_products] 'Other': chose us-gaap:OtherNoncashIncomeExpense, filer tags us-gaap:NoninterestIncomeOther|us-gaap:OtherNoninterestExpense
- [build_products] 'Income tax expense': chose ifrs-full:AdjustmentsForIncomeTaxExpense, filer tags us-gaap:IncomeTaxExpenseBenefit
- [build_products] 'Net income before noncontrolling interests': chose us-gaap:NetIncomeLoss, filer tags us-gaap:ProfitLoss
- [build_products] 'Changes in fair values of equity warrant assets, net of proceeds from exercises': chose ifrs-full:ProceedsFromExerciseOfOptions, filer tags sivb:FairValueOfEquityWarrantAssetsNetOfProceeds
- [build_products] 'Changes in fair values of derivatives, net': chose ifrs-full:IncreaseDecreaseInCashAndCashEquivalentsBeforeEffectOfExchangeRateChanges, filer tags us-gaap:UnrealizedGainLossOnDerivatives
- [build_products] '(Gains) losses on investment securities, net': chose msft:GainLossOnInvestmentsAndDerivativeInstruments, filer tags us-gaap:DebtAndEquitySecuritiesGainLoss
- [build_products] 'Distributions of earnings from non-marketable and other equity securities': chose us-gaap:LongTermInvestments, filer tags us-gaap:MarketableSecuritiesRealizedGainLossExcludingOtherThanTemporaryImpairments
- [build_products] 'Depreciation and amortization': chose us-gaap:DepreciationDepletionAndAmortization, filer tags us-gaap:DepreciationAmortizationAndAccretionNet
- [build_products] 'Amortization of premiums and discounts on investment securities, net': chose us-gaap:DepreciationDepletionAndAmortization, filer tags us-gaap:AccretionAmortizationOfDiscountsAndPremiumsInvestments
- [build_products] 'Amortization of share-based compensation': chose ifrs-full:AdjustmentsForSharebasedPayments, filer tags us-gaap:ShareBasedCompensation
- [build_products] 'Amortization of deferred loan fees': chose ifrs-full:AdjustmentsForAmortisationExpense, filer tags us-gaap:AmortizationOfDeferredLoanOriginationFeesNet
- [build_products] 'Excess tax benefit from exercise of stock options and vesting of restricted shares': chose ck0001639920:PaymentsForTaxesWithheldFromRestrictedStockUnitReleases, filer tags sivb:ExcessTaxBenefitExpenseFromShareBasedCompensationOperatingActivities
- [build_products] 'Losses from the write-off of premises and equipment and right-of-use assets': chose ck0001639920:AdjustmentForWriteOffOfContentAssets, filer tags us-gaap:AssetImpairmentCharges
- [build_products] 'Income tax receivable and payable, net': chose ifrs-full:CurrentTaxAssetsCurrent, filer tags us-gaap:IncreaseDecreaseInIncomeTaxesReceivable
- [build_products] 'Accrued compensation': chose us-gaap:EmployeeRelatedLiabilitiesCurrent, filer tags us-gaap:IncreaseDecreaseInDeferredCompensation
- [build_products] 'Other, net': chose us-gaap:ProceedsFromPaymentsForOtherFinancingActivities, filer tags us-gaap:IncreaseDecreaseInOtherOperatingCapitalNet
- [build_products] 'Purchases of HTM securities': chose us-gaap:PaymentsToAcquireInvestments, filer tags us-gaap:PaymentsToAcquireHeldToMaturitySecurities
- [build_products] 'Proceeds from maturities and paydowns of HTM securities': chose us-gaap:ProceedsFromMaturitiesPrepaymentsAndCallsOfAvailableForSaleSecurities, filer tags us-gaap:ProceedsFromMaturitiesPrepaymentsAndCallsOfHeldToMaturitySecurities
- [build_products] 'Purchases of non-marketable and other equity securities': chose us-gaap:LongTermInvestments, filer tags sivb:PaymentsToAcquireNonMarketableandOtherSecurities
- [build_products] 'Proceeds from sales and distributions of capital of non-marketable and other equity securities': chose ifrs-full:OtherCashReceiptsFromSalesOfEquityOrDebtInstrumentsOfOtherEntitiesClassifiedAsInvestingActivities, filer tags sivb:ProceedsFromSaleOfNonmarketableandOtherSecurities
- [build_products] 'Net increase (decrease) in cash and cash equivalents': chose ifrs-full:IncreaseDecreaseInCashAndCashEquivalents, filer tags us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect

## bbby_ar2022

Bed Bath & Beyond Inc. 10-K, accession 000088615823000059, period 2023-02-25; document replayed deterministically from its committed artifact (no model constructed).

| Statement | compared | match | mismatch | missing | flagged | gt unmatched |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| balance_sheet | 60 | 60 | 0 | 0 | 0 | 3 |
| income_statement | 57 | 57 | 0 | 0 | 0 | 0 |
| cash_flow | 138 | 138 | 0 | 0 | 0 | 3 |

- balance_sheet ground-truth rows unmatched: 2 derived (unprinted subtotal), 1 leaf, not extracted
- cash_flow ground-truth rows unmatched: 1 derived (unprinted subtotal), 2 leaf, not extracted

#### Concept choices vs the filer's tags

| Statement | source | match | mismatch | off-face |
| --- | --- | ---: | ---: | ---: |
| balance_sheet | lexical | 10 | 1 | 0 |
| balance_sheet | llm | 3 | 11 | 0 |
| income_statement | lexical | 2 | 1 | 0 |
| income_statement | llm | 4 | 3 | 0 |
| cash_flow | lexical | 2 | 4 | 0 |
| cash_flow | llm | 6 | 7 | 0 |

Mismatches:
- [llm] 'Restricted cash': chose us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents, filer tags us-gaap:RestrictedCashAndCashEquivalentsAtCarryingValue
- [llm] 'Prepaid expenses and other current assets': chose us-gaap:OtherAssetsCurrent, filer tags us-gaap:PrepaidExpenseAndOtherAssetsCurrent
- [llm] 'Property and equipment, net': chose us-gaap:PropertyPlantAndEquipmentNet, filer tags us-gaap:PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization
- [llm] 'Other assets': chose us-gaap:OtherAssetsCurrent, filer tags us-gaap:OtherAssetsNoncurrent
- [llm] 'Current operating lease liabilities': chose ifrs-full:CurrentFinancialLiabilities, filer tags us-gaap:OperatingLeaseLiabilityCurrent
- [llm] 'Preferred stock warrant liabilities': chose us-gaap:OtherLiabilitiesCurrent, filer tags bbby:PreferredStockWarrantLiabilitiesCurrent
- [lexical] 'Derivative liabilities': chose ifrs-full:CurrentDerivativeFinancialLiabilities, filer tags us-gaap:DerivativeLiabilitiesCurrent
- [llm] 'Other liabilities': chose us-gaap:OtherLiabilitiesCurrent, filer tags us-gaap:OtherLiabilitiesNoncurrent
- [llm] 'Income taxes payable': chose us-gaap:AccruedIncomeTaxesCurrent, filer tags us-gaap:AccruedIncomeTaxesNoncurrent
- [llm] 'Common stock - $0.01 par value; authorized - 900,000 shares; issued 382,353 and 344,146, respectively; outstanding 259,033 and 81,979 shares, respectively': chose us-gaap:CommonStocksIncludingAdditionalPaidInCapital, filer tags us-gaap:CommonStockValue
- [llm] 'Additional paid-in capital': chose ifrs-full:AdditionalPaidinCapital, filer tags us-gaap:AdditionalPaidInCapitalCommonStock
- [llm] 'Treasury stock, at cost; 123,320 and 262,167 shares, respectively': chose ifrs-full:TreasuryShares, filer tags us-gaap:TreasuryStockCommonValue
- [lexical] 'Gross profit': chose ifrs-full:GrossProfit, filer tags us-gaap:GrossProfit
- [llm] 'Loss on preferred stock warrants and derivative liabilities': chose msft:GainLossOnInvestmentsAndDerivativeInstruments, filer tags us-gaap:UnrealizedGainLossOnDerivatives
- [llm] 'Net loss per share - Basic': chose ifrs-full:BasicEarningsLossPerShare, filer tags us-gaap:EarningsPerShareBasic
- [llm] 'Net loss per share - Diluted': chose ifrs-full:DilutedEarningsLossPerShare, filer tags us-gaap:EarningsPerShareDiluted
- [llm] 'Loss on preferred stock warrants and derivative liabilities': chose msft:GainLossOnInvestmentsAndDerivativeInstruments, filer tags us-gaap:UnrealizedGainLossOnDerivatives
- [lexical] 'Deferred income taxes': chose us-gaap:DeferredIncomeTaxLiabilitiesNet, filer tags bbby:DeferredIncomeTaxNoncashExpenseBenefit
- [lexical] 'Other current assets': chose us-gaap:OtherAssetsCurrent, filer tags us-gaap:IncreaseDecreaseInOtherCurrentAssets
- [lexical] 'Accounts payable': chose us-gaap:AccountsPayableCurrent, filer tags us-gaap:IncreaseDecreaseInAccountsPayable
- [llm] 'Merchandise credit and gift card liabilities': chose us-gaap:IncreaseDecreaseInOtherOperatingLiabilities, filer tags bbby:IncreaseDecreaseInMerchandiseCreditAndGiftCardLiabilities
- [llm] 'Purchases of held-to-maturity investment securities': chose us-gaap:PaymentsToAcquireInvestments, filer tags us-gaap:PaymentsToAcquireHeldToMaturitySecurities
- [llm] 'Deconsolidation of subsidiaries cash, cash equivalents and restricted cash': chose us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents, filer tags us-gaap:CashDivestedFromDeconsolidation
- [llm] 'Proceeds received from note receivable': chose msft:ProceedsFromInvestments, filer tags us-gaap:ProceedsFromSaleOfNotesReceivable
- [llm] 'Net proceeds from sales of businesses': chose ifrs-full:CashFlowsFromLosingControlOfSubsidiariesOrOtherBusinessesClassifiedAsInvestingActivities, filer tags us-gaap:ProceedsFromDivestitureOfBusinesses
- [llm] 'Net proceeds from sales of property': chose ifrs-full:ProceedsFromDisposalsOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets, filer tags us-gaap:ProceedsFromSaleOfPropertyPlantAndEquipment
- [lexical] 'Repayments of debt': chose us-gaap:RepaymentsOfDebtMaturingInMoreThanThreeMonths, filer tags us-gaap:RepaymentsOfLongTermDebt

## Totals

Accepted cells compared 1343, matching the filing exactly 1316, mismatching 27, missing from the document read 11.
