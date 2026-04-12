from pathlib import Path

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.generate_reply.schema import GenerateReplyResultSchema
from app.agent.core.tools.generate_reply.tool import GenerateReplyTool
from app.agent.core.tools.generate_reply_candidates.schema import (
    GenerateReplyCandidatesResultSchema,
    GeneratedReplyCandidateSchema,
)
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store


class GenerateReplyCandidatesTool(GenerateReplyTool):
    """4つの返信テーマに沿った返信候補を生成するツール。"""

    name = "generate_reply_candidates"
    description = "4つの返信テーマに沿って返信候補を生成する"
    THEMES = (
        {
            "theme_id": "question_continue",
            "theme_label": "質問を行い話題継続",
            "instruction": "相手が直前に出した話題をそのまま広げ、最後に質問を1つだけ入れてください。",
        },
        {
            "theme_id": "question_shift",
            "theme_label": "質問を行い話題変換",
            "instruction": "相手の最新メッセージに応答したうえで、自然な接続を入れて別の話題へ移り、質問を1つだけ入れてください。",
        },
        {
            "theme_id": "topic_continue",
            "theme_label": "話題継続し具体的な話題提供",
            "instruction": "相手が直前に出した話題をそのまま広げ、質問に頼らず、相手が返しやすい具体的な話題提供や自己開示を1つ入れてください。",
        },
        {
            "theme_id": "topic_shift",
            "theme_label": "話題変換し具体的な話題提供",
            "instruction": "相手の最新メッセージに応答したうえで、自然な接続を入れて別の話題へ移り、質問に頼らず、相手が返しやすい具体的な話題提供や自己開示を1つ入れてください。",
        },
    )

    def __init__(self) -> None:
        self.llm = self._build_llm()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        # execution_idを基に共有ストアとキャンバスを取得する
        scoped_store = get_shared_store(execution_id)
        scoped_canvas = get_shared_canvas(execution_id)

        # 実行に必要な情報の取得
        self_profile = scoped_store.get("self_profile", {})
        profile = scoped_store.get("profile", {})
        conversation = scoped_store.get("conversation", {})
        messages = conversation.get("messages", [])
        conversation_facts = scoped_canvas.get("conversation_facts", {})

        # 相手の最新メッセージを取得
        latest_message = None
        for msg in reversed(messages):
            if msg.get("sender") == "other":
                latest_message = msg
                break

        # プロンプトに渡すための入力データを構築
        input_payload = {
            "self_profile_text": self._build_self_profile_text(self_profile),
            "profile_text": self._build_profile_text(profile),
            "conversation_text": self._build_conversation_text(messages),
            "conversation_facts_text": self._build_conversation_facts_text(conversation_facts),
            "fact_collection_guidance": self._build_fact_collection_guidance(conversation_facts),
            "latest_message": latest_message.get("message", "") if latest_message else "最新のメッセージはありません。これから作るものが初回メッセージです。",
        }

        try:
            structured_llm = self.llm.with_structured_output(GenerateReplyResultSchema)
            generated_candidates: list[GeneratedReplyCandidateSchema] = []

            for index, theme in enumerate(self.THEMES, start=1):
                prompt_value = self.prompt.invoke(
                    {
                        **input_payload,
                        "reply_theme": theme["theme_label"],
                        "reply_theme_instruction": theme["instruction"],
                    }
                )
                result = structured_llm.invoke(prompt_value)
                reply_data = GenerateReplyResultSchema.model_validate(result)
                generated_candidates.append(
                    GeneratedReplyCandidateSchema(
                        candidate_id=f"candidate_{index}",
                        theme_id=theme["theme_id"],
                        theme_label=theme["theme_label"],
                        reply_text=reply_data.reply_text,
                        tone=reply_data.tone,
                        reasoning=reply_data.reasoning,
                        follow_up_suggestion=reply_data.follow_up_suggestion,
                        selected=False,
                    )
                )

            result_data = GenerateReplyCandidatesResultSchema(
                reply_candidates=generated_candidates,
            )
            candidate_payload = [candidate.model_dump() for candidate in result_data.reply_candidates]

            scoped_canvas["reply_candidates"] = candidate_payload
            scoped_canvas["selected_reply_candidate_id"] = ""
            scoped_canvas["reply_selection_reason"] = ""
            scoped_canvas["reply_selection_summary"] = {}
            scoped_canvas["generated_reply"] = ""
            scoped_canvas["reply_reasoning"] = ""

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="4つの返信候補を生成しました。",
                tool_result={
                    "reply_candidates": candidate_payload,
                    "candidate_count": len(candidate_payload),
                },
            )
        except Exception as exc:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"返信候補生成中にエラーが発生しました: {str(exc)}",
                tool_result={},
            )

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _build_llm(self):
        return self._get_chat_model()

    def _get_chat_model(self):
        from app.agent.core.services.llm_client import get_chat_model_gpt5_4

        return get_chat_model_gpt5_4()
