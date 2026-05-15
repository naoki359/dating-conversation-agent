from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.tools.generate_hint_candidates.schema import HintCandidatesSchema
from app.agent.core.utils.formatCommon import (
    format_conversation_text,
    format_profile_text,
    format_self_profile_text,
)
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store

_JST = timezone(timedelta(hours=9))

# ヒント履歴ファイル: agent_logs/hints.yaml（全ユーザー共通の1ファイル）
_HINTS_FILE = Path(__file__).resolve().parents[6] / "agent_logs" / "hints.yaml"


class GenerateHintCandidatesTool:
    """返信生成後に次回向けのヒントを1件生成し data/config/hints.yaml に追記するツール。

    現時点では保存のみで参照は行わない。
    将来的なユーザー嗜好性モデルの基盤として活用することを想定している。
    """

    name = "generate_hint_candidates"
    description = (
        "返信生成後に次回の会話で役立つヒントを1件自動生成し、agent_logs/hints.yaml に追記する。"
        "生成したヒントは現時点では参照しない（将来的なユーザー嗜好性学習のために保持）。"
    )

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        """ヒントを1件生成し data/config/hints.yaml に追記する。
        
        now_hint が空の場合は記録をスキップする。
        """
        scoped_store = get_shared_store(execution_id)
        scoped_canvas = get_shared_canvas(execution_id)

        user_id = scoped_store.get("user_id", "")
        if not user_id:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary="user_id が見つからないためヒントを生成できません。",
                tool_result={},
            )

        now_hint = scoped_store.get("conversation", {}).get("now_hint", "")
        if not now_hint:
            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="now_hint が設定されていないため、ヒントの記録をスキップしました。",
                tool_result={},
            )

        self_profile = scoped_store.get("self_profile", {})
        profile = scoped_store.get("profile", {})
        conversation = scoped_store.get("conversation", {})
        messages = conversation.get("messages", [])
        generated_reply = str(scoped_canvas.get("generated_reply", "")).strip()

        self_profile_text = format_self_profile_text(self_profile)
        profile_text = format_profile_text(profile)
        conversation_text = format_conversation_text(messages)

        try:
            prompt_value = self.prompt.invoke(
                {
                    "self_profile_text": self_profile_text,
                    "profile_text": profile_text,
                    "conversation_text": conversation_text,
                    "generated_reply": generated_reply or "（返信なし）",
                }
            )

            structured_llm = self.llm.with_structured_output(HintCandidatesSchema)
            result = structured_llm.invoke(prompt_value)
            hint_result = HintCandidatesSchema.model_validate(result)

            self._append_hint_to_file(user_id, hint_result.hint, hint_result.conversation_summary)

            scoped_canvas["hint_candidate"] = hint_result.hint

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="ヒントを生成し agent_logs/hints.yaml に追記しました。",
                tool_result=hint_result.model_dump(),
            )

        except Exception as e:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"ヒントの生成中にエラーが発生しました: {str(e)}",
                tool_result={},
            )

    def _append_hint_to_file(self, user_id: str, hint: str, conversation_summary: str) -> None:
        """agent_logs/hints.yaml に新しいヒントエントリを追記する。"""
        _HINTS_FILE.parent.mkdir(parents=True, exist_ok=True)

        entries: list = []
        if _HINTS_FILE.exists():
            with _HINTS_FILE.open("r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, list):
                    entries = loaded

        now = datetime.now(tz=_JST)
        date_str = f"{now.year}/{now.month}/{now.day}"

        entries.append({
            "date": date_str,
            "user_id": user_id,
            "hint": hint,
            "conversation_summary": conversation_summary,
        })

        with _HINTS_FILE.open("w", encoding="utf-8") as f:
            yaml.dump(
                entries,
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"
