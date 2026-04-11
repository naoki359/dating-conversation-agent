from typing import Optional

from pydantic import BaseModel, Field


class InviteDateReplyResultSchema(BaseModel):
    """デート打診返信ツールの出力スキーマ。"""

    reply_text: str = Field(
        description="実際に送信するデート打診メッセージ。",
    )

    proposed_area: str = Field(
        description="提案に使用したエリア。",
    )

    proposed_time_slot: str = Field(
        description="提案に使用した時間帯。",
    )

    proposed_datetime: str = Field(
        description="返信文で提示する日時の表現。",
    )

    proposed_shop_name: str = Field(
        description="提案に使用した店舗名。",
    )

    proposed_shop_type: str = Field(
        description="提案に使用した店舗種別。",
    )

    alternative_plan: Optional[str] = Field(
        default=None,
        description="通話希望時に併記する代替案。不要なら null。",
    )

    reasoning: str = Field(
        description="この提案が適切だと判断した理由。",
    )
