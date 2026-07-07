"""Chinese-language statement support (HK/PRC annual-report sections).

US-listed Chinese filers publish HK annual reports whose English half is
often image-based while the Chinese half carries a text layer. The face
lines of those statements follow a small, stable vocabulary, so a curated
label table maps them onto the same US GAAP concepts the English pipeline
uses. This is taxonomy mapping, not financial data: no values live here.

Matching is exact on a normalized form (spaces, full-width punctuation,
list dashes, and leading 減：/加： markers stripped), traditional and
simplified variants both listed. Unmatched rows stay unmapped, per the
abstain rule.
"""
from __future__ import annotations

import re

# (concept local name, balance, period_type)
_C = tuple[str, str, str]

_LABELS: dict[str, _C] = {
    # income statement
    "收入": ("Revenues", "credit", "duration"),
    "營業收入": ("Revenues", "credit", "duration"),
    "营业收入": ("Revenues", "credit", "duration"),
    "營業成本": ("CostOfRevenue", "debit", "duration"),
    "营业成本": ("CostOfRevenue", "debit", "duration"),
    "產品開發費用": ("ResearchAndDevelopmentExpense", "debit", "duration"),
    "产品开发费用": ("ResearchAndDevelopmentExpense", "debit", "duration"),
    "研發費用": ("ResearchAndDevelopmentExpense", "debit", "duration"),
    "研发费用": ("ResearchAndDevelopmentExpense", "debit", "duration"),
    "銷售及市場費用": ("SellingAndMarketingExpense", "debit", "duration"),
    "销售及市场费用": ("SellingAndMarketingExpense", "debit", "duration"),
    "一般及行政費用": ("GeneralAndAdministrativeExpense", "debit", "duration"),
    "一般及行政费用": ("GeneralAndAdministrativeExpense", "debit", "duration"),
    "無形資產攤銷": ("AmortizationOfIntangibleAssets", "debit", "duration"),
    "无形资产摊销": ("AmortizationOfIntangibleAssets", "debit", "duration"),
    "無形資產攤銷及減值": ("AmortizationOfIntangibleAssets", "debit", "duration"),
    "商譽減值": ("GoodwillImpairmentLoss", "debit", "duration"),
    "商誉减值": ("GoodwillImpairmentLoss", "debit", "duration"),
    "成本及費用總額": ("CostsAndExpenses", "debit", "duration"),
    "成本及费用总额": ("CostsAndExpenses", "debit", "duration"),
    "經營利潤": ("OperatingIncomeLoss", "credit", "duration"),
    "经营利润": ("OperatingIncomeLoss", "credit", "duration"),
    "利息收入": ("InvestmentIncomeInterest", "credit", "duration"),
    "利息費用": ("InterestExpense", "debit", "duration"),
    "利息费用": ("InterestExpense", "debit", "duration"),
    "權益法核算的投資收益": ("IncomeLossFromEquityMethodInvestments", "credit", "duration"),
    "权益法核算的投资收益": ("IncomeLossFromEquityMethodInvestments", "credit", "duration"),
    "所得稅費用": ("IncomeTaxExpenseBenefit", "debit", "duration"),
    "所得税费用": ("IncomeTaxExpenseBenefit", "debit", "duration"),
    "稅前利潤": ("IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest", "credit", "duration"),
    "税前利润": ("IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest", "credit", "duration"),
    "淨利潤": ("ProfitLoss", "credit", "duration"),
    "净利润": ("ProfitLoss", "credit", "duration"),
    "年度利潤": ("ProfitLoss", "credit", "duration"),
    "歸屬於普通股股東的淨利潤": ("NetIncomeLoss", "credit", "duration"),
    "归属于普通股股东的净利润": ("NetIncomeLoss", "credit", "duration"),
    # balance sheet
    "現金及現金等價物": ("CashAndCashEquivalentsAtCarryingValue", "debit", "instant"),
    "现金及现金等价物": ("CashAndCashEquivalentsAtCarryingValue", "debit", "instant"),
    "短期投資": ("ShortTermInvestments", "debit", "instant"),
    "短期投资": ("ShortTermInvestments", "debit", "instant"),
    "應收賬款": ("AccountsReceivableNetCurrent", "debit", "instant"),
    "应收账款": ("AccountsReceivableNetCurrent", "debit", "instant"),
    "預付款項": ("PrepaidExpenseAndOtherAssetsCurrent", "debit", "instant"),
    "预付款项": ("PrepaidExpenseAndOtherAssetsCurrent", "debit", "instant"),
    "存貨": ("InventoryNet", "debit", "instant"),
    "存货": ("InventoryNet", "debit", "instant"),
    "物業及設備": ("PropertyPlantAndEquipmentNet", "debit", "instant"),
    "物业及设备": ("PropertyPlantAndEquipmentNet", "debit", "instant"),
    "物業及設備淨值": ("PropertyPlantAndEquipmentNet", "debit", "instant"),
    "無形資產": ("IntangibleAssetsNetExcludingGoodwill", "debit", "instant"),
    "无形资产": ("IntangibleAssetsNetExcludingGoodwill", "debit", "instant"),
    "商譽": ("Goodwill", "debit", "instant"),
    "商誉": ("Goodwill", "debit", "instant"),
    "流動資產總額": ("AssetsCurrent", "debit", "instant"),
    "流动资产总额": ("AssetsCurrent", "debit", "instant"),
    "流動資產合計": ("AssetsCurrent", "debit", "instant"),
    "總資產": ("Assets", "debit", "instant"),
    "总资产": ("Assets", "debit", "instant"),
    "資產總額": ("Assets", "debit", "instant"),
    "资产总额": ("Assets", "debit", "instant"),
    "應付賬款": ("AccountsPayableCurrent", "credit", "instant"),
    "应付账款": ("AccountsPayableCurrent", "credit", "instant"),
    "遞延收入": ("ContractWithCustomerLiabilityCurrent", "credit", "instant"),
    "递延收入": ("ContractWithCustomerLiabilityCurrent", "credit", "instant"),
    "遞延收入及客戶預付款": ("ContractWithCustomerLiabilityCurrent", "credit", "instant"),
    "流動負債總額": ("LiabilitiesCurrent", "credit", "instant"),
    "流动负债总额": ("LiabilitiesCurrent", "credit", "instant"),
    "流動負債合計": ("LiabilitiesCurrent", "credit", "instant"),
    "總負債": ("Liabilities", "credit", "instant"),
    "总负债": ("Liabilities", "credit", "instant"),
    "負債總額": ("Liabilities", "credit", "instant"),
    "负债总额": ("Liabilities", "credit", "instant"),
    "留存收益": ("RetainedEarningsAccumulatedDeficit", "credit", "instant"),
    "保留盈利": ("RetainedEarningsAccumulatedDeficit", "credit", "instant"),
    "額外實收資本": ("AdditionalPaidInCapital", "credit", "instant"),
    "额外实收资本": ("AdditionalPaidInCapital", "credit", "instant"),
    "非控制性權益": ("MinorityInterest", "credit", "instant"),
    "非控制性权益": ("MinorityInterest", "credit", "instant"),
    "股東權益總額": ("StockholdersEquity", "credit", "instant"),
    "股东权益总额": ("StockholdersEquity", "credit", "instant"),
    "股東權益合計": ("StockholdersEquity", "credit", "instant"),
    # cash flow
    "經營活動產生的現金流量淨額": ("NetCashProvidedByUsedInOperatingActivities", "", "duration"),
    "经营活动产生的现金流量净额": ("NetCashProvidedByUsedInOperatingActivities", "", "duration"),
    "投資活動所用的現金流量淨額": ("NetCashProvidedByUsedInInvestingActivities", "", "duration"),
    "投資活動產生的現金流量淨額": ("NetCashProvidedByUsedInInvestingActivities", "", "duration"),
    "投资活动产生的现金流量净额": ("NetCashProvidedByUsedInInvestingActivities", "", "duration"),
    "融資活動產生的現金流量淨額": ("NetCashProvidedByUsedInFinancingActivities", "", "duration"),
    "融資活動所用的現金流量淨額": ("NetCashProvidedByUsedInFinancingActivities", "", "duration"),
    "筹资活动产生的现金流量净额": ("NetCashProvidedByUsedInFinancingActivities", "", "duration"),
    "現金及現金等價物淨增加額": ("CashAndCashEquivalentsPeriodIncreaseDecrease", "", "duration"),
    "现金及现金等价物净增加额": ("CashAndCashEquivalentsPeriodIncreaseDecrease", "", "duration"),
    "匯率變動對現金及現金等價物的影響": ("EffectOfExchangeRateOnCashAndCashEquivalents", "", "duration"),
    "折舊及攤銷": ("DepreciationDepletionAndAmortization", "debit", "duration"),
    "折旧及摊销": ("DepreciationDepletionAndAmortization", "debit", "duration"),
    "股權激勵費用": ("ShareBasedCompensation", "debit", "duration"),
    "股权激励费用": ("ShareBasedCompensation", "debit", "duration"),
    "購置物業及設備": ("PaymentsToAcquirePropertyPlantAndEquipment", "credit", "duration"),
    "购置物业及设备": ("PaymentsToAcquirePropertyPlantAndEquipment", "credit", "duration"),
}

_STRIP = re.compile(r"[\s（）()：:，,、。．\.\-－—–]|^減|^减|^加|^除|^less|^add", re.IGNORECASE)
_TRAILING_NOTE = re.compile(r"[（(][^（）()]*[）)]$")
_CJK = re.compile(r"[一-鿿]")


def has_cjk(text: str) -> bool:
    return bool(_CJK.search(text))


def normalize(label: str) -> str:
    text = _TRAILING_NOTE.sub("", label.strip())
    return _STRIP.sub("", text)


def lookup(label: str) -> tuple[str, str, str] | None:
    """(concept local name, balance, period_type) for a Chinese face line."""
    return _LABELS.get(normalize(label))
