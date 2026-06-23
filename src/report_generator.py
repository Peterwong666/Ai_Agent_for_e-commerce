"""本地 Markdown 报告生成: 不依赖 AI, 使用模板渲染."""

from datetime import date


def generate_markdown_report(
    metrics: dict,
    scoring: dict,
    risk: dict,
    brand: dict,
    market_insights: dict | None = None,
) -> str:
    """基于模板生成本地 Markdown 报告 (无 AI 回退方案)."""
    today = date.today().isoformat()

    lines: list[str] = []
    lines.append("# 选品分析报告")
    lines.append("")
    lines.append(f"> 生成日期: {today}")
    lines.append("> 生成方式: 规则引擎 (本地报告)")
    lines.append("")

    # 1
    lines.append("## 1. 基础信息")
    lines.append(f"- 分析产品数: {metrics.get('product_count', 0)}")
    lines.append(f"- 品牌数: {brand.get('brand_count', 'N/A')}")
    lines.append("")

    # 2
    lines.append("## 2. 类目概况")
    lines.append(f"- 平均价格: ${metrics.get('avg_price', 0)}")
    lines.append(f"- 中位价格: ${metrics.get('median_price', 0)}")
    lines.append(f"- 价格区间: ${metrics.get('min_price', 0)} - ${metrics.get('max_price', 0)}")
    lines.append(f"- 平均评分: {metrics.get('avg_rating', 0)}")
    lines.append(f"- 平均评论数: {metrics.get('avg_review_count', 0)}")
    lines.append(f"- 评论总数: {metrics.get('total_review_count', 0)}")
    lines.append("")

    # 3
    lines.append("## 3. 市场需求判断")
    total_reviews = metrics.get("total_review_count", 0)
    if total_reviews > 50000:
        lines.append("市场需求**强劲**, 评论总量大。")
    elif total_reviews > 20000:
        lines.append("市场需求**良好**。")
    elif total_reviews > 0:
        lines.append("市场需求**一般**, 评论量偏小。")
    else:
        lines.append("暂无评论数据。")
    lines.append("")

    # 4
    lines.append("## 4. 竞争强度判断")
    top_share = brand.get("top_1_brand_share", 0)
    if top_share > 0.3:
        lines.append(f"品牌集中度较高 (Top 1 占比 {top_share:.1%}), 竞争**激烈**。")
    elif top_share > 0.15:
        lines.append(f"品牌集中度中等, 竞争**适中**。")
    else:
        lines.append("品牌集中度较低, 新卖家有**进入机会**。")
    lines.append("")

    # 5
    lines.append("## 5. 价格带分析")
    price_bands = metrics.get("price_bands", {})
    if price_bands:
        lines.append("| 价格带 | 产品数 |")
        lines.append("|--------|--------|")
        for band, count in price_bands.items():
            lines.append(f"| {band} | {count} |")
    lines.append("")

    # 6
    lines.append("## 6. 品牌集中度分析")
    if brand.get("top_brands"):
        lines.append("| 品牌 | 产品数 | 占比 |")
        lines.append("|------|--------|------|")
        for b in brand["top_brands"][:5]:
            lines.append(f"| {b['brand']} | {b['count']} | {b['share']:.1%} |")
    lines.append("")

    # 7
    lines.append("## 7. 潜在产品机会")
    findings = scoring.get("key_findings", [])
    for f in findings:
        lines.append(f"- {f}")
    lines.append("")

    # 7.5
    market_insights = market_insights or {}
    if market_insights:
        lines.append("## Google Trends 关键词")
        keywords = market_insights.get("trend_keywords", [])
        if keywords:
            lines.append(f"- 关键词: {', '.join(keywords)}")
        if market_insights.get("google_trends_url"):
            lines.append(f"- 链接: {market_insights['google_trends_url']}")
        lines.append("- 区域: 美国; 时间范围: 2004 年至今; 其它默认")
        lines.append("")

        lines.append("## 竞品对比")
        competitors = market_insights.get("competitors", {})
        if competitors:
            lines.append("| 类型 | ASIN | 单价 | 品牌 | 月销量 | 优点 | 缺点 | 关键词 | 季节性 |")
            lines.append("|------|------|------|------|--------|------|------|--------|--------|")
            for comp in competitors.values():
                lines.append(
                    f"| {comp.get('label', 'N/A')} | {comp.get('asin', 'N/A')} | "
                    f"${comp.get('price', 0)} | {comp.get('brand', 'N/A')} | "
                    f"{comp.get('monthly_sales', 0)} | {comp.get('advantages', 'N/A')} | "
                    f"{comp.get('disadvantages', 'N/A')} | {comp.get('keywords', 'N/A')} | "
                    f"{comp.get('seasonal', 'N/A')} |"
                )
        lines.append("")

        top10 = market_insights.get("top10_selling_points", {})
        lines.append("## Top10 卖点共性")
        for item in top10.get("summary", []):
            lines.append(f"- {item}")
        if top10.get("common_phrases"):
            lines.append(f"- 共同短语: {', '.join(top10['common_phrases'][:8])}")
        if top10.get("review_data_note"):
            lines.append(f"- 评论分析缺口: {top10['review_data_note']}")
        lines.append("")

    # 8
    lines.append("## 8. 可能的差异化方向")
    for d in ["材质升级 (BPA-Free → 不锈钢/陶瓷)", "尺寸组合 (多尺寸套装)", "颜色/图案差异化",
              "包装升级 (礼物盒/环保包装)", "说明书优化 (多语言/图解)", "场景化定位 (旅行/慢食/训练)"]:
        lines.append(f"- {d}")
    lines.append("")

    # 9
    lines.append("## 9. 风险点")
    for r in risk.get("risk_reasons", []):
        lines.append(f"- {r}")
    lines.append(f"\n风险等级: **{risk.get('risk_level', 'N/A')}**")
    if risk.get("matched_keywords"):
        lines.append(f"匹配关键词: {', '.join(risk['matched_keywords'])}")
    lines.append("")

    # 10
    lines.append("## 10. 综合评分")
    total = scoring.get("total_score", 0)
    level = scoring.get("level", "N/A")
    lines.append(f"**总分: {total}/100**  \n**等级: {level}**")
    dims = scoring.get("dimension_scores", {})
    if dims:
        lines.append("| 维度 | 得分 |")
        lines.append("|------|------|")
        for dim_name, dim_data in dims.items():
            lines.append(f"| {dim_name} | {dim_data['score']} |")
    lines.append("")

    # 11
    lines.append("## 11. 是否建议进入产品开发")
    if total >= 65:
        lines.append(f"**建议进行二次验证** (得分 {total})。需要进一步验证供应链和差异化方案。")
    elif total >= 50:
        lines.append(f"**谨慎观察** (得分 {total})。建议先验证关键风险。")
    else:
        lines.append(f"**暂不建议开发** (得分 {total})。风险较高或机会有限。")
    lines.append("")

    # 12
    lines.append("## 12. 下一步验证清单")
    tasks = [
        "手动查看 Top 10 竞品详情页",
        "收集 Top 10 竞品 1-3 星差评",
        "查询 1688 / Alibaba 供应价",
        "估算 FBA 费用和头程费用",
        "检查是否涉及专利 / 外观侵权",
        "检查是否涉及认证 (CPC/FCC/UL/CE)",
        "对比 3 个可差异化方向",
        "选择 1-2 个方向做产品定义",
    ]
    for i, t in enumerate(tasks, 1):
        lines.append(f"{i}. {t}")
    lines.append("")

    lines.append("---")
    lines.append("> ⚠️ 本报告由规则引擎自动生成 (无 AI 增强)。")
    lines.append("> 所有分析结论仅作为选品辅助参考, 不能替代人工验证。")

    return "\n".join(lines)
