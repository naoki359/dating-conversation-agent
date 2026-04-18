from __future__ import annotations

import re

from app.agent.core.config.personal_topics import (
    CATEGORY_KEYWORDS,
    DIRECT_TOPIC_KEYWORDS,
    OUTING_CATEGORIES,
    TOPIC_SUFFIXES,
)


_PREFIX_PATTERN = re.compile(
    r"^(最近は|最近|この前|先日|先週|昨日|今日|今度|ちょっと|結構|かなり|すごく|めっちゃ|めちゃ|そういえば|なんとなく|たまたま|ふと|先ほど|さっき|このあいだ|前に)+"
)
_NOISE_PATTERN = re.compile(
    r"^[\[\(（].*[\]\)）]$|^(name|age|basic_info|interests)$",
    re.IGNORECASE,
)
_NORMALIZE_PATTERN = re.compile(r"[^一-龥ぁ-んァ-ヶーA-Za-z0-9]")
_TOPIC_SUFFIX_CLEANUP_PATTERN = re.compile(
    r"(が好き|が好きです|が気になる|気になります|気になる|気になってます|気になっています|"
    r"に行きました|行きました|行ってきました|行った|"
    r"みました|見ました|見た|観ました|観た|"
    r"食べました|飲みました|やりました|"
    r"でした|でしたよ|ですよ|です)$"
)
_TRIGGER_SOURCE_REMOVAL_PATTERN = re.compile(r"[♪🪼😊👍✨☺️♨️🎶wW…・,.、!！?？]")
_TRIGGER_SOURCE_WHITESPACE_PATTERN = re.compile(r"[\s\u3000]+")

# 施設名や展示名など、会話のフックになりやすい語尾を先に定義しておく。
# 「すみだ水族館」「下村観山展」のように、固有名詞 + 語尾のまとまりを
# 優先抽出するため、長い suffix から先に見るよう長さ順に並べている。
SPLIT_PATTERN = re.compile(r"[\n/・、,。！？!？]+")


# テキストをスペース区切りの単語列に変換する
# "水族館    行きました\n\nクラゲ"
# ↓
# "水族館 行きました クラゲ"
def clean_trigger_source_text(text: str) -> str:
    """絵文字や連続空白を落とし、抽出しやすい入力文字列に揃える。"""
    cleaned_text = _TRIGGER_SOURCE_REMOVAL_PATTERN.sub(" ", text)
    cleaned_text = _TRIGGER_SOURCE_WHITESPACE_PATTERN.sub(" ", cleaned_text)
    return cleaned_text.strip()


def normalize_topic_text(topic: str) -> str:
    """句読点や記号差分を無視して比較できるように正規化する。"""
    return _NORMALIZE_PATTERN.sub("", topic).lower()


def clean_trigger_topic(raw_topic: str) -> str:
    """
    会話トリガー候補から接尾表現や文脈由来の装飾を落とした比較用文字列を返す。

    ここでは domain-independent な文字列整形だけを担当し、
    話題として弱いかどうかの判定は呼び出し側で行う。
    """
    topic = raw_topic.strip(" 　-:：[]()（）")
    topic = _PREFIX_PATTERN.sub("", topic)
    topic = re.sub(r"^[はがをにでとやも]+", "", topic)
    topic = topic.strip(" 　-:：[]()（）")
    topic = _TOPIC_SUFFIX_CLEANUP_PATTERN.sub("", topic)
    topic = topic.strip(" 　-:：[]()（）")

    if not topic:
        return ""

    if _NOISE_PATTERN.match(topic):
        return ""

    if len(normalize_topic_text(topic)) <= 1:
        return ""

    return topic

def extract_phrase_candidates(text: str) -> list[str]:
    """
    suffix ごとにフレーズを走査し、「固有名詞 + 語尾（suffix）」の形になっている
    トピック候補を抽出する。

    例:
        text = "すみだ水族館 行きましたよ クラゲ 綺麗でした"
        → 抽出結果:
            [
                "すみだ水族館",
                "クラゲ",
            ]

        text = "下村観山展に行きました"
        → 抽出結果:
            [
                "下村観山展",
            ]

        text = "展に行きました"

        → 抽出結果:
            []
            ※ "展" 単体は抽象的なため除外（prefix_min=1）

    挙動:
        - 最大12文字の「名前っぽい文字列 + suffix」を抽出する
        - suffix（例: 水族館 / 展 / カフェ / ホテル など）で終わる語を対象とする
        - 前後の文脈（助詞など）が含まれたまま抽出されることがある
            例: "前すみだ水族館", "でクラゲ"

    注意:
        - この関数は「候補を広く拾う」ことが目的であり、最終的なトピック整形は行わない
        - 不要な接頭語・助詞・語尾の除去は後段の clean 処理で行う
        - suffix が "展" / "展覧会" の場合は prefix を最低1文字要求し、
          "展" 単体のような抽象語は除外する
    """
    phrases: list[str] = []
    for suffix in TOPIC_SUFFIXES:
        # 「展」「展覧会」は suffix 単体だと抽象的すぎるので、
        # 最低でも1文字以上の prefix を要求して固有名詞寄りにする。
        prefix_min = 1 if suffix in {"展", "展覧会"} else 0

        # 「名前っぽい文字列 + 語尾（suffix）」を抽出するための正規表現
        #
        # 例:
        # - "すみだ水族館" → マッチ（"すみだ" + "水族館"）
        # - "下村観山展" → マッチ（"下村観山" + "展"）
        # - "東京ディズニーホテル" → マッチ
        #
        # 挙動:
        # - prefix部分は最大12文字まで
        # - suffix（例: 水族館 / 展 / カフェ など）で終わる語を対象にする
        #
        # 注意:
        # - suffixが「展」の場合は prefix_min=1 にすることで
        #   "展" 単体のような抽象語は除外する
        pattern = re.compile(
            rf"[一-龥ぁ-んァ-ヶーA-Za-z0-9]{{{prefix_min},12}}{re.escape(suffix)}"
        )
        for match in pattern.finditer(text):
            phrases.append(match.group(0))
    return phrases

## 話題として利用できるか判定する
# True: 話題として弱い
# False: 話題として利用できる可能性がある
def looks_like_non_topic(topic: str) -> bool:
    """プロフィール項目名や説明文の断片など、話題として弱い語を除外する。"""

    # プロフィール構造やメタ情報として出てきやすい語を除外する
    if topic in {"プロフィール", "要約", "原文", "名前", "年齢", "東京在住", "真剣な恋"}:
        return True
    
    # 文としての終わりを示す語尾を持つ場合は除外する
    if topic.endswith("したい") or topic.endswith("です") or topic.endswith("ます"):
        return True
    
    # 助詞（や・が・で・を・に・と・は・も）を含み、かつ一定以上の長さがある場合は除外
    if re.search(r"[やがでをにとはも]", topic) and len(topic) > 6:
        return True
    
    # 長すぎる語は文章や説明文の可能性が高いため除外
    if len(topic) > 24:
        return True
    return False