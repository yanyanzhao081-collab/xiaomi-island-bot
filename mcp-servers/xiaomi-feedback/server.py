"""小米反馈平台 MCP Server"""

import os
import json
import httpx
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("xiaomi-feedback")

FEEDBACK_URL = "https://feedback.pt.xiaomi.com/main/data"
COOKIE = os.environ.get("XIAOMI_FEEDBACK_COOKIE", "")


def _build_headers():
    return {
        "Cookie": COOKIE,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://feedback.pt.xiaomi.com/",
    }


def _default_time_range():
    """默认查最近 72 小时"""
    end = datetime.now()
    begin = end - timedelta(hours=72)
    return begin.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


async def _fetch_feedback(keyword: str, begin_time: str, end_time: str, page: int, page_size: int) -> dict:
    """调用反馈平台 API"""
    params = {
        "appid": 2,
        "productName": "phone",
        "displayLanguage": "zh_CN",
        "pageSize": page_size,
        "currentPage": page,
        "language": "",
        "region": "",
        "department": "",
        "showScope": 1,
        "fixedProblemType": -1,
        "wideTagId": "",
        "tagId": "",
        "ids": "",
        "model": "",
        "keyword": keyword,
        "osMediumVersion": "",
        "appVersion": "",
        "appVersions": "",
        "miVersion": "",
        "miVersions": "",
        "replier": "",
        "operator": "",
        "dealtOption": -1,
        "showJiraFeedbackOption": 0,
        "platform": -1,
        "beginTime": begin_time,
        "endTime": end_time,
        "searchType": 3,
        "uuids": "",
        "subChannel": "",
        "problemClass": 0,
        "productIdsOfDevice": 1,
        "customizer": "",
        "deviceNameList": "",
        "deviceNames": "",
        "versionType": 0,
        "osVersions": "",
        "position": "",
        "userLevel": "",
        "imei": "",
        "ufiProblem": -1,
        "packageNames": "",
        "isAutoSubmit": -1,
        "tagPropertyName": "",
        "xmsVersions": "",
        "did": "",
        "firmwareVersion": "",
        "originate": "",
        "hasDesktopLogAnalysis": -1,
        "xmsVersionList": "",
    }
    async with httpx.AsyncClient(timeout=15, verify=False) as client:
        resp = await client.get(FEEDBACK_URL, headers=_build_headers(), params=params, follow_redirects=True)
        content_type = resp.headers.get("content-type", "")
        if "json" not in content_type:
            return {"error": f"非 JSON 响应, status={resp.status_code}, content-type={content_type}, body={resp.text[:200]}"}
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def search_feedback(
    keyword: str,
    beginTime: str = "",
    endTime: str = "",
    page: int = 1,
    pageSize: int = 20,
) -> str:
    """搜索小米反馈平台的用户反馈列表。

    Args:
        keyword: 搜索关键词，如"耗电"、"卡顿"、"状态栏"
        beginTime: 开始时间，格式 YYYY-MM-DD HH:MM:SS，默认72小时前
        endTime: 结束时间，格式 YYYY-MM-DD HH:MM:SS，默认当前时间
        page: 页码，默认1
        pageSize: 每页条数，最大100，默认20
    """
    if not beginTime or not endTime:
        beginTime, endTime = _default_time_range()
    if pageSize > 100:
        pageSize = 100

    try:
        data = await _fetch_feedback(keyword, beginTime, endTime, page, pageSize)

        # 适配返回结构
        items = data.get("userFeedBackList", [])
        total = data.get("counts", 0)

        results = []
        for item in items:
            results.append({
                "id": item.get("id", ""),
                "content": item.get("content", ""),
                "createTime": item.get("createTime", ""),
                "status": item.get("checkStatus", ""),
                "device": item.get("deviceName", item.get("model", "")),
                "version": item.get("osVersion", ""),
                "appName": item.get("appName", ""),
                "businessName": item.get("businessName", ""),
                "channel": item.get("channel", ""),
            })

        return json.dumps({
            "total": total,
            "page": page,
            "pageSize": pageSize,
            "count": len(results),
            "items": results,
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
async def get_feedback_stats(
    keyword: str,
    beginTime: str = "",
    endTime: str = "",
) -> str:
    """获取反馈统计概览：总数 + Top 5 摘要。

    Args:
        keyword: 搜索关键词
        beginTime: 开始时间，格式 YYYY-MM-DD HH:MM:SS，默认72小时前
        endTime: 结束时间，格式 YYYY-MM-DD HH:MM:SS，默认当前时间
    """
    if not beginTime or not endTime:
        beginTime, endTime = _default_time_range()

    try:
        data = await _fetch_feedback(keyword, beginTime, endTime, page=1, page_size=5)

        items = data.get("userFeedBackList", [])
        total = data.get("counts", 0)

        top5 = []
        for item in items[:5]:
            content = item.get("content", "")
            if len(content) > 100:
                content = content[:100] + "..."
            top5.append({
                "content": content,
                "createTime": item.get("createTime", ""),
                "device": item.get("deviceName", item.get("model", "")),
            })

        return json.dumps({
            "keyword": keyword,
            "timeRange": f"{beginTime} ~ {endTime}",
            "total": total,
            "top5": top5,
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
