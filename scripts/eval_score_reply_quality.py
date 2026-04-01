# Run: uv run python scripts/eval_score_reply_quality.py --cases eval/score_reply_quality_cases.yaml --data-dir data/test_user --output-dir eval/results
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

ScoreReplyQualityTool = None
DEFAULT_SELF_PROFILE = None
shared_store = None
shared_canvas = None


def ensure_runtime_imports() -> None:
    # 実行時依存は遅延インポートし、import 時の副作用を抑える。
    global ScoreReplyQualityTool
    global DEFAULT_SELF_PROFILE
    global shared_store
    global shared_canvas

    if ScoreReplyQualityTool is not None:
        return

    from app.agent.core.tools.score_reply_quality.tool import (
        ScoreReplyQualityTool as _Tool,
    )
    from app.agent.core.utils.shared_store import (
        DEFAULT_SELF_PROFILE as _DefaultSelfProfile,
    )
    from app.agent.core.utils.shared_store import shared_canvas as _SharedCanvas
    from app.agent.core.utils.shared_store import shared_store as _SharedStore

    ScoreReplyQualityTool = _Tool
    DEFAULT_SELF_PROFILE = _DefaultSelfProfile
    shared_store = _SharedStore
    shared_canvas = _SharedCanvas


@dataclass
class CheckConfig:
    min_quality_score: int | None = None
    max_quality_score: int | None = None
    expect_should_regenerate: bool | None = None
    required_any_reasons: list[str] | None = None
    required_all_reasons: list[str] | None = None
    forbidden_reasons: list[str] | None = None


@dataclass
class EvalCase:
    case_id: str
    user_id: str
    generated_reply: str
    checks: CheckConfig


def parse_args() -> argparse.Namespace:
    # デフォルトはワークスペース相対パスにし、手元実行を簡単にする。
    parser = argparse.ArgumentParser(
        description="Run standalone evaluation for score_reply_quality tool.",
    )
    parser.add_argument(
        "--cases",
        default="eval/score_reply_quality_cases.yaml",
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
    # YAML読み込みを共通化し、ルート型の不正を早期検知する。
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be mapping: {path}")
    return data


def as_str_list(value: Any) -> list[str]:
    # YAML配列を文字列配列へ正規化する。
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Expected list")
    return [str(v) for v in value]


def load_cases(path: Path) -> list[EvalCase]:
    # ケース定義を厳格に検証し、静かな評価ドリフトを防ぐ。
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
            min_quality_score=int(checks_raw["min_quality_score"])
            if checks_raw.get("min_quality_score") is not None
            else None,
            max_quality_score=int(checks_raw["max_quality_score"])
            if checks_raw.get("max_quality_score") is not None
            else None,
            expect_should_regenerate=bool(checks_raw["expect_should_regenerate"])
            if checks_raw.get("expect_should_regenerate") is not None
            else None,
            required_any_reasons=as_str_list(checks_raw.get("required_any_reasons", [])),
            required_all_reasons=as_str_list(checks_raw.get("required_all_reasons", [])),
            forbidden_reasons=as_str_list(checks_raw.get("forbidden_reasons", [])),
        )

        cases.append(
            EvalCase(
                case_id=str(item.get("case_id", "")),
                user_id=str(item.get("user_id", "")),
                generated_reply=str(item.get("generated_reply", "")),
                checks=checks,
            )
        )

    for case in cases:
        if not case.case_id or not case.user_id or not case.generated_reply.strip():
            raise ValueError("case_id, user_id, generated_reply are required in every case")

    return cases


def reset_shared_state() -> None:
    # ケース間で状態が混ざらないよう、shared_store/canvas を毎回初期化する。
    ensure_runtime_imports()
    shared_store.clear()
    shared_canvas.clear()
    shared_store["self_profile"] = deepcopy(DEFAULT_SELF_PROFILE)


