from pydantic import BaseModel, Field


class ConversationTopicStrategySchema(BaseModel):
    """話題継続・切り替え判定ツールの出力スキーマ。"""

    current_topic: str = Field(
        default="",
        description="現在議論されている主題（例: 旅行, 温泉旅行, 北海道旅行など）。",
    )

    current_topic_category: str = Field(
        default="",
        description="現在の主題のカテゴリ（例: 旅行, 趣味, 食事, 日常, 仕事, 人柄・価値観など）。",
    )

    same_topic_turns: int = Field(
        default=0,
        description="同一主題が何往復続いているか。1往復 = こちらの発言 + 相手の発言 の1セット。",
    )

    last_question_by_self: str = Field(
        default="",
        description="直近にこちら（self）が行った質問内容。質問がなければ空文字。",
    )

    is_monotonous: bool = Field(
        default=False,
        description="次も同じ話題を継続すると単調になりそうか。",
    )

    should_continue_topic: bool = Field(
        default=True,
        description="現在の話題を継続するべきか（False の場合は切り替え）。",
    )

    continuation_policy: str = Field(
        default="",
        description="話題を継続する場合の深掘り方針。should_continue_topic=True のときのみ有効。",
    )

    switch_policy: str = Field(
        default="",
        description=(
            "話題を切り替える場合の返信生成ノードへの指示。"
            "should_continue_topic=False のときのみ有効。"
        ),
    )

    next_topic_suggestion: str = Field(
        default="",
        description="切り替え先として推奨する話題または方向性。継続時は空文字。",
    )

    reasoning: str = Field(
        default="",
        description="判定の根拠（1〜2文）。",
    )
