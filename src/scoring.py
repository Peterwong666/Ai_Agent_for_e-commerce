"""选品评分引擎: 基于规则计算 0-100 综合机会评分."""

from pathlib import Path

import pandas as pd
import yaml


def _load_rules(rules_path: str = "config/scoring_rules.yaml") -> dict:
    """加载评分规则配置, 验证权重总和."""
    with open(rules_path, encoding="utf-8") as f:
        rules = yaml.safe_load(f)

    total = sum(v["weight"] for v in rules.values())
    if total != 100:
        raise ValueError(f"评分权重总和必须为 100, 当前为 {total}")
    return rules


def _level(total: float) -> str:
    if total >= 80:
        return "优先开发"
    elif total >= 65:
        return "进入二次验证"
    elif total >= 50:
        return "谨慎观察"
    return "不建议开发"


def calculate_opportunity_score(
    df: pd.DataFrame,
    metrics: dict,
    risk: dict | None = None,
    rules_path: str = "config/scoring_rules.yaml",
) -> dict:
    """根据清洗后的表格和基础指标, 计算选品机会评分.

    risk: detect_risk_keywords() 的返回值, 用於扣減風險維度得分.
    """
    rules = _load_rules(rules_path)
    product_count = metrics.get("product_count", 0)

    def _reason(dim: str, score: float, detail: str) -> str:
        return f"[{dim}] 得分 {score}/{rules[dim]['weight']}: {detail}"

    dims: dict = {}
    warnings: list[str] = []
    findings: list[str] = []

    # 1. 市场需求 (20)
    weight_md = rules["market_demand"]["weight"]
    total_reviews = metrics.get("total_review_count", 0)
    avg_reviews = metrics.get("avg_review_count", 0)
    md_score = 0
    if total_reviews > 100000:
        md_score = weight_md
    elif total_reviews > 50000:
        md_score = weight_md * 0.8
    elif total_reviews > 20000:
        md_score = weight_md * 0.6
    elif total_reviews > 5000:
        md_score = weight_md * 0.4
    else:
        md_score = weight_md * 0.2
    dims["market_demand"] = {
        "score": round(md_score, 1),
        "reason": _reason("market_demand", md_score, f"总评论 {total_reviews}, 均评论 {avg_reviews}"),
    }
    if total_reviews > 50000:
        findings.append("市场需求强劲, 评论总量大")

    # 2. 竞争强度 (15)
    weight_ci = rules["competition_intensity"]["weight"]
    top_share = metrics.get("top_brand_share", 0)
    avg_rating = metrics.get("avg_rating", 0)
    ci_score = weight_ci * 0.6
    if top_share < 0.1:
        ci_score = weight_ci * 0.9
    elif top_share < 0.2:
        ci_score = weight_ci * 0.7
    elif top_share > 0.4:
        ci_score = weight_ci * 0.3
    if avg_rating > 4.5:
        ci_score = max(ci_score * 0.7, weight_ci * 0.1)
        findings.append(f"平均评分 {avg_rating}, 市场成熟度高, 竞争激烈")
    dims["competition_intensity"] = {
        "score": round(ci_score, 1),
        "reason": _reason("competition_intensity", ci_score, f"Top 品牌占比 {top_share}, 均分 {avg_rating}"),
    }

    # 3. 价格机会 (15)
    weight_po = rules["price_opportunity"]["weight"]
    price_bands = metrics.get("price_bands", {})
    band_count = len([v for v in price_bands.values() if v > 0])
    po_score = weight_po * 0.5
    if band_count >= 4:
        po_score = weight_po * 0.8
        findings.append("价格带分布分散, 存在切入机会")
    elif band_count >= 2:
        po_score = weight_po * 0.6
    dims["price_opportunity"] = {
        "score": round(po_score, 1),
        "reason": _reason("price_opportunity", po_score, f"覆盖 {band_count} 个价格带"),
    }

    # 4. 改良机会 (20)
    weight_io = rules["improvement_opportunity"]["weight"]
    io_score = weight_io * 0.3
    if "rating" in df.columns and "review_count" in df.columns:
        low_high = df[(df["rating"] < 4.3) & (df["review_count"] > df["review_count"].median())]
        low_high_pct = len(low_high) / max(product_count, 1)
        if low_high_pct > 0.3:
            io_score = weight_io * 0.9
            findings.append(f"{len(low_high)} 个产品评分低但评论多, 存在明显改良机会")
        elif low_high_pct > 0.15:
            io_score = weight_io * 0.6
        elif low_high_pct > 0.05:
            io_score = weight_io * 0.4
    dims["improvement_opportunity"] = {
        "score": round(io_score, 1),
        "reason": _reason("improvement_opportunity", io_score, "评分低但评论多的产品比例"),
    }

    # 5. 品牌集中度 (10)
    weight_bc = rules["brand_concentration"]["weight"]
    bc_score = weight_bc * 0.8
    if top_share > 0.3:
        bc_score = weight_bc * 0.3
        warnings.append(f"品牌集中度高 (Top 品牌占比 {top_share}), 新卖家进入难度大")
    elif top_share > 0.15:
        bc_score = weight_bc * 0.5
    dims["brand_concentration"] = {
        "score": round(bc_score, 1),
        "reason": _reason("brand_concentration", bc_score, f"Top 品牌占比 {top_share}"),
    }

    # 6. 风险等级 (10) — 根据 risk_checker 结果扣分
    weight_rl = rules["risk_level"]["weight"]
    rl_score = weight_rl
    if risk:
        rl = risk.get("risk_level", "low")
        if rl == "high":
            rl_score = weight_rl * 0.1
            warnings.append("产品涉及多个高风险关键词, 风险维度大幅扣分")
        elif rl == "medium":
            rl_score = weight_rl * 0.5
            warnings.append(f"产品涉及风险关键词: {', '.join(risk.get('matched_keywords', []))}")
    dims["risk_level"] = {
        "score": round(rl_score, 1),
        "reason": _reason("risk_level", rl_score, f"风险等级: {risk.get('risk_level', 'low') if risk else 'low'}"),
    }

    # 7. 数据质量 (10)
    weight_dq = rules["data_quality"]["weight"]
    expected_cols = {"title", "price", "rating", "review_count", "brand", "rank"}
    present = expected_cols & set(df.columns)
    completeness = len(present) / len(expected_cols) if expected_cols else 0
    dq_score = weight_dq * completeness
    dims["data_quality"] = {
        "score": round(dq_score, 1),
        "reason": _reason("data_quality", dq_score, f"字段完整度 {len(present)}/{len(expected_cols)}"),
    }

    total_score = round(sum(d["score"] for d in dims.values()), 1)

    return {
        "total_score": total_score,
        "level": _level(total_score),
        "dimension_scores": dims,
        "key_findings": findings if findings else ["暂无特殊发现"],
        "warnings": warnings if warnings else ["暂无特别风险"],
    }
