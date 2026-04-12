import uuid
from typing import Any, Optional

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
    reply_candidates: list[dict[str, Any]] = Field(default_factory=list)
    selected_reply_candidate_id: str = ""


# @lru_cache(maxsize=1)
def get_graph():
    print("get_graph() called")
    return build_graph()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/reply", response_model=ReplyResponse)
def generate_reply(request: ReplyRequest):
    print(f"{request.id}への返信を生成します")

    # リクエスト毎にユニークなexecution_idを生成し、実行用のバケットを作成
    execution_id = str(uuid.uuid4())
    create_execution_bucket(execution_id, user_id=request.id)

    # グラフの生成
    graph = get_graph()

    try:
        # グラフを実行して返信を生成
        graph.invoke(
            {
                "user_id": request.id,
                "execution_id": execution_id,
            },
            config={"recursion_limit": 100},
        )

        # 作成した返信を取得して返却する
        canvas = get_shared_canvas(execution_id)
        reply_candidates = canvas.get("reply_candidates", [])
        return ReplyResponse(
            generated_reply=str(canvas.get("generated_reply", "")),
            reply_reasoning=str(canvas.get("reply_reasoning", "")),
            reply_candidates=(
                reply_candidates if isinstance(reply_candidates, list) else []
            ),
            selected_reply_candidate_id=str(canvas.get("selected_reply_candidate_id", "")),
        )
    finally:
        # バケットの削除
        destroy_execution_bucket(execution_id)