from typing import Any, Literal, TypedDict

# ============================================
# ReactState: ReActの作業状態
# ============================================
class ReactState(TypedDict, total=False):
    """
    LangGraphでノード間を流れる状態。

    役割:
    - 思考（Thought）
    - タスク洗い出し（Task Discovery）
    - 意思決定（Decision）
    - 行動結果（Action）

    ※ 成果物（返信など）は持たない
    """

    # ===== Thought =====
    current_thought: str

    # ===== Task Discovery =====
    required_tasks: list[str]

    # ===== Decision =====
    decided_action: str
    action_reasoning: str

    # ===== Action =====
    selected_tool: str
    tool_result: dict[str, Any]

    # ===== Control =====
    is_finished: bool

    # ===== Trace =====
    trace_id: str


# ============================================
# CanvasData: 成果物
# ============================================
class CanvasData(TypedDict, total=False):
    """
    最終的にユーザーに見せる成果物。
    1ループの最後にのみ更新される。

    ReactStateと重複させない（重要）。
    """

    generated_reply: str
    reply_reasoning: str