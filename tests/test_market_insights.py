"""测试市场洞察和竞品分析模块."""

import pandas as pd

from src.market_insights import (
    analyze_top_selling_points,
    build_google_trends_iframe_html,
    build_google_trends_url,
    extract_title_keywords,
    select_competitors,
)


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "rank": [1, 2, 3, 4, 5],
        "asin": ["A1", "A2", "A3", "A4", "A5"],
        "title": [
            "Reusable Cloth Diaper Cover Waterproof Baby Swim Diaper",
            "Cloth Diaper Cover Adjustable Waterproof Baby Pants",
            "Baby Cloth Diaper Cover Reusable Leakproof Swim",
            "Waterproof Toddler Training Pants Cloth Diaper Cover",
            "Reusable Baby Diaper Cover with Snap Buttons",
        ],
        "brand": ["TopBrand", "NewHot", "FixMe", "TinyNew", "Other"],
        "price": [19.99, 24.99, 12.99, 15.99, 9.99],
        "rating": [4.8, 4.5, 3.7, 4.2, 4.1],
        "review_count": [2000, 120, 800, 50, 30],
        "monthly_sales": [3000, 700, 900, 180, 80],
        "listing_days": [900, 100, 700, 30, 40],
        "fulfillment": ["FBA", "FBA", "FBM", "FBA", "FBA"],
        "image_url": ["https://example.com/1.jpg", "https://example.com/2.jpg", "", "", ""],
        "bullet_points": [
            "Waterproof reusable cover\nSoft adjustable snaps",
            "Leakproof cloth cover\nFast dry reusable material",
            "Low rated but high demand\nWaterproof shell",
            "New design for toddler training\nReusable waterproof",
            "Budget reusable baby cover",
        ],
        "category": ["Baby Products:Diapering"] * 5,
    })


def test_extract_title_keywords_returns_four_phrases():
    keywords = extract_title_keywords(_sample_df(), limit=4)
    assert len(keywords) == 4
    assert "diaper cover" in keywords
    assert "reusable" in keywords


def test_build_google_trends_url_uses_us_2004_to_today():
    url = build_google_trends_url(["diaper cover", "reusable", "waterproof", "baby"])
    assert url.startswith("https://trends.google.com/trends/explore")
    assert "geo=US" in url
    assert "date=2004-01-01%20" in url
    assert "q=diaper%20cover,reusable,waterproof,baby" in url


def test_build_google_trends_iframe_html_escapes_url():
    html = build_google_trends_iframe_html('https://example.com?a=1&b="x"', height=200)
    assert "<iframe" in html
    assert "height=\"320\"" in html
    assert "&amp;" in html
    assert "&quot;x&quot;" in html


def test_select_competitors_matches_business_rules():
    competitors = select_competitors(_sample_df())
    assert competitors["head_seller"]["asin"] == "A1"
    assert competitors["new_hot"]["asin"] == "A2"
    assert competitors["optimizable"]["asin"] == "A3"
    assert competitors["new_fast_seller"]["asin"] == "A4"


def test_analyze_top_selling_points_summarizes_top_10():
    analysis = analyze_top_selling_points(_sample_df())
    assert analysis["analyzed_count"] == 5
    assert "waterproof" in analysis["common_keywords"]
    assert analysis["review_analysis_required"] is True
    assert "需要下载评论" in analysis["review_data_note"]
