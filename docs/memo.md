# 開発用のメモ

## よく使うコマンド

### サーバー起動

```bash
uv run python -m uvicorn app.agent.entrypoint:app --reload --app-dir src
```

### ツールの単独実行

```bash
uv run python scripts/eval_score_reply_quality.py --cases eval/score_reply_quality_cases.yaml --data-dir data/test_user --output-dir eval/results
```

### テストの実行

```bash
uv run pytest tests/
```

特定のファイルのみ実行する場合:
```bash
uv run pytest tests/core/utils/test_trigger_text.py -v
```

### issueの生成
```bash
gh issue create --title "[BUG] モジュールグローバルな値の取り扱い方法検討" --body-file ".\docs\issues\011_issue.md"
```

### 修正の退避（git stash）

修正を退避する
```bash
git stash -u -m "ワークフローを事前定義型に変更する" 
```

- `-u` 未追跡のファイルも対象とする
- `-m` メッセージ付与

退避履歴を確認する
```bash
git stash list
```

退避した修正を戻す
```bash
git stash apply "stash@{0}"
```

### コミットを消す（git reset）

最新のコミットを消す
```bash
git reset --soft HEAD~1  
```

- `--soft` ソースは残す

## 課題

### 📊 テストデータ・会話品質
- テスト用の会話のバリエーションが少ない

### 📝 ログ・履歴管理
- プロンプトの内容も履歴に残したい
- 各ノード、ツールのスキーマが持つ情報の整理
- jsonログ確認用のUIが欲しい

### 🧪 テスト・評価
- ツールのテストを書きたい
- 評価用のツールをひとまとめにしたい。
- 

### 🏗️ アーキテクチャ・状態管理

### 🐛 バグより
- `observe_node`の観測結果をもっと詳細に書く必要がある。と思った