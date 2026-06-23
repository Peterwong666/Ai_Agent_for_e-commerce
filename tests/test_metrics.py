"""测试 metrics 模块."""

from pathlib import Path

import pandas as pd

from src.data_loader import load_table
from src.data_cleaner import clean_product_data
from src.field_mapper import map_fields
from src.metrics import (
    analyze_price_opportunity,
    calculate_basic_metrics,
    calculate_brand_concentration,
)


def _load_sample() -> pd.DataFrame:
    """加载并清洗示例数据."""
    path = Path(__file__).parent.parent / "data" / "samples" / "amazon_top100_sample.csv"
    df = load_table(str(path))
    df = map_fields(df)
    df = clean_product_data(df)
    return df


class TestBasicMetrics:
    """P2.1: 基础指标测试."""

    def test_returns_all_keys(self):
        """输出包含所有必需字段."""
        df = _load_sample()
        m = calculate_basic_metrics(df)
        required = [
            "product_count", "avg_price", "median_price", "min_price", "max_price",
            "avg_rating", "median_rating", "avg_review_count", "median_review_count",
            "total_review_count", "brand_count", "top_brand_share",
            "price_bands", "rating_distribution", "review_count_distribution",
        ]
        for key in required:
            assert key in m, f"Missing key: {key}"

    def test_product_count(self):
        """产品数正确."""
        df = _load_sample()
        m = calculate_basic_metrics(df)
        assert m["product_count"] == 25

    def test_price_range(self):
        """价格范围合理."""
        df = _load_sample()
        m = calculate_basic_metrics(df)
        assert m["min_price"] > 0
        assert m["max_price"] >= m["avg_price"] >= m["min_price"]

    def test_price_bands(self):
        """价格带有数据."""
        df = _load_sample()
        m = calculate_basic_metrics(df)
        assert sum(m["price_bands"].values()) == 25

    def test_empty_dataframe(self):
        """空 DataFrame 返回安全默认值, 不报错."""
        m = calculate_basic_metrics(pd.DataFrame())
        assert m["product_count"] == 0
        assert m["avg_price"] == 0


class TestBrandConcentration:
    """P2.2: 品牌集中度测试."""

    def test_brand_count(self):
        """品牌数正确."""
        df = _load_sample()
        b = calculate_brand_concentration(df)
        assert b["brand_count"] > 0

    def test_top_brands_list(self):
        """Top brands 列表非空."""
        df = _load_sample()
        b = calculate_brand_concentration(df)
        assert len(b["top_brands"]) > 0
        assert "brand" in b["top_brands"][0]
        assert "count" in b["top_brands"][0]
        assert "share" in b["top_brands"][0]

    def test_shares_sum_to_1(self):
        """Top 5 份额不超过 1."""
        df = _load_sample()
        b = calculate_brand_concentration(df)
        assert b["top_1_brand_share"] <= 1.0
        assert b["top_5_brand_share"] <= 1.0

    def test_no_brand_column(self):
        """没有 brand 字段时不报错."""
        b = calculate_brand_concentration(pd.DataFrame({"price": [10]}))
        assert b["brand_count"] == 0


class TestPriceOpportunity:
    """P2.3: 价格机会测试."""

    def test_main_price_band(self):
        """能识别主要价格带."""
        df = _load_sample()
        p = analyze_price_opportunity(df)
        assert p["main_price_band"] != "N/A"

    def test_suggested_range(self):
        """建议切入价格带合理."""
        df = _load_sample()
        p = analyze_price_opportunity(df)
        lo, hi = p["suggested_entry_price_range"]
        assert lo > 0
        assert hi > lo

    def test_no_price_column(self):
        """没有 price 字段时不报错."""
        p = analyze_price_opportunity(pd.DataFrame({"title": ["A"]}))
        assert p["main_price_band"] == "N/A"
