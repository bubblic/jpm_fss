"""Role classification: statement rows -> economic roles.

This is the authored layer of the knowledge graph: it decides which law of
motion and which driver attachment each native line inherits. Rules are
concept-first (a curated table over us-gaap and ifrs-full local names),
then label keywords with the section as context. Extensions inherit
through their labels and anchors. Every assignment is deterministic and
recorded, so a reviewer can audit why a line moved the way it did.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from fss.statements import StatementRow, StructuredStatement

# ---- income statement roles ----
REVENUE = "revenue"
COGS = "cogs"
OPEX_RND = "opex_rnd"
OPEX_SELLING = "opex_selling"
OPEX_ADMIN = "opex_admin"
OPEX_OTHER = "opex_other"
RESTRUCTURING = "restructuring"
INTEREST_INCOME = "interest_income"
INTEREST_EXPENSE = "interest_expense"
OTHER_INCOME = "other_income"
TAX = "tax"
DISCONTINUED = "discontinued"
ATTRIB_PARENT = "attrib_parent"
ATTRIB_NCI = "attrib_nci"
EPS = "eps"
SHARE_COUNT = "share_count"
IS_DERIVED = "is_derived"
GROSS_PROFIT_ROW = "gross_profit_row"  # a filer-printed gross line outside the calc tree

# ---- balance sheet roles ----
CASH = "cash"
SECURITIES = "securities"
AR = "ar"
VENDOR_RECEIVABLE = "vendor_receivable"
INVENTORY = "inventory"
OTHER_CURRENT_ASSET = "other_current_asset"
PPE = "ppe"
LEASE_ROU = "lease_rou"
GOODWILL = "goodwill"
INTANGIBLE = "intangible"
DEFERRED_TAX_ASSET = "deferred_tax_asset"
TAX_RECEIVABLE = "tax_receivable"
OTHER_NONCURRENT_ASSET = "other_noncurrent_asset"
AP = "ap"
ACCRUED = "accrued"
DEFERRED_REVENUE = "deferred_revenue"
COMMERCIAL_PAPER = "commercial_paper"
DEBT = "debt"
LEASE_LIABILITY = "lease_liability"
TAX_LIABILITY = "tax_liability"
PROVISION = "provision"
DERIVATIVE_LIABILITY = "derivative_liability"
OTHER_CURRENT_LIAB = "other_current_liab"
DEFERRED_TAX_LIAB = "deferred_tax_liab"
OTHER_NONCURRENT_LIAB = "other_noncurrent_liab"
COMMON_STOCK_APIC = "common_stock_apic"
TREASURY = "treasury"
RETAINED_EARNINGS = "retained_earnings"
AOCI = "aoci"
NCI_EQUITY = "nci_equity"
OTHER_EQUITY = "other_equity"
COMMITMENTS = "commitments"
BS_DERIVED = "bs_derived"
BS_SHARE_ROW = "bs_share_row"

# ---- cash flow roles ----
CF_NI = "cf_ni"
CF_DA = "cf_da"
CF_SBC = "cf_sbc"
CF_IMPAIRMENT = "cf_impairment"
CF_DEFERRED_TAX = "cf_deferred_tax"
CF_OTHER_NONCASH = "cf_other_noncash"
CF_WC = "cf_wc"  # working-capital delta rows (bound to BS roles)
CF_INTEREST_TAX_ADJ = "cf_interest_tax_adj"
CF_CAPEX = "cf_capex"
CF_ACQUISITION = "cf_acquisition"
CF_INVEST_PURCHASE = "cf_invest_purchase"
CF_INVEST_MATURITY = "cf_invest_maturity"
CF_INVEST_SALE = "cf_invest_sale"
CF_OTHER_INVESTING = "cf_other_investing"
CF_DIVIDENDS = "cf_dividends"
CF_BUYBACK = "cf_buyback"
CF_SBC_TAX_WITHHOLD = "cf_sbc_tax_withhold"
CF_DEBT_ISSUE = "cf_debt_issue"
CF_DEBT_REPAY = "cf_debt_repay"
CF_CP_NET = "cf_cp_net"
CF_LEASE_PAYMENT = "cf_lease_payment"
CF_STOCK_ISSUE = "cf_stock_issue"
CF_OTHER_FINANCING = "cf_other_financing"
CF_FX = "cf_fx"
CF_ACTIVITY_TOTAL = "cf_activity_total"
CF_NET_CHANGE = "cf_net_change"
CF_CASH_BEGIN = "cf_cash_begin"
CF_CASH_END = "cf_cash_end"
CF_SUPPLEMENTAL = "cf_supplemental"
CF_NONCASH_DISCLOSURE = "cf_noncash_disclosure"
CF_TAX_ADDBACK = "cf_tax_addback"  # IFRS: income tax expense added back
CF_FINANCE_ADDBACK = "cf_finance_addback"  # IFRS: net finance items added back
CF_TAX_PAID = "cf_tax_paid"
CF_INTEREST_RECEIVED = "cf_interest_received"
CF_INTEREST_PAID = "cf_interest_paid"
CF_DIVIDENDS_RECEIVED = "cf_dividends_received"
CF_DISCONTINUED = "cf_discontinued"
CF_ASSET_DISPOSAL = "cf_asset_disposal"

# Cash-outflow rows whose base-year value the engine consumes as a
# MAGNITUDE. Tagged filings store these at concept polarity (payments are
# positive facts under negated labels); untagged documents store the
# printed sign (outflows print negative). abs() yields the outflow
# magnitude under both conventions, and a legitimately negative magnitude
# does not exist for these roles. Genuinely signed net rows (CF_CP_NET)
# stay out.
CF_OUTFLOW_MAGNITUDE = frozenset(
    {
        CF_CAPEX,
        CF_DIVIDENDS,
        CF_BUYBACK,
        CF_SBC_TAX_WITHHOLD,
        CF_DEBT_REPAY,
        CF_LEASE_PAYMENT,
        CF_INVEST_PURCHASE,
    }
)

# Concept local-name tables (us-gaap and ifrs-full), the backbone.
CONCEPT_ROLES: dict[str, str] = {
    # income statement
    "RevenueFromContractWithCustomerExcludingAssessedTax": REVENUE,
    "Revenue": REVENUE,
    "RevenueFromSaleOfGoods": REVENUE,
    "RevenueFromRenderingOfServices": REVENUE,
    "CostOfGoodsAndServicesSold": COGS,
    "CostOfRevenue": COGS,
    "CostOfSales": COGS,
    "CostOfMerchandiseSalesBuyingAndOccupancyCosts": COGS,
    "ResearchAndDevelopmentExpense": OPEX_RND,
    "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost": OPEX_RND,
    "SellingAndMarketingExpense": OPEX_SELLING,
    "SellingGeneralAndAdministrativeExpense": OPEX_SELLING,
    "SalesAndMarketingExpense": OPEX_SELLING,
    "GeneralAndAdministrativeExpense": OPEX_ADMIN,
    "AdministrativeExpense": OPEX_ADMIN,
    "GrossProfit": GROSS_PROFIT_ROW,
    "RestructuringCharges": RESTRUCTURING,
    "RestructuringAndOtherExpenses": RESTRUCTURING,
    "OtherOperatingIncomeExpenseNet": OPEX_OTHER,
    "InvestmentIncomeInterest": INTEREST_INCOME,
    "FinanceIncome": INTEREST_INCOME,
    "InterestExpense": INTEREST_EXPENSE,
    "InterestExpenseNonoperating": INTEREST_EXPENSE,
    "FinanceCosts": INTEREST_EXPENSE,
    "NonoperatingIncomeExpense": OTHER_INCOME,
    "OtherNonoperatingIncomeExpense": OTHER_INCOME,
    "IncomeTaxExpenseBenefit": TAX,
    "IncomeTaxExpenseContinuingOperations": TAX,
    "ProfitLossFromDiscontinuedOperations": DISCONTINUED,
    "IncomeLossFromDiscontinuedOperationsNetOfTax": DISCONTINUED,
    "ProfitLossAttributableToOwnersOfParent": ATTRIB_PARENT,
    "NetIncomeLossAttributableToNoncontrollingInterest": ATTRIB_NCI,
    "ProfitLossAttributableToNoncontrollingInterests": ATTRIB_NCI,
    "EarningsPerShareBasic": EPS,
    "EarningsPerShareDiluted": EPS,
    "BasicEarningsLossPerShare": EPS,
    "DilutedEarningsLossPerShare": EPS,
    "BasicEarningsLossPerShareFromContinuingOperations": EPS,
    "DilutedEarningsLossPerShareFromContinuingOperations": EPS,
    "WeightedAverageNumberOfSharesOutstandingBasic": SHARE_COUNT,
    "WeightedAverageNumberOfDilutedSharesOutstanding": SHARE_COUNT,
    "WeightedAverageShares": SHARE_COUNT,
    "WeightedAverageNumberOfOrdinarySharesOutstanding": SHARE_COUNT,
    "AdjustedWeightedAverageNumberOfOrdinarySharesOutstanding": SHARE_COUNT,
    # balance sheet
    "CashAndCashEquivalentsAtCarryingValue": CASH,
    "CashAndCashEquivalents": CASH,
    "MarketableSecuritiesCurrent": SECURITIES,
    "MarketableSecuritiesNoncurrent": SECURITIES,
    "ShortTermInvestments": SECURITIES,
    "CurrentInvestments": SECURITIES,
    "OtherCurrentFinancialAssets": SECURITIES,
    "OtherNoncurrentFinancialAssets": SECURITIES,
    "NoncurrentInvestments": SECURITIES,
    "EquitySecuritiesFvNiNoncurrent": SECURITIES,
    "AccountsReceivableNetCurrent": AR,
    "TradeAndOtherCurrentReceivables": AR,
    "TradeAndOtherNonCurrentReceivables": AR,
    "CurrentTradeReceivables": AR,
    "NontradeReceivablesCurrent": VENDOR_RECEIVABLE,
    "InventoryNet": INVENTORY,
    "Inventories": INVENTORY,
    "OtherAssetsCurrent": OTHER_CURRENT_ASSET,
    "OtherCurrentAssets": OTHER_CURRENT_ASSET,
    "OtherCurrentNonfinancialAssets": OTHER_CURRENT_ASSET,
    "PropertyPlantAndEquipmentNet": PPE,
    "PropertyPlantAndEquipment": PPE,
    "RightofUseAssets": LEASE_ROU,
    "RightOfUseAssets": LEASE_ROU,
    "OperatingLeaseRightOfUseAsset": LEASE_ROU,
    "Goodwill": GOODWILL,
    "IntangibleAssetsOtherThanGoodwill": INTANGIBLE,
    "FiniteLivedIntangibleAssetsNet": INTANGIBLE,
    "IntangibleAssetsNetExcludingGoodwill": INTANGIBLE,
    "DeferredTaxAssets": DEFERRED_TAX_ASSET,
    "DeferredIncomeTaxAssetsNet": DEFERRED_TAX_ASSET,
    "CurrentTaxAssetsCurrent": TAX_RECEIVABLE,
    "CurrentTaxAssets": TAX_RECEIVABLE,
    "OtherAssetsNoncurrent": OTHER_NONCURRENT_ASSET,
    "OtherNoncurrentAssets": OTHER_NONCURRENT_ASSET,
    "OtherNoncurrentNonfinancialAssets": OTHER_NONCURRENT_ASSET,
    "AccountsPayableCurrent": AP,
    "TradeAndOtherCurrentPayables": AP,
    "TradeAndOtherPayablesToTradeSuppliers": AP,
    "TradeAndOtherNonCurrentPayables": AP,
    "AccruedLiabilitiesCurrent": ACCRUED,
    "AccrualsClassifiedAsCurrent": ACCRUED,
    "ContractWithCustomerLiabilityCurrent": DEFERRED_REVENUE,
    "ContractWithCustomerLiabilityNoncurrent": DEFERRED_REVENUE,
    "CurrentContractLiabilities": DEFERRED_REVENUE,
    "NoncurrentContractLiabilities": DEFERRED_REVENUE,
    "DeferredRevenueCurrent": DEFERRED_REVENUE,
    "CommercialPaper": COMMERCIAL_PAPER,
    "LongTermDebtCurrent": DEBT,
    "LongTermDebtNoncurrent": DEBT,
    "LongtermDebtCurrentMaturities": DEBT,
    "ShorttermBorrowings": DEBT,
    "CurrentFinancialLiabilities": DEBT,
    "NoncurrentFinancialLiabilities": DEBT,
    "OperatingLeaseLiabilityCurrent": LEASE_LIABILITY,
    "OperatingLeaseLiabilityNoncurrent": LEASE_LIABILITY,
    "CurrentLeaseLiabilities": LEASE_LIABILITY,
    "NoncurrentLeaseLiabilities": LEASE_LIABILITY,
    "CurrentTaxLiabilitiesCurrent": TAX_LIABILITY,
    "CurrentTaxLiabilities": TAX_LIABILITY,
    "TaxesPayableCurrent": TAX_LIABILITY,
    "AccruedIncomeTaxesNoncurrent": TAX_LIABILITY,
    "CurrentProvisions": PROVISION,
    "NoncurrentProvisions": PROVISION,
    "OtherProvisions": PROVISION,
    "DerivativeFinancialLiabilities": DERIVATIVE_LIABILITY,
    "OtherLiabilitiesCurrent": OTHER_CURRENT_LIAB,
    "OtherCurrentNonfinancialLiabilities": OTHER_CURRENT_LIAB,
    "DeferredTaxLiabilities": DEFERRED_TAX_LIAB,
    "DeferredIncomeTaxLiabilitiesNet": DEFERRED_TAX_LIAB,
    "OtherLiabilitiesNoncurrent": OTHER_NONCURRENT_LIAB,
    "OtherNoncurrentNonfinancialLiabilities": OTHER_NONCURRENT_LIAB,
    "CommonStocksIncludingAdditionalPaidInCapital": COMMON_STOCK_APIC,
    "CommonStockValue": COMMON_STOCK_APIC,
    "CommonStockSharesOutstanding": BS_SHARE_ROW,
    "CommonStockSharesIssued": BS_SHARE_ROW,
    "AdditionalPaidInCapital": COMMON_STOCK_APIC,
    "IssuedCapital": COMMON_STOCK_APIC,
    "SharePremium": COMMON_STOCK_APIC,
    "OtherReserves": AOCI,
    "TreasuryShares": TREASURY,
    "TreasuryStockCommonValue": TREASURY,
    "RetainedEarningsAccumulatedDeficit": RETAINED_EARNINGS,
    "RetainedEarnings": RETAINED_EARNINGS,
    "AccumulatedOtherComprehensiveIncomeLossNetOfTax": AOCI,
    "AccumulatedOtherComprehensiveIncome": AOCI,
    "NoncontrollingInterests": NCI_EQUITY,
    "MinorityInterest": NCI_EQUITY,
    "CommitmentsAndContingencies": COMMITMENTS,
    # cash flow
    "DepreciationDepletionAndAmortization": CF_DA,
    "DepreciationAmortizationAndAccretionNet": CF_DA,
    "DepreciationAndAmortisationExpense": CF_DA,
    "DepreciationExpense": CF_DA,
    "AmortisationExpense": CF_DA,
    "ShareBasedCompensation": CF_SBC,
    "ShareBasedPaymentsExpense": CF_SBC,
    "ImpairmentLossRecognisedInProfitOrLoss": CF_IMPAIRMENT,
    "DeferredIncomeTaxExpenseBenefit": CF_DEFERRED_TAX,
    "OtherNoncashIncomeExpense": CF_OTHER_NONCASH,
    "PaymentsToAcquirePropertyPlantAndEquipment": CF_CAPEX,
    "PurchaseOfPropertyPlantAndEquipment": CF_CAPEX,
    "PaymentsToAcquireBusinessesNetOfCashAcquired": CF_ACQUISITION,
    "CashFlowsUsedInObtainingControlOfSubsidiariesOrOtherBusinessesClassifiedAsInvestingActivities": CF_ACQUISITION,
    "PaymentsToAcquireAvailableForSaleSecuritiesDebt": CF_INVEST_PURCHASE,
    "PaymentsToAcquireInvestments": CF_INVEST_PURCHASE,
    "PurchaseOfFinancialInstrumentsClassifiedAsInvestingActivities": CF_INVEST_PURCHASE,
    "ProceedsFromMaturitiesPrepaymentsAndCallsOfAvailableForSaleSecurities": CF_INVEST_MATURITY,
    "ProceedsFromSaleAndMaturityOfMarketableSecurities": CF_INVEST_MATURITY,
    "ProceedsFromSalesAndMaturityOfFinancialInstrumentsClassifiedAsInvestingActivities": CF_INVEST_MATURITY,
    "ProceedsFromSaleOfAvailableForSaleSecuritiesDebt": CF_INVEST_SALE,
    "PaymentsOfDividends": CF_DIVIDENDS,
    "PaymentsOfDividendsCommonStock": CF_DIVIDENDS,
    "DividendsPaidClassifiedAsFinancingActivities": CF_DIVIDENDS,
    "PaymentsForRepurchaseOfCommonStock": CF_BUYBACK,
    "PaymentsForRepurchaseOfOrdinaryShares": CF_BUYBACK,
    "PaymentsToAcquireOrRedeemEntitysShares": CF_BUYBACK,
    "PaymentsRelatedToTaxWithholdingForShareBasedCompensation": CF_SBC_TAX_WITHHOLD,
    "ProceedsFromIssuanceOfLongTermDebt": CF_DEBT_ISSUE,
    "ProceedsFromIssuingOtherLongtermBorrowings": CF_DEBT_ISSUE,
    "RepaymentsOfLongTermDebt": CF_DEBT_REPAY,
    "RepaymentsOfLongtermBorrowings": CF_DEBT_REPAY,
    "ProceedsFromRepaymentsOfCommercialPaper": CF_CP_NET,
    "PaymentsOfLeaseLiabilitiesClassifiedAsFinancingActivities": CF_LEASE_PAYMENT,
    "FinanceLeasePrincipalPayments": CF_LEASE_PAYMENT,
    "ProceedsFromIssuanceOfCommonStock": CF_STOCK_ISSUE,
    "ProceedsFromExerciseOfOptions": CF_STOCK_ISSUE,
    "ProceedsFromExerciseOfStockOptions": CF_STOCK_ISSUE,
    "EffectOfExchangeRateChangesOnCashAndCashEquivalents": CF_FX,
    "EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents": CF_FX,
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect": CF_NET_CHANGE,
    "IncreaseDecreaseInCashAndCashEquivalents": CF_NET_CHANGE,
    "IncreaseDecreaseInCashAndCashEquivalentsBeforeEffectOfExchangeRateChanges": CF_NET_CHANGE,
    "IncomeTaxesPaidNet": CF_TAX_PAID,
    "IncomeTaxesPaidClassifiedAsOperatingActivities": CF_TAX_PAID,
    "IncomeTaxesPaidRefundClassifiedAsOperatingActivities": CF_TAX_PAID,
    "InterestPaidClassifiedAsOperatingActivities": CF_INTEREST_PAID,
    "InterestPaidClassifiedAsFinancingActivities": CF_INTEREST_PAID,
    "InterestPaidNet": CF_INTEREST_PAID,
    "InterestReceivedClassifiedAsOperatingActivities": CF_INTEREST_RECEIVED,
    "InterestReceivedClassifiedAsInvestingActivities": CF_INTEREST_RECEIVED,
    "DividendsReceivedClassifiedAsOperatingActivities": CF_DIVIDENDS_RECEIVED,
    "DividendsReceivedClassifiedAsInvestingActivities": CF_DIVIDENDS_RECEIVED,
    "AdjustmentsForIncomeTaxExpense": CF_TAX_ADDBACK,
    "AdjustmentsForFinanceIncomeCost": CF_FINANCE_ADDBACK,
    "AdjustmentsForNetFinanceIncomeCost": CF_FINANCE_ADDBACK,
    "AdjustmentsForDepreciationAndAmortisationExpense": CF_DA,
    "AdjustmentsForSharebasedPayments": CF_SBC,
    "AdjustmentsForImpairmentLossRecognisedInProfitOrLoss": CF_IMPAIRMENT,
    "AdjustmentsForDeferredTaxExpense": CF_DEFERRED_TAX,
    "ProceedsFromSalesOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities": CF_ASSET_DISPOSAL,
}

# Label fallback rules, applied in order, with section context available.
LABEL_RULES: tuple[tuple[str, str], ...] = (
    (r"per share|per ordinary share", EPS),
    (r"weighted[- ]average .*shares|shares used in computing", SHARE_COUNT),
    (r"^revenue|net sales|total revenue", REVENUE),
    (r"cost of (revenue|sales|goods)|cost of cloud|cost of software|cost of services", COGS),
    (r"research and development", OPEX_RND),
    (r"sales and marketing|selling", OPEX_SELLING),
    (r"general and administrat", OPEX_ADMIN),
    (r"restructuring", RESTRUCTURING),
    (r"finance income|interest income", INTEREST_INCOME),
    (r"finance costs|interest expense", INTEREST_EXPENSE),
    (r"other (operating )?income", OTHER_INCOME),
    (r"income tax|provision for.*tax", TAX),
    (r"discontinued operations", DISCONTINUED),
    (r"non-?controlling interests?$", ATTRIB_NCI),
    (r"owners of (the )?parent", ATTRIB_PARENT),
    (r"cash and cash equivalents", CASH),
    (r"marketable securities|short term investments|long term investments", SECURITIES),
    (r"accounts receivable|trade (and other )?receivables", AR),
    (r"vendor non-trade receivables", VENDOR_RECEIVABLE),
    (r"inventor", INVENTORY),
    (r"property(,| and)? (plant|equipment)", PPE),
    (r"right-of-use|lease right", LEASE_ROU),
    (r"goodwill", GOODWILL),
    (r"intangible", INTANGIBLE),
    (r"deferred tax assets", DEFERRED_TAX_ASSET),
    (r"income tax receivable|tax assets", TAX_RECEIVABLE),
    (r"accounts payable|trade and other payables", AP),
    (r"accrued", ACCRUED),
    (r"deferred revenue|contract liabilit", DEFERRED_REVENUE),
    (r"commercial paper", COMMERCIAL_PAPER),
    (r"term debt|borrowings|exchangeable notes|financial liabilit", DEBT),
    (r"lease liabilit", LEASE_LIABILITY),
    (r"income tax payable|tax liabilit", TAX_LIABILITY),
    (r"provisions", PROVISION),
    (r"derivative liabilit", DERIVATIVE_LIABILITY),
    (r"deferred tax liabilit", DEFERRED_TAX_LIAB),
    (r"common stock|share capital|issued capital|share premium|paid[- ]?in capital", COMMON_STOCK_APIC),
    (r"treasury", TREASURY),
    (r"retained earnings|accumulated deficit", RETAINED_EARNINGS),
    (r"accumulated other comprehensive|other reserves", AOCI),
    (r"commitments and contingencies", COMMITMENTS),
    (r"depreciation|amorti[sz]ation", CF_DA),
    (r"share-based (compensation|payment)", CF_SBC),
    (r"impairment|write-off", CF_IMPAIRMENT),
    (r"deferred (income )?tax", CF_DEFERRED_TAX),
)


@dataclass(frozen=True)
class RoleAssignment:
    role: str
    source: str  # "concept" | "label" | "section" | "default"


def classify_row(row: StatementRow, statement_kind: str) -> RoleAssignment:
    if row.kind == "abstract":
        return RoleAssignment("", "default")
    local = row.concept.split(":", 1)[1] if ":" in row.concept else row.concept
    if row.kind == "derived":
        if statement_kind == "cash_flow":
            mapped = CONCEPT_ROLES.get(local)
            if mapped in (CF_NET_CHANGE,):
                return RoleAssignment(CF_NET_CHANGE, "concept")
            return RoleAssignment(CF_ACTIVITY_TOTAL, "default")
        return RoleAssignment(
            IS_DERIVED if statement_kind == "income_statement" else BS_DERIVED, "default"
        )
    if statement_kind == "cash_flow":
        return _classify_cf_leaf(row, local)
    mapped = CONCEPT_ROLES.get(local)
    if mapped:
        return RoleAssignment(mapped, "concept")
    label = f"{' '.join(row.section)} {row.label}".lower()
    for pattern, role in LABEL_RULES:
        if re.search(pattern, label):
            return RoleAssignment(role, "label")
    if statement_kind == "income_statement":
        return RoleAssignment(OPEX_OTHER, "default")
    # balance-sheet default by side and section
    section = " ".join(row.section).lower()
    if row.balance == "debit":
        role = OTHER_CURRENT_ASSET if "current" in section and "non-current" not in section else OTHER_NONCURRENT_ASSET
    elif "equity" in section:
        role = OTHER_EQUITY
    else:
        role = OTHER_CURRENT_LIAB if "current" in section and "non-current" not in section else OTHER_NONCURRENT_LIAB
    return RoleAssignment(role, "section")


def _classify_cf_leaf(row: StatementRow, local: str) -> RoleAssignment:
    preferred = (row.preferred_label or "").lower()
    if row.period_type == "instant":
        return RoleAssignment(
            CF_CASH_BEGIN if "periodstart" in preferred else CF_CASH_END, "concept"
        )
    section = " ".join(row.section).lower()
    label = row.label.lower()
    if "discontinued" in label:
        return RoleAssignment(CF_DISCONTINUED, "label")
    mapped = CONCEPT_ROLES.get(local)
    if mapped:
        return RoleAssignment(mapped, "concept")
    if "supplemental" in section or "supplemental" in label:
        return RoleAssignment(CF_SUPPLEMENTAL, "section")
    if "non-cash" in section or "noncash" in section:
        return RoleAssignment(CF_NONCASH_DISCLOSURE, "section")
    if re.search(r"share-based payment", label) and "expense" not in label:
        # the cash settlement of share plans, not the expense add-back
        return RoleAssignment(CF_SBC_TAX_WITHHOLD, "label")
    if re.search(r"income tax(es)? paid", label):
        return RoleAssignment(CF_TAX_PAID, "label")
    if re.search(r"interest received", label):
        return RoleAssignment(CF_INTEREST_RECEIVED, "label")
    if re.search(r"interest paid", label):
        return RoleAssignment(CF_INTEREST_PAID, "label")
    if re.search(r"dividends received", label):
        return RoleAssignment(CF_DIVIDENDS_RECEIVED, "label")
    if re.search(r"income tax expense", label):
        return RoleAssignment(CF_TAX_ADDBACK, "label")
    if re.search(r"financial income|finance income|finance costs?", label):
        return RoleAssignment(CF_FINANCE_ADDBACK, "label")
    if "allowance" in label:
        return RoleAssignment(CF_OTHER_NONCASH, "label")
    if re.search(r"changes in operating|working capital|increase|decrease|\(increase\)", label + " " + section):
        if re.search(r"changes in|working capital", section) or re.search(
            r"^\(?(increase|decrease)", label
        ):
            return RoleAssignment(CF_WC, "section")
    for pattern, role in LABEL_RULES:
        if re.search(pattern, label):
            if role in (CF_DA, CF_SBC, CF_IMPAIRMENT, CF_DEFERRED_TAX):
                return RoleAssignment(role, "label")
    if re.search(r"net income|net loss|profit.*after tax|loss.*after tax", label):
        return RoleAssignment(CF_NI, "label")
    if "operating" in section:
        # remaining operating rows: working-capital style deltas of named
        # balance-sheet lines ("Accounts receivable, net") or other non-cash
        if re.search(r"receivable|inventor|payable|deferred revenue|assets|liabilit|provisions", label):
            return RoleAssignment(CF_WC, "section")
        return RoleAssignment(CF_OTHER_NONCASH, "section")
    if "investing" in section:
        if re.search(r"acquisition of (companies|businesses)|business combination", label):
            return RoleAssignment(CF_ACQUISITION, "label")
        if re.search(r"(proceeds|sales?) .*(property|equipment|intangible)", label):
            return RoleAssignment(CF_ASSET_DISPOSAL, "label")
        if re.search(r"(purchases?|additions?) .*(property|equipment|intangible)", label):
            return RoleAssignment(CF_CAPEX, "label")
        if re.search(r"purchases? of", label):
            return RoleAssignment(CF_INVEST_PURCHASE, "label")
        if re.search(
            r"maturities|sales? of .*(investments|securities|instruments)", label
        ):
            return RoleAssignment(CF_INVEST_MATURITY, "label")
        if re.search(r"property|equipment|intangible", label):
            return RoleAssignment(CF_CAPEX, "label")
        return RoleAssignment(CF_OTHER_INVESTING, "section")
    if "financing" in section:
        if re.search(r"repurchase", label):
            return RoleAssignment(CF_BUYBACK, "label")
        if re.search(r"dividend", label):
            return RoleAssignment(CF_DIVIDENDS, "label")
        if re.search(r"\bnet\b", label) and re.search(r"proceeds|issuance", label) and re.search(
            r"repayments?|maturities", label
        ):
            return RoleAssignment(CF_CP_NET, "label")  # net short-term borrowing line
        if re.search(r"repayment", label):
            return RoleAssignment(CF_DEBT_REPAY, "label")
        if re.search(r"taxes withheld|tax withholding", label):
            return RoleAssignment(CF_SBC_TAX_WITHHOLD, "label")
        if re.search(r"issuance of debt|proceeds from.*(debt|borrowings|notes)", label):
            return RoleAssignment(CF_DEBT_ISSUE, "label")
        if re.search(r"exercise of (stock )?options|issuance of.*shares|common stock issued", label):
            return RoleAssignment(CF_STOCK_ISSUE, "label")
        if re.search(r"lease", label):
            return RoleAssignment(CF_LEASE_PAYMENT, "label")
        return RoleAssignment(CF_OTHER_FINANCING, "section")
    if re.search(r"exchange rate|effect of.*exchange", label):
        return RoleAssignment(CF_FX, "label")
    if re.search(r"(increase|decrease).*cash", label):
        return RoleAssignment(CF_NET_CHANGE, "label")
    return RoleAssignment(CF_OTHER_NONCASH, "default")


def classify_statement(statement: StructuredStatement) -> dict[tuple[str, tuple], RoleAssignment]:
    """(concept, dims, period role) -> role for every row of the statement."""
    out: dict[tuple[str, tuple], RoleAssignment] = {}
    for row in statement.rows:
        assignment = classify_row(row, statement.statement)
        key = (row.concept, row.dims, _row_period_role(row))
        out[key] = assignment
    if statement.statement == "income_statement":
        _propagate_through_calc(statement, out)
    return out


def _propagate_through_calc(
    statement: StructuredStatement, out: dict[tuple, RoleAssignment]
) -> None:
    """Leaves under a revenue or cost-of-revenue calculation parent inherit
    its role: filers disaggregate with extension concepts ("Cloud revenue",
    "Cost of cloud") that no static table can list."""
    anchor_roles = {REVENUE, COGS}
    concept_role: dict[str, str] = {}
    for row in statement.rows:
        local = row.concept.split(":", 1)[-1]
        mapped = CONCEPT_ROLES.get(local)
        if mapped in anchor_roles:
            concept_role[row.concept] = mapped
            continue
        key = (row.concept, row.dims, _row_period_role(row))
        assignment = out.get(key)
        if assignment and assignment.role in anchor_roles:
            concept_role[row.concept] = assignment.role
    # walk down the calc tree from anchored concepts
    changed = True
    while changed:
        changed = False
        for parent, kids in statement.calc_children.items():
            parent_role = concept_role.get(parent)
            if not parent_role:
                continue
            for child, _ in kids:
                if child not in concept_role:
                    concept_role[child] = parent_role
                    changed = True
    for row in statement.rows:
        if row.kind != "leaf":
            continue
        key = (row.concept, row.dims, _row_period_role(row))
        inherited = concept_role.get(row.concept)
        current = out.get(key)
        if inherited and current and current.role in (OPEX_OTHER, OTHER_INCOME):
            out[key] = RoleAssignment(inherited, "calc")


def _row_period_role(row: StatementRow) -> str:
    preferred = (row.preferred_label or "").lower()
    if row.period_type == "instant" and "periodstart" in preferred:
        return "start"
    if row.period_type == "instant" and "periodend" in preferred:
        return "end"
    return ""
