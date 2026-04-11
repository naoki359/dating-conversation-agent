 # Run: uv run python scripts/run_invite_date_reply.py --pretty
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

InviteDateReplyTool = None
create_execution_bucket = None
destroy_execution_bucket = None
get_shared_canvas = None
get_shared_store = None


def ensure_runtime_imports() -> None:
    global InviteDateReplyTool
    global create_execution_bucket
    global destroy_execution_bucket
    global get_shared_canvas
    global get_shared_store

    if InviteDateReplyTool is not None:
        return

    from app.agent.core.tools.invite_date_reply.tool import InviteDateReplyTool as _InviteDateReplyTool
    from app.agent.core.utils.shared_store import (
        create_execution_bucket as _create_execution_bucket,
    )
    from app.agent.core.utils.shared_store import (
        destroy_execution_bucket as _destroy_execution_bucket,
    )
    from app.agent.core.utils.shared_store import get_shared_canvas as _get_shared_canvas
    from app.agent.core.utils.shared_store import get_shared_store as _get_shared_store

    InviteDateReplyTool = _InviteDateReplyTool
    create_execution_bucket = _create_execution_bucket
    destroy_execution_bucket = _destroy_execution_bucket
    get_shared_canvas = _get_shared_canvas
    get_shared_store = _get_shared_store


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run InviteDateReplyTool with sample data or a user YAML file.",
    )
    parser.add_argument(
        "--user-yaml",
        help="Path to a YAML file containing profile and conversation.",
    )
    parser.add_argument(
        "--meeting-area",
        default="新宿",
        help="Meeting area for conversation_facts when not supplied elsewhere.",
    )
    parser.add_argument(
        "--available-time",
        default="土、日、祝日の19:00以降",
        help="Available time for conversation_facts when not supplied elsewhere.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    return parser.parse_args()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def build_sample_source() -> dict[str, Any]:
    # InviteDateReplyTool が参照する事前情報のうち、
    # `profile` と `conversation` はここでテスト用サンプルを定義する。
    # 実データを使う場合は --user-yaml で同等の構造を持つ YAML を渡す。
    # 型の基準は src/app/agent/core/utils/shared_store.py の
    # Profile / Conversation / Message を参照。
    return {
        "profile": {
            "name": "美咲",
            "age": 29,
            "raw_profile_text": "映画とご飯が好きです。お酒も好きで、居酒屋開拓もよくします。",
            "profile_summary": "映画と食事が好きで、お酒も楽しめるタイプ。新宿に出やすい。",
            "meeting_timing_preference": "会う前に通話したい",
            # "meeting_timing_preference": "気が合えば会いたい",
        },
        "conversation": {
            "messages": [
                {
                    "id": "1",
                    "timestamp": "2026-04-08T20:10:00+09:00",
                    "sender": "self",
                    "message": "映画お好きなんですね。最近観てよかった作品ありますか？",
                },
                {
                    "id": "2",
                    "timestamp": "2026-04-08T20:18:00+09:00",
                    "sender": "other",
                    "message": "最近だとミステリー系をよく観てます！新宿なら行きやすいですし、土日の夜はわりと空いてます。",
                },
                {
                    "id": "3",
                    "timestamp": "2026-04-09T12:15:00+09:00",
                    "sender": "self",
                    "message": "ミステリーいいですね。伏線回収がうまい作品だとつい見入っちゃいます。",
                },
                {
                    "id": "4",
                    "timestamp": "2026-04-09T12:27:00+09:00",
                    "sender": "other",
                    "message": "わかります！考察できる系が好きで、観たあとに感想を話したくなるタイプです。",
                },
                {
                    "id": "5",
                    "timestamp": "2026-04-09T21:03:00+09:00",
                    "sender": "self",
                    "message": "感想を話したくなるのいいですね。ごはん食べながら映画の話できたら楽しそうです。",
                },
                {
                    "id": "6",
                    "timestamp": "2026-04-09T21:11:00+09:00",
                    "sender": "other",
                    "message": "たしかにそれ楽しそうです！ごはんも好きなので、そういう時間かなり好きです。",
                },
                {
                    "id": "7",
                    "timestamp": "2026-04-10T19:40:00+09:00",
                    "sender": "self",
                    "message": "食の好み合いそうで嬉しいです。美咲さんは和食とか洋食だとどっちが好きですか？",
                },
                {
                    "id": "8",
                    "timestamp": "2026-04-10T19:52:00+09:00",
                    "sender": "other",
                    "message": "どっちも好きですけど、わりと居酒屋っぽいお店も好きです。お酒も少し飲みます。",
                }
            ],
            "updated_at": "2026-04-11T20:09:00+09:00",
        },
    }


def resolve_source(args: argparse.Namespace) -> dict[str, Any]:
    if not args.user_yaml:
        return build_sample_source()

    # --user-yaml で渡すファイルにも、build_sample_source と同じく
    # `profile` と `conversation` のトップレベルキーが必要。
    source_path = Path(args.user_yaml)
    if not source_path.is_absolute():
        source_path = PROJECT_ROOT / source_path
    return load_yaml(source_path)


def set_runtime_inputs(execution_id: str, source: dict[str, Any], args: argparse.Namespace) -> None:
    ensure_runtime_imports()
    scoped_store = get_shared_store(execution_id)
    scoped_canvas = get_shared_canvas(execution_id)

    # ツール本体は src/app/agent/core/tools/invite_date_reply/tool.py で
    # shared_store["profile"], shared_store["conversation"],
    # shared_canvas["conversation_facts"] を読み取る。
    scoped_store["profile"] = source.get("profile", {})
    scoped_store["conversation"] = source.get("conversation", {})

    # `conversation_facts` は通常フローでは抽出ツールが作るが、
    # このテストスクリプトでは CLI 引数から最低限の値を直接注入する。
    # 必要なのは meeting_area と available_time の2項目。
    scoped_canvas["conversation_facts"] = {
        "meeting_area": {
            "value": args.meeting_area,
            "confidence": "high",
            "source_quote": args.meeting_area,
        },
        "available_time": {
            "value": args.available_time,
            "confidence": "high",
            "source_quote": args.available_time,
        },
    }


def print_result(result: Any, pretty: bool) -> None:
    payload = result.model_dump() if hasattr(result, "model_dump") else result
    if pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(json.dumps(payload, ensure_ascii=False))


def main() -> int:
    ensure_runtime_imports()
    args = parse_args()
    source = resolve_source(args)
    execution_id = f"invite-date-reply-test-{uuid4()}"

    create_execution_bucket(execution_id)
    try:
        set_runtime_inputs(execution_id, source, args)
        result = InviteDateReplyTool().execute(execution_id)
        print_result(result, args.pretty)
        return 0 if getattr(result, "success", False) else 1
    finally:
        destroy_execution_bucket(execution_id)


if __name__ == "__main__":
    raise SystemExit(main())