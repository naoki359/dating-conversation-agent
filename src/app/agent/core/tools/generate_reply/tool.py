from pathlib import Path
from textwrap import dedent

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.generate_reply.schema import GenerateReplyResultSchema
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store


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

        if not latest_message:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="相手からのメッセージが見つかりません。",
                tool_result={},
            )

        # プロンプト用のテキストを構築
        profile_text = self._build_profile_text(profile)
        conversation_text = self._build_conversation_text(messages)
        conversation_facts_text = self._build_conversation_facts_text(conversation_facts)
        fact_collection_guidance = self._build_fact_collection_guidance(conversation_facts)
        latest_message_text = latest_message.get("message", "")

        print("=== プロンプト用テキスト（会話履歴） ===")
        print(fact_collection_guidance)

        try:
            # LLMに構造化出力を指定
            prompt_value = self.prompt.invoke(
                {
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

    def _build_conversation_facts_text(self, conversation_facts: dict) -> str:
        """抽出済みの重要情報テキストを構築。"""
        if not conversation_facts:
            return "抽出済み情報はありません。"

        meeting_area = conversation_facts.get("meeting_area")
        if not meeting_area:
            return "meeting_area: 未取得"

        value = meeting_area.get("value", "")
        confidence = meeting_area.get("confidence", "")
        source_quote = meeting_area.get("source_quote", "")
        return dedent(
            f"""
            meeting_area: {value or '未取得'}
            confidence: {confidence or 'unknown'}
            source_quote: {source_quote or 'なし'}
            """
        ).strip()

    def _build_fact_collection_guidance(self, conversation_facts: dict) -> str:
        """情報取得の優先度に関するガイダンスを構築。"""
        meeting_area = conversation_facts.get("meeting_area") if conversation_facts else None
        if not meeting_area or not meeting_area.get("value"):
            return (
                "meeting_area が未取得です。"
                "自然な流れを崩さず、次の会話で会いやすいエリアを聞き出せる返信を優先してください。"
                "デート提案は meeting_area 取得後に行ってください。"
            )

        return (
            "meeting_area は取得済みです。"
            "会話フェーズに応じて、自然なタイミングでデート提案を検討できます。"
        )
