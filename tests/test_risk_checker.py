"""测试 risk_checker 模块."""

import pandas as pd

from src.risk_checker import detect_risk_keywords


def test_detect_baby_risk():
    """标题含 baby 时能识别."""
    df = pd.DataFrame({"title": ["Baby safe slow feeder bowl"]})
    result = detect_risk_keywords(df)
    assert "baby" in result["matched_keywords"]
    assert result["risk_level"] in ("medium", "high")


def test_detect_ip_risk():
    """标题含 Disney 时返回 high."""
    df = pd.DataFrame({"title": ["Disney princess slow feeder"]})
    result = detect_risk_keywords(df)
    assert result["risk_level"] == "high"


def test_detect_battery_risk():
    """标题含 electric/battery 时能识别."""
    df = pd.DataFrame({"title": ["Electric slow feeder with battery"]})
    result = detect_risk_keywords(df)
    assert any(w in result["matched_keywords"] for w in ["electric", "battery"])


def test_no_risk():
    """无风险词时返回 low."""
    df = pd.DataFrame({"title": ["Dog slow feeder bowl silicone"]})
    result = detect_risk_keywords(df)
    assert result["risk_level"] == "low"


def test_no_text_columns():
    """没有 title/category 列时不报错."""
    df = pd.DataFrame({"price": [10]})
    result = detect_risk_keywords(df)
    assert result["risk_level"] == "low"


def test_chinese_risk_words():
    """中文风险词能识别."""
    df = pd.DataFrame({"title": ["儿童慢食碗 带电"]})
    result = detect_risk_keywords(df)
    assert result["risk_level"] in ("medium", "high")
