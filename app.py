"""跨境电商选品 AI Agent — Streamlit 入口."""

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.ai_reporter import (
    answer_user_question,
    generate_ai_report,
    get_deepseek_config_status,
    test_deepseek_connection,
)
from src.data_cleaner import clean_product_data
from src.data_loader import load_table
from src.db import get_analysis_run, list_analysis_runs
from src.field_mapper import map_fields
from src.metrics import (
    analyze_price_opportunity,
    calculate_basic_metrics,
    calculate_brand_concentration,
)
from src.market_insights import (
    build_google_trends_iframe_html,
    build_market_insights,
    capture_google_trends_screenshot,
)
from src.report_generator import generate_markdown_report
from src.risk_checker import detect_risk_keywords
from src.scoring import calculate_opportunity_score

SAMPLE_PATH = Path("data/samples/amazon_top100_sample.csv")

st.set_page_config(page_title="跨境电商选品 AI Agent", layout="wide")
st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"], .main {
        overflow-y: auto !important;
    }
    [data-testid="stDataFrame"] {
        max-height: 420px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("跨境电商选品 AI Agent")
st.markdown("上传 Amazon 类目 Top 100 表格（卖家精灵导出），自动分析并生成选品报告。")


def _format_money(value) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _analysis_base_name(market: str, category: str) -> str:
    today = date.today().isoformat()
    cat_slug = category.replace(" ", "_").replace("/", "_") if category else "analysis"
    return f"{market}_{cat_slug}_{today}"


def _display_band_chart(title: str, values: dict, index_name: str) -> None:
    st.subheader(title)
    chart_df = pd.DataFrame({index_name: list(values.keys()), "产品数": list(values.values())})
    if chart_df["产品数"].sum() > 0:
        st.bar_chart(chart_df.set_index(index_name), use_container_width=True)
    else:
        st.info(f"{title}暂无可计算数据，请检查上传表格是否包含对应字段。")


def _render_market_insights(insights: dict) -> None:
    st.markdown("---")
    st.subheader("Google Trends 关键词")
    keywords = insights.get("trend_keywords", [])
    trends_url = insights.get("google_trends_url", "")
    if keywords and trends_url:
        st.write("、".join(f"`{kw}`" for kw in keywords))
        st.caption("区域: 美国 | 时间范围: 2004-01-01 至今 | 其它保持默认")
        col1, col2 = st.columns(2)
        with col1:
            st.link_button("打开 Google Trends", trends_url, use_container_width=True)
        with col2:
            st.download_button(
                "复制/下载 Trends 链接",
                data=trends_url,
                file_name="google_trends_link.txt",
                mime="text/plain",
                use_container_width=True,
            )

        with st.expander("页面内预览 Google Trends", expanded=True):
            components.html(build_google_trends_iframe_html(trends_url), height=680, scrolling=True)
            st.caption("如果 Google 阻止内嵌或显示空白，请点击上方按钮在新窗口打开。")

        if st.button("保存趋势截图", use_container_width=True):
            with st.spinner("正在打开 Google Trends 并截图..."):
                result = capture_google_trends_screenshot(trends_url)
            if result.get("ok"):
                st.image(result["path"], caption="Google Trends: 热度随时间变化")
            else:
                st.warning(f"自动截图失败: {result.get('error')}")
                st.info("请点击上方链接打开 Google Trends 后手动截图。")
    else:
        st.info("标题关键词不足，无法生成 Google Trends 链接。")

    st.markdown("---")
    st.subheader("4 个竞品对比")
    competitors = list(insights.get("competitors", {}).values())
    if competitors:
        cols = st.columns(len(competitors))
        for col, comp in zip(cols, competitors):
            with col:
                st.caption(comp.get("label", "竞品"))
                image_url = comp.get("image_url")
                if image_url:
                    st.image(image_url, use_container_width=True)
                st.write(f"**ASIN:** {comp.get('asin', 'N/A')}")
                st.write(f"**单价:** {_format_money(comp.get('price'))}")
                st.write(f"**品牌:** {comp.get('brand', 'N/A')}")
                st.write(f"**月销量:** {comp.get('monthly_sales', 0):,}")
                st.write(f"**关键词:** {comp.get('keywords', '') or 'N/A'}")
                st.write(f"**季节性:** {comp.get('seasonal', 'N/A')}")
                st.caption(comp.get("reason", ""))

        comp_df = pd.DataFrame(competitors)
        display_cols = [
            "label",
            "asin",
            "price",
            "brand",
            "monthly_sales",
            "advantages",
            "disadvantages",
            "keywords",
            "seasonal",
        ]
        st.dataframe(comp_df[display_cols], use_container_width=True, hide_index=True, height=260)
    else:
        st.info("缺少月销量等字段，无法筛选竞品。")

    st.markdown("---")
    st.subheader("前 10 名产品卖点分析")
    top10 = insights.get("top10_selling_points", {})
    for item in top10.get("summary", []):
        st.write(f"- {item}")
    if top10.get("common_phrases"):
        st.caption("共同短语: " + ", ".join(top10["common_phrases"][:8]))
    if top10.get("common_keywords"):
        st.caption("高频词: " + ", ".join(top10["common_keywords"][:12]))
    if top10.get("review_analysis_required"):
        st.warning(top10.get("review_data_note"))


def _render_analysis(payload: dict) -> None:
    df = payload["df"]
    metrics = payload["metrics"]
    brand = payload["brand"]
    price_opp = payload["price_opp"]
    risk = payload["risk"]
    scoring = payload["scoring"]
    report_md = payload["report_md"]
    market_insights = payload.get("market_insights", {})

    st.markdown("---")
    st.subheader("基础指标")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("产品数", metrics["product_count"])
    col2.metric("平均价格", _format_money(metrics["avg_price"]))
    col3.metric("中位价格", _format_money(metrics["median_price"]))
    col4.metric("平均评分", metrics["avg_rating"])
    col5.metric("评论总数", f"{metrics['total_review_count']:,}")

    st.markdown("---")
    _display_band_chart("价格带分布", metrics["price_bands"], "价格带")
    _display_band_chart("评论数分布", metrics["review_count_distribution"], "区间")

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("品牌集中度")
        if brand["top_brands"]:
            brand_df = pd.DataFrame(brand["top_brands"][:5])
            brand_df["share"] = brand_df["share"].apply(lambda x: f"{x:.1%}")
            st.dataframe(brand_df[["brand", "count", "share"]], use_container_width=True, height=220)
        else:
            st.info("缺少品牌字段，无法计算品牌集中度。")
        st.caption(
            f"Top 1: {brand['top_1_brand_share']:.1%} | "
            f"Top 3: {brand['top_3_brand_share']:.1%} | "
            f"Top 5: {brand['top_5_brand_share']:.1%}"
        )
    with col2:
        st.subheader("价格机会")
        st.metric("主流价格带", price_opp.get("main_price_band", "N/A"))
        lo, hi = price_opp.get("suggested_entry_price_range", [0, 0])
        st.caption(f"建议切入: {_format_money(lo)} - {_format_money(hi)}")
        st.caption(f"低端竞争: {price_opp.get('low_price_competition', 'N/A')}")
        st.caption(f"中端机会: {price_opp.get('mid_price_opportunity', 'N/A')}")
        st.caption(f"高端机会: {price_opp.get('premium_price_opportunity', 'N/A')}")
    with col3:
        st.subheader("风险检测")
        st.metric("风险等级", risk["risk_level"])
        if risk["matched_keywords"]:
            st.write("匹配风险词:", ", ".join(risk["matched_keywords"]))
        for reason in risk.get("risk_reasons", []):
            st.info(reason)

    st.markdown("---")
    st.subheader(f"综合评分: {scoring['total_score']}/100 — {scoring['level']}")
    st.progress(scoring["total_score"] / 100)

    dims = scoring["dimension_scores"]
    dim_df = pd.DataFrame(
        [
            {
                "维度": name,
                "得分": value["score"],
                "满分": 20 if name in ("market_demand", "improvement_opportunity")
                else 15 if name in ("competition_intensity", "price_opportunity")
                else 10,
                "依据": value.get("reason", ""),
            }
            for name, value in dims.items()
        ]
    )
    st.dataframe(dim_df, use_container_width=True, hide_index=True, height=280)

    col1, col2 = st.columns(2)
    with col1:
        st.caption("关键发现")
        for finding in scoring.get("key_findings", []):
            st.write(f"- {finding}")
    with col2:
        st.caption("注意事项")
        for warning in scoring.get("warnings", []):
            st.write(f"- {warning}")

    st.markdown("---")
    st.subheader("产品机会候选 (评分低但评论多的产品)")
    if "rating" in df.columns and "review_count" in df.columns:
        candidate_df = df.copy()
        candidate_df["rating"] = pd.to_numeric(candidate_df["rating"], errors="coerce")
        candidate_df["review_count"] = pd.to_numeric(candidate_df["review_count"], errors="coerce")
        med_reviews = candidate_df["review_count"].median()
        opp_candidates = candidate_df[
            (candidate_df["rating"] < 4.3)
            & (candidate_df["review_count"] > med_reviews)
        ].head(10)
        if not opp_candidates.empty:
            cols = [c for c in ["rank", "title", "brand", "price", "rating", "review_count"] if c in opp_candidates]
            st.dataframe(opp_candidates[cols], use_container_width=True, hide_index=True, height=320)
        else:
            st.info("当前数据中未发现评分低但评论多的明显机会产品。")
    else:
        st.info("缺少 rating 或 review_count 字段，无法计算产品机会。")

    _render_market_insights(market_insights)

    st.markdown("---")
    st.subheader("选品分析报告")
    report_status = payload.get("report_status", {})
    if report_status.get("type") == "ai":
        st.success("AI 报告已生成")
    elif report_status.get("message"):
        st.info(report_status["message"])
    st.markdown(report_md)

    st.markdown("---")
    base_name = _analysis_base_name(payload["market"], payload["category"])
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "下载 Markdown 报告",
            data=report_md,
            file_name=f"report_{base_name}.md",
            mime="text/markdown",
        )
    with col2:
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "下载清洗后 CSV",
            data=csv_data,
            file_name=f"cleaned_{base_name}.csv",
            mime="text/csv",
        )

    st.markdown("---")
    st.subheader("继续提问")
    st.caption("基于当前表格、类目信息和已计算指标回答。")
    question = st.text_area(
        "请输入你的问题",
        placeholder="例如：这个类目最适合切入哪个价格带？有哪些差异化方向？",
        height=100,
    )
    if st.button("让 AI 回答", type="secondary", use_container_width=True):
        if not question.strip():
            st.warning("请先输入问题。")
        else:
            with st.spinner("AI 正在基于当前表格回答..."):
                try:
                    answer = answer_user_question(
                        question,
                        df,
                        metrics,
                        scoring,
                        risk,
                        brand,
                        price_opp,
                        market_insights,
                    )
                    st.markdown(answer)
                except Exception as exc:
                    st.warning(f"AI 问答失败: {type(exc).__name__}: {exc}")


