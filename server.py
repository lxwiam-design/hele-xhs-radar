"""Read-only MCP gateway for RedFoxHub Xiaohongshu research.

The RedFox credential remains server-side in REDFOX_API_KEY.  Do not add it to
tool parameters, tool output, source control, or client-side configuration.
"""
import os
from datetime import date, timedelta
from typing import Any

from fastmcp import FastMCP
from redfox import RedFoxClient

mcp = FastMCP("和乐创意城小红书热点雷达")


def client() -> RedFoxClient:
    key = os.environ.get("REDFOX_API_KEY")
    if not key:
        raise RuntimeError("服务端尚未配置 REDFOX_API_KEY。请在部署平台的 Secret 中配置。")
    return RedFoxClient(api_key=key)


def as_json(value: Any) -> Any:
    """SDK responses are normally JSON-compatible; preserve unknown data safely."""
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return value


def day_before(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


@mcp.tool()
def search_local_notes(
    keywords: str,
    sort_type: str = "0",
    offset: int = 0,
) -> dict:
    """搜索小红书笔记。keywords 可用逗号写多个词，例如“佛山,乐从,商场”。

    用于了解本地内容、竞品与用户表达；结果是公开平台数据，不能代表完整人群。
    """
    results = {}
    for term in [x.strip() for x in keywords.split(",") if x.strip()][:5]:
        results[term] = as_json(client().xiaohongshu.search_articles(
            keyword=term, offset=offset, sort_type=sort_type
        ))
    return {"queried_on": date.today().isoformat(), "results": results}


@mcp.tool()
def xiaohongshu_hot_radar(
    category: str = "综合全部",
    lookback_days: int = 7,
) -> dict:
    """获取小红书日榜与周榜，作为宏观热点参照。

    category 例如“综合全部”。lookback_days 限制为 1 至 30。
    """
    days = max(1, min(lookback_days, 30))
    rank_date = day_before(days)
    api = client().xiaohongshu
    return {
        "queried_on": date.today().isoformat(),
        "rank_date": rank_date,
        "category": category,
        "daily": as_json(api.get_daily_hot_rank(rank_date=rank_date, category=category)),
        "weekly": as_json(api.get_weekly_hot_rank(rank_date=rank_date, category=category)),
    }


@mcp.tool()
def find_breakout_notes(keywords: str, lookback_days: int = 30) -> dict:
    """查询与关键词相关的爆款洞察与黑马笔记。

    适合“佛山商场”“乐从探店”“周末遛娃”等。只用于发现案例，ChatGPT 必须
    区分事实数据与创意推断，不能把单条案例当作普遍规律。
    """
    days = max(1, min(lookback_days, 30))
    start_date = day_before(days)
    api = client().xiaohongshu
    return {
        "queried_on": date.today().isoformat(),
        "start_date": start_date,
        "keywords": keywords,
        "hot_notes": as_json(api.search_hot_notes(
            keyword=keywords, start_date=start_date, end_date=date.today().isoformat()
        )),
        "dark_horses": as_json(api.get_dark_horse_notes(
            keyword=keywords, start_date=start_date
        )),
    }


@mcp.tool()
def get_note_detail(work_id: str) -> dict:
    """获取一条候选小红书笔记详情，用于拆解标题、内容结构和互动线索。"""
    return {
        "queried_on": date.today().isoformat(),
        "work_id": work_id,
        "detail": as_json(client().xiaohongshu.get_work(work_id=work_id)),
    }


@mcp.tool()
def health() -> dict:
    """检查热点雷达是否已配置服务端密钥。不会返回密钥。"""
    return {"ok": bool(os.environ.get("REDFOX_API_KEY")), "read_only": True}


if __name__ == "__main__":
    # Streamable HTTP is the remote transport to register in ChatGPT.
    mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.getenv("PORT", "8080")), path="/mcp")
