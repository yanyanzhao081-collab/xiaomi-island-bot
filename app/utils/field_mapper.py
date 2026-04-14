"""表格列名 → Bitable 标准字段名映射"""

import pandas as pd

# 标准字段名 → 可能的用户列名别名（全小写匹配）
COLUMN_ALIASES = {
    "应用名称": ["app", "应用", "应用名", "名称", "app_name", "应用名称"],
    "场景": ["scene", "场景", "接入场景"],
    "大岛": ["big_island", "一级分类", "大岛"],
    "小岛": ["small_island", "二级分类", "小岛"],
    "接入版本": ["version", "版本", "接入版本"],
    "进度排期": ["schedule", "进度", "排期", "时间", "进度排期", "进度与排期"],
    "支持小窗": ["mini_window", "小窗", "支持小窗", "是否支持小窗"],
    "支持分享": ["share", "分享", "支持分享", "是否支持分享"],
}

# 反向索引：别名 → 标准字段名
_ALIAS_MAP = {}
for standard, aliases in COLUMN_ALIASES.items():
    for alias in aliases:
        _ALIAS_MAP[alias.lower().strip()] = standard


def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """将 DataFrame 的列名映射为标准字段名，忽略无法映射的列"""
    rename_map = {}
    for col in df.columns:
        key = str(col).lower().strip()
        if key in _ALIAS_MAP:
            rename_map[col] = _ALIAS_MAP[key]

    df = df.rename(columns=rename_map)

    # 只保留标准字段列
    standard_fields = list(COLUMN_ALIASES.keys())
    valid_cols = [c for c in df.columns if c in standard_fields]
    return df[valid_cols]
