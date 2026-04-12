from typing import Any

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.tools.evaluate_reply_candidates.schema import (
    EvaluateReplyCandidatesResultSchema,
)
from app.agent.core.tools.reply_rule_check.tool import ReplyRuleCheckTool
from app.agent.core.tools.reply_safety_check.tool import ReplySafetyCheckTool
from app.agent.core.utils.improvement_feedback import merge_improvement_suggestions
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store


class EvaluateReplyCandidatesTool:
    """返信候補を安全性とルールで評価し、最適候補を選抜するツール。"""

    name = "evaluate_reply_candidates"
    description = "複数の返信候補を安全性とルールで評価し、最適な候補を選ぶ"

    def __init__(self) -> None:
        self.safety_tool = ReplySafetyCheckTool()
        self.rule_tool = ReplyRuleCheckTool()

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        scoped_store = get_shared_store(execution_id)
        scoped_canvas = get_shared_canvas(execution_id)
        raw_candidates = scoped_canvas.get("reply_candidates", [])

        if not isinstance(raw_candidates, list) or not raw_candidates:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="評価対象の返信候補が見つかりません。",
                tool_result={},
            )

        conversation = scoped_store.get("conversation", {})
        messages = conversation.get("messages", []) if isinstance(conversation, dict) else []
        profile = scoped_store.get("profile", {})
        evaluated_candidates: list[dict[str, Any]] = []

        try:
            for candidate in raw_candidates:
                candidate_payload = dict(candidate) if isinstance(candidate, dict) else {}
                reply_text = str(candidate_payload.get("reply_text", "")).strip()
                if not reply_text:
                    return BaseToolResult(
                        tool_name=self.name,
                        success=False,
                        summary="返信候補に reply_text が存在しません。",
                        tool_result={},
                    )

                safety_result = self.safety_tool.evaluate_reply_text(reply_text, messages)
                candidate_payload["safety_check"] = safety_result

                if safety_result.get("safety_ok", False):
                    rule_result = self.rule_tool.evaluate_reply_text(reply_text, messages, profile)
                else:
                    rule_result = {
                        "rule_score": 0,
                        "passed": False,
                        "should_regenerate": True,
                        "reasons": ["安全性チェックを通過していないため、順位付け対象外です。"],
                        "improvement_suggestions": [],
                        "violations": ["safety_blocked"],
                    }

                candidate_payload["rule_check"] = rule_result
                candidate_payload["final_score"] = int(rule_result.get("rule_score", 0) or 0) if safety_result.get("safety_ok", False) else 0
                candidate_payload["selected"] = False
                evaluated_candidates.append(candidate_payload)

            ranked_candidates = sorted(
                evaluated_candidates,
                key=lambda item: (
                    bool(item.get("safety_check", {}).get("safety_ok", False)),
                    int(item.get("final_score", 0) or 0),
                ),
                reverse=True,
            )

            selected_candidate: dict[str, Any] | None = None
            passed_candidate_count = 0
            for rank, candidate in enumerate(ranked_candidates, start=1):
                candidate["rank"] = rank
                if candidate.get("safety_check", {}).get("safety_ok", False):
                    passed_candidate_count += 1
                    if selected_candidate is None:
                        candidate["selected"] = True
                        selected_candidate = candidate

            scoped_canvas["reply_candidates"] = ranked_candidates
            scoped_canvas["improvement_suggestions"] = []

            if selected_candidate is None:
                selection_reason = "安全性を通過した候補がなかったため、返信候補の再生成が必要です。"
                scoped_canvas["selected_reply_candidate_id"] = ""
                scoped_canvas["reply_selection_reason"] = selection_reason
                scoped_canvas["reply_selection_summary"] = {
                    "selected_candidate_id": "",
                    "selection_reason": selection_reason,
                    "evaluated_candidate_count": len(ranked_candidates),
                }
                scoped_canvas["generated_reply"] = ""
                scoped_canvas["reply_reasoning"] = ""
                scoped_canvas["reply_should_regenerate"] = True
                scoped_canvas["reply_safety_ok"] = False
                scoped_canvas["reply_safety_reasons"] = [selection_reason]
                scoped_canvas["reply_rule_score"] = 0
                scoped_canvas["reply_rule_passed"] = False
                scoped_canvas["reply_rule_reasons"] = [selection_reason]
            else:
                safety_suggestions = selected_candidate.get("safety_check", {}).get("improvement_suggestions", [])
                rule_suggestions = selected_candidate.get("rule_check", {}).get("improvement_suggestions", [])
                merged_suggestions = merge_improvement_suggestions(
                    safety_suggestions,
                    rule_suggestions,
                    default_priority="high",
                )
                selection_reason = (
                    f"安全性を通過した候補の中で、ルールスコアが最も高かったため {selected_candidate.get('candidate_id', '')} を採用しました。"
                )
                scoped_canvas["selected_reply_candidate_id"] = str(selected_candidate.get("candidate_id", ""))
                scoped_canvas["reply_selection_reason"] = selection_reason
                scoped_canvas["reply_selection_summary"] = {
                    "selected_candidate_id": str(selected_candidate.get("candidate_id", "")),
                    "selected_theme_id": str(selected_candidate.get("theme_id", "")),
                    "selection_reason": selection_reason,
                    "evaluated_candidate_count": len(ranked_candidates),
                }
                scoped_canvas["generated_reply"] = str(selected_candidate.get("reply_text", ""))
                scoped_canvas["reply_reasoning"] = str(selected_candidate.get("reasoning", ""))
                scoped_canvas["reply_should_regenerate"] = bool(selected_candidate.get("rule_check", {}).get("should_regenerate", False))
                scoped_canvas["reply_safety_ok"] = bool(selected_candidate.get("safety_check", {}).get("safety_ok", False))
                scoped_canvas["reply_safety_reasons"] = list(selected_candidate.get("safety_check", {}).get("reasons", []))
                scoped_canvas["reply_rule_score"] = int(selected_candidate.get("rule_check", {}).get("rule_score", 0) or 0)
                scoped_canvas["reply_rule_passed"] = bool(selected_candidate.get("rule_check", {}).get("passed", False))
                scoped_canvas["reply_rule_reasons"] = list(selected_candidate.get("rule_check", {}).get("reasons", []))
                scoped_canvas["improvement_suggestions"] = [
                    suggestion.model_dump() for suggestion in merged_suggestions
                ]

            result_data = EvaluateReplyCandidatesResultSchema(
                selected_reply_candidate_id=str(scoped_canvas.get("selected_reply_candidate_id", "")),
                candidate_count=len(ranked_candidates),
                passed_candidate_count=passed_candidate_count,
                should_regenerate=bool(scoped_canvas.get("reply_should_regenerate", False)),
                reply_selection_reason=str(scoped_canvas.get("reply_selection_reason", "")),
            )

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="返信候補を評価し、最適候補を選抜しました。",
                tool_result={
                    **result_data.model_dump(),
                    "reply_candidates": ranked_candidates,
                },
            )
        except Exception as exc:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"返信候補評価中にエラーが発生しました: {str(exc)}",
                tool_result={},
            )
