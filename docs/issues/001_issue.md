# [BUG] POST /reply が generated_reply を空文字で返す

## 概要

`POST /reply` エンドポイントが、エージェントの生成した返信文を常に空文字（`""`）で返却している。
`GenerateReplyTool` が生成した返信は `shared_canvas["generated_reply"]` に書き込まれているが、APIレスポンスに含まれていない。

## 背景

エージェンティックマニュフェストの行動指針「動くソフトウェアが進捗の主要指標」に基づけば、ユーザーへ価値を届ける最終出力が壊れているのは最優先の修正対象となる。

現在のコードでは `ReplyResponse.generated_reply` がハードコードで `""` となっており、`shared_canvas` から値を取り出すコードが存在しない。

## 要件

- `POST /reply` のレスポンス `generated_reply` フィールドに、`shared_canvas["generated_reply"]` の値を返すこと
- `shared_canvas["generated_reply"]` が存在しない場合（エラー時など）は空文字を返すこと（現状と同じ挙動）
- `reply_reasoning` は引き続き `state["action_reasoning"]` ではなく `shared_canvas["reply_reasoning"]` を使うよう修正すること

## 受け入れ条件

- `POST /reply` を実行したとき、レスポンスの `generated_reply` に生成された返信文が含まれること
- `GenerateReplyTool` が正常に実行された場合、空文字にならないこと

## 補足

- 対象ファイル: `src/app/agent/entrypoint.py`
- `shared_canvas` はモジュールレベルの dict であり、グラフ実行後に `shared_canvas["generated_reply"]` を参照することで取得可能
- 将来的に並列リクエストを処理する場合、`shared_canvas` のグローバル状態がスレッドセーフでない問題も別途対処が必要（→ 007_issue で扱う想定）