def evaluate_result(data: dict[str, Any], checks: CheckConfig) -> dict[str, Any]:
    # ルールベース判定で、LLM出力の妥当性を最低限担保する。
    quality_score_raw = data.get("quality_score")
    should_regenerate_raw = data.get("should_regenerate")
    reasons_raw = data.get("reasons", [])

    score_valid = isinstance(quality_score_raw, int) and 0 <= quality_score_raw <= 100
    should_valid = isinstance(should_regenerate_raw, bool)

    quality_score = int(quality_score_raw) if score_valid else -1
    should_regenerate = bool(should_regenerate_raw) if should_valid else False

    reasons = [str(r) for r in reasons_raw] if isinstance(reasons_raw, list) else []
    reasons_text = "\n".join(reasons)

    min_score_ok = True
    if checks.min_quality_score is not None and score_valid:
        min_score_ok = quality_score >= checks.min_quality_score

    max_score_ok = True
    if checks.max_quality_score is not None and score_valid:
        max_score_ok = quality_score <= checks.max_quality_score

    should_expected_ok = True
    if checks.expect_should_regenerate is not None and should_valid:
        should_expected_ok = should_regenerate == checks.expect_should_regenerate

    required_any = checks.required_any_reasons or []
    required_all = checks.required_all_reasons or []
    forbidden = checks.forbidden_reasons or []

    any_hits = [word for word in required_any if word in reasons_text]
    any_ok = True if not required_any else len(any_hits) > 0

    all_hits = [word for word in required_all if word in reasons_text]
    all_ok = len(all_hits) == len(required_all)

    forbidden_hits = [word for word in forbidden if word in reasons_text]
    forbidden_ok = len(forbidden_hits) == 0

    check_items = [
        score_valid,
        should_valid,
        min_score_ok,
        max_score_ok,
        should_expected_ok,
        any_ok,
        all_ok,
        forbidden_ok,
    ]
    checks_total = len(check_items)
    checks_passed = sum(int(v) for v in check_items)
    score = round((checks_passed / checks_total) * 100, 2)

    return {
        "score": score,
        "checks_total": checks_total,
        "checks_passed": checks_passed,
        "quality_score_valid": score_valid,
        "should_regenerate_valid": should_valid,
        "min_score_ok": min_score_ok,
        "max_score_ok": max_score_ok,
        "should_expected_ok": should_expected_ok,
        "required_any_reasons_ok": any_ok,
        "required_any_reasons_hits": any_hits,
        "required_all_reasons_ok": all_ok,
        "required_all_reasons_hits": all_hits,
        "forbidden_reasons_ok": forbidden_ok,
        "forbidden_reasons_hits": forbidden_hits,
    }


def run_case(case: EvalCase, data_dir: Path) -> dict[str, Any]:
    # 1ケースごとに profile/conversation と評価対象返信を投入してツールを直接実行する。
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

    reset_shared_state()
    shared_store["user_id"] = case.user_id
    shared_store["profile"] = profile
    shared_store["conversation"] = {
        "messages": messages,
        "updated_at": str(conversation.get("updated_at", "")),
    }
    shared_canvas["generated_reply"] = case.generated_reply

    result = ScoreReplyQualityTool().execute()
    row: dict[str, Any] = {
        "case_id": case.case_id,
        "user_id": case.user_id,
        "generated_reply": case.generated_reply,
        "tool_success": result.success,
        "tool_summary": result.summary,
        "status": "ok" if result.success else "error",
    }

    if not result.success:
        row["error"] = result.summary
        return row

    payload = result.data
    eval_result = evaluate_result(payload, case.checks)

    row.update(
        {
            "quality_score": payload.get("quality_score"),
            "should_regenerate": payload.get("should_regenerate"),
            "reasons": payload.get("reasons", []),
            "improvement_suggestions": payload.get("improvement_suggestions", []),
            "deduction_breakdown": payload.get("deduction_breakdown", []),
            "score": eval_result["score"],
            "checks_passed": eval_result["checks_passed"],
            "checks_total": eval_result["checks_total"],
            "quality_score_valid": eval_result["quality_score_valid"],
            "should_regenerate_valid": eval_result["should_regenerate_valid"],
            "min_score_ok": eval_result["min_score_ok"],
            "max_score_ok": eval_result["max_score_ok"],
            "should_expected_ok": eval_result["should_expected_ok"],
            "required_any_reasons_ok": eval_result["required_any_reasons_ok"],
            "required_any_reasons_hits": eval_result["required_any_reasons_hits"],
            "required_all_reasons_ok": eval_result["required_all_reasons_ok"],
            "required_all_reasons_hits": eval_result["required_all_reasons_hits"],
            "forbidden_reasons_ok": eval_result["forbidden_reasons_ok"],
            "forbidden_reasons_hits": eval_result["forbidden_reasons_hits"],
        }
    )
    return row


def write_json(path: Path, data: Any) -> None:
    # UTF-8整形JSONで保存し、目視確認と差分確認をしやすくする。
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    # CSVは表計算ソフトでの確認に向いている。
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return

    preferred_order = [
        "case_id",
        "user_id",
        "status",
        "tool_success",
        "tool_summary",
        "score",
        "checks_passed",
        "checks_total",
        "quality_score",
        "should_regenerate",
        "quality_score_valid",
        "should_regenerate_valid",
        "min_score_ok",
        "max_score_ok",
        "should_expected_ok",
        "required_any_reasons_ok",
        "required_all_reasons_ok",
        "forbidden_reasons_ok",
        "generated_reply",
        "reasons",
        "improvement_suggestions",
        "deduction_breakdown",
        "required_any_reasons_hits",
        "required_all_reasons_hits",
        "forbidden_reasons_hits",
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
    # 実行結果の全体像を要約し、成否確認をすばやく行えるようにする。
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
    # タイムスタンプ付き出力先を作成し、結果を保存する。
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

    print("=== score_reply_quality evaluation ===")
    print(f"cases={summary['total_cases']} ok={summary['ok_cases']} error={summary['error_cases']}")
    print(f"average_score={summary['average_score']}")
    print(f"output={run_dir}")


if __name__ == "__main__":
    main()
