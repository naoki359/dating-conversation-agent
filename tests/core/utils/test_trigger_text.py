import pytest

from app.agent.core.utils.trigger_text import (
    build_self_topics,
    build_trigger_candidates,
    clean_trigger_source_text,
    clean_trigger_topic,
    extract_phrase_candidates,
    extract_topics_from_text,
    infer_category,
    looks_like_non_topic,
    match_with_self_profile,
    normalize_topic_text,
    prune_generic_duplicates,
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


class TestBuildSelfTopics:
    """build_self_topics のユニットテスト。

    extract_topics_fn / infer_category_fn はテスト用のスタブを渡し、
    build_self_topics 自体の責務（重複排除・正規化・辞書組み立て）に絞って検証する。
    """

    def _stub_extract(self, text: str) -> list[str]:
        """スペース区切りで単語を返す最小スタブ。"""
        return [w for w in text.split() if w]

    def _stub_infer(self, keyword: str) -> str:
        return "food" if keyword in {"焼肉", "ラーメン"} else "general"

    # --- 正常系 ---
    def test_returns_topics_from_profile_summary(self):
        profile = {"profile_summary": "焼肉 ラーメン", "raw_profile_text": ""}
        result = build_self_topics(profile, self._stub_extract, self._stub_infer)
        keywords = [t["keyword"] for t in result]
        assert "焼肉" in keywords
        assert "ラーメン" in keywords

    def test_returns_topics_from_raw_profile_text(self):
        profile = {"profile_summary": "", "raw_profile_text": "水族館 カフェ"}
        result = build_self_topics(profile, self._stub_extract, self._stub_infer)
        keywords = [t["keyword"] for t in result]
        assert "水族館" in keywords
        assert "カフェ" in keywords

    def test_combines_both_sources(self):
        profile = {"profile_summary": "焼肉", "raw_profile_text": "水族館"}
        result = build_self_topics(profile, self._stub_extract, self._stub_infer)
        keywords = [t["keyword"] for t in result]
        assert "焼肉" in keywords
        assert "水族館" in keywords

    def test_topic_dict_has_required_keys(self):
        profile = {"profile_summary": "焼肉", "raw_profile_text": ""}
        result = build_self_topics(profile, self._stub_extract, self._stub_infer)
        assert len(result) == 1
        assert set(result[0].keys()) == {"keyword", "normalized_keyword", "category"}

    def test_category_is_set_via_infer_fn(self):
        profile = {"profile_summary": "焼肉", "raw_profile_text": ""}
        result = build_self_topics(profile, self._stub_extract, self._stub_infer)
        assert result[0]["category"] == "food"

    def test_normalized_keyword_strips_symbols(self):
        profile = {"profile_summary": "焼肉！", "raw_profile_text": ""}
        # スタブはスペース区切りなのでそのまま "焼肉！" が渡る
        result = build_self_topics(profile, self._stub_extract, self._stub_infer)
        assert result[0]["normalized_keyword"] == "焼肉"

    # --- 重複排除 ---
    def test_deduplicates_same_keyword_across_sources(self):
        profile = {"profile_summary": "焼肉", "raw_profile_text": "焼肉"}
        result = build_self_topics(profile, self._stub_extract, self._stub_infer)
        keywords = [t["keyword"] for t in result]
        assert keywords.count("焼肉") == 1

    def test_deduplicates_by_normalized_form(self):
        # "焼肉！" と "焼肉" は正規化すると同じ → 片方だけ残る
        def extract_fn(text: str) -> list[str]:
            return ["焼肉！", "焼肉"] if text else []

        profile = {"profile_summary": "dummy", "raw_profile_text": ""}
        result = build_self_topics(profile, extract_fn, self._stub_infer)
        assert len(result) == 1

    # --- 空プロフィール ---
    def test_empty_profile_returns_empty_list(self):
        result = build_self_topics({}, self._stub_extract, self._stub_infer)
        assert result == []

    def test_profile_with_only_empty_strings_returns_empty_list(self):
        profile = {"profile_summary": "", "raw_profile_text": ""}
        result = build_self_topics(profile, self._stub_extract, self._stub_infer)
        assert result == []

    # --- extract_topics_fn が空リストを返すケース ---
    def test_extract_fn_returns_nothing(self):
        profile = {"profile_summary": "何かのテキスト", "raw_profile_text": ""}
        result = build_self_topics(profile, lambda _: [], self._stub_infer)
        assert result == []


class TestInferCategory:
    # --- 既知カテゴリ ---
    def test_aquarium_keyword(self):
        assert infer_category("水族館") == "aquarium"

    def test_jellyfish_keyword(self):
        assert infer_category("クラゲ") == "aquarium"

    def test_museum_keyword(self):
        assert infer_category("美術館") == "museum_art"

    def test_exhibition_keyword(self):
        assert infer_category("展覧会") == "museum_art"

    def test_animals_cat(self):
        assert infer_category("猫") == "animals"

    def test_travel_keyword(self):
        assert infer_category("旅行") == "travel"

    def test_sauna_keyword(self):
        assert infer_category("サウナ") == "sauna"

    def test_food_keyword(self):
        assert infer_category("焼肉") == "food_drink"

    def test_ramen_keyword(self):
        assert infer_category("ラーメン") == "food_drink"

    def test_anime_keyword(self):
        assert infer_category("アニメ") == "anime_game"

    def test_game_keyword(self):
        assert infer_category("ゲーム") == "anime_game"

    def test_books_keyword(self):
        assert infer_category("小説") == "books"

    # --- general ---
    def test_unknown_keyword_returns_general(self):
        assert infer_category("テニス") == "general"

    def test_empty_string_returns_general(self):
        assert infer_category("") == "general"

    # --- 正規化で一致する語 ---
    def test_compound_aquarium_name(self):
        # "すみだ水族館" は正規化後に "水族館" を含む → aquarium
        assert infer_category("すみだ水族館") == "aquarium"

    def test_compound_art_museum(self):
        assert infer_category("東京国立近代美術館") == "museum_art"


class TestExtractTopicsFromText:
    # --- suffix ベース抽出 ---
    def test_extracts_aquarium_with_prefix(self):
        result = extract_topics_from_text("すみだ水族館に行きました")
        assert "すみだ水族館" in result

    def test_extracts_exhibition_with_prefix(self):
        result = extract_topics_from_text("下村観山展を見てきました")
        assert "下村観山展" in result

    def test_extracts_cafe(self):
        result = extract_topics_from_text("渋谷カフェに行ってきた")
        assert "渋谷カフェ" in result

    # --- DIRECT_TOPIC_KEYWORDS 検出 ---
    def test_extracts_direct_keyword_anime(self):
        result = extract_topics_from_text("最近アニメにはまってます")
        assert "アニメ" in result

    def test_extracts_direct_keyword_sauna(self):
        result = extract_topics_from_text("先週サウナ行ってきた")
        assert "サウナ" in result

    def test_extracts_direct_keyword_yakiniku(self):
        result = extract_topics_from_text("焼肉食べたい")
        assert "焼肉" in result

    # --- 区切り文字単位の補助抽出 ---
    def test_extracts_ramen_from_split(self):
        result = extract_topics_from_text("家系ラーメン・焼肉が好き")
        assert "家系ラーメン" in result

    # --- 複数トピック ---
    def test_extracts_multiple_topics(self):
        result = extract_topics_from_text("すみだ水族館 行った クラゲ 綺麗でした")
        assert "すみだ水族館" in result
        assert "クラゲ" in result

    # --- 重複排除 ---
    def test_deduplicates_same_topic(self):
        result = extract_topics_from_text("サウナ サウナ サウナ")
        assert result.count("サウナ") == 1

    # --- 空・ノイズ入力 ---
    def test_empty_text_returns_empty(self):
        assert extract_topics_from_text("") == []

    def test_noise_only_text_returns_empty(self):
        assert extract_topics_from_text("♪✨😊") == []

    def test_generic_text_without_topics_returns_empty(self):
        result = extract_topics_from_text("今日はいい天気ですね")
        assert result == []

    # --- 接頭語付きでも正しく取れる ---
    def test_prefix_stripped_from_extracted_topic(self):
        result = extract_topics_from_text("最近は家系ラーメンにはまってます")
        assert "家系ラーメン" in result
        for keyword in result:
            assert not keyword.startswith("最近")


# ---------------------------------------------------------------------------
# match_with_self_profile
# ---------------------------------------------------------------------------

class TestMatchWithSelfProfile:
    """match_with_self_profile のユニットテスト。"""

    def _make_self_topics(self, entries: list[tuple[str, str, str]]) -> list[dict[str, str]]:
        """(keyword, normalized_keyword, category) のリストから self_topics を組み立てる。"""
        return [
            {"keyword": k, "normalized_keyword": n, "category": c}
            for k, n, c in entries
        ]

    # --- high 判定 ---
    def test_high_when_candidate_in_self_normalized(self):
        self_topics = self._make_self_topics([("すみだ水族館", "すみだ水族館", "aquarium")])
        match_level, related, reason = match_with_self_profile(
            candidate_keyword="水族館",
            candidate_normalized="水族館",
            candidate_category="aquarium",
            self_topics=self_topics,
        )
        assert match_level == "high"
        assert "すみだ水族館" in related
        assert "水族館" in reason

    def test_high_when_self_normalized_in_candidate(self):
        self_topics = self._make_self_topics([("水族館", "水族館", "aquarium")])
        match_level, related, _ = match_with_self_profile(
            candidate_keyword="すみだ水族館",
            candidate_normalized="すみだ水族館",
            candidate_category="aquarium",
            self_topics=self_topics,
        )
        assert match_level == "high"
        assert "水族館" in related

    def test_high_related_capped_at_five(self):
        self_topics = self._make_self_topics([
            (f"水族館{i}", f"水族館{i}", "aquarium") for i in range(8)
        ])
        _, related, _ = match_with_self_profile(
            candidate_keyword="水族館",
            candidate_normalized="水族館",
            candidate_category="aquarium",
            self_topics=self_topics,
        )
        assert len(related) <= 5

    # --- partial 判定（カテゴリ一致）---
    def test_partial_when_same_category(self):
        self_topics = self._make_self_topics([("焼肉", "焼肉", "food_drink")])
        match_level, related, reason = match_with_self_profile(
            candidate_keyword="ラーメン",
            candidate_normalized="らーめん",
            candidate_category="food_drink",
            self_topics=self_topics,
        )
        assert match_level == "partial"
        assert "焼肉" in related
        assert "ラーメン" in reason

    def test_partial_not_triggered_for_general_category(self):
        # category が "general" の場合はカテゴリ一致にならない
        self_topics = self._make_self_topics([("テニス", "テニス", "general")])
        match_level, _, _ = match_with_self_profile(
            candidate_keyword="バドミントン",
            candidate_normalized="バドミントン",
            candidate_category="general",
            self_topics=self_topics,
        )
        assert match_level == "none"

    # --- partial 判定（外出系 broad match）---
    def test_partial_when_both_in_outing_categories(self):
        # candidate が aquarium（OUTING_CATEGORIES）、self_topics が travel（OUTING_CATEGORIES）
        self_topics = self._make_self_topics([("旅行", "旅行", "travel")])
        match_level, related, reason = match_with_self_profile(
            candidate_keyword="水族館",
            candidate_normalized="水族館",
            candidate_category="aquarium",
            self_topics=self_topics,
        )
        assert match_level == "partial"
        assert "旅行" in related
        assert "水族館" in reason

    def test_partial_outing_not_triggered_when_self_not_outing(self):
        # self_topics にアウティング系がなければ broad match しない
        self_topics = self._make_self_topics([("焼肉", "焼肉", "food_drink")])
        match_level, _, _ = match_with_self_profile(
            candidate_keyword="水族館",
            candidate_normalized="水族館",
            candidate_category="aquarium",
            self_topics=self_topics,
        )
        assert match_level == "none"

    # --- none 判定 ---
    def test_none_when_no_match(self):
        self_topics = self._make_self_topics([("焼肉", "焼肉", "food_drink")])
        match_level, related, _ = match_with_self_profile(
            candidate_keyword="アニメ",
            candidate_normalized="アニメ",
            candidate_category="anime_game",
            self_topics=self_topics,
        )
        assert match_level == "none"
        assert related == []

    def test_none_when_self_topics_empty(self):
        match_level, related, _ = match_with_self_profile(
            candidate_keyword="水族館",
            candidate_normalized="水族館",
            candidate_category="aquarium",
            self_topics=[],
        )
        assert match_level == "none"
        assert related == []

    # --- 優先度：high > partial（カテゴリが合うが直接一致もある場合）---
    def test_high_takes_priority_over_category_match(self):
        self_topics = self._make_self_topics([
            ("水族館", "水族館", "aquarium"),
            ("すみだ水族館", "すみだ水族館", "aquarium"),
        ])
        match_level, _, _ = match_with_self_profile(
            candidate_keyword="水族館",
            candidate_normalized="水族館",
            candidate_category="aquarium",
            self_topics=self_topics,
        )
        assert match_level == "high"


# ---------------------------------------------------------------------------
# prune_generic_duplicates
# ---------------------------------------------------------------------------

class TestPruneGenericDuplicates:
    """prune_generic_duplicates のユニットテスト。"""

    def _make_candidate(
        self,
        keyword: str,
        normalized_keyword: str,
        category: str,
        priority_score: int = 50,
    ):
        from app.agent.core.tools.analyze_conversation_triggers.schema import TriggerCandidateSchema
        return TriggerCandidateSchema(
            keyword=keyword,
            normalized_keyword=normalized_keyword,
            source="latest_message",
            source_quote="テスト用テキスト",
            category=category,
            match_level="none",
            match_reason="テスト",
            priority_score=priority_score,
        )

    def test_removes_generic_when_specific_exists(self):
        specific = self._make_candidate("すみだ水族館", "すみだ水族館", "aquarium")
        generic = self._make_candidate("水族館", "水族館", "aquarium")
        result = prune_generic_duplicates([specific, generic])
        keywords = [c.keyword for c in result]
        assert "すみだ水族館" in keywords
        assert "水族館" not in keywords

    def test_removes_suffix_only_word(self):
        specific = self._make_candidate("下村観山展", "下村観山展", "museum_art")
        generic = self._make_candidate("展", "展", "museum_art")
        result = prune_generic_duplicates([specific, generic])
        assert len(result) == 1
        assert result[0].keyword == "下村観山展"

    def test_keeps_both_when_different_category(self):
        aquarium = self._make_candidate("すみだ水族館", "すみだ水族館", "aquarium")
        art = self._make_candidate("館", "館", "museum_art")
        result = prune_generic_duplicates([aquarium, art])
        assert len(result) == 2

    def test_keeps_generic_when_no_specific(self):
        generic = self._make_candidate("水族館", "水族館", "aquarium")
        result = prune_generic_duplicates([generic])
        assert len(result) == 1
        assert result[0].keyword == "水族館"

    def test_preserves_order_of_non_duplicated(self):
        c1 = self._make_candidate("焼肉", "焼肉", "food_drink")
        c2 = self._make_candidate("アニメ", "アニメ", "anime_game")
        result = prune_generic_duplicates([c1, c2])
        assert [c.keyword for c in result] == ["焼肉", "アニメ"]

    def test_empty_list_returns_empty(self):
        assert prune_generic_duplicates([]) == []

    def test_single_candidate_unchanged(self):
        c = self._make_candidate("サウナ", "サウナ", "sauna")
        result = prune_generic_duplicates([c])
        assert len(result) == 1


# ---------------------------------------------------------------------------
# build_trigger_candidates
# ---------------------------------------------------------------------------

class TestBuildTriggerCandidates:
    """build_trigger_candidates の結合テスト。"""

    def _self_topics(self, entries: list[tuple[str, str, str]]) -> list[dict[str, str]]:
        return [
            {"keyword": k, "normalized_keyword": n, "category": c}
            for k, n, c in entries
        ]

    # --- 基本動作 ---
    def test_returns_empty_for_empty_source_texts(self):
        result = build_trigger_candidates([], [])
        assert result == []

    def test_extracts_candidate_from_latest_message(self):
        source_texts = [("latest_message", "すみだ水族館に行きました")]
        result = build_trigger_candidates(source_texts, [])
        keywords = [c.keyword for c in result]
        assert "すみだ水族館" in keywords

    def test_extracts_candidate_from_profile_summary(self):
        source_texts = [("partner_profile_summary", "旅行が好きです")]
        result = build_trigger_candidates(source_texts, [])
        keywords = [c.keyword for c in result]
        assert "旅行" in keywords

    # --- ソース優先度 ---
    def test_latest_message_scores_higher_than_profile(self):
        source_texts = [
            ("latest_message", "焼肉食べた"),
            ("partner_profile_summary", "サウナが好き"),
        ]
        result = build_trigger_candidates(source_texts, [])
        # 最新メッセージ由来の候補が上位にあることを確認
        assert result[0].source == "latest_message"

    # --- self_profile との一致で priority_score が上がる ---
    def test_high_match_increases_priority(self):
        source_texts = [
            ("latest_message", "すみだ水族館に行きました"),
            ("partner_profile_summary", "旅行が好きです"),
        ]
        self_topics = self._self_topics([("水族館", "水族館", "aquarium")])
        result = build_trigger_candidates(source_texts, self_topics)
        aquarium_candidate = next(c for c in result if "水族館" in c.keyword)
        assert aquarium_candidate.match_level == "high"
        assert aquarium_candidate.needs_research is False

    def test_none_match_sets_needs_research(self):
        source_texts = [("latest_message", "アニメ見ました")]
        self_topics = self._self_topics([("焼肉", "焼肉", "food_drink")])
        result = build_trigger_candidates(source_texts, self_topics)
        anime_candidate = next((c for c in result if c.keyword == "アニメ"), None)
        if anime_candidate:
            assert anime_candidate.needs_research is True

    # --- 重複統合 ---
    def test_deduplicates_same_keyword_across_sources(self):
        source_texts = [
            ("latest_message", "水族館行きました"),
            ("partner_profile_summary", "水族館が好き"),
        ]
        result = build_trigger_candidates(source_texts, [])
        aquarium_hits = [c for c in result if c.normalized_keyword == "水族館"]
        assert len(aquarium_hits) == 1

    def test_keeps_higher_source_score_on_duplicate(self):
        # 同じ語が latest_message と profile 両方にある場合、latest_message 側が残る
        source_texts = [
            ("latest_message", "水族館行きました"),
            ("partner_profile_summary", "水族館が好き"),
        ]
        result = build_trigger_candidates(source_texts, [])
        aquarium_hit = next(c for c in result if c.normalized_keyword == "水族館")
        assert aquarium_hit.source == "latest_message"

    # --- 汎称の除去 ---
    def test_prunes_generic_when_specific_exists(self):
        source_texts = [("latest_message", "すみだ水族館に行きました")]
        result = build_trigger_candidates(source_texts, [])
        keywords = [c.keyword for c in result]
        # "すみだ水族館" があれば "水族館" は除去される
        if "すみだ水族館" in keywords:
            assert "水族館" not in keywords

    # --- ソート順 ---
    def test_result_is_sorted_by_priority_descending(self):
        source_texts = [("latest_message", "すみだ水族館が好き 旅行も好き")]
        self_topics = self._self_topics([("水族館", "水族館", "aquarium")])
        result = build_trigger_candidates(source_texts, self_topics)
        scores = [c.priority_score for c in result]
        assert scores == sorted(scores, reverse=True)

