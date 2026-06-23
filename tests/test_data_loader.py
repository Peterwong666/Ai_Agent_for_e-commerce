"""测试 data_loader 模块."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import load_table

SAMPLE_CSV = Path(__file__).parent.parent / "data" / "samples" / "amazon_top100_sample.csv"


def test_load_csv_sample():
    """验证示例 CSV 可以被正常读取."""
    df = load_table(str(SAMPLE_CSV))
    assert len(df) >= 20
    assert "rank" in df.columns
    assert "asin" in df.columns
    assert "title" in df.columns
    assert "price" in df.columns
    assert "rating" in df.columns
    assert "review_count" in df.columns


def test_load_xlsx():
    """验证 XLSX 文件可以被正常读取."""
    df_in = pd.read_csv(str(SAMPLE_CSV))
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        df_in.to_excel(tmp.name, index=False)
        tmp_path = tmp.name
    try:
        df = load_table(tmp_path)
        assert len(df) >= 20
        assert "rank" in df.columns
    finally:
        Path(tmp_path).unlink()


def test_load_unsupported_type():
    """验证不支持的文件类型抛出异常."""
    with pytest.raises(ValueError, match="不支持的文件类型"):
        load_table("test.txt")
