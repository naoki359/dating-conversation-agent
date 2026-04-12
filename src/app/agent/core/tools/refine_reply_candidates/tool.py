from typing import Any

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.refine_reply.tool import RefineReplyTool
from app.agent.core.utils.improvement_feedback import merge_improvement_suggestions
from app.agent.core.utils.shared_store import get_shared_canvas


class RefineReplyCandidatesTool:
    """共有キャンバス上の返信候補すべてに refine_reply を適用するツール。"""

    name = "refine_reply_candidates"
    description = "保存済みの返信候補すべてに改善提案を反映する"

    def __init__(self) -> None:
        self.refine_tool = RefineReplyTool()

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        scoped_canvas = get_shared_canvas(execution_id)
        raw_candidates = scoped_canvas.get("reply_candidates", [])

        if not isinstance(raw_candidates, list) or not raw_candidates:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="修正対象の返信候補が見つかりません。",
                tool_result={},
            )

        original_generated_reply = scoped_canvas.get("generated_reply", "")
        original_reply_reasoning = scoped_canvas.get("reply_reasoning", "")
        original_improvement_suggestions = scoped_canvas.get("improvement_suggestions", [])
        original_reply_should_regenerate = scoped_canvas.get("reply_should_regenerate", False)
        original_reply_candidates = list(raw_candidates)

        refined_candidates: list[dict[str, Any]] = []
        refined_count = 0

        try:
            for raw_candidate in raw_candidates:
                candidate = dict(raw_candidate) if isinstance(raw_candidate, dict) else {}
                reply_text = str(candidate.get("reply_text", "")).strip()
                if not reply_text:
                    return BaseToolResult(
                        tool_name=self.name,
                        success=False,
                        summary="返信候補に reply_text が存在しません。",
                        tool_result={},
                    )

                safety_suggestions = candidate.get("safety_check", {}).get("improvement_suggestions", [])
                rule_suggestions = candidate.get("rule_check", {}).get("improvement_suggestions", [])
                merged_suggestions = merge_improvement_suggestions(
                    safety_suggestions,
                    rule_suggestions,
                    default_priority="high",
                )

                scoped_canvas["generated_reply"] = reply_text
                scoped_canvas["reply_reasoning"] = str(candidate.get("reasoning", ""))
                scoped_canvas["improvement_suggestions"] = [
                    suggestion.model_dump() for suggestion in merged_suggestions
                ]
                scoped_canvas["reply_should_regenerate"] = bool(
                    candidate.get("rule_check", {}).get("should_regenerate", False)
                )

                tool_result = self.refine_tool.execute(execution_id)
                if not tool_result.success:
                    return BaseToolResult(
                        tool_name=self.name,
                        success=False,
                        summary=(
                            f"候補 {candidate.get('candidate_id', '')} の修正に失敗しました。"
                            f"原因: {tool_result.summary}"
                        ),
                        tool_result={},
                    )

                refined_candidate = {
                    **candidate,
                    "reply_text": str(scoped_canvas.get("generated_reply", reply_text)),
                    "reasoning": str(scoped_canvas.get("reply_reasoning", candidate.get("reasoning", ""))),
                    "selected": False,
                }
                refined_candidates.append(refined_candidate)
                refined_count += 1

            scoped_canvas["reply_candidates"] = refined_candidates
            scoped_canvas["generated_reply"] = original_generated_reply
            scoped_canvas["reply_reasoning"] = original_reply_reasoning
            scoped_canvas["improvement_suggestions"] = original_improvement_suggestions
            scoped_canvas["reply_should_regenerate"] = original_reply_should_regenerate

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="保存済みの返信候補すべてに改善提案を反映しました。",
                tool_result={
                    "refined_candidate_count": refined_count,
                    "reply_candidates": refined_candidates,
                },
            )
        except Exception:
            scoped_canvas["reply_candidates"] = original_reply_candidates
            scoped_canvas["generated_reply"] = original_generated_reply
            scoped_canvas["reply_reasoning"] = original_reply_reasoning
            scoped_canvas["improvement_suggestions"] = original_improvement_suggestions
            scoped_canvas["reply_should_regenerate"] = original_reply_should_regenerate
            raise
