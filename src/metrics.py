"""基础指标分析: 市场统计, 品牌集中度, 价格机会."""

import pandas as pd

# 价格带区间
PRICE_BANDS = [
    (0, 9.99, "0-9.99"),
    (10, 19.99, "10-19.99"),
    (20, 29.99, "20-29.99"),
    (30, 49.99, "30-49.99"),
    (50, 99.99, "50-99.99"),
    (100, float("inf"), "100+"),
]

# 评论数区间
REVIEW_BANDS = [
    (0, 99, "0-99"),
    (100, 499, "100-499"),
    (500, 999, "500-999"),
    (1000, 4999, "1000-4999"),
    (5000, 9999, "5000-9999"),
    (10000, float("inf"), "10000+"),
]


def _safe_float(col) -> pd.Series:
    return pd.to_numeric(col, errors="coerce")


def _count_band(col: pd.Series, bands: list[tuple]) -> dict[str, int]:
    """统计各区间产品数量."""
    result: dict[str, int] = {}
    for lo, hi, label in bands:
        result[label] = int(((col >= lo) & (col <= hi)).sum())
    return result


def calculate_basic_metrics(df: pd.DataFrame) -> dict:
    """计算基础市场指标."""
    product_count = len(df)

    prices = _safe_float(df["price"]) if "price" in df.columns else pd.Series(dtype=float)
    ratings = _safe_float(df["rating"]) if "rating" in df.columns else pd.Series(dtype=float)
    reviews = _safe_float(df["review_count"]) if "review_count" in df.columns else pd.Series(dtype=float)

    metrics: dict = {
        "product_count": product_count,
        "avg_price": round(float(prices.mean()), 2) if not prices.dropna().empty else 0,
        "median_price": round(float(prices.median()), 2) if not prices.dropna().empty else 0,
        "min_price": round(float(prices.min()), 2) if not prices.dropna().empty else 0,
        "max_price": round(float(prices.max()), 2) if not prices.dropna().empty else 0,
        "avg_rating": round(float(ratings.mean()), 2) if not ratings.dropna().empty else 0,
        "median_rating": round(float(ratings.median()), 2) if not ratings.dropna().empty else 0,
        "avg_review_count": int(reviews.mean()) if not reviews.dropna().empty else 0,
        "median_review_count": int(reviews.median()) if not reviews.dropna().empty else 0,
        "total_review_count": int(reviews.sum()) if not reviews.dropna().empty else 0,
        "brand_count": int(df["brand"].nunique()) if "brand" in df.columns else 0,
        "top_brand_share": 0.0,
        "price_bands": _count_band(prices, PRICE_BANDS),
        "rating_distribution": {},
        "review_count_distribution": _count_band(reviews, REVIEW_BANDS),
    }

    # 评分分布
    if not ratings.dropna().empty:
        for r in [3.0, 3.5, 4.0, 4.3, 4.5, 4.7]:
            metrics["rating_distribution"][f">={r}"] = int((ratings >= r).sum())

    # Top brand share
    if "brand" in df.columns and not df["brand"].dropna().empty:
        top_brand = df["brand"].value_counts().iloc[0]
        metrics["top_brand_share"] = round(float(top_brand / product_count), 3)

    return metrics


def calculate_brand_concentration(df: pd.DataFrame) -> dict:
    """计算品牌集中度."""
    product_count = len(df)

    if "brand" not in df.columns or product_count == 0:
        return {
            "brand_count": 0,
            "top_1_brand_share": 0,
            "top_3_brand_share": 0,
            "top_5_brand_share": 0,
            "top_brands": [],
        }

    brands = df["brand"].fillna("Unknown")
    brand_counts = brands.value_counts()

    def share(n: int) -> float:
        top = brand_counts.head(n).sum()
        return round(float(top / product_count), 3)

    top_brands = [
        {"brand": str(b), "count": int(c), "share": round(float(c / product_count), 3)}
        for b, c in brand_counts.head(10).items()
    ]

    return {
        "brand_count": int(brands.nunique()),
        "top_1_brand_share": share(1),
        "top_3_brand_share": share(3),
        "top_5_brand_share": share(5),
        "top_brands": top_brands,
    }


def analyze_price_opportunity(df: pd.DataFrame) -> dict:
    """分析价格机会."""
    if "price" not in df.columns:
        return {
            "main_price_band": "N/A",
            "low_price_competition": "N/A",
            "mid_price_opportunity": "N/A",
            "premium_price_opportunity": "N/A",
            "suggested_entry_price_range": [0, 0],
        }

    prices = _safe_float(df["price"]).dropna()
    if prices.empty:
        return {
            "main_price_band": "N/A",
            "low_price_competition": "N/A",
            "mid_price_opportunity": "N/A",
            "premium_price_opportunity": "N/A",
            "suggested_entry_price_range": [0, 0],
        }

    band_counts = _count_band(prices, PRICE_BANDS)
    main_band = max(band_counts, key=lambda k: band_counts[k])

    low_pct = band_counts.get("0-9.99", 0) / len(prices)
    med_pct = (band_counts.get("10-19.99", 0) + band_counts.get("20-29.99", 0) + band_counts.get("30-49.99", 0)) / len(prices)
    high_pct = (band_counts.get("50-99.99", 0) + band_counts.get("100+", 0)) / len(prices)

    def level(pct: float) -> str:
        if pct < 0.1:
            return "low"
        elif pct < 0.3:
            return "medium"
        return "high"

    median_price = float(prices.median())

    return {
        "main_price_band": main_band,
        "low_price_competition": level(low_pct),
        "mid_price_opportunity": level(med_pct),
        "premium_price_opportunity": level(high_pct),
        "suggested_entry_price_range": [
            round(median_price * 0.8, 2),
            round(median_price * 1.2, 2),
        ],
    }
