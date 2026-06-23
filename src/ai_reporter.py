"""AI 报告生成: 调用 DeepSeek API 生成 Markdown 选品报告."""

import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def _load_prompt(prompt_path: str) -> str:
    with open(prompt_path, encoding="utf-8") as f:
        return f.read()


def _format_product_data(df, max_rows: int = 100) -> str:
    cols = [
        c for c in [
            "rank",
            "asin",
            "title",
            "brand",
            "price",
            "rating",
            "review_count",
            "monthly_sales",
            "monthly_revenue",
            "seller_count",
            "listing_days",
            "fulfillment",
            "category",
            "bsr",
        ]
        if c in df.columns
    ]
    return df[cols].head(max_rows).to_csv(index=False)


def _message_text(message) -> str:
    """兼容部分 DeepSeek 模型的 content/reasoning_content 返回差异."""
    content = getattr(message, "content", None) or ""
    if content.strip():
        return content
    reasoning = getattr(message, "reasoning_content", None) or ""
    return reasoning


def get_deepseek_config_status() -> dict:
    """检测 DeepSeek 配置是否存在且格式基本合理."""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip()

    issues: list[str] = []
    if not api_key:
        issues.append("DEEPSEEK_API_KEY 未配置")
    elif not re.match(r"^sk-[A-Za-z0-9_\-]{20,}$", api_key):
        issues.append("DEEPSEEK_API_KEY 格式不像 DeepSeek/OpenAI 兼容 key, 应以 sk- 开头")

    if not base_url.startswith(("https://", "http://")):
        issues.append("DEEPSEEK_BASE_URL 必须以 http:// 或 https:// 开头")
    if not model:
        issues.append("DEEPSEEK_MODEL 未配置")

    return {
        "configured": bool(api_key),
        "valid_format": not issues,
        "base_url": base_url,
        "model": model,
        "issues": issues,
    }


def test_deepseek_connection(timeout: float = 20.0) -> dict:
    """用极小请求测试 DeepSeek 是否可连通."""
    status = get_deepseek_config_status()
    if status["issues"]:
        return {"ok": False, **status}

    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"].strip(),
        base_url=status["base_url"],
        timeout=timeout,
    )
    try:
        response = client.chat.completions.create(
            model=status["model"],
            messages=[
                {"role": "system", "content": "You are a connectivity checker."},
                {"role": "user", "content": "请只回答 OK 两个字母。"},
            ],
            temperature=0,
            max_tokens=32,
        )
        content = _message_text(response.choices[0].message)
        return {"ok": True, "response": content.strip(), **status}
    except Exception as exc:
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            **status,
        }


def generate_ai_report(
    df,
    metrics: dict,
    scoring: dict,
    risk: dict,
    brand: dict,
    market_insights: dict | None = None,
    prompt_path: str = "prompts/product_report_prompt.md",
) -> str:
    """调用 OpenAI 兼容接口生成 Markdown 报告.

    如果没有配置 API Key, 抛出 RuntimeError, 由调用方回退到本地报告.
    """
    config = get_deepseek_config_status()
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    base_url = config["base_url"]
    model = config["model"]

    if config["issues"]:
        raise RuntimeError("; ".join(config["issues"]))

    prompt_template = _load_prompt(prompt_path)
    product_table = _format_product_data(df)

    context = {
        "metrics": metrics,
        "scoring": scoring,
        "risk": risk,
        "brand_concentration": brand,
        "market_insights": market_insights or {},
    }

    user_message = f"""以下是选品分析的结构化数据和产品原始数据:

## 结构化分析数据
```json
{json.dumps(context, ensure_ascii=False, indent=2)}
```

## 产品原始数据 (Top 100)
{product_table}

请按照 Prompt 要求的 12 章节结构生成完整的选品分析 Markdown 报告。"""

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt_template},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=8192,
    )

    content = _message_text(response.choices[0].message)
    if not content.strip():
        raise RuntimeError("DeepSeek 返回内容为空")
    return content


def answer_user_question(
    question: str,
    df,
    metrics: dict,
    scoring: dict,
    risk: dict,
    brand: dict,
    price_opportunity: dict | None = None,
    market_insights: dict | None = None,
) -> str:
    """基于当前表格和结构化指标回答用户追问."""
    if not question.strip():
        return ""

    config = get_deepseek_config_status()
    if config["issues"]:
        raise RuntimeError("; ".join(config["issues"]))

    context = {
        "metrics": metrics,
        "scoring": scoring,
        "risk": risk,
        "brand_concentration": brand,
        "price_opportunity": price_opportunity or {},
        "market_insights": market_insights or {},
    }

    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"].strip(),
        base_url=config["base_url"],
    )
    response = client.chat.completions.create(
        model=config["model"],
        messages=[
            {
                "role": "system",
                "content": (
                    "你是跨境电商选品分析助手。只能基于用户上传表格和结构化指标回答。"
                    "如果数据不足, 明确说明缺少哪些字段或证据。回答要简洁、可执行。"
                ),
            },
            {
                "role": "user",
                "content": f"""## 当前类目结构化指标
```json
{json.dumps(context, ensure_ascii=False, indent=2)}
```

## 当前产品表
{_format_product_data(df)}

## 用户问题
{question}
""",
            },
        ],
        temperature=0.4,
        max_tokens=2048,
    )
    content = _message_text(response.choices[0].message)
    if not content.strip():
        raise RuntimeError("DeepSeek 返回内容为空")
    return content
