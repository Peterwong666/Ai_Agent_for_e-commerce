"""市场趋势、竞品和卖点分析辅助函数."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import quote
from html import escape

import pandas as pd

STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "pack",
    "set",
    "size",
    "color",
    "baby",
    "boys",
    "girls",
    "unisex",
}

SEASONAL_TERMS = {
    "christmas",
    "halloween",
    "easter",
    "thanksgiving",
    "winter",
    "summer",
    "swim",
    "pool",
    "beach",
    "school",
    "holiday",
}


def _text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9]+", text.lower())
    return [word for word in words if word not in STOPWORDS and len(word) > 2]


def _safe_number(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def extract_title_keywords(df: pd.DataFrame, limit: int = 4) -> list[str]:
    """从产品标题中提取用于 Google Trends 的关键词/短语."""
    if "title" not in df.columns or df.empty:
        return []

    unigram_counts: Counter[str] = Counter()
    bigram_counts: Counter[str] = Counter()

    for title in df["title"].dropna():
        words = _tokens(str(title))
        unigram_counts.update(words)
        bigram_counts.update(
            f"{words[i]} {words[i + 1]}" for i in range(len(words) - 1)
        )

    selected: list[str] = []
    for phrase, count in bigram_counts.most_common():
        if count < 2:
            continue
        if not any(phrase in item or item in phrase for item in selected):
            selected.append(phrase)
        if len(selected) >= limit:
            return selected

    for word, _ in unigram_counts.most_common():
        if not any(word in item.split() for item in selected):
            selected.append(word)
        if len(selected) >= limit:
            break

    return selected


def build_google_trends_url(keywords: list[str], geo: str = "US") -> str:
    """生成 Google Trends 链接: 美国, 2004-01-01 至今."""
    cleaned = [kw.strip() for kw in keywords if kw and kw.strip()][:5]
    encoded_keywords = ",".join(quote(kw) for kw in cleaned)
    today = date.today().isoformat()
    return (
        "https://trends.google.com/trends/explore"
        f"?date=2004-01-01%20{today}&geo={geo}&q={encoded_keywords}"
    )


def build_google_trends_iframe_html(url: str, height: int = 640) -> str:
    """生成内嵌 Google Trends 的 iframe HTML."""
    safe_url = escape(url, quote=True)
    safe_height = max(int(height), 320)
    return (
        f'<iframe src="{safe_url}" width="100%" height="{safe_height}" '
        'style="border:0; width:100%; background:#fff;" '
        'loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>'
    )


def _first_matching_row(df: pd.DataFrame, mask, sort_col: str = "monthly_sales") -> pd.Series | None:
    candidates = df[mask].copy()
    if candidates.empty:
        return None
    if sort_col in candidates.columns:
        candidates[sort_col] = pd.to_numeric(candidates[sort_col], errors="coerce").fillna(0)
        candidates = candidates.sort_values(sort_col, ascending=False)
    return candidates.iloc[0]


def _row_to_competitor(row: pd.Series | None, label: str, reason: str) -> dict:
    if row is None:
        return {
            "label": label,
            "reason": reason,
            "asin": "N/A",
            "title": "N/A",
            "brand": "N/A",
            "price": 0,
            "monthly_sales": 0,
            "image_url": "",
            "advantages": "N/A",
            "disadvantages": "N/A",
            "keywords": "",
            "seasonal": "N/A",
        }

    title = _text(row.get("title"))
    bullet_points = _text(row.get("bullet_points"))
    product_keywords = extract_title_keywords(pd.DataFrame([row.to_dict()]), limit=4)
    rating = _safe_number(row.get("rating"))
    review_count = _safe_number(row.get("review_count"))
    seller_count = _safe_number(row.get("seller_count"))

    advantages = _summarize_advantages(title, bullet_points, rating, review_count)
    disadvantages = _summarize_disadvantages(row, seller_count)

    return {
        "label": label,
        "reason": reason,
        "asin": _text(row.get("asin")) or "N/A",
        "title": title or "N/A",
        "brand": _text(row.get("brand")) or "N/A",
        "price": _safe_number(row.get("price")),
        "monthly_sales": int(_safe_number(row.get("monthly_sales"))),
        "image_url": _text(row.get("image_url")),
        "advantages": advantages,
        "disadvantages": disadvantages,
        "keywords": ", ".join(product_keywords),
        "seasonal": "是" if _is_seasonal(title, _text(row.get("category"))) else "否",
    }


def _summarize_advantages(title: str, bullet_points: str, rating: float, review_count: float) -> str:
    text = f"{title}\n{bullet_points}".lower()
    signals = []
    for term in ["waterproof", "reusable", "adjustable", "leakproof", "soft", "breathable", "washable"]:
        if term in text:
            signals.append(term)
    if rating >= 4.5:
        signals.append("高评分")
    if review_count >= 1000:
        signals.append("评论验证充分")
    return ", ".join(dict.fromkeys(signals)) or "需查看详情页和评论验证"


def _summarize_disadvantages(row: pd.Series, seller_count: float) -> str:
    signals = []
    rating = _safe_number(row.get("rating"))
    review_count = _safe_number(row.get("review_count"))
    listing_days = _safe_number(row.get("listing_days"))
    if rating and rating < 4.0:
        signals.append("评分偏低")
    if review_count < 100:
        signals.append("评论样本少")
    if listing_days < 180:
        signals.append("上架时间短")
    if seller_count > 3:
        signals.append("卖家数较多")
    return ", ".join(signals) or "表格未显示明显短板"


def _is_seasonal(title: str, category: str) -> bool:
    text = f"{title} {category}".lower()
    return any(term in text for term in SEASONAL_TERMS)


def select_competitors(df: pd.DataFrame) -> dict[str, dict]:
    """按业务规则选择 4 个竞品."""
    work = df.copy()
    for col in ["monthly_sales", "listing_days", "rating"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")

    if "fulfillment" not in work.columns:
        work["fulfillment"] = ""

    head = _first_matching_row(work, work["monthly_sales"].notna())
    new_hot = _first_matching_row(
        work,
        (work.get("listing_days", pd.Series(index=work.index, dtype=float)) < 180)
        & (work.get("monthly_sales", pd.Series(index=work.index, dtype=float)) >= 450)
        & (work["fulfillment"].astype(str).str.upper() == "FBA"),
    )
    optimizable = _first_matching_row(
        work,
        work.get("rating", pd.Series(index=work.index, dtype=float)) < 4,
    )
    new_fast = _first_matching_row(
        work,
        (work.get("listing_days", pd.Series(index=work.index, dtype=float)) < 60)
        & (work.get("monthly_sales", pd.Series(index=work.index, dtype=float)) > 100),
    )

    return {
        "head_seller": _row_to_competitor(head, "竞品1 头部卖家", "月销量最大产品"),
        "new_hot": _row_to_competitor(new_hot, "竞品2 新上架热销", "上架天数 < 180, 月销量 >= 450, FBA"),
        "optimizable": _row_to_competitor(optimizable, "竞品3 可优化产品", "评分 < 4 的产品中销量最高"),
        "new_fast_seller": _row_to_competitor(new_fast, "竞品4 新上架销量大", "上架天数 < 60, 月销量 > 100"),
    }


def analyze_top_selling_points(df: pd.DataFrame, top_n: int = 10) -> dict:
    """分析前 N 名产品标题和卖点的共性."""
    if df.empty:
        return {
            "analyzed_count": 0,
            "common_keywords": [],
            "common_phrases": [],
            "summary": [],
            "review_analysis_required": True,
            "review_data_note": "需要下载评论后才能分析用户认可/吐槽/购买动机/改进点。",
        }

    work = df.copy()
    if "rank" in work.columns:
        work["rank"] = pd.to_numeric(work["rank"], errors="coerce")
        work = work.sort_values("rank")
    top = work.head(top_n)

    combined_text = []
    for _, row in top.iterrows():
        combined_text.append(_text(row.get("title")))
        combined_text.append(_text(row.get("bullet_points")))

    token_counts = Counter()
    phrase_counts = Counter()
    for text in combined_text:
        words = _tokens(text)
        token_counts.update(words)
        phrase_counts.update(f"{words[i]} {words[i + 1]}" for i in range(len(words) - 1))

    common_keywords = [word for word, _ in token_counts.most_common(12)]
    common_phrases = [phrase for phrase, count in phrase_counts.most_common(8) if count >= 2]

    summary = []
    for term in ["waterproof", "reusable", "adjustable", "leakproof", "soft", "breathable", "washable"]:
        if term in common_keywords:
            summary.append(f"Top{len(top)} 高频卖点包含 {term}")
    if not summary:
        summary.append("Top 产品共同点主要集中在标题高频词和基础功能表达, 建议结合评论进一步验证。")

    return {
        "analyzed_count": len(top),
        "common_keywords": common_keywords,
        "common_phrases": common_phrases,
        "summary": summary,
        "review_analysis_required": True,
        "review_data_note": "需要下载评论后才能分析用户认可最多的优点、吐槽最多的点、购买动机和具体改进点。",
    }


def build_market_insights(df: pd.DataFrame) -> dict:
    """生成页面和 AI 报告需要的市场洞察上下文."""
    keywords = extract_title_keywords(df, limit=4)
    return {
        "trend_keywords": keywords,
        "google_trends_url": build_google_trends_url(keywords) if keywords else "",
        "competitors": select_competitors(df),
        "top10_selling_points": analyze_top_selling_points(df, top_n=10),
    }


def _system_chrome_path() -> str | None:
    """返回本机已安装 Chrome/Chromium 路径."""
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def capture_google_trends_screenshot(url: str, output_dir: str | Path = "data/reports") -> dict:
    """尽力截取 Google Trends 页面; 不可用时返回失败原因和链接."""
    if not url:
        return {"ok": False, "path": "", "error": "Google Trends URL 为空"}

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return {"ok": False, "path": "", "error": f"Playwright 不可用: {exc}", "url": url}

    output_path = Path(output_dir) / f"google_trends_{date.today().isoformat()}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as p:
            chrome_path = _system_chrome_path()
            launch_options = {"headless": True}
            if chrome_path:
                launch_options["executable_path"] = chrome_path
            browser = p.chromium.launch(**launch_options)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(12000)
            page_text = page.locator("body").inner_text(timeout=5000).lower()
            if "429" in page_text or "too many requests" in page_text:
                browser.close()
                return {
                    "ok": False,
                    "path": "",
                    "error": "Google Trends 返回 429: 请求过多, 请点击链接手动打开或稍后重试",
                    "url": url,
                    "browser": chrome_path or "playwright chromium",
                }
            page.screenshot(path=str(output_path), full_page=False)
            browser.close()
        return {
            "ok": True,
            "path": str(output_path),
            "error": "",
            "url": url,
            "browser": chrome_path or "playwright chromium",
        }
    except Exception as exc:
        return {"ok": False, "path": "", "error": str(exc), "url": url}
