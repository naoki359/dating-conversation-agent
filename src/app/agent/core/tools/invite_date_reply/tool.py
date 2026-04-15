import json
from pathlib import Path
from textwrap import dedent

from app.agent.core.schemas.base_tool_schema import BaseToolResult
from app.agent.core.services.llm_client import get_chat_model_gpt5_4
from app.agent.core.tools.invite_date_reply.schema import InviteDateReplyResultSchema
from app.agent.core.utils.formatCommon import (
    format_conversation_text,
    format_profile_text,
)
from app.agent.core.utils.prompt_loader import load_prompt_from_yaml
from app.agent.core.utils.shared_store import get_shared_canvas, get_shared_store


class InviteDateReplyTool:
    """重要情報と店舗データをもとにデート打診文を生成するツール。"""

    name = "invite_date_reply"
    description = "重要情報を参照し、デート場所と日時を含む返信を生成する"

    def __init__(self) -> None:
        self.llm = get_chat_model_gpt5_4()
        self.prompt = load_prompt_from_yaml(self._get_prompt_path())
        self.shops = self._load_shops()

    def execute(self, execution_id: str | None = None) -> BaseToolResult:
        scoped_store = get_shared_store(execution_id)
        scoped_canvas = get_shared_canvas(execution_id)

        profile = scoped_store.get("profile", {})
        conversation = scoped_store.get("conversation", {})
        messages = conversation.get("messages", [])
        conversation_facts = scoped_canvas.get("conversation_facts", {})

        latest_message = self._find_latest_other_message(messages)
        meeting_area_value = self._get_fact_value(conversation_facts, "meeting_area")
        available_time_value = self._get_fact_value(conversation_facts, "available_time")

        selected_area = self._normalize_area(meeting_area_value, messages)
        selected_time_slot = self._normalize_time_slot(available_time_value)
        selected_shop_type = self._select_shop_type(profile, selected_time_slot)
        selected_shop = self._select_shop(selected_area, selected_time_slot, selected_shop_type)
        proposed_datetime = self._build_datetime_suggestion(available_time_value, selected_time_slot)
        call_alternative = self._build_call_alternative(profile, messages)

        profile_text = self._build_profile_text(profile)
        conversation_text = self._build_conversation_text(messages)
        latest_message_text = latest_message.get("message", "") if latest_message else ""
        conversation_facts_text = self._build_conversation_facts_text(conversation_facts)
        shops_catalog_text = self._build_shops_catalog_text()
        plan_text = self._build_plan_text(
            selected_shop=selected_shop,
            selected_area=selected_area,
            selected_time_slot=selected_time_slot,
            proposed_datetime=proposed_datetime,
        )
        call_alternative_text = call_alternative or "不要"

        try:
            prompt_value = self.prompt.invoke(
                {
                    "profile_text": profile_text,
                    "conversation_text": conversation_text,
                    "latest_message": latest_message_text or "最新メッセージはありません。",
                    "conversation_facts_text": conversation_facts_text,
                    "shops_catalog_text": shops_catalog_text,
                    "plan_text": plan_text,
                    "call_alternative_text": call_alternative_text,
                }
            )

            structured_llm = self.llm.with_structured_output(InviteDateReplyResultSchema)
            result = structured_llm.invoke(prompt_value)
            reply_data = InviteDateReplyResultSchema.model_validate(result)
            selected_shop_url = selected_shop.get("url", "")
            reply_data.reply_text = self._compose_reply_text(
                reply_text=reply_data.reply_text,
                shop_url=selected_shop_url,
                alternative_plan=reply_data.alternative_plan,
            )

            scoped_canvas["generated_reply"] = reply_data.reply_text
            scoped_canvas["reply_reasoning"] = reply_data.reasoning

            return BaseToolResult(
                tool_name=self.name,
                success=True,
                summary="デート打診の返信を生成しました。",
                tool_result=reply_data.model_dump(),
            )
        except Exception as e:
            return BaseToolResult(
                tool_name=self.name,
                success=False,
                summary=f"デート打診返信の生成中にエラーが発生しました: {str(e)}",
                tool_result={},
            )

    def _get_prompt_path(self) -> Path:
        return Path(__file__).resolve().parent / "prompt.yaml"

    def _get_shops_path(self) -> Path:
        return Path(__file__).resolve().parent / "shops.json"

    def _load_shops(self) -> list[dict[str, str]]:
        with self._get_shops_path().open("r", encoding="utf-8") as file:
            return json.load(file)

    def _find_latest_other_message(self, messages: list[dict]) -> dict | None:
        for message in reversed(messages):
            if message.get("sender") == "other":
                return message
        return None

    def _get_fact_value(self, conversation_facts: dict, key: str) -> str:
        fact = conversation_facts.get(key) or {}
        return str(fact.get("value") or "")

    def _normalize_area(self, meeting_area_value: str, messages: list[dict]) -> str:
        candidate_texts = [meeting_area_value]
        candidate_texts.extend(str(message.get("message", "")) for message in messages[-4:])

        for text in candidate_texts:
            for area in ("新宿", "池袋", "新橋", "上野"):
                if area in text:
                    return area
        return "新宿"

    def _normalize_time_slot(self, available_time_value: str) -> str:
        value = available_time_value or ""

        if any(keyword in value for keyword in ("夜", "仕事終わり", "ディナー", "18:", "19:", "20:", "21:")):
            return "夜"
        if any(keyword in value for keyword in ("夕方", "午後", "15:", "16:", "17:")):
            return "夕方"
        if any(keyword in value for keyword in ("昼", "ランチ", "12:", "13:", "14:")):
            return "昼"
        return "夕方"

    def _select_shop_type(self, profile: dict, time_slot: str) -> str:
        if time_slot == "夜" and self._profile_prefers_izakaya(profile):
            return "居酒屋"
        return "カフェ"

    def _profile_prefers_izakaya(self, profile: dict) -> bool:
        profile_text = "\n".join(
            [
                str(profile.get("profile_summary", "")),
                str(profile.get("raw_profile_text", "")),
            ]
        )

        izakaya_keywords = (
            "お酒",
            "飲み",
            "飲酒",
            "居酒屋",
            "ビール",
            "ハイボール",
            "ワイン",
            "日本酒",
            "焼酎",
            "食べるの好き",
            "食事が好き",
            "ご飯が好き",
            "食べ歩き",
            "グルメ",
        )
        return any(keyword in profile_text for keyword in izakaya_keywords)

    def _select_shop(
        self,
        area: str,
        time_slot: str,
        shop_type: str,
    ) -> dict[str, str]:
        for shop in self.shops:
            if (
                shop.get("area") == area
                and shop.get("time_slot") == time_slot
                and shop.get("type") == shop_type
            ):
                return shop

        for shop in self.shops:
            if shop.get("area") == area and shop.get("time_slot") == time_slot:
                return shop

        for shop in self.shops:
            if shop.get("area") == area:
                return shop

        return self.shops[0]

    def _build_datetime_suggestion(self, available_time_value: str, time_slot: str) -> str:
        value = available_time_value or ""

        if "金" in value and time_slot == "夜":
            return "今度の金曜の夜"
        if any(keyword in value for keyword in ("土", "日", "週末", "祝日")):
            if time_slot == "昼":
                return "今度の土日どちらかの昼"
            if time_slot == "夜":
                return "今度の土日どちらかの夜"
            return "今度の土日どちらかの15時ごろ"
        if "平日" in value and time_slot == "夜":
            return "来週どこかの平日夜"
        if time_slot == "昼":
            return "今度の土日どちらかの昼"
        if time_slot == "夜":
            return "来週どこかの夜"
        return "今度の土日どちらかの15時ごろ"

    def _build_call_alternative(self, profile: dict, messages: list[dict]) -> str | None:
        preference = str(profile.get("meeting_timing_preference") or "")
        recent_text = "\n".join(str(message.get("message", "")) for message in messages[-6:])

        if preference == "会う前に通話したい" or "通話" in recent_text or "電話" in recent_text:
            return "もしまだ会う前に通話のほうが安心なら、先に15〜30分くらいお電話でも大丈夫です。"
        return None

    def _build_profile_text(self, profile: dict) -> str:
        return format_profile_text(
            profile,
            use_default_meeting_timing_preference=False,
        )

    def _build_conversation_text(self, messages: list[dict]) -> str:
        return format_conversation_text(messages)

    def _build_conversation_facts_text(self, conversation_facts: dict) -> str:
        meeting_area = conversation_facts.get("meeting_area") or {}
        available_time = conversation_facts.get("available_time") or {}

        return dedent(
            f"""
            meeting_area: {meeting_area.get('value', '未取得')}
            meeting_area_source: {meeting_area.get('source_quote', 'なし')}

            available_time: {available_time.get('value', '未取得')}
            available_time_source: {available_time.get('source_quote', 'なし')}
            """
        ).strip()

    def _build_shops_catalog_text(self) -> str:
        lines: list[str] = []
        for shop in self.shops:
            lines.append(
                " / ".join(
                    [
                        f"店名: {shop.get('name', '')}",
                        f"エリア: {shop.get('area', '')}",
                        f"時間帯: {shop.get('time_slot', '')}",
                        f"種類: {shop.get('type', '')}",
                        f"URL: {shop.get('url', '')}",
                    ]
                )
            )
        return "\n".join(lines)

    def _build_plan_text(
        self,
        selected_shop: dict[str, str],
        selected_area: str,
        selected_time_slot: str,
        proposed_datetime: str,
    ) -> str:
        shop_name = selected_shop.get("name", "候補のお店")
        shop_type = selected_shop.get("type", "カフェ")
        shop_url = selected_shop.get("url", "")

        plan_lines = [
            f"エリア: {selected_area}",
            f"時間帯: {selected_time_slot}",
            f"日時案: {proposed_datetime}",
            f"店名: {shop_name}",
            f"種類: {shop_type}",
            f"URL: {shop_url}",
        ]
        return "\n".join(plan_lines)

    def _compose_reply_text(
        self,
        reply_text: str,
        shop_url: str,
        alternative_plan: str | None,
    ) -> str:
        body = reply_text.strip()

        if alternative_plan:
            body = body.replace(alternative_plan, "").strip()

        parts = [body] if body else []

        if shop_url and shop_url not in body:
            parts.append(f"このお店なんてどうでしょう？ {shop_url}")

        if alternative_plan:
            parts.append(alternative_plan.strip())

        return "\n".join(part for part in parts if part)
