#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ローマ字入力中に ATOK の読みバッファに何が入るかを再現する。

ATOK の入力モードは「全角ひらがな／全角カタカナ／半角カタカナ／半角英数」で、
半角英数モードではスペースを押しても変換されない（実測）。
つまり**半角英字のよみは一致しようがない**。

ひらがな入力モードで `test` と打つと、読みバッファは `test` ではなく
`てｓｔ` になる。TeX 名のよみ（infty、bbr、argmax …）を使うには、
**打ったときに実際に出来上がる綴り**で登録する必要がある。

    >>> romaji_buffer("test")
    'てｓｔ'
    >>> romaji_buffer("infty")
    'いんｆｔｙ'

規則:
  * ローマ字表に一致する綴りはかなになる
  * `n` + 子音 → ん
  * 同じ子音の重なり → っ
  * かなにならずに残った子音は全角英字のまま残る
  * 数字・記号はそのまま通す

ただし ATOK のローマ字テーブルには版や設定による揺れがあり、`la` を ぁ とするか
ら とするか、`th` を てゃ行に割り当てるかなどは確かめようがない。そこで
`romaji_variants()` は**揺れる規則の組み合わせを全部展開**して、ありうる綴りを
すべて返す。辞書にはその全部を登録しておけば、実機がどちらでも一致する。
"""
from __future__ import annotations

from itertools import product

VOWELS = "aiueo"
VOWEL_KANA = {"a": "あ", "i": "い", "u": "う", "e": "え", "o": "お"}

# 子音 + 母音（あ い う え お の順）。揺れのないものだけここに置く。
_BASE_FIXED = {
    "k": "か き く け こ",
    "g": "が ぎ ぐ げ ご",
    "s": "さ し す せ そ",
    "z": "ざ じ ず ぜ ぞ",
    "t": "た ち つ て と",
    "d": "だ ぢ づ で ど",
    "n": "な に ぬ ね の",
    "h": "は ひ ふ へ ほ",
    "b": "ば び ぶ べ ぼ",
    "p": "ぱ ぴ ぷ ぺ ぽ",
    "m": "ま み む め も",
    "r": "ら り る れ ろ",
    "y": "や い ゆ いぇ よ",
    "w": "わ うぃ う うぇ を",
    "f": "ふぁ ふぃ ふ ふぇ ふぉ",
    "j": "じゃ じ じゅ じぇ じょ",
    "v": "ゔぁ ゔぃ ゔ ゔぇ ゔぉ",
    "q": "くぁ くぃ く くぇ くぉ",
}

# 2 文字の子音（しゃ・ちゃ・つぁ 系）。揺れのないもの。
_DIGRAPH_FIXED = {
    "sh": "しゃ し しゅ しぇ しょ",
    "ch": "ちゃ ち ちゅ ちぇ ちょ",
    "ts": "つぁ つぃ つ つぇ つぉ",
}

# 版や設定で揺れる 2 文字の子音
_DIGRAPH_EXTRA = {
    "th": "てゃ てぃ てゅ てぇ てょ",
    "dh": "でゃ でぃ でゅ でぇ でょ",
    "wh": "うぁ うぃ う うぇ うぉ",
    "kw": "くぁ くぃ くぅ くぇ くぉ",
    "gw": "ぐぁ ぐぃ ぐぅ ぐぇ ぐぉ",
    "tw": "とぁ とぃ とぅ とぇ とぉ",
    "dw": "どぁ どぃ どぅ どぇ どぉ",
    "sw": "すぁ すぃ すぅ すぇ すぉ",
    "zw": "ずぁ ずぃ ずぅ ずぇ ずぉ",
}

_SMALL = "ぁ ぃ ぅ ぇ ぉ"
_RA = "ら り る れ ろ"
_CA = "か し く せ こ"

# 拗音（きゃ・しゃ・にゃ …）を作る子音
_YOON_SOURCE = "kgszjtdnhbpmrvf"
_SMALL_Y = "ゃ ぃ ゅ ぇ ょ".split()

# ATOK Passport（Windows）で実測して確定した規則。
#   test   -> てｓｔ    かなにならない子音は全角で残る
#   infty  -> いんｆｔｙ n + 子音 は ん
#   leq    -> ぇｑ      l + 母音 は小書き（ら行ではない）
#   lambda -> ぁｍｂだ  同上
#   theta  -> てぇた    th は てゃ行に割り当てられている
#   cup    -> くｐ      c + 母音 は か行
CONFIRMED_OPTS = {
    "l_as": "small",
    "c_as": "ka",
    "th_as": "tya",
}

# まだ確かめていない規則。ありうる選択肢を全部展開して、どちらでも一致するように
# 両方のよみを登録する。既定（先頭）が確定済みの規則から素直に導かれる版。
OPTIONS = {
    "x_as": ["small", "leftover"],    # xi → ぃ か ｘい か
    "n_final": ["kana", "leftover"],  # 末尾の n → ん か ｎ か
    "sokuon": ["repeat", "single"],   # sss → っっ か っ か
}
DEFAULT_OPTS = {k: v[0] for k, v in OPTIONS.items()} | CONFIRMED_OPTS

_table_cache: dict[tuple, tuple[dict[str, str], int]] = {}


def _build_table(opts: dict[str, str]) -> tuple[dict[str, str], int]:
    key = tuple(sorted(opts.items()))
    if key in _table_cache:
        return _table_cache[key]

    base = dict(_BASE_FIXED)
    base["l"] = _SMALL if opts["l_as"] == "small" else _RA
    if opts["x_as"] == "small":
        base["x"] = _SMALL
    if opts["c_as"] == "ka":
        base["c"] = _CA

    table: dict[str, str] = {}
    for c, kana in base.items():
        for v, k in zip(VOWELS, kana.split()):
            table[c + v] = k

    digraphs = dict(_DIGRAPH_FIXED)
    if opts["th_as"] == "tya":
        digraphs.update(_DIGRAPH_EXTRA)
    for c, kana in digraphs.items():
        for v, k in zip(VOWELS, kana.split()):
            table[c + v] = k

    # 拗音: ky + a -> き + ゃ
    for c in _YOON_SOURCE:
        i_kana = _BASE_FIXED[c].split()[1]
        for v, small in zip(VOWELS, _SMALL_Y):
            table[c + "y" + v] = i_kana + small
    # 小書き文字と促音の直接入力
    for c in ("l", "x"):
        if c == "x" and opts["x_as"] != "small":
            continue
        for v, small in zip(VOWELS, _SMALL_Y):
            table[c + "y" + v] = small
        table[c + "tu"] = "っ"
        table[c + "tsu"] = "っ"
    table["nn"] = "ん"
    table["xn"] = "ん"
    # 例外的な綴り
    table.update({
        "shi": "し", "chi": "ち", "tsu": "つ", "fu": "ふ",
        "si": "し", "ti": "ち", "tu": "つ", "hu": "ふ", "zi": "じ",
        "ji": "じ", "di": "ぢ", "du": "づ", "wo": "を",
        "cya": "ちゃ", "cyi": "ちぃ", "cyu": "ちゅ", "cye": "ちぇ", "cyo": "ちょ",
    })
    result = (table, max(len(k) for k in table))
    _table_cache[key] = result
    return result


def to_fullwidth(ch: str) -> str:
    """半角英字を全角にする（ATOK の読みバッファでの見え方に合わせる）。"""
    o = ord(ch)
    if 0x21 <= o <= 0x7E:
        return chr(o - 0x20 + 0xFF00)
    return ch


def pascal_text(text: str) -> str:
    """先頭の英字を大文字にする。

    ATOK のひらがな入力は、大文字から始まる綴りをローマ字変換せずに
    アルファベットのまま保持する。`infty` と打つと `いんｆｔｙ` になるが、
    `Infty` と打てば `Infty` のまま残るので、TeX 名をそのままよみにできる。

        >>> pascal_text("infty")
        'Infty'
        >>> pascal_text("_i")
        '_I'
    """
    out = list(text)
    for i, ch in enumerate(out):
        if ch.isascii() and ch.isalpha():
            out[i] = ch.upper()
            break
    return "".join(out)


def fullwidth_text(text: str) -> str:
    """全角英数モードで text を打ったときの読みバッファを返す。

    このモードではローマ字変換が起きないので、ASCII がそのまま全角になる。
    `infty` → `ｉｎｆｔｙ`、`^2` → `＾２`。
    """
    return "".join(to_fullwidth(c) if c.isascii() else c for c in text)


def romaji_buffer(text: str, opts: dict[str, str] | None = None) -> str:
    """ひらがな入力モードで text を打ったときの読みバッファを返す。"""
    o = dict(DEFAULT_OPTS)
    if opts:
        o.update(opts)
    table, max_len = _build_table(o)

    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        low = ch.lower()

        # 英字以外（数字・記号）はそのまま
        if not (ch.isascii() and ch.isalpha()):
            out.append(ch)
            i += 1
            continue

        # ローマ字表の最長一致
        hit = None
        for length in range(min(max_len, n - i), 1, -1):
            seq = text[i:i + length].lower()
            if seq in table:
                hit = (table[seq], length)
                break
        if hit:
            out.append(hit[0])
            i += hit[1]
            continue

        # n + 子音 → ん（末尾の n をどう扱うかは揺れる）
        if low == "n":
            nxt = text[i + 1].lower() if i + 1 < n else ""
            if nxt and nxt.isalpha() and nxt not in VOWELS and nxt != "y":
                out.append("ん")
                i += 1
                continue
            if not nxt and o["n_final"] == "kana":
                out.append("ん")
                i += 1
                continue

        # 同じ子音の重なり → っ
        if (i + 1 < n and low == text[i + 1].lower()
                and low not in VOWELS and low != "n"):
            if not (o["sokuon"] == "single" and out and out[-1] == "っ"):
                out.append("っ")
            i += 1
            continue

        # 母音 1 文字
        if low in VOWELS:
            out.append(VOWEL_KANA[low])
            i += 1
            continue

        # かなにならなかった子音はそのまま残る
        out.append(to_fullwidth(ch))
        i += 1
    return "".join(out)


def romaji_variants(text: str, limit: int = 8) -> list[str]:
    """ありうる読みバッファを全部返す（先頭が既定の予測）。

    揺れる規則の組み合わせを展開し、同じ綴りになるものはまとめる。
    text に関係しない規則は結果を変えないので、ほとんどの語は 1〜2 通りで済む。
    """
    keys = list(OPTIONS)
    seen: dict[str, None] = {}
    for combo in product(*(OPTIONS[k] for k in keys)):
        opts = dict(CONFIRMED_OPTS)
        opts.update(zip(keys, combo))
        seen.setdefault(romaji_buffer(text, opts), None)
        if len(seen) >= limit:
            break
    return list(seen)


if __name__ == "__main__":
    import sys
    names = sys.argv[1:] or [
        "test", "infty", "to", "in", "int", "leq", "alpha", "beta", "sum",
        "bbr", "mathbb", "argmax", "nabla", "partial", "rightarrow",
        "subseteq", "psi", "phi", "ll", "gg", "sin", "esssup", "theta",
        "cup", "xi", "lambda", "vec", "ell",
    ]
    for name in names:
        variants = romaji_variants(name)
        print(f"{name:<12} -> {variants[0]}"
              + (f"   他: {' / '.join(variants[1:])}" if len(variants) > 1 else ""))
