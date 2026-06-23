"""测试 field_mapper 模块."""

import pandas as pd

from src.field_mapper import map_fields


def test_map_chinese_fields():
    """中文字段名可以被识别."""
    df = pd.DataFrame({
        "排名": [1, 2],
        "价格": [19.99, 29.99],
        "评分": [4.5, 4.0],
        "评论数": [100, 200],
    })
    result = map_fields(df)
    assert "rank" in result.columns
    assert "price" in result.columns
    assert "rating" in result.columns
    assert "review_count" in result.columns


def test_map_english_fields():
    """英文字段别名可以被识别."""
    df = pd.DataFrame({
        "ranking": [1, 2],
        "current price": [19.99, 29.99],
        "stars": [4.5, 4.0],
        "reviews": [100, 200],
    })
    result = map_fields(df)
    assert "rank" in result.columns
    assert "price" in result.columns
    assert "rating" in result.columns
    assert "review_count" in result.columns


def test_case_insensitive():
    """大小写不同也可以识别."""
    df = pd.DataFrame({
        "RANK": [1, 2],
        "Price": [19.99, 29.99],
        "Rating": [4.5, 4.0],
        "Review_Count": [100, 200],
    })
    result = map_fields(df)
    assert "rank" in result.columns
    assert "price" in result.columns
    assert "rating" in result.columns
    assert "review_count" in result.columns


def test_unrecognized_kept():
    """无法识别的字段保留原名."""
    df = pd.DataFrame({"custom_field": [1, 2], "price": [19.99, 29.99]})
    result = map_fields(df)
    assert "custom_field" in result.columns
    assert "price" in result.columns


def test_seller_export_variants():
    """卖家工具常见中文变体可以被识别."""
    df = pd.DataFrame({
        "商品标题": ["A", "B"],
        "售价($)": ["$19.99", "$29.99"],
        "商品评分": [4.5, 4.1],
        "评分数": ["1,234", "567"],
    })
    result = map_fields(df)
    assert "title" in result.columns
    assert "price" in result.columns
    assert "rating" in result.columns
    assert "review_count" in result.columns
    assert "评分数" not in result.columns


def test_duplicate_mapped_columns_are_merged():
    """多个列映射到同一标准字段时合并为单列."""
    df = pd.DataFrame({
        "价格": [None, "$29.99"],
        "售价($)": ["$19.99", None],
    })
    result = map_fields(df)
    assert list(result.columns) == ["price"]
    assert result["price"].tolist() == ["$19.99", "$29.99"]


def test_sellersprite_rank_and_bsr_are_distinct():
    """卖家精灵 # 是榜单排名, BSR 字段保留为 bsr."""
    df = pd.DataFrame({
        "#": [1, 2],
        "大类BSR": [1429, 2981],
        "小类BSR": [1, 2],
        "月销量": [3611, 1638],
        "月销售额($)": [46762, 48960],
        "卖家数": [1, 2],
        "商品主图": ["https://example.com/1.jpg", "https://example.com/2.jpg"],
        "产品卖点": ["A\nB", "C\nD"],
        "上架天数": [20, 200],
        "配送方式": ["FBA", "FBM"],
    })
    result = map_fields(df)
    assert "rank" in result.columns
    assert "bsr" in result.columns
    assert "monthly_sales" in result.columns
    assert "monthly_revenue" in result.columns
    assert "seller_count" in result.columns
    assert "image_url" in result.columns
    assert "bullet_points" in result.columns
    assert "listing_days" in result.columns
    assert "fulfillment" in result.columns
    assert result["rank"].tolist() == [1, 2]
    assert result["bsr"].tolist() == [1429, 2981]


def test_empty_df():
    """空 DataFrame 不报错."""
    df = pd.DataFrame()
    result = map_fields(df)
    assert result.empty
