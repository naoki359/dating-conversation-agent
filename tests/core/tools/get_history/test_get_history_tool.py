import pytest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from app.agent.core.tools.get_history.tool import GetHistoryTool


# テスト用のYAMLデータ（基本構成）
SAMPLE_YAML_DATA = {
    "profile": {
        "name": "テスト太郎",
        "age": 28,
        "raw_profile_text": "趣味は読書です。",
        "profile_summary": "本が好き",
        "meeting_timing_preference": "気が合えば会いたい",
    },
    "conversation": {
        "messages": [
            {"id": "msg001", "timestamp": "2026-01-01T12:00:00", "sender": "other", "message": "こんにちは"},
            {"id": "msg002", "timestamp": "2026-01-01T12:01:00", "sender": "self", "message": "はじめまして"},
        ],
        "updated_at": "2026-01-01T12:01:00",
    },
}


class TestGetHistoryToolExecute:
    """GetHistoryTool.execute() の正常系・異常系・境界値を検証する"""

    def _make_store(self, user_id: str | None = "with_0001") -> MagicMock:
        """共有ストアのモックを生成するヘルパー"""
        store = {}
        if user_id is not None:
            store["user_id"] = user_id
        mock_store = MagicMock()
        mock_store.get = lambda key, default=None: store.get(key, default)
        mock_store.__setitem__ = lambda self_inner, k, v: store.__setitem__(k, v)
        mock_store.__getitem__ = lambda self_inner, k: store[k]
        return mock_store

    # ============================================================
    # 正常系
    # ============================================================

    def test_returns_success_result_with_valid_user(self, tmp_path):
        # user_idが正常に存在する場合、success=Trueで履歴が返ること
        import yaml

        yaml_file = tmp_path / "with_0001.yaml"
        yaml_file.write_text(yaml.dump(SAMPLE_YAML_DATA, allow_unicode=True), encoding="utf-8")

        store = {}
        store["user_id"] = "with_0001"
        mock_store = MagicMock()
        mock_store.get = lambda key, default=None: store.get(key, default)
        mock_store.__setitem__ = lambda self_inner, k, v: store.__setitem__(k, v)
        mock_store.__getitem__ = lambda self_inner, k: store[k]

        with patch(
            "app.agent.core.tools.get_history.tool.get_shared_store",
            return_value=mock_store,
        ), patch(
            "app.agent.core.tools.get_history.tool.Settings.get_data_dir",
            return_value=tmp_path,
        ):
            tool = GetHistoryTool()
            result = tool.execute(execution_id="test-exec-id")

        assert result.success is True
        assert result.tool_name == "get_history"
        assert "partner_profile" in result.tool_result
        assert "conversation_history" in result.tool_result

    def test_profile_fields_are_correctly_mapped(self, tmp_path):
        # YAMLのprofileが正しくtool_resultに反映されることを確認する
        import yaml

        yaml_file = tmp_path / "with_0001.yaml"
        yaml_file.write_text(yaml.dump(SAMPLE_YAML_DATA, allow_unicode=True), encoding="utf-8")

        store = {}
        store["user_id"] = "with_0001"
        mock_store = MagicMock()
        mock_store.get = lambda key, default=None: store.get(key, default)
        mock_store.__setitem__ = lambda self_inner, k, v: store.__setitem__(k, v)
        mock_store.__getitem__ = lambda self_inner, k: store[k]

        with patch(
            "app.agent.core.tools.get_history.tool.get_shared_store",
            return_value=mock_store,
        ), patch(
            "app.agent.core.tools.get_history.tool.Settings.get_data_dir",
            return_value=tmp_path,
        ):
            tool = GetHistoryTool()
            result = tool.execute()

        profile = result.tool_result["partner_profile"]
        assert profile["name"] == "テスト太郎"
        assert profile["age"] == 28
        assert profile["meeting_timing_preference"] == "気が合えば会いたい"

    def test_conversation_history_messages_are_returned(self, tmp_path):
        # メッセージ一覧が正しく返ることを確認する
        import yaml

        yaml_file = tmp_path / "with_0001.yaml"
        yaml_file.write_text(yaml.dump(SAMPLE_YAML_DATA, allow_unicode=True), encoding="utf-8")

        store = {}
        store["user_id"] = "with_0001"
        mock_store = MagicMock()
        mock_store.get = lambda key, default=None: store.get(key, default)
        mock_store.__setitem__ = lambda self_inner, k, v: store.__setitem__(k, v)
        mock_store.__getitem__ = lambda self_inner, k: store[k]

        with patch(
            "app.agent.core.tools.get_history.tool.get_shared_store",
            return_value=mock_store,
        ), patch(
            "app.agent.core.tools.get_history.tool.Settings.get_data_dir",
            return_value=tmp_path,
        ):
            tool = GetHistoryTool()
            result = tool.execute()

        messages = result.tool_result["conversation_history"]
        assert len(messages) == 2
        assert messages[0]["message"] == "こんにちは"
        assert messages[1]["sender"] == "self"

    def test_now_hint_stored_when_present(self, tmp_path):
        # now_hintが存在する場合、shared_storeのconversationに含まれることを確認する
        import yaml

        data = {
            **SAMPLE_YAML_DATA,
            "conversation": {
                **SAMPLE_YAML_DATA["conversation"],
                "now_hint": "今は夜です",
            },
        }
        yaml_file = tmp_path / "with_0001.yaml"
        yaml_file.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")

        store = {}
        store["user_id"] = "with_0001"
        mock_store = MagicMock()
        mock_store.get = lambda key, default=None: store.get(key, default)
        mock_store.__setitem__ = lambda self_inner, k, v: store.__setitem__(k, v)
        mock_store.__getitem__ = lambda self_inner, k: store[k]

        with patch(
            "app.agent.core.tools.get_history.tool.get_shared_store",
            return_value=mock_store,
        ), patch(
            "app.agent.core.tools.get_history.tool.Settings.get_data_dir",
            return_value=tmp_path,
        ):
            tool = GetHistoryTool()
            result = tool.execute()

        # now_hintがstoreに反映されていることをcallsで確認する
        set_calls = {k: v for k, v in store.items()}
        assert "now_hint" in set_calls.get("conversation", {})
        assert set_calls["conversation"]["now_hint"] == "今は夜です"

    def test_picture_added_to_profile_when_present(self, tmp_path):
        # pictureフィールドがprofile外のルートにある場合、profileに追加されることを確認する
        import yaml

        data = dict(SAMPLE_YAML_DATA)
        data["picture"] = "https://example.com/image.jpg"
        yaml_file = tmp_path / "with_0001.yaml"
        yaml_file.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")

        store = {}
        store["user_id"] = "with_0001"
        mock_store = MagicMock()
        mock_store.get = lambda key, default=None: store.get(key, default)
        mock_store.__setitem__ = lambda self_inner, k, v: store.__setitem__(k, v)
        mock_store.__getitem__ = lambda self_inner, k: store[k]

        with patch(
            "app.agent.core.tools.get_history.tool.get_shared_store",
            return_value=mock_store,
        ), patch(
            "app.agent.core.tools.get_history.tool.Settings.get_data_dir",
            return_value=tmp_path,
        ):
            tool = GetHistoryTool()
            result = tool.execute()

        profile = result.tool_result["partner_profile"]
        assert profile["picture"] == "https://example.com/image.jpg"

    def test_invalid_meeting_timing_preference_falls_back_to_default(self, tmp_path):
        # 不正なmeeting_timing_preferenceはデフォルト値に正規化されることを確認する
        import yaml

        data = dict(SAMPLE_YAML_DATA)
        data["profile"] = dict(data["profile"])
        data["profile"]["meeting_timing_preference"] = "不正な値"
        yaml_file = tmp_path / "with_0001.yaml"
        yaml_file.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")

        store = {}
        store["user_id"] = "with_0001"
        mock_store = MagicMock()
        mock_store.get = lambda key, default=None: store.get(key, default)
        mock_store.__setitem__ = lambda self_inner, k, v: store.__setitem__(k, v)
        mock_store.__getitem__ = lambda self_inner, k: store[k]

        with patch(
            "app.agent.core.tools.get_history.tool.get_shared_store",
            return_value=mock_store,
        ), patch(
            "app.agent.core.tools.get_history.tool.Settings.get_data_dir",
            return_value=tmp_path,
        ):
            tool = GetHistoryTool()
            result = tool.execute()

        profile = result.tool_result["partner_profile"]
        assert profile["meeting_timing_preference"] == "気が合えば会いたい"

    # ============================================================
    # 異常系
    # ============================================================

    def test_returns_failure_when_user_id_not_in_store(self, tmp_path):
        # shared_storeにuser_idが存在しない場合、success=Falseが返ることを確認する
        mock_store = MagicMock()
        mock_store.get = lambda key, default=None: None  # user_idが未設定

        with patch(
            "app.agent.core.tools.get_history.tool.get_shared_store",
            return_value=mock_store,
        ):
            tool = GetHistoryTool()
            result = tool.execute()

        assert result.success is False
        assert result.tool_name == "get_history"
        assert result.tool_result == {}

    def test_raises_file_not_found_when_yaml_missing(self, tmp_path):
        # 対応するYAMLファイルが存在しない場合、FileNotFoundErrorが送出されることを確認する
        store = {}
        store["user_id"] = "nonexistent_user"
        mock_store = MagicMock()
        mock_store.get = lambda key, default=None: store.get(key, default)
        mock_store.__setitem__ = lambda self_inner, k, v: store.__setitem__(k, v)

        with patch(
            "app.agent.core.tools.get_history.tool.get_shared_store",
            return_value=mock_store,
        ), patch(
            "app.agent.core.tools.get_history.tool.Settings.get_data_dir",
            return_value=tmp_path,
        ):
            tool = GetHistoryTool()
            with pytest.raises(FileNotFoundError):
                tool.execute()

    # ============================================================
    # 境界値
    # ============================================================

    def test_empty_conversation_messages(self, tmp_path):
        # conversationのmessagesが空リストの場合でも正常に返ることを確認する
        import yaml

        data = dict(SAMPLE_YAML_DATA)
        data["conversation"] = {"messages": [], "updated_at": ""}
        yaml_file = tmp_path / "with_0001.yaml"
        yaml_file.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")

        store = {}
        store["user_id"] = "with_0001"
        mock_store = MagicMock()
        mock_store.get = lambda key, default=None: store.get(key, default)
        mock_store.__setitem__ = lambda self_inner, k, v: store.__setitem__(k, v)
        mock_store.__getitem__ = lambda self_inner, k: store[k]

        with patch(
            "app.agent.core.tools.get_history.tool.get_shared_store",
            return_value=mock_store,
        ), patch(
            "app.agent.core.tools.get_history.tool.Settings.get_data_dir",
            return_value=tmp_path,
        ):
            tool = GetHistoryTool()
            result = tool.execute()

        assert result.success is True
        assert result.tool_result["conversation_history"] == []

    def test_empty_profile(self, tmp_path):
        # profileが空dictの場合でも正常に動作し、デフォルトのmeeting_timing_preferenceが設定されることを確認する
        import yaml

        data = {"profile": {}, "conversation": {"messages": [], "updated_at": ""}}
        yaml_file = tmp_path / "with_0001.yaml"
        yaml_file.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")

        store = {}
        store["user_id"] = "with_0001"
        mock_store = MagicMock()
        mock_store.get = lambda key, default=None: store.get(key, default)
        mock_store.__setitem__ = lambda self_inner, k, v: store.__setitem__(k, v)
        mock_store.__getitem__ = lambda self_inner, k: store[k]

        with patch(
            "app.agent.core.tools.get_history.tool.get_shared_store",
            return_value=mock_store,
        ), patch(
            "app.agent.core.tools.get_history.tool.Settings.get_data_dir",
            return_value=tmp_path,
        ):
            tool = GetHistoryTool()
            result = tool.execute()

        assert result.success is True
        # 空profileでもmeeting_timing_preferenceがデフォルト値に設定されること
        assert result.tool_result["partner_profile"]["meeting_timing_preference"] == "気が合えば会いたい"

    def test_none_meeting_timing_preference_falls_back_to_default(self, tmp_path):
        # meeting_timing_preferenceがNoneの場合もデフォルト値に正規化されることを確認する
        import yaml

        data = dict(SAMPLE_YAML_DATA)
        data["profile"] = dict(data["profile"])
        data["profile"]["meeting_timing_preference"] = None
        yaml_file = tmp_path / "with_0001.yaml"
        yaml_file.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")

        store = {}
        store["user_id"] = "with_0001"
        mock_store = MagicMock()
        mock_store.get = lambda key, default=None: store.get(key, default)
        mock_store.__setitem__ = lambda self_inner, k, v: store.__setitem__(k, v)
        mock_store.__getitem__ = lambda self_inner, k: store[k]

        with patch(
            "app.agent.core.tools.get_history.tool.get_shared_store",
            return_value=mock_store,
        ), patch(
            "app.agent.core.tools.get_history.tool.Settings.get_data_dir",
            return_value=tmp_path,
        ):
            tool = GetHistoryTool()
            result = tool.execute()

        assert result.tool_result["partner_profile"]["meeting_timing_preference"] == "気が合えば会いたい"
