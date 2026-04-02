import uuid
from typing import Optional
from functools import lru_cache

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.agent.core.graph.build_graph import build_graph
from app.agent.core.utils.shared_store import (
    create_execution_bucket,
    destroy_execution_bucket,
    get_shared_canvas,
)

app = FastAPI(title="Dating Conversation Agent")


class ReplyRequest(BaseModel):
    id: str = Field(..., description="会話のID")


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
    print(f"{request.id}への返信を生成します")
    execution_id = str(uuid.uuid4())
    create_execution_bucket(execution_id, user_id=request.id)

    graph = get_graph()

    try:
        graph.invoke(
            {
                "user_id": request.id,
                "execution_id": execution_id,
            },
            config={"recursion_limit": 100},
        )

        canvas = get_shared_canvas(execution_id)
        return ReplyResponse(
            generated_reply=str(canvas.get("generated_reply", "")),
            reply_reasoning=str(canvas.get("reply_reasoning", "")),
        )
    finally:
        destroy_execution_bucket(execution_id)