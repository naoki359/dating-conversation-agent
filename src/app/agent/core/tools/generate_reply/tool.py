from pathlib import Path
from textwrap import dedent

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.generate_reply.schema import GenerateReplyResultSchema
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import shared_store


class GenerateReplyTool:
    """相手のメッセージに対して適切な返信を生成するツール。"""

    name = "generate_reply"
    description = "相手のプロフィールと会話履歴を参考に、自然な返信を生成する"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self) -> BaseToolResult:
        """返信を生成する。"""
        # 必要なデータを取得
        profile = shared_store.get("profile", {})
        conversation = shared_store.get("conversation", {})
        messages = conversation.get("messages", [])

        if not messages:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="会話履歴が見つかりません。",
                data={},
            )

        # 最新のメッセージ（相手からのメッセージ）を取得
        latest_message = None
        for msg in reversed(messages):
            if msg.get("sender") == "other":
                latest_message = msg
                break

        if not latest_message:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="相手からのメッセージが見つかりません。",
                data={},
            )

        # プロンプト用のテキストを構築
        profile_text = self._build_profile_text(profile)
        conversation_text = self._build_conversation_text(messages)
        latest_message_text = latest_message.get("message", "")

        try:
            # LLMに構造化出力を指定
            prompt_value = self.prompt.invoke(
                {
                    "profile_text": profile_text,
                    "conversation_text": conversation_text,
                    "latest_message": latest_message_text,
                }
            )

            structured_llm = self.llm.with_structured_output(GenerateReplyResultSchema)
            result = structured_llm.invoke(prompt_value)

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary=f"返信を生成しました。",
                data=result.model_dump(),
            )
        except Exception as e:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"返信生成中にエラーが発生しました: {str(e)}",
                data={},
            )

    def _get_prompt_path(self) -> Path:
        """プロンプトファイルのパスを取得。"""
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _build_profile_text(self, profile: dict) -> str:
        """プロフィールテキストを構築。"""
        name = profile.get("name", "")
        age = profile.get("age", "")
        profile_summary = profile.get("profile_summary", "")

        return dedent(
            f"""
            [基本情報]
            名前: {name}
            年齢: {age}

            [プロフィール要約]
            {profile_summary}
            """
        ).strip()

    def _build_conversation_text(self, messages: list) -> str:
        """会話履歴テキストを構築。"""
        if not messages:
            return "会話履歴はありません。"

        lines = []
        for msg in messages:
            sender = msg.get("sender", "")
            message = msg.get("message", "")
            sender_label = "相手" if sender == "other" else "自分"
            lines.append(f"{sender_label}: {message}")

        return "\n".join(lines)
