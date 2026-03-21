from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Dating Conversation Agent")


class ReplyRequest(BaseModel):
    partner_profile: str = Field(..., description="相手プロフィール")
    conversation_history: List[str] = Field(..., description="会話履歴")


class ReplyResponse(BaseModel):
    generated_reply: str
    reply_reasoning: Optional[str] = None


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/reply", response_model=ReplyResponse)
def generate_reply(request: ReplyRequest):
    # ダミー処理（リクエスト確認用）
    return ReplyResponse(
        generated_reply="テスト返信です！ちゃんとリクエスト受け取れてます 👍",
        reply_reasoning=f"履歴件数: {len(request.conversation_history)}件",
    )