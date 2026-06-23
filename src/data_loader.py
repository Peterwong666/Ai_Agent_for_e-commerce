"""读取用户上传的 CSV 或 XLSX 文件."""

from pathlib import Path

import pandas as pd


def load_table(file) -> pd.DataFrame:
    """读取 CSV 或 XLSX 文件，返回 DataFrame.

    支持 .csv, .xlsx, .xls.
    如果文件类型不支持, 抛出 ValueError.
    """
    if hasattr(file, "name"):
        filename = file.name
    else:
        filename = str(file)

    ext = Path(filename).suffix.lower()

    if ext == ".csv":
        return pd.read_csv(file)
    elif ext in (".xlsx", ".xls"):
        return pd.read_excel(file)
    else:
        raise ValueError(f"不支持的文件类型: {ext}, 请上传 .csv, .xlsx 或 .xls 文件")
