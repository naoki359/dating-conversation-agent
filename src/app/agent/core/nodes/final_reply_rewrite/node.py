from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import override

from app.agent.core.nodes.base_node import BaseNode
from app.agent.core.nodes.final_reply_rewrite.schema import (
    ConversationWordClassification,
    FinalReplyRewriteOutputSchema,
    FinalReplyRewriteStructuredOutputSchema,
)
from app.agent.core.schemas.base_output_schema import BaseOutputSchema
from app.agent.core.schemas.state import ReactState
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.utils.formatCommon import format_conversation_text
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store


class FinalReplyRewriteNode(BaseNode):
    """会話履歴から分類表を作成し、最終返信を言いかえるノード。"""

    node_name = "final_reply_rewrite_node"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())
        self._last_execution_id: str | None = None

    def execute(self, state: ReactState) -> FinalReplyRewriteOutputSchema:
        execution_id = state.get("execution_id")
        self._last_execution_id = execution_id

        scoped_store = get_shared_store(execution_id)
        scoped_canvas = get_shared_canvas(execution_id)

        original_reply = str(scoped_canvas.get("generated_reply", "")).strip()
        conversation = scoped_store.get("conversation", {})
        conversation_text = self._build_conversation_text(conversation.get("messages", []))

        if not original_reply:
            return FinalReplyRewriteOutputSchema(
                node_name=self.node_name,
                success=True,
                summary="返信案が存在しないため、最終言いかえは行いませんでした。",
                reasoning="generated_reply が空のため、そのまま終了しました。",
                thought_process=["generated_reply が空であることを確認"],
                rewritten_reply="",
                detected_repetition_risks=[],
                word_classification=ConversationWordClassification(),
            )

        prompt_value = self.prompt.invoke(
            {
                "conversation_text": conversation_text,
                "original_reply": original_reply,
            }
        )

        structured_llm = self.llm.with_structured_output(
            FinalReplyRewriteStructuredOutputSchema
        )
        result = structured_llm.invoke(prompt_value)

        rewritten_reply = result.rewritten_reply.strip() or original_reply
        repetition_risks = result.detected_repetition_risks

        summary = "会話履歴の分類表を作成し、最終返信を言いかえました。"
        if rewritten_reply == original_reply:
            summary = "会話履歴の分類表を作成し、元の返信をそのまま採用しました。"

        thought_process = repetition_risks or ["顕著な重複リスクは限定的でした。"]

        return FinalReplyRewriteOutputSchema(
            node_name=self.node_name,
            success=True,
            summary=summary,
            reasoning=result.reasoning,
            thought_process=thought_process,
            rewritten_reply=rewritten_reply,
            detected_repetition_risks=repetition_risks,
            word_classification=result.word_classification,
        )

    @override
    def update_state(
        self,
        node_result: BaseOutputSchema,
        state: ReactState,
    ) -> ReactState:
        assert isinstance(node_result, FinalReplyRewriteOutputSchema)

        return {
            **state,
            "is_finished": True,
        }

    @override
    def canvas_update(self, node_result: BaseOutputSchema) -> None:
        if not isinstance(node_result, FinalReplyRewriteOutputSchema):
            return

        scoped_canvas = get_shared_canvas(self._last_execution_id)
        scoped_canvas["generated_reply"] = node_result.rewritten_reply
        scoped_canvas["reply_reasoning"] = node_result.reasoning
        scoped_canvas["conversation_word_classification"] = (
            node_result.word_classification.model_dump()
        )

    def console_render(self, result: BaseOutputSchema) -> None:
        if not isinstance(result, FinalReplyRewriteOutputSchema):
            return

        print("\n=== FinalReplyRewriteNode ===")
        print(result.summary)

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _build_conversation_text(self, messages: list[dict]) -> str:
        return format_conversation_text(messages, strip_message=True)
