from pydantic import BaseModel, Field


class GenerateFirstMessageResultSchema(BaseModel):
    """初回メッセージ生成ツールの出力スキーマ。"""

    reply_text: str = Field(
        description="実際に送信する初回メッセージ。",
    )

    selected_topic: str = Field(
        description="プロフィールから今回の初回メッセージで取り上げた話題。",
    )

    tone: str = Field(
        description="メッセージ全体のトーンや距離感の説明。",
    )

    reasoning: str = Field(
        description="その話題選定と文面が適切だと判断した理由。",
    )

    question_intent: str = Field(
        description="最後の問いかけで何を引き出したいかの説明。",
    )