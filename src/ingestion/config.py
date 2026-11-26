"""Load provider credentials from separate, explicit env files."""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import dotenv_values


def _load_env_file(filename: str) -> dict[str, str]:
    path = Path(filename).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Environment file not found: {path}")
    values = dotenv_values(path)
    return {key: str(value) for key, value in values.items() if value is not None}


def load_aliyun_config(filename: str = ".env.aliyun") -> dict[str, str]:
    values = _load_env_file(filename)
    return {
        "access_key_id": values.get("ALIYUN_ACCESS_KEY_ID", ""),
        "access_key_secret": values.get("ALIYUN_ACCESS_KEY_SECRET", ""),
        "endpoint": values.get("ALIYUN_SLS_ENDPOINT", ""),
        "project": values.get("ALIYUN_SLS_PROJECT", ""),
        "logstore": values.get("ALIYUN_SLS_LOGSTORE", ""),
        "region": values.get("ALIYUN_SLS_REGION", ""),
    }


def load_tencent_config(filename: str = ".env.tencent") -> dict[str, str]:
    values = _load_env_file(filename)
    return {
        "secret_id": values.get("TENCENT_SECRET_ID", ""),
        "secret_key": values.get("TENCENT_SECRET_KEY", ""),
        "endpoint": values.get("TENCENT_CLS_ENDPOINT", ""),
        "region": values.get("TENCENT_CLS_REGION", ""),
        "topic_id": values.get("TENCENT_CLS_TOPIC_ID", ""),
    }
