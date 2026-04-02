# [FEATURE] fit_score に基づく自己修正ループの実装

## 概要

`CheckReplyProfileFitTool` が算出する `fit_score`（0〜100）と `revised_reply` を、返信生成の自己修正ループに活用する。現在はスコアが計算されるだけで次の行動に影響しておらず、評価が「観測で終わっている」状態になっている。

## 背景

エージェンティックマニュフェストの価値観「合否判定のテストよりも継続的なチューニングを重視する」に基づき、エージェントは自身の出力を評価し、一定水準に達するまで改善を繰り返す仕組みが必要。

現状のフロー：
```
generate_reply → check_reply → (スコアを無視) → END
```

あるべきフロー：
```
generate_reply → check_reply → observe（fit_score・loop_countを判定）
             ↓ 継続
           generate_reply へ戻る
             ↓ 終了
            END
```

また、`revised_reply` は `CheckReplyProfileFitTool` が生成しているにもかかわらず `shared_canvas` に書き込まれておらず、未活用の状態である。

## 要件

- `observe` ノードを追加し、`fit_score` と `action_loop_count` に基づいて「継続」または「終了」を判定すること
- `fit_score` が閾値（例：70）未満の場合、`observe` の判定結果により `GENERATE_REPLY` を再実行すること
- `CheckReplyProfileFitTool` の `revised_reply` と `improvement_suggestions` を `shared_canvas` に書き込み、次回の `GENERATE_REPLY` 実行時に参照できるようにすること
- `fit_score` が閾値以上になった場合、または最大ループ回数に達した場合に `observe` が終了を選択すること
- `fit_score` と判定結果をJSONログに含めること

## 受け入れ条件

- `fit_score` が閾値未満のとき、エージェントが `CHECK_REPLY_PROFILE_FIT` の後に `OBSERVE` を経由して `GENERATE_REPLY` を再実行すること
- `fit_score` が閾値以上のとき、`OBSERVE` が終了を判定し、ループを抜けること
- `revised_reply` が存在する場合、次の `GENERATE_REPLY` がその内容を参照して改善された返信を生成すること
- ループの上限回数（既存の `action_loop_count` ≥ 4）を超えた場合、`OBSERVE` が強制終了を判定すること

## 補足

- 対象ファイル:
  - `src/app/agent/core/schemas/state.py`（`fit_score` フィールドの追加）
  - `src/app/agent/core/nodes/action/node.py`（`fit_score` を `ReactState` に書き込む）
  - `src/app/agent/core/tools/check_reply_profile_fit/tool.py`（`revised_reply` を `shared_canvas` に書き込む）
  - `src/app/agent/core/nodes/observe/node.py`（継続/終了判定ロジックを実装）
  - グラフ定義ファイル（`CHECK_REPLY_PROFILE_FIT` の次遷移を `OBSERVE` に変更し、`OBSERVE` から `GENERATE_REPLY` または `END` に分岐）
- 閾値は環境変数 `AGENT_FIT_SCORE_THRESHOLD`（デフォルト: `70`）で設定可能にすること
- これはADLC Phase 3「妥当性評価とロバスト性」の中核実装となる