st.sidebar.header("分析设置")

market = st.sidebar.selectbox("目标市场", ["US", "UK", "DE", "JP", "CA"], index=0)
category = st.sidebar.text_input("类目名称", placeholder="例如: Pet Supplies > Dog Bowls")
price_min = st.sidebar.number_input("目标最低售价 ($)", min_value=0.0, value=10.0, step=1.0)
price_max = st.sidebar.number_input("目标最高售价 ($)", min_value=0.0, value=30.0, step=1.0)

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader(
    "上传 Amazon Top 100 表格",
    type=["csv", "xlsx", "xls"],
    help="支持 CSV / XLSX 格式",
)

if st.sidebar.button("使用示例数据 (Dog Slow Feeder Bowl)"):
    st.session_state["use_sample"] = True

use_sample = st.session_state.get("use_sample", False)

st.sidebar.markdown("---")
st.sidebar.subheader("DeepSeek")
deepseek_status = get_deepseek_config_status()
if deepseek_status["issues"]:
    st.sidebar.warning("配置需检查")
    for issue in deepseek_status["issues"]:
        st.sidebar.caption(issue)
else:
    st.sidebar.success(f"配置格式正常: {deepseek_status['model']}")

if st.sidebar.button("测试 DeepSeek 连接"):
    with st.sidebar:
        with st.spinner("正在测试 DeepSeek..."):
            result = test_deepseek_connection()
        if result["ok"]:
            st.success(f"连接成功: {result.get('response', 'OK')}")
        else:
            st.error("连接失败")
            if result.get("error"):
                st.caption(f"{result.get('error_type')}: {result['error']}")

