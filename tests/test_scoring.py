"""测试 scoring 模块."""

from pathlib import Path

from src.data_cleaner import clean_product_data
from src.data_loader import load_table
from src.field_mapper import map_fields
from src.metrics import calculate_basic_metrics
from src.risk_checker import detect_risk_keywords
from src.scoring import calculate_opportunity_score


def _load_and_score() -> dict:
    path = Path(__file__).parent.parent / "data" / "samples" / "amazon_top100_sample.csv"
    df = load_table(str(path))
    df = map_fields(df)
    df = clean_product_data(df)
    metrics = calculate_basic_metrics(df)
    risk = detect_risk_keywords(df)
    return calculate_opportunity_score(df, metrics, risk)


def test_total_score_in_range():
    """总分在 0-100 范围内."""
    result = _load_and_score()
    assert 0 <= result["total_score"] <= 100


def test_has_all_dimensions():
    """包含所有评分维度."""
    result = _load_and_score()
    expected = [
        "market_demand", "competition_intensity", "price_opportunity",
        "improvement_opportunity", "brand_concentration",
        "risk_level", "data_quality",
    ]
    for dim in expected:
        assert dim in result["dimension_scores"], f"Missing: {dim}"
        assert "score" in result["dimension_scores"][dim]
        assert "reason" in result["dimension_scores"][dim]


def test_level_is_valid():
    """分级是四个预设值之一."""
    result = _load_and_score()
    assert result["level"] in ["优先开发", "进入二次验证", "谨慎观察", "不建议开发"]


def test_key_findings_and_warnings():
    """key_findings 和 warnings 存在."""
    result = _load_and_score()
    assert isinstance(result["key_findings"], list)
    assert isinstance(result["warnings"], list)
