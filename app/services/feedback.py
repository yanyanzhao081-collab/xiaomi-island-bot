"""小米反馈平台查询服务"""

import os
import httpx
from datetime import datetime, timedelta
from app.config import Config

FEEDBACK_URL = "https://feedback.pt.xiaomi.com/main/data"


def _build_headers():
    cookie = getattr(Config, "XIAOMI_FEEDBACK_COOKIE", "")
    return {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://feedback.pt.xiaomi.com/",
    }


def _default_time_range():
    end = datetime.now()
    begin = end - timedelta(hours=72)
    return begin.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


def search_feedback(keyword: str, begin_time: str = "", end_time: str = "",
                    page: int = 1, page_size: int = 10) -> dict:
    """搜索反馈，返回 {total, items: [{id, content, device, version, appName, businessName}]}"""
    if not begin_time or not end_time:
        begin_time, end_time = _default_time_range()
    if page_size > 100:
        page_size = 100

    params = {
        "appid": 2, "productName": "phone", "displayLanguage": "zh_CN",
        "pageSize": page_size, "currentPage": page,
        "keyword": keyword, "searchType": 3, "showScope": 1,
        "fixedProblemType": -1, "dealtOption": -1, "platform": -1,
        "problemClass": 0, "productIdsOfDevice": 1, "versionType": 0,
        "ufiProblem": -1, "isAutoSubmit": -1, "hasDesktopLogAnalysis": -1,
        "showJiraFeedbackOption": 0,
        "beginTime": begin_time, "endTime": end_time,
        "language": "", "region": "", "department": "", "wideTagId": "",
        "tagId": "", "ids": "", "model": "", "osMediumVersion": "",
        "appVersion": "", "appVersions": "", "miVersion": "", "miVersions": "",
        "replier": "", "operator": "", "uuids": "", "subChannel": "",
        "customizer": "", "deviceNames": "", "osVersions": "", "position": "",
        "userLevel": "", "imei": "", "packageNames": "", "tagPropertyName": "",
        "xmsVersions": "", "did": "", "firmwareVersion": "", "originate": "",
        "xmsVersionList": "", "deviceNameList": "",
    }

    try:
        resp = httpx.get(FEEDBACK_URL, headers=_build_headers(), params=params,
                         timeout=15, verify=False, follow_redirects=True)
        content_type = resp.headers.get("content-type", "")
        if "json" not in content_type:
            return {"total": 0, "items": [], "error": "认证失败，请更新 Cookie"}

        data = resp.json()
        items = data.get("userFeedBackList", [])
        total = data.get("counts", 0)

        results = []
        for item in items:
            results.append({
                "id": item.get("id", ""),
                "content": item.get("content", ""),
                "device": item.get("deviceName", item.get("model", "")),
                "version": item.get("osVersion", ""),
                "appName": item.get("appName", ""),
                "businessName": item.get("businessName", ""),
            })
        return {"total": total, "items": results}

    except Exception as e:
        return {"total": 0, "items": [], "error": str(e)}
