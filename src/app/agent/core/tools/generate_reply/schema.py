from typing import Optional

from pydantic import BaseModel, Field


class GenerateReplyResultSchema(BaseModel):
    """返信生成ツールの出力スキーマ。"""

    reply_text: str = Field(
        description="生成された返信テキスト。",
    )

    tone: str = Field(
        description="返信のトーン（例: 親切, ユーモア, 関心を示す等）。",
    )

    reasoning: str = Field(
        description="この返信を生成した理由。",
    )

    follow_up_suggestion: Optional[str] = Field(
        default=None,
        description="次のステップで確認すべき点や改善提案など。",
    )
