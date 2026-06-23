"""数据清洗: 将价格/评分/评论数等字段转为可计算格式."""

import re

import pandas as pd


def _parse_price(val) -> float | None:
    """解析价格字符串为 float. 处理 $19.99, US$19.99, 19.99, 空值等情况."""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    text = str(val).replace(",", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else None


def _parse_rating(val) -> float | None:
    """解析评分字符串为 float. 处理 4.5 out of 5 stars, 4.5, 空值等情况."""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        v = float(val)
        return v if v <= 5 else None
    match = re.search(r"(\d+\.?\d*)", str(val))
    if match:
        v = float(match.group(1))
        if v <= 5:
            return v
    return None


def _parse_review_count(val) -> int | None:
    """解析评论数字符串为 int. 处理 1,234, 1.2k, 1234 ratings 等情况."""
    if pd.isna(val):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    cleaned = str(val).lower().replace(",", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)(\s*[kmw万]?)", cleaned)
    if not match:
        return None
    number = float(match.group(1))
    suffix = match.group(2).strip()
    if suffix == "k":
        number *= 1_000
    elif suffix == "m":
        number *= 1_000_000
    elif suffix in {"w", "万"}:
        number *= 10_000
    return int(number)


def _parse_rank(val) -> int | None:
    """解析排名."""
    if pd.isna(val):
        return None
    if isinstance(val, int):
        return val
    cleaned = str(val).replace(",", "").replace("#", "").strip()
    try:
        return int(cleaned)
    except ValueError:
        return None


def clean_product_data(df: pd.DataFrame) -> pd.DataFrame:
    """清洗产品数据.

    - price 转 float
    - rating 转 float
    - review_count 转 int
    - rank 转 int
    - 去除空标题行
    - 去除重复 ASIN
    - 对缺失字段做安全处理
    """
    df = df.copy()

    if "price" in df.columns:
        df["price"] = df["price"].apply(_parse_price)

    if "rating" in df.columns:
        df["rating"] = df["rating"].apply(_parse_rating)

    if "review_count" in df.columns:
        df["review_count"] = df["review_count"].apply(_parse_review_count)

    if "rank" in df.columns:
        df["rank"] = df["rank"].apply(_parse_rank)

    if "bsr" in df.columns:
        df["bsr"] = df["bsr"].apply(_parse_rank)

    if "monthly_sales" in df.columns:
        df["monthly_sales"] = df["monthly_sales"].apply(_parse_review_count)

    if "monthly_revenue" in df.columns:
        df["monthly_revenue"] = df["monthly_revenue"].apply(_parse_price)

    if "seller_count" in df.columns:
        df["seller_count"] = df["seller_count"].apply(_parse_review_count)

    if "listing_days" in df.columns:
        df["listing_days"] = df["listing_days"].apply(_parse_review_count)

    # 去除空标题行
    if "title" in df.columns:
        df = df[df["title"].notna() & (df["title"].astype(str).str.strip() != "")]

    # 去除重复 ASIN
    if "asin" in df.columns:
        df = df.drop_duplicates(subset=["asin"], keep="first")

    return df.reset_index(drop=True)
