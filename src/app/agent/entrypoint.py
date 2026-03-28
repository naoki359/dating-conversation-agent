from typing import List, Optional
from functools import lru_cache

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.agent.core.graph.build_graph import build_graph
from app.agent.repositories.yaml_user_repository import load_agent_state
from app.agent.core.utils.shared_store import shared_store

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
    # shared_storeにuser_idを設定
    shared_store["user_id"] = request.id

    graph = get_graph()

    # 仮：固定IDで読み込み
    # state = load_agent_state(request.id)

    # print("Loaded AgentState:", state)

    result = graph.invoke({"user_id": request.id}, config={"recursion_limit": 100})

    # テスト用：最終的なstateの情報を出力
    print("Final State:", result["history"])

    print("")
    # shared_storeの内容を確認
    print("Shared Store:", shared_store)

    return ReplyResponse(
        generated_reply="",
        reply_reasoning=result.get("action_reasoning"),
    )