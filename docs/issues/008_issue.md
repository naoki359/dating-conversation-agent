## 概要

`ActionNode` 内にある `GenerateReplyResultSchema` の変換と `shared_canvas` 反映処理を、`GenerateReplyTool.execute` 内へ移設する。あわせて、失敗時の挙動と責務境界を整理し、既存フローの挙動を維持する。

## 背景

現状は `GENERATE_REPLY` の実行結果に対する後処理が `ActionNode` 側に存在し、ツール固有の処理がノードに漏れている。ノードが特定ツールの戻り値スキーマを知っているため、拡張時に分岐が増えやすく、保守性が下がる懸念がある。移設によりツール単位で完結した実装へ寄せ、ノードは共通オーケストレーションに集中させたい。

## 要件

- `GenerateReplyTool.execute` 内で `GenerateReplyResultSchema` への変換を実施する
- 変換成功時は `generated_reply` と `reply_reasoning` を `shared_canvas` に反映する
- 変換失敗時は `BaseToolResult.success=False` を返し、原因が追跡可能な要約を付与する
- `ActionNode` から `ToolEnum.GENERATE_REPLY` 固有の分岐を削除し、ツール共通処理に統一する
- 既存の `BaseOutputSchema` の成功/失敗判定とサマリ生成の挙動を維持する
- 既存の `shared_store`/`shared_canvas` を利用する場合でも、副作用が分かる命名・コメント・テストで補強する

## 受け入れ条件

- `GENERATE_REPLY` 実行時に、正常系で `shared_canvas.generated_reply` と `shared_canvas.reply_reasoning` が設定される
- `GenerateReplyResultSchema` へ変換できないデータを受け取った場合、ツール失敗として処理される
- `ActionNode` に `GENERATE_REPLY` 専用のパース/Canvas 反映ロジックが残っていない
- 他ツール実行時の `ActionNode` の挙動に回帰がない
- 最低限、正常系1件・異常系1件（スキーマ変換失敗）のテストが追加される

## 補足

- 主な懸念は「ツールがグローバルな `shared_canvas` を直接更新する副作用」であり、テストとログで可視化する前提で実施する
- 将来的には `BaseToolResult.data` に Canvas 反映用ペイロードを持たせ、ノード側で一括反映する方式も検討余地がある
- 今回の目的は最小変更で責務のねじれを減らすことであり、外部 I/O や状態管理方式の全面変更は対象外とする