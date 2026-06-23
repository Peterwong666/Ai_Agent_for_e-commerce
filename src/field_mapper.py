"""字段自动识别与映射."""

import re

import pandas as pd
import yaml


def _load_aliases(aliases_path: str) -> dict[str, list[str]]:
    """加载字段别名配置."""
    with open(aliases_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _normalize_column_name(name: object) -> str:
    """将列名规整到可比较形式, 保留中英文和数字."""
    text = str(name).lower().strip()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def _infer_standard_field(col: object, reverse_map: dict[str, str]) -> str | None:
    """根据别名和常见导出字段模式推断标准字段名."""
    raw = str(col).lower().strip()
    normalized = _normalize_column_name(col)

    if raw in reverse_map:
        return reverse_map[raw]
    if normalized in reverse_map:
        return reverse_map[normalized]

    # 卖家精灵/表格导出常见变体: "售价($)", "商品评分", "评分数" 等。
    if any(token in normalized for token in ("评分数", "评分数量", "评论数", "评论数量", "评价数", "评价数量", "reviewcount", "ratingscount")):
        return "review_count"
    if any(token in normalized for token in ("评分", "星级", "rating", "stars")):
        return "rating"
    if any(token in normalized for token in ("价格", "售价", "现价", "price")):
        return "price"
    if any(token in normalized for token in ("标题", "名称", "title", "productname")):
        return "title"
    if any(token in normalized for token in ("商品主图", "图片", "imageurl", "mainimage")):
        return "image_url"
    if any(token in normalized for token in ("产品卖点", "卖点", "bulletpoints", "productfeatures")):
        return "bullet_points"
    if any(token in normalized for token in ("品牌", "brand")):
        return "brand"
    if normalized in {"#", "序号"} or any(token in normalized for token in ("排名", "ranking")):
        return "rank"
    if ("bsr" in normalized or "bestsellersrank" in normalized) and not any(
        token in normalized for token in ("增长", "growth", "rate")
    ):
        return "bsr"
    if normalized == "asin" or "商品编码" in normalized:
        return "asin"
    if any(token in normalized for token in ("类目", "分类", "category")):
        return "category"
    if any(token in normalized for token in ("月销量", "monthlysales")):
        return "monthly_sales"
    if any(token in normalized for token in ("月销售额", "monthlyrevenue")):
        return "monthly_revenue"
    if any(token in normalized for token in ("卖家数", "sellercount", "sellers")):
        return "seller_count"
    if any(token in normalized for token in ("上架天数", "listingdays", "dayslive")):
        return "listing_days"
    if any(token in normalized for token in ("配送方式", "fulfillment", "shippingmethod")):
        return "fulfillment"

    return None


def map_fields(
    df: pd.DataFrame,
    aliases_path: str = "config/field_aliases.yaml",
) -> pd.DataFrame:
    """将用户上传表格的字段名映射为标准字段名.

    无法识别的字段保留原名.
    """
    if df.empty:
        return df

    aliases = _load_aliases(aliases_path)

    reverse_map: dict[str, str] = {}
    for standard, candidates in aliases.items():
        for c in candidates:
            reverse_map[c.lower().strip()] = standard
            reverse_map[_normalize_column_name(c)] = standard

    rename: dict[str, str] = {}
    for col in df.columns:
        standard = _infer_standard_field(col, reverse_map)
        if standard:
            rename[col] = standard

    mapped = df.rename(columns=rename)

    # 如果多个原始列映射到同一标准字段, 用左侧第一个非空值合并, 避免重复列破坏后续清洗。
    result = pd.DataFrame(index=mapped.index)
    for col in mapped.columns:
        data = mapped[col]
        if isinstance(data, pd.DataFrame):
            combined = data.bfill(axis=1).iloc[:, 0]
        else:
            combined = data
        if col in result.columns:
            result[col] = result[col].combine_first(combined)
        else:
            result[col] = combined

    return result
