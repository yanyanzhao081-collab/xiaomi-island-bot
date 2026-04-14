"""飞书多维表格 (Bitable) CRUD 封装 — 作为机器人的数据库层"""

import json
from typing import Optional

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *

from app.config import Config


class BitableService:
    """封装飞书 Bitable 的增删改查操作"""

    def __init__(self):
        self.app_token = Config.BITABLE_APP_TOKEN
        self.table_id = Config.BITABLE_TABLE_ID
        self.client = lark.Client.builder() \
            .app_id(Config.FEISHU_APP_ID) \
            .app_secret(Config.FEISHU_APP_SECRET) \
            .build()

    def query_by_app_name(self, app_name: str) -> Optional[dict]:
        """根据应用名称查询单条记录，返回 {record_id, fields} 或 None"""
        try:
            req = SearchAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .request_body(
                    SearchAppTableRecordRequestBody.builder()
                    .field_names(["应用名称", "场景", "大岛", "小岛",
                                  "接入版本", "进度排期", "支持小窗", "支持分享"])
                    .filter(
                        FilterInfo.builder()
                        .conjunction("and")
                        .conditions([
                            Condition.builder()
                            .field_name("应用名称")
                            .operator("is")
                            .value([app_name])
                            .build()
                        ])
                        .build()
                    )
                    .build()
                ) \
                .build()

            resp = self.client.bitable.v1.app_table_record.search(req)
            if not resp.success():
                print(f"查询记录失败: code={resp.code}, msg={resp.msg}")
                return None

            items = resp.data.items
            if items and len(items) > 0:
                record = items[0]
                return {
                    "record_id": record.record_id,
                    "fields": record.fields,
                }
            return None

        except Exception as e:
            print(f"query_by_app_name 异常: {e}")
            return None

    def query_by_app_and_scene(self, app_name: str, scene: str) -> Optional[dict]:
        """根据应用名称+场景联合查询"""
        try:
            req = SearchAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .request_body(
                    SearchAppTableRecordRequestBody.builder()
                    .field_names(["应用名称", "场景", "大岛", "小岛",
                                  "接入版本", "进度排期", "支持小窗", "支持分享"])
                    .filter(
                        FilterInfo.builder()
                        .conjunction("and")
                        .conditions([
                            Condition.builder()
                            .field_name("应用名称")
                            .operator("is")
                            .value([app_name])
                            .build(),
                            Condition.builder()
                            .field_name("场景")
                            .operator("is")
                            .value([scene])
                            .build(),
                        ])
                        .build()
                    )
                    .build()
                ) \
                .build()

            resp = self.client.bitable.v1.app_table_record.search(req)
            if not resp.success():
                return None
            items = resp.data.items
            if items and len(items) > 0:
                return {"record_id": items[0].record_id, "fields": items[0].fields}
            return None
        except Exception as e:
            print(f"query_by_app_and_scene 异常: {e}")
            return None

    def query_by_scene(self, scene: str) -> list[dict]:
        """根据场景查询所有匹配的记录"""
        try:
            req = SearchAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .request_body(
                    SearchAppTableRecordRequestBody.builder()
                    .field_names(["应用名称", "场景", "大岛", "小岛",
                                  "接入版本", "进度排期", "支持小窗", "支持分享"])
                    .filter(
                        FilterInfo.builder()
                        .conjunction("and")
                        .conditions([
                            Condition.builder()
                            .field_name("场景")
                            .operator("is")
                            .value([scene])
                            .build()
                        ])
                        .build()
                    )
                    .build()
                ) \
                .build()

            resp = self.client.bitable.v1.app_table_record.search(req)
            if not resp.success():
                print(f"按场景查询失败: code={resp.code}, msg={resp.msg}")
                return []

            items = resp.data.items or []
            return [
                {"record_id": r.record_id, "fields": r.fields}
                for r in items
            ]

        except Exception as e:
            print(f"query_by_scene 异常: {e}")
            return []

    def query_all(self) -> list[dict]:
        """查询全部记录，返回 [{record_id, fields}, ...]"""
        try:
            req = SearchAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .request_body(
                    SearchAppTableRecordRequestBody.builder()
                    .field_names(["应用名称", "场景", "大岛", "小岛",
                                  "接入版本", "进度排期", "支持小窗", "支持分享"])
                    .build()
                ) \
                .build()

            resp = self.client.bitable.v1.app_table_record.search(req)
            if not resp.success():
                print(f"查询全部记录失败: code={resp.code}, msg={resp.msg}")
                return []

            items = resp.data.items or []
            return [
                {"record_id": r.record_id, "fields": r.fields}
                for r in items
            ]

        except Exception as e:
            print(f"query_all 异常: {e}")
            return []

    def create_record(self, fields: dict) -> Optional[str]:
        """新增一条记录，返回 record_id 或 None"""
        try:
            req = CreateAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .request_body(
                    AppTableRecord.builder()
                    .fields(fields)
                    .build()
                ) \
                .build()

            resp = self.client.bitable.v1.app_table_record.create(req)
            if not resp.success():
                print(f"新增记录失败: code={resp.code}, msg={resp.msg}")
                return None

            return resp.data.record.record_id

        except Exception as e:
            print(f"create_record 异常: {e}")
            return None

    def update_record(self, record_id: str, fields: dict) -> bool:
        """更新指定记录，返回是否成功"""
        try:
            req = UpdateAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .record_id(record_id) \
                .request_body(
                    AppTableRecord.builder()
                    .fields(fields)
                    .build()
                ) \
                .build()

            resp = self.client.bitable.v1.app_table_record.update(req)
            if not resp.success():
                print(f"更新记录失败: code={resp.code}, msg={resp.msg}")
                return False
            return True

        except Exception as e:
            print(f"update_record 异常: {e}")
            return False

    def upsert_record(self, app_name: str, fields: dict) -> Optional[str]:
        """智能 upsert：按应用名称查询，存在则更新，不存在则新增。返回 record_id"""
        existing = self.query_by_app_name(app_name)
        if existing:
            record_id = existing["record_id"]
            success = self.update_record(record_id, fields)
            if success:
                print(f"已更新记录: {app_name} (record_id={record_id})")
                return record_id
            return None
        else:
            # 确保 fields 中包含应用名称
            fields["应用名称"] = app_name
            record_id = self.create_record(fields)
            if record_id:
                print(f"已新增记录: {app_name} (record_id={record_id})")
            return record_id

    def batch_create_records(self, records: list[dict]) -> dict:
        """批量新增记录，返回 {"success": N, "failed": M, "errors": [...]}"""
        result = {"success": 0, "failed": 0, "errors": []}

        # 飞书 Bitable 批量接口单次上限 500 条，分批处理
        batch_size = 500
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            try:
                req = BatchCreateAppTableRecordRequest.builder() \
                    .app_token(self.app_token) \
                    .table_id(self.table_id) \
                    .request_body(
                        BatchCreateAppTableRecordRequestBody.builder()
                        .records([
                            AppTableRecord.builder().fields(r).build()
                            for r in batch
                        ])
                        .build()
                    ) \
                    .build()

                resp = self.client.bitable.v1.app_table_record.batch_create(req)
                if resp.success():
                    created = resp.data.records or []
                    result["success"] += len(created)
                    print(f"批量写入成功: {len(created)} 条")
                else:
                    result["failed"] += len(batch)
                    error_msg = f"批量写入失败: code={resp.code}, msg={resp.msg}"
                    result["errors"].append(error_msg)
                    print(error_msg)

            except Exception as e:
                result["failed"] += len(batch)
                error_msg = f"batch_create_records 异常: {e}"
                result["errors"].append(error_msg)
                print(error_msg)

        return result

    def delete_record(self, record_id: str) -> bool:
        """删除单条记录"""
        try:
            req = DeleteAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .record_id(record_id) \
                .build()
            resp = self.client.bitable.v1.app_table_record.delete(req)
            if not resp.success():
                print(f"删除记录失败: {resp.msg}")
                return False
            return True
        except Exception as e:
            print(f"delete_record 异常: {e}")
            return False

    def delete_all_records(self) -> int:
        """清空表格中的所有记录，返回删除总数"""
        total_deleted = 0
        while True:
            records = self.query_all()
            if not records:
                break
            ids = [r["record_id"] for r in records]
            try:
                req = BatchDeleteAppTableRecordRequest.builder() \
                    .app_token(self.app_token) \
                    .table_id(self.table_id) \
                    .request_body(
                        BatchDeleteAppTableRecordRequestBody.builder()
                        .records(ids)
                        .build()
                    ) \
                    .build()
                resp = self.client.bitable.v1.app_table_record.batch_delete(req)
                if resp.success():
                    total_deleted += len(ids)
                else:
                    print(f"批量删除失败: {resp.msg}")
                    break
            except Exception as e:
                print(f"delete_all_records 异常: {e}")
                break
        return total_deleted


# 全局单例
bitable_service = BitableService()
