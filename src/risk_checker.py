"""风险关键词识别: 根据产品标题和类目识别潜在风险品类."""

import re

import pandas as pd

EN_RISK_WORDS = [
    "baby", "kids", "children", "toy", "medical", "health", "supplement",
    "electric", "battery", "wireless", "heated", "magnetic", "knife",
    "laser", "glass", "fragile", "liquid", "chemical", "patent",
    "disney", "marvel", "pokemon", "nintendo", "lego",
]

ZH_RISK_WORDS = [
    "婴儿", "儿童", "玩具", "医疗", "保健", "带电", "电池",
    "无线", "加热", "磁吸", "刀", "激光", "玻璃", "易碎",
    "液体", "化学", "专利", "迪士尼", "漫威", "宝可梦",
]


def detect_risk_keywords(df: pd.DataFrame) -> dict:
    """根据标题和类目信息识别潜在风险."""
    matched: set[str] = set()
    risk_reasons: list[str] = []

    text_cols = [col for col in ["title", "category"] if col in df.columns]
    if not text_cols:
        return {"risk_level": "low", "matched_keywords": [], "risk_reasons": []}

    parts: list[str] = []
    for col in text_cols:
        parts.extend(df[col].dropna().astype(str).str.lower().tolist())
    all_text = " ".join(parts)

    for w in EN_RISK_WORDS:
        if re.search(r'\b' + re.escape(w) + r'\b', all_text):
            matched.add(w)
    for w in ZH_RISK_WORDS:
        if w in all_text:
            matched.add(w)

    safety_words = {"baby", "kids", "children", "toy", "婴儿", "儿童", "玩具"}
    ip_words = {"disney", "marvel", "pokemon", "nintendo", "lego", "迪士尼", "漫威", "宝可梦", "patent", "专利"}
    cert_words = {"electric", "battery", "wireless", "heated", "带电", "电池", "无线", "加热"}
    fragile_words = {"glass", "fragile", "liquid", "易碎", "玻璃", "液体"}

    if matched & safety_words:
        risk_reasons.append("涉及儿童/婴儿用品, 需关注安全认证要求 (CPC/ASTM)")
    if matched & ip_words:
        risk_reasons.append("涉及知名 IP 或专利, 需确认不侵权")
    if matched & cert_words:
        risk_reasons.append("涉及电子/电池产品, 需关注 FCC/UL/CE 认证")
    if matched & fragile_words:
        risk_reasons.append("涉及易碎/液体产品, 物流和包装成本较高")

    if len(matched) >= 5 or (matched & ip_words):
        level = "high"
    elif len(matched) >= 2 or (matched & safety_words):
        level = "medium"
    else:
        level = "low"

    return {
        "risk_level": level,
        "matched_keywords": sorted(matched),
        "risk_reasons": risk_reasons if risk_reasons else ["未发现明显高风险关键词"],
    }
