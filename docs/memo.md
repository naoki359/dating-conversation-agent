# 開発用のメモ

## よく使うコマンド

### サーバー起動

```bash
uv run python -m uvicorn app.agent.entrypoint:app --reload --app-dir src
```