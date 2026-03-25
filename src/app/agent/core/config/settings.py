import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ========= ① LLM =========
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # ========= ② ログ =========
    AGENT_LOG_ENABLED: bool = os.getenv("AGENT_LOG_ENABLED", "true").lower() == "true"
    AGENT_LOG_DIR: str = os.getenv("AGENT_LOG_DIR", "logs")
    AGENT_LOG_CONVERSATION_TAIL_COUNT: int = int(
        os.getenv("AGENT_LOG_CONVERSATION_TAIL_COUNT", "3")
    )

    # ========= ③ 表示 =========
    AGENT_LOCAL_MODE: bool = os.getenv("AGENT_LOCAL_MODE", "true").lower() == "true"
    AGENT_CONSOLE_LOG_ENABLED: bool = os.getenv(
        "AGENT_CONSOLE_LOG_ENABLED", "true"
    ).lower() == "true"

    # ========= 将来拡張 =========
    AGENT_CONSOLE_USE_LLM: bool = os.getenv(
        "AGENT_CONSOLE_USE_LLM", "false"
    ).lower() == "true"

    @classmethod
    def validate(cls):
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY が設定されていません")