from pydantic import BaseModel, Field


class HintCandidatesSchema(BaseModel):
    """次回のヒント生成ツールの出力スキーマ。"""

    hint: str = Field(
        default="",
        description=(
            "次回の返信生成時に now_hint として設定できるヒント（1件）。"
            "例: 「この旅行の話題を続けたい」「共通点の焼肉について掘り下げる」"
        ),
    )

    conversation_summary: str = Field(
        default="",
        description=(
            "このヒントが生まれた会話の状態を1文で記録する分析メモ。"
            "例: 「相手が旅行好きと判明し、共通点として焼肉の話題も出た段階」"
            "将来的な嗜好性ログの基盤として活用する。"
        ),
    )

