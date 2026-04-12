import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_VALID_DATA_SOURCES = {"test", "prod"}
_VALID_PIPELINE_MODES = {"fixed", "react"}
_DATA_SOURCE_DIR_MAP = {
    "test": "test_user",
    "prod": "user",
}


class Settings:
    # ========= ① LLM =========
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # ========= ② データソース =========
    DATA_SOURCE: str = os.getenv("DATA_SOURCE", "test")

    # ========= ③ ログ =========
    AGENT_LOG_ENABLED: bool = os.getenv("AGENT_LOG_ENABLED", "true").lower() == "true"
    AGENT_LOG_DIR: str = os.getenv("AGENT_LOG_DIR", "logs")
    AGENT_LOG_CONVERSATION_TAIL_COUNT: int = int(
        os.getenv("AGENT_LOG_CONVERSATION_TAIL_COUNT", "3")
    )

    # ========= ④ 表示 =========
    AGENT_LOCAL_MODE: bool = os.getenv("AGENT_LOCAL_MODE", "true").lower() == "true"
    AGENT_CONSOLE_LOG_ENABLED: bool = os.getenv(
        "AGENT_CONSOLE_LOG_ENABLED", "true"
    ).lower() == "true"

    # ========= ⑤ 将来拡張 =========
    AGENT_CONSOLE_USE_LLM: bool = os.getenv(
        "AGENT_CONSOLE_USE_LLM", "false"
    ).lower() == "true"

    # ========= ⑥ 実行パイプライン =========
    AGENT_PIPELINE_MODE: str = os.getenv("AGENT_PIPELINE_MODE", "fixed")

    @classmethod
    def get_data_dir(cls) -> Path:
        project_root = Path(__file__).resolve().parents[5]
        subdir = _DATA_SOURCE_DIR_MAP[cls.DATA_SOURCE]
        return project_root / "data" / subdir

    @classmethod
    def validate(cls):
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY が設定されていません")
        if cls.DATA_SOURCE not in _VALID_DATA_SOURCES:
            raise ValueError(
                f"DATA_SOURCE の値が不正です: '{cls.DATA_SOURCE}' "
                f"(有効な値: {', '.join(sorted(_VALID_DATA_SOURCES))})"
            )
        if cls.AGENT_PIPELINE_MODE not in _VALID_PIPELINE_MODES:
            raise ValueError(
                f"AGENT_PIPELINE_MODE の値が不正です: '{cls.AGENT_PIPELINE_MODE}' "
                f"(有効な値: {', '.join(sorted(_VALID_PIPELINE_MODES))})"
            )