# Run: uv run python scripts/eval_generate_reply.py --cases eval/generate_reply_cases.yaml --data-dir data/test_user --output-dir eval/results
from __future__ import annotations

import argparse
import csv
import json
import sys
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

GenerateReplyTool = None
DEFAULT_SELF_PROFILE = None
shared_store = None


def ensure_runtime_imports() -> None:
    # 実行時依存は遅延インポートする。
    # これにより、import 時に重い初期化が走るのを防ぐ。
    global GenerateReplyTool
    global DEFAULT_SELF_PROFILE
    global shared_store

    if GenerateReplyTool is not None:
        return

    from app.agent.core.tools.generate_reply.tool import GenerateReplyTool as _Tool
    from app.agent.core.utils.shared_store import (
        DEFAULT_SELF_PROFILE as _DefaultSelfProfile,
    )
    from app.agent.core.utils.shared_store import shared_store as _SharedStore

    GenerateReplyTool = _Tool
    DEFAULT_SELF_PROFILE = _DefaultSelfProfile
    shared_store = _SharedStore


@dataclass
class CheckConfig:
    min_reply_length: int = 1
    required_any_keywords: list[str] | None = None
    required_all_keywords: list[str] | None = None
    forbidden_keywords: list[str] | None = None


@dataclass
class EvalCase:
    case_id: str
    user_id: str
    checks: CheckConfig


def parse_args() -> argparse.Namespace:
    # コマンドを簡潔に保つため、デフォルトはワークスペース相対パスにする。
    parser = argparse.ArgumentParser(
        description="Run standalone evaluation for generate_reply tool.",
    )
    parser.add_argument(
        "--cases",
        default="eval/generate_reply_cases.yaml",
        help="Path to evaluation case YAML.",
    )
    parser.add_argument(
        "--data-dir",
        default="data/test_user",
        help="Directory that contains user YAML files.",
    )
    parser.add_argument(
        "--output-dir",
        default="eval/results",
        help="Directory to write evaluation outputs.",
    )
    return parser.parse_args()


def load_yaml(path: Path) -> dict[str, Any]:
    # YAML読み込みを共通化し、ルート型を検証して早期に不正入力を検知する。
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be mapping: {path}")
    return data


def load_cases(path: Path) -> list[EvalCase]:
    # ケース定義は厳格に検証し、静かな評価ドリフトを防ぐ。
    raw = load_yaml(path)
    raw_cases = raw.get("cases", [])
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("cases must be a non-empty list")

    cases: list[EvalCase] = []
    for item in raw_cases:
        if not isinstance(item, dict):
            raise ValueError("Each case must be mapping")

        checks_raw = item.get("checks", {})
        if not isinstance(checks_raw, dict):
            raise ValueError("checks must be mapping")

        checks = CheckConfig(
            min_reply_length=int(checks_raw.get("min_reply_length", 1)),
            required_any_keywords=as_str_list(checks_raw.get("required_any_keywords", [])),
            required_all_keywords=as_str_list(checks_raw.get("required_all_keywords", [])),
            forbidden_keywords=as_str_list(checks_raw.get("forbidden_keywords", [])),
        )

        cases.append(
            EvalCase(
                case_id=str(item.get("case_id", "")),
                user_id=str(item.get("user_id", "")),
                checks=checks,
            )
        )

    for case in cases:
        if not case.case_id or not case.user_id:
            raise ValueError("case_id and user_id are required in every case")

    return cases


def as_str_list(value: Any) -> list[str]:
    # 任意のYAML配列を文字列配列へ正規化し、キーワード判定を安定させる。
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Expected list")
    return [str(v) for v in value]


def reset_shared_store() -> None:
    # ケースごとに shared_store を初期化し、状態のケース間リークを防ぐ。
    ensure_runtime_imports()
    shared_store.clear()
    shared_store["self_profile"] = deepcopy(DEFAULT_SELF_PROFILE)


def evaluate_keywords(reply_text: str, checks: CheckConfig) -> dict[str, Any]:
    # 表現ゆれに強いルールベース採点。
    #
    # - required_any: いずれか1語以上を含む
    # - required_all: すべての語を含む
    # - forbidden: 禁止語を含まない
    # - min_reply_length: 最低文字数を満たす
    required_any = checks.required_any_keywords or []
    required_all = checks.required_all_keywords or []
    forbidden = checks.forbidden_keywords or []

    any_hit = True
    any_hit_words: list[str] = []
    if required_any:
        any_hit_words = [word for word in required_any if word in reply_text]
        any_hit = len(any_hit_words) > 0

    all_hit_words = [word for word in required_all if word in reply_text]
    all_hit = len(all_hit_words) == len(required_all)

    forbidden_hit_words = [word for word in forbidden if word in reply_text]
    forbidden_ok = len(forbidden_hit_words) == 0

    length_ok = len(reply_text.strip()) >= checks.min_reply_length

    checks_total = 4
    checks_passed = int(length_ok) + int(any_hit) + int(all_hit) + int(forbidden_ok)
    score = round((checks_passed / checks_total) * 100, 2)

    return {
        "score": score,
        "checks_total": checks_total,
        "checks_passed": checks_passed,
        "length_ok": length_ok,
        "required_any_ok": any_hit,
        "required_any_hits": any_hit_words,
        "required_all_ok": all_hit,
        "required_all_hits": all_hit_words,
        "forbidden_ok": forbidden_ok,
        "forbidden_hits": forbidden_hit_words,
    }