st.sidebar.markdown("---")
st.sidebar.subheader("历史记录")
try:
    runs = list_analysis_runs(limit=10)
    if runs:
        for run in runs:
            label = (
                f"[{run['level']}] {run['market']} - "
                f"{run['category_name'] or 'N/A'} ({run['created_at'][:10]})"
            )
            if st.sidebar.button(label, key=f"hist_{run['id']}"):
                detail = get_analysis_run(run["id"])
                if detail and detail.get("report_markdown"):
                    st.session_state["history_report"] = detail["report_markdown"]
                    st.session_state["history_title"] = label
    else:
        st.sidebar.caption("暂无历史记录")
except Exception as exc:
    st.sidebar.caption(f"数据库错误: {exc}")

if st.session_state.get("history_report"):
    with st.expander(f"历史报告: {st.session_state.get('history_title', '')}", expanded=True):
        st.markdown(st.session_state["history_report"])

df: pd.DataFrame | None = None
source_name = ""

if use_sample:
    df = load_table(str(SAMPLE_PATH))
    source_name = "sample.csv"
    st.sidebar.success(f"已加载示例数据: {len(df)} 行")
elif uploaded_file is not None:
    df = load_table(uploaded_file)
    source_name = uploaded_file.name
    st.sidebar.success(f"已上传: {uploaded_file.name} ({len(df)} 行)")

