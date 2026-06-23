"""测试 data_cleaner 模块."""

import pandas as pd

from src.data_cleaner import clean_product_data


def test_price_clean_dollar():
    """$19.99 转为 float 19.99."""
    df = pd.DataFrame({"title": ["A"], "price": ["$19.99"]})
    result = clean_product_data(df)
    assert result["price"].iloc[0] == 19.99
    assert isinstance(result["price"].iloc[0], float)


def test_price_clean_comma():
    """1,234 格式价格转为 float."""
    df = pd.DataFrame({"title": ["A"], "price": ["1,234.56"]})
    result = clean_product_data(df)
    assert result["price"].iloc[0] == 1234.56


def test_price_clean_currency_text():
    """带币种和文案的价格可解析."""
    df = pd.DataFrame({"title": ["A"], "price": ["US$19.99 coupon"]})
    result = clean_product_data(df)
    assert result["price"].iloc[0] == 19.99


def test_rating_clean_stars():
    """4.5 out of 5 stars 转为 float 4.5."""
    df = pd.DataFrame({"title": ["A"], "rating": ["4.5 out of 5 stars"]})
    result = clean_product_data(df)
    assert result["rating"].iloc[0] == 4.5


def test_rating_clean_plain():
    """纯数字评分保持不变."""
    df = pd.DataFrame({"title": ["A"], "rating": [4.3]})
    result = clean_product_data(df)
    assert result["rating"].iloc[0] == 4.3


def test_review_count_comma():
    """1,234 转为 int 1234."""
    df = pd.DataFrame({"title": ["A"], "review_count": ["1,234"]})
    result = clean_product_data(df)
    assert result["review_count"].iloc[0] == 1234
    import numpy as np
    assert isinstance(result["review_count"].iloc[0], (int, float, np.integer))


def test_review_count_with_suffix():
    """1.2k ratings 转为 int 1200."""
    df = pd.DataFrame({"title": ["A"], "review_count": ["1.2k ratings"]})
    result = clean_product_data(df)
    assert result["review_count"].iloc[0] == 1200


def test_empty_title_removed():
    """空标题行被删除."""
    df = pd.DataFrame({"title": ["A", "", None], "price": [10, 20, 30]})
    result = clean_product_data(df)
    assert len(result) == 1
    assert result["title"].iloc[0] == "A"


def test_duplicate_asin_removed():
    """重复 ASIN 被删除."""
    df = pd.DataFrame({
        "title": ["A", "B"],
        "asin": ["X001", "X001"],
        "price": [10, 20],
    })
    result = clean_product_data(df)
    assert len(result) == 1


def test_missing_non_critical_fields():
    """缺少非关键字段时不崩溃."""
    df = pd.DataFrame({"title": ["A"], "price": [19.99]})
    result = clean_product_data(df)
    assert len(result) == 1


def test_rank_clean():
    """排名 #123 转为 int."""
    df = pd.DataFrame({"title": ["A"], "rank": ["#123"]})
    result = clean_product_data(df)
    assert result["rank"].iloc[0] == 123