def run_case(case: EvalCase, data_dir: Path) -> dict[str, Any]:
    # 1ケースにつき1つのユーザーYAMLを読み込み、GenerateReplyToolを直接実行する。
    # これにより、評価対象をツール単体の振る舞いに限定できる。
    ensure_runtime_imports()
    user_file = data_dir / f"{case.user_id}.yaml"
    if not user_file.exists():
        return {
            "case_id": case.case_id,
            "user_id": case.user_id,
            "status": "error",
            "error": f"User YAML not found: {user_file}",
        }

    source = load_yaml(user_file)
    profile = source.get("profile", {})
    conversation = source.get("conversation", {})

    if not isinstance(profile, dict) or not isinstance(conversation, dict):
        return {
            "case_id": case.case_id,
            "user_id": case.user_id,
            "status": "error",
            "error": "Invalid profile or conversation in user YAML",
        }

    messages = conversation.get("messages", [])
    if not isinstance(messages, list):
        return {
            "case_id": case.case_id,
            "user_id": case.user_id,
            "status": "error",
            "error": "conversation.messages must be list",
        }

    # generate_reply ツールが期待する最小限の shared_store キーを準備する。
    reset_shared_store()
    shared_store["user_id"] = case.user_id
    shared_store["profile"] = profile
    shared_store["conversation"] = {
        "messages": messages,
        "updated_at": str(conversation.get("updated_at", "")),
    }

    result = GenerateReplyTool().execute()
    row: dict[str, Any] = {
        "case_id": case.case_id,
        "user_id": case.user_id,
        "tool_success": result.success,
        "tool_summary": result.summary,
        "status": "ok" if result.success else "error",
    }

    if not result.success:
        row["error"] = result.summary
        return row

    # ツール成功時のみ、返信品質を決定論的なルールで評価する。
    payload = result.data
    reply_text = str(payload.get("reply_text", ""))
    eval_result = evaluate_keywords(reply_text, case.checks)

    row.update(
        {
            "reply_text": reply_text,
            "tone": payload.get("tone", ""),
            "reasoning": payload.get("reasoning", ""),
            "follow_up_suggestion": payload.get("follow_up_suggestion", ""),
            "score": eval_result["score"],
            "checks_passed": eval_result["checks_passed"],
            "checks_total": eval_result["checks_total"],
            "length_ok": eval_result["length_ok"],
            "required_any_ok": eval_result["required_any_ok"],
            "required_any_hits": eval_result["required_any_hits"],
            "required_all_ok": eval_result["required_all_ok"],
            "required_all_hits": eval_result["required_all_hits"],
            "forbidden_ok": eval_result["forbidden_ok"],
            "forbidden_hits": eval_result["forbidden_hits"],
        }
    )
    return row


def write_json(path: Path, data: Any) -> None:
    # UTF-8の整形JSONで保存し、目視確認と差分確認をしやすくする。
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    # CSVは表計算での確認やフィルタ/ソートに向いている。
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return

    # キー順を固定し、差分レビューを容易にする。
    preferred_order = [
        "case_id",
        "user_id",
        "status",
        "tool_success",
        "tool_summary",
        "score",
        "checks_passed",
        "checks_total",
        "length_ok",
        "required_any_ok",
        "required_all_ok",
        "forbidden_ok",
        "reply_text",
        "tone",
        "reasoning",
        "follow_up_suggestion",
        "required_any_hits",
        "required_all_hits",
        "forbidden_hits",
        "error",
    ]

    all_keys = set().union(*(row.keys() for row in rows))
    fieldnames = [key for key in preferred_order if key in all_keys]
    fieldnames.extend(sorted(k for k in all_keys if k not in fieldnames))

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            normalized_row = {
                key: json.dumps(value, ensure_ascii=False)
                if isinstance(value, (list, dict))
                else value
                for key, value in row.items()
            }
            writer.writerow(normalized_row)


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    # 実行全体の健全性を要約し、CI/ローカルの判定を素早く行えるようにする。
    total = len(rows)
    error_count = sum(1 for r in rows if r.get("status") != "ok")
    scored_rows = [r for r in rows if isinstance(r.get("score"), (int, float))]
    avg_score = (
        round(sum(float(r["score"]) for r in scored_rows) / len(scored_rows), 2)
        if scored_rows
        else 0.0
    )

    return {
        "timestamp": datetime.now().isoformat(),
        "total_cases": total,
        "ok_cases": total - error_count,
        "error_cases": error_count,
        "average_score": avg_score,
    }


def main() -> None:
    # タイムスタンプ付き出力先を作成し、過去実行結果を保存する。
    ensure_runtime_imports()
    args = parse_args()

    cases_path = PROJECT_ROOT / args.cases
    data_dir = PROJECT_ROOT / args.data_dir
    output_root = PROJECT_ROOT / args.output_dir
    run_dir = output_root / datetime.now().strftime("%Y%m%d_%H%M%S")

    cases = load_cases(cases_path)
    rows = [run_case(case, data_dir) for case in cases]
    summary = build_summary(rows)

    write_json(run_dir / "summary.json", summary)
    write_json(run_dir / "results.json", rows)
    write_csv(run_dir / "results.csv", rows)

    print("=== generate_reply evaluation ===")
    print(f"cases={summary['total_cases']} ok={summary['ok_cases']} error={summary['error_cases']}")
    print(f"average_score={summary['average_score']}")
    print(f"output={run_dir}")


if __name__ == "__main__":
    main()
