from typing import List, Optional
from functools import lru_cache

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.agent.core.graph.build_graph import build_graph

app = FastAPI(title="Dating Conversation Agent")


class ReplyRequest(BaseModel):
    partner_profile: str = Field(..., description="相手プロフィール")
    conversation_history: List[str] = Field(..., description="会話履歴")


class ReplyResponse(BaseModel):
    generated_reply: str
    reply_reasoning: Optional[str] = None


@lru_cache(maxsize=1)
def get_graph():
    print("get_graph() called")
    return build_graph()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/reply", response_model=ReplyResponse)
def generate_reply(request: ReplyRequest):
    graph = get_graph()

    result = graph.invoke(request)

    return ReplyResponse(
        generated_reply=result["generated_reply"],
        reply_reasoning=result["reply_reasoning"],
    )