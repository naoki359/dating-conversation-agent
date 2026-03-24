import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    AGENT_LOG_ENABLED: bool = os.getenv("AGENT_LOG_ENABLED", "true").lower() == "true"
    AGENT_LOG_DIR: str = os.getenv("AGENT_LOG_DIR", "logs")
    AGENT_LOG_CONVERSATION_TAIL_COUNT: int = int(
        os.getenv("AGENT_LOG_CONVERSATION_TAIL_COUNT", "3")
    )

    @classmethod
    def validate(cls):
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY が設定されていません")