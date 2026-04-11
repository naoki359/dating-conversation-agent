from pathlib import Path
from textwrap import dedent
from typing import Any

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.generate_reply.schema import GenerateReplyResultSchema
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import (
    DEFAULT_MEETING_TIMING_PREFERENCE,
    get_shared_canvas,
    get_shared_store,
)


class GenerateReplyTool:
    """相手のメッセージに対して適切な返信を生成するツール。"""

    name = "generate_reply"
    description = "相手のプロフィールと会話履歴を参考に、自然な返信を生成する"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        """返信を生成する。"""
        # 必要なデータを取得
        scoped_store = get_shared_store(execution_id)
        scoped_canvas = get_shared_canvas(execution_id)
        self_profile = scoped_store.get("self_profile", {})
        profile = scoped_store.get("profile", {})
        conversation = scoped_store.get("conversation", {})
        messages = conversation.get("messages", [])
        conversation_facts = scoped_canvas.get("conversation_facts", {})

        # 初回メッセージ作成時は空になるため、コメントアウト
        # if not messages:
        #     return BaseToolResult(
        #         tool_name=self.name,
        #         success=False,
        #         summary="会話履歴が見つかりません。",
        #         tool_result={},
        #     )

        # 最新のメッセージ（相手からのメッセージ）を取得
        latest_message = None
        for msg in reversed(messages):
            if msg.get("sender") == "other":
                latest_message = msg
                break

        # 初回メッセージ作成時は空になるため、コメントアウト
        # if not latest_message:
        #     return BaseToolResult(
        #         tool_name=self.name,
        #         success=False,
        #         summary="相手からのメッセージが見つかりません。",
        #         tool_result={},
        #     )

        # プロンプト用のテキストを構築
        self_profile_text = self._build_self_profile_text(self_profile)
        profile_text = self._build_profile_text(profile)
        conversation_text = self._build_conversation_text(messages)
        conversation_facts_text = self._build_conversation_facts_text(conversation_facts)
        fact_collection_guidance = self._build_fact_collection_guidance(conversation_facts)
        latest_message_text = latest_message.get("message", "") if latest_message else "最新のメッセージはありません。これから作るものが初回メッセージです。"

        print("=== プロンプト用テキスト（会話履歴） ===")
        print(fact_collection_guidance)

        try:
            # LLMに構造化出力を指定
            prompt_value = self.prompt.invoke(
                {
                    "self_profile_text": self_profile_text,
                    "profile_text": profile_text,
                    "conversation_text": conversation_text,
                    "conversation_facts_text": conversation_facts_text,
                    "fact_collection_guidance": fact_collection_guidance,
                    "latest_message": latest_message_text,
                }
            )

            structured_llm = self.llm.with_structured_output(GenerateReplyResultSchema)
            result = structured_llm.invoke(prompt_value)

            try:
                reply_data = GenerateReplyResultSchema.model_validate(result)
                scoped_canvas = get_shared_canvas(execution_id)
                scoped_canvas["generated_reply"] = reply_data.reply_text
                scoped_canvas["reply_reasoning"] = reply_data.reasoning
            except Exception as e:
                return BaseToolResult(
                    tool_name=self.name,
                    success=False,
                    summary=f"返信データの処理に失敗しました: {str(e)}",
                    tool_result={},
                )

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="返信を生成しました。",
                tool_result=reply_data.model_dump(),
            )
        except Exception as e:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"返信生成中にエラーが発生しました: {str(e)}",
                tool_result={},
            )

    def _get_prompt_path(self) -> Path:
        """プロンプトファイルのパスを取得。"""
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _build_profile_text(self, profile: dict[str, Any]) -> str:
        """プロフィールテキストを構築。"""
        name = profile.get("name", "")
        age = profile.get("age", "")
        profile_summary = profile.get("profile_summary", "")
        meeting_timing_preference = (
            profile.get("meeting_timing_preference")
            or DEFAULT_MEETING_TIMING_PREFERENCE
        )

        return dedent(
            f"""
            [基本情報]
            名前: {name}
            年齢: {age}
            出会うまでの希望: {meeting_timing_preference}

            [プロフィール要約]
            {profile_summary}
            """
        ).strip()

    def _build_self_profile_text(self, profile: dict[str, Any]) -> str:
        """自分のプロフィールテキストを構築。"""
        if not profile:
            return "自分のプロフィール情報はありません。"

        name = profile.get("name", "")
        age = profile.get("age", "")
        profile_summary = profile.get("profile_summary", "")
        raw_profile_text = str(profile.get("raw_profile_text", "")).strip()

        return dedent(
            f"""
            [基本情報]
            名前: {name}
            年齢: {age}

            [プロフィール要約]
            {profile_summary or '要約はありません。'}

            [プロフィール原文]
            {raw_profile_text or '原文はありません。'}
            """
        ).strip()

    def _build_conversation_text(self, messages: list[dict[str, Any]]) -> str:
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

    def _build_conversation_facts_text(self, conversation_facts: dict) -> str:
        """抽出済みの重要情報テキストを構築。"""
        if not conversation_facts:
            return "抽出済み情報はありません。"

        meeting_area = conversation_facts.get("meeting_area")
        available_time = conversation_facts.get("available_time")

        meeting_area_text = "meeting_area: 未取得"
        if meeting_area:
            meeting_area_text = dedent(
                f"""
                meeting_area: {meeting_area.get('value', '') or '未取得'}
                confidence: {meeting_area.get('confidence', '') or 'unknown'}
                source_quote: {meeting_area.get('source_quote', '') or 'なし'}
                """
            ).strip()

        available_time_text = "available_time: 未取得"
        if available_time:
            available_time_text = dedent(
                f"""
                available_time: {available_time.get('value', '') or '未取得'}
                confidence: {available_time.get('confidence', '') or 'unknown'}
                source_quote: {available_time.get('source_quote', '') or 'なし'}
                """
            ).strip()

        return f"{meeting_area_text}\n\n{available_time_text}"

    def _build_fact_collection_guidance(self, conversation_facts: dict) -> str:
        """情報取得の優先度に関するガイダンスを構築。"""
        meeting_area = conversation_facts.get("meeting_area") if conversation_facts else None
        available_time = conversation_facts.get("available_time") if conversation_facts else None

        missing_facts: list[str] = []
        if not meeting_area or not meeting_area.get("value"):
            missing_facts.append(
                "meeting_area が未取得です。自然な流れを崩さず、次の会話で会いやすいエリアを聞き出せる返信を優先してください。"
            )
        if not available_time or not available_time.get("value"):
            missing_facts.append(
                "available_time が未取得です。自然な流れを崩さず、次の会話で空いている時間帯を聞き出せる返信を優先してください。"
            )

        if missing_facts:
            return "".join(missing_facts) + "デート提案は必要情報の取得後に行ってください。"

        return (
            "meeting_area と available_time は取得済みです。"
            "会話フェーズに応じて、自然なタイミングでデート提案を検討できます。"
        )
