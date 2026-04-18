import pytest

from app.agent.core.utils.trigger_text import (
    clean_trigger_source_text,
    clean_trigger_topic,
    extract_phrase_candidates,
    looks_like_non_topic,
    normalize_topic_text,
)


class TestCleanTriggerSourceText:
    def test_removes_emoji(self):
        result = clean_trigger_source_text("水族館行きました♪")
        assert "♪" not in result
        assert "水族館行きました" in result

    def test_removes_multiple_emojis(self):
        result = clean_trigger_source_text("楽しかった✨😊")
        assert "✨" not in result
        assert "😊" not in result

    def test_normalizes_multiple_spaces(self):
        assert clean_trigger_source_text("水族館    行きました") == "水族館 行きました"

    def test_normalizes_newlines(self):
        assert clean_trigger_source_text("水族館\n\nクラゲ") == "水族館 クラゲ"

    def test_strips_leading_trailing_whitespace(self):
        assert clean_trigger_source_text("  水族館  ") == "水族館"

    def test_preserves_japanese_text(self):
        result = clean_trigger_source_text("東京タワーに行きました")
        assert result == "東京タワーに行きました"

    def test_already_clean_text_unchanged(self):
        assert clean_trigger_source_text("水族館") == "水族館"

    def test_removes_punctuation_symbols(self):
        result = clean_trigger_source_text("焼肉…おいしい！")
        assert "…" not in result
        assert "！" not in result

    def test_removes_w(self):
        result = clean_trigger_source_text("楽しかったw")
        assert "w" not in result


class TestNormalizeTopicText:
    def test_removes_punctuation(self):
        assert normalize_topic_text("水族館！") == "水族館"

    def test_converts_to_lowercase(self):
        assert normalize_topic_text("Aquarium") == "aquarium"

    def test_preserves_japanese(self):
        assert normalize_topic_text("水族館") == "水族館"

    def test_removes_brackets(self):
        assert normalize_topic_text("[水族館]") == "水族館"

    def test_removes_spaces(self):
        assert normalize_topic_text("水族 館") == "水族館"

    def test_keeps_alphanumeric(self):
        assert normalize_topic_text("abc123") == "abc123"


class TestCleanTriggerTopic:
    # --- 接頭語の除去 ---
    def test_removes_prefix_recently(self):
        assert clean_trigger_topic("最近は水族館") == "水族館"

    def test_removes_prefix_this_before(self):
        assert clean_trigger_topic("この前水族館") == "水族館"

    def test_removes_prefix_day_before(self):
        assert clean_trigger_topic("先日水族館") == "水族館"

    def test_removes_multiple_prefixes(self):
        assert clean_trigger_topic("最近そういえば焼肉") == "焼肉"

    # --- 語尾の除去 ---
    def test_removes_suffix_ga_suki(self):
        assert clean_trigger_topic("水族館が好き") == "水族館"

    def test_removes_suffix_ni_ikimashita(self):
        assert clean_trigger_topic("水族館に行きました") == "水族館"

    def test_removes_suffix_mimashita(self):
        assert clean_trigger_topic("映画みました") == "映画"

    def test_removes_suffix_desu(self):
        assert clean_trigger_topic("好きです") == "好き"

    # --- 前後の記号除去 ---
    def test_strips_square_brackets(self):
        assert clean_trigger_topic("[水族館]") == "水族館"

    def test_strips_parentheses(self):
        assert clean_trigger_topic("（水族館）") == "水族館"

    # --- ノイズ / 空文字 ---
    def test_returns_empty_for_noise_pattern(self):
        assert clean_trigger_topic("[name]") == ""

    def test_returns_empty_for_bracket_only_content(self):
        assert clean_trigger_topic("(age)") == ""

    def test_returns_empty_for_single_char_topic(self):
        assert clean_trigger_topic("展") == ""

    def test_returns_empty_for_blank_input(self):
        assert clean_trigger_topic("") == ""

    def test_returns_empty_after_strip_leaves_nothing(self):
        assert clean_trigger_topic("最近は") == ""

    # --- 正常系 ---
    def test_clean_topic_unchanged(self):
        assert clean_trigger_topic("焼肉") == "焼肉"


class TestExtractPhraseCandidates:
    def test_extracts_aquarium_with_prefix(self):
        result = extract_phrase_candidates("すみだ水族館 行きましたよ")
        assert "すみだ水族館" in result

    def test_extracts_exhibition_with_prefix(self):
        result = extract_phrase_candidates("下村観山展に行きました")
        assert "下村観山展" in result

    def test_does_not_extract_standalone_ten(self):
        result = extract_phrase_candidates("展に行きました")
        assert "展" not in result

    def test_extracts_museum(self):
        result = extract_phrase_candidates("東京国立博物館")
        assert "東京国立博物館" in result

    def test_extracts_multiple_candidates(self):
        result = extract_phrase_candidates("すみだ水族館 行きました クラゲ 綺麗でした")
        assert "すみだ水族館" in result
        assert "クラゲ" in result

    def test_returns_empty_for_no_match(self):
        result = extract_phrase_candidates("今日は天気がいい")
        assert result == []

    def test_extracts_cafe(self):
        result = extract_phrase_candidates("渋谷カフェに行きました")
        assert "渋谷カフェ" in result

    def test_extracts_ramen(self):
        result = extract_phrase_candidates("家系ラーメン食べた")
        assert "家系ラーメン" in result


class TestLooksLikeNonTopic:
    # --- 除外される語 ---
    def test_profile_keyword_is_non_topic(self):
        assert looks_like_non_topic("プロフィール") is True

    def test_summary_keyword_is_non_topic(self):
        assert looks_like_non_topic("要約") is True

    def test_name_keyword_is_non_topic(self):
        assert looks_like_non_topic("名前") is True

    def test_age_keyword_is_non_topic(self):
        assert looks_like_non_topic("年齢") is True

    def test_tokyo_resident_is_non_topic(self):
        assert looks_like_non_topic("東京在住") is True

    # --- 語尾による除外 ---
    def test_shitai_ending_is_non_topic(self):
        assert looks_like_non_topic("旅行したい") is True

    def test_desu_ending_is_non_topic(self):
        assert looks_like_non_topic("好きです") is True

    def test_masu_ending_is_non_topic(self):
        assert looks_like_non_topic("行きます") is True

    # --- 助詞 + 長さ ---
    def test_particle_with_long_text_is_non_topic(self):
        assert looks_like_non_topic("映画やアニメが大好き") is True

    def test_particle_with_short_text_is_not_excluded(self):
        # 助詞を含んでいても6文字以下なら除外しない
        assert looks_like_non_topic("猫が好") is False

    # --- 長さ ---
    def test_very_long_text_is_non_topic(self):
        assert looks_like_non_topic("これはとても長い文章で話題としての価値がありません") is True

    # --- 正常系 ---
    def test_aquarium_is_topic(self):
        assert looks_like_non_topic("水族館") is False

    def test_ramen_is_topic(self):
        assert looks_like_non_topic("焼肉") is False

    def test_anime_is_topic(self):
        assert looks_like_non_topic("アニメ") is False
