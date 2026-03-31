# 開発用のメモ

## よく使うコマンド

### サーバー起動

```bash
uv run python -m uvicorn app.agent.entrypoint:app --reload --app-dir src
```


## 課題

- テスト用の会話のバリエーションが少ない
- 似たような話題を振っている場面が散在
- jsonログの見直しが必要