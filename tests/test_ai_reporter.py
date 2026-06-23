"""测试 ai_reporter 模块."""

import pandas as pd

from src.ai_reporter import _format_product_data


def test_format_product_data_without_tabulate():
    """产品数据格式化不依赖 pandas 的 tabulate 可选依赖."""
    df = pd.DataFrame({
        "rank": [1],
        "title": ["A"],
        "price": [19.99],
        "rating": [4.5],
        "review_count": [1234],
    })
    text = _format_product_data(df)
    assert "rank,title,price,rating,review_count" in text
    assert "1,A,19.99,4.5,1234" in text