if df is not None:
    source_key = f"{source_name}:{len(df)}:{','.join(map(str, df.columns))}"
    if st.session_state.get("analysis_source_key") != source_key:
        st.session_state.pop("analysis_payload", None)
        st.session_state["analysis_source_key"] = source_key

    st.markdown("---")

    try:
        df = map_fields(df)
        df = clean_product_data(df)
    except Exception as exc:
        st.error(f"数据处理失败: {exc}")
        st.stop()

    st.subheader("数据预览")
    st.dataframe(df.head(10), use_container_width=True, height=320)
    st.caption(f"共 {len(df)} 条记录, {len(df.columns)} 个字段")

    if st.button("开始分析", type="primary", use_container_width=True):
        with st.spinner("正在分析..."):
            metrics = calculate_basic_metrics(df)
            brand = calculate_brand_concentration(df)
            price_opp = analyze_price_opportunity(df)
            risk = detect_risk_keywords(df)
            scoring = calculate_opportunity_score(df, metrics, risk)
            market_insights = build_market_insights(df)

            try:
                report_md = generate_ai_report(df, metrics, scoring, risk, brand, market_insights)
                report_status = {"type": "ai"}
            except RuntimeError as exc:
                report_md = generate_markdown_report(metrics, scoring, risk, brand, market_insights)
                report_status = {"type": "local", "message": f"使用本地模板报告 ({exc})"}
            except Exception as exc:
                report_md = generate_markdown_report(metrics, scoring, risk, brand, market_insights)
                report_status = {
                    "type": "local",
                    "message": f"AI 报告生成失败 ({type(exc).__name__}: {exc}), 已回退到本地报告",
                }

            payload = {
                "df": df,
                "metrics": metrics,
                "brand": brand,
                "price_opp": price_opp,
                "risk": risk,
                "scoring": scoring,
                "market_insights": market_insights,
                "report_md": report_md,
                "report_status": report_status,
                "market": market,
                "category": category or "",
                "source_key": source_key,
            }
            st.session_state["analysis_payload"] = payload

            try:
                from src.db import save_analysis_run

                save_analysis_run(
                    market=market,
                    category_name=category or "",
                    file_name=source_name or "sample.csv",
                    product_count=len(df),
                    total_score=scoring["total_score"],
                    level=scoring["level"],
                    metrics_json=metrics,
                    scoring_json=scoring,
                    risk_json=risk,
                    report_markdown=report_md,
                )
            except Exception as exc:
                st.warning(f"分析记录保存失败: {exc}")

    if st.session_state.get("analysis_payload"):
        _render_analysis(st.session_state["analysis_payload"])

else:
    if st.session_state.get("analysis_payload"):
        _render_analysis(st.session_state["analysis_payload"])
    else:
        st.info("请上传 CSV/XLSX 文件或点击「使用示例数据」开始分析。")
        st.markdown(
            """
            ### 支持的数据格式
            - **CSV** (.csv) — 卖家精灵直接导出
            - **Excel** (.xlsx / .xls) — 手动整理表格

            ### 必要字段
            | 字段 | 说明 | 示例 |
            |------|------|------|
            | title / 商品标题 | 产品名称 | Dog Slow Feeder Bowl |
            | price / 价格 / 售价 | 售价 (美元) | 19.99 |
            | rating / 评分 / 商品评分 | 评分 (1-5) | 4.5 |
            | review_count / 评论数 / 评分数 | 评论数量 | 4521 |

            字段名支持中英文, 系统自动识别映射。
            """
        )
