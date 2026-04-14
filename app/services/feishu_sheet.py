"""飞书电子表格 / Bitable 读取服务"""

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *
from app.config import Config

client = lark.Client.builder() \
    .app_id(Config.FEISHU_APP_ID) \
    .app_secret(Config.FEISHU_APP_SECRET) \
    .build()


def read_bitable(app_token: str, table_id: str) -> list[dict]:
    """读取指定 Bitable 表格的全部记录"""
    try:
        # 如果没有 table_id，先获取默认表
        if not table_id:
            list_req = ListAppTableRequest.builder() \
                .app_token(app_token) \
                .build()
            list_resp = client.bitable.v1.app_table.list(list_req)
            if not list_resp.success() or not list_resp.data.items:
                print(f"获取表列表失败: {list_resp.msg}")
                return []
            table_id = list_resp.data.items[0].table_id

        req = SearchAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(
                SearchAppTableRecordRequestBody.builder().build()
            ) \
            .build()

        resp = client.bitable.v1.app_table_record.search(req)
        if not resp.success():
            print(f"读取 Bitable 失败: {resp.msg}")
            return []

        items = resp.data.items or []
        results = []
        for r in items:
            row = {}
            for k, v in (r.fields or {}).items():
                if isinstance(v, list) and len(v) > 0:
                    if isinstance(v[0], dict):
                        row[k] = v[0].get("text", str(v[0]))
                    else:
                        row[k] = str(v[0])
                else:
                    row[k] = str(v) if v else ""
            results.append(row)
        return results

    except Exception as e:
        print(f"read_bitable 异常: {e}")
        return []


def read_sheet(spreadsheet_token: str, sheet_id: str = "") -> list[dict]:
    """读取飞书电子表格 (Sheets) 数据，支持指定工作表"""
    try:
        from lark_oapi.api.sheets.v3 import QuerySpreadsheetSheetRequest

        # 1. 获取工作表列表
        sheet_req = QuerySpreadsheetSheetRequest.builder() \
            .spreadsheet_token(spreadsheet_token) \
            .build()
        sheet_resp = client.sheets.v3.spreadsheet_sheet.query(sheet_req)

        if not sheet_resp.success():
            print(f"获取工作表列表失败: code={sheet_resp.code}, msg={sheet_resp.msg}")
            return []

        sheets = sheet_resp.data.sheets
        if not sheets:
            print("电子表格中没有工作表")
            return []

        # 如果指定了 sheet_id 则用指定的，否则用第一个
        target_sheet = None
        if sheet_id:
            for s in sheets:
                if s.sheet_id == sheet_id:
                    target_sheet = s
                    break
        if not target_sheet:
            target_sheet = sheets[0]

        sid = target_sheet.sheet_id
        total_rows = target_sheet.grid_properties.row_count
        total_cols = target_sheet.grid_properties.column_count

        print(f"[Sheets] 读取工作表: {sid}, {total_rows}行 x {total_cols}列")

        # 2. 计算范围（如 Sheet1!A1:Z200）
        end_col_letter = _col_index_to_letter(total_cols)
        range_str = f"{sid}!A1:{end_col_letter}{min(total_rows, 1000)}"

        # 3. 读取数据
        from lark_oapi.api.sheets.v2 import GetSpreadsheetSheetFilterRequest
        import httpx

        # 使用 REST API 直接读取（SDK 对 v2 range 支持不完整）
        token_resp = _get_tenant_access_token()
        if not token_resp:
            return []

        url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{range_str}"
        resp = httpx.get(url, headers={"Authorization": f"Bearer {token_resp}"}, params={"valueRenderOption": "ToString"})
        data = resp.json()

        if data.get("code") != 0:
            print(f"读取 Sheets 数据失败: {data.get('msg')}")
            return []

        values = data.get("data", {}).get("valueRange", {}).get("values", [])
        if len(values) < 2:
            print("Sheets 数据不足（需要至少表头+1行数据）")
            return []

        # 4. 第一行作为表头，后续行作为数据
        headers = [str(h).strip() if h else "" for h in values[0]]
        results = []
        for row in values[1:]:
            record = {}
            for i, header in enumerate(headers):
                if header and i < len(row):
                    val = str(row[i]).strip() if row[i] is not None else ""
                    if val:
                        record[header] = val
            if record:
                results.append(record)

        print(f"从 Sheets 读取到 {len(results)} 条数据")
        return results

    except Exception as e:
        print(f"read_sheet 异常: {e}")
        return []


def _get_tenant_access_token() -> str:
    """获取 tenant_access_token"""
    try:
        resp = httpx.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": Config.FEISHU_APP_ID, "app_secret": Config.FEISHU_APP_SECRET},
        )
        data = resp.json()
        if data.get("code") == 0:
            return data.get("tenant_access_token", "")
        print(f"获取 token 失败: {data.get('msg')}")
        return ""
    except Exception as e:
        print(f"获取 token 异常: {e}")
        return ""


def _col_index_to_letter(col: int) -> str:
    """列号转字母，如 1->A, 26->Z, 27->AA"""
    result = ""
    while col > 0:
        col, remainder = divmod(col - 1, 26)
        result = chr(65 + remainder) + result
    return result


# 需要 httpx
import httpx
