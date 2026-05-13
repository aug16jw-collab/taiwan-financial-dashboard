from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

METRIC_DEFS = [
    ("毛利率(%)",        "gross_margin",   "%"),
    ("營業利益率(%)",    "op_margin",      "%"),
    ("淨利率(%)",        "net_margin",     "%"),
    ("ROE(%)",           "roe",            "%"),
    ("ROA(%)",           "roa",            "%"),
    ("流動比率(x)",      "current_ratio",  "x"),
    ("負債比率(%)",      "debt_ratio",     "%"),
    ("EPS(元)",          "eps",            "元"),
    ("每股淨值(元)",     "bvps",           "元"),
    ("營業收入(千元)",   "revenue",        "千元"),
    ("營業毛利(千元)",   "gross_profit",   "千元"),
    ("營業利益(千元)",   "op_income",      "千元"),
    ("稅後淨利(千元)",   "net_income",     "千元"),
    ("總資產(千元)",     "total_assets",   "千元"),
    ("股東權益(千元)",   "equity",         "千元"),
    ("自由現金流(千元)", "free_cf",        "千元"),
]

METRIC_LABELS = [m[0] for m in METRIC_DEFS]
METRIC_FIELDS = [m[1] for m in METRIC_DEFS]
METRIC_UNITS  = {m[1]: m[2] for m in METRIC_DEFS}

# (good_threshold, higher_is_good, bad_threshold)
THRESHOLDS = {
    "gross_margin":  (20,  True,  10),
    "op_margin":     (5,   True,  0),
    "net_margin":    (5,   True,  0),
    "roe":           (10,  True,  0),
    "roa":           (5,   True,  0),
    "current_ratio": (1.5, True,  1.0),
    "debt_ratio":    (50,  False, 70),
    "eps":           (1,   True,  0),
    "free_cf":       (0,   True,  None),
}

QUALITY_CRITERIA = {
    "gross_margin": (">=", 20),
    "op_margin":    (">=", 5),
    "roe":          (">=", 10),
    "free_cf":      (">",  0),
}

COLOR_LISTED = "#D6E4F7"
COLOR_OTC    = "#D6F0DB"
COLOR_GOOD   = "#C6EFCE"
COLOR_BAD    = "#FFC7CE"
COLOR_BLUE   = "#1F5CA8"
COLOR_GREEN  = "#217A3C"
COLOR_DARK   = "#2E4057"
