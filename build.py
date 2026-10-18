#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ATOK 向け Unicode 絵文字・数学記号 辞書ビルダー。

data/*.tsv の手書きデータと、Unicode の規則から機械生成できる部分
（上付き・下付き・数学英数字記号）を合成して、ATOK の
「単語一括処理」で読み込める単語ファイルを dist/ に出力する。

    python build.py            # 既定の設定で全部ビルド
    python build.py --help     # オプション一覧

よみは既定で半角コロン ":" を前置する。通常の日本語変換を一切汚さず、
Slack/GitHub の :smile: と同じ感覚で引ける。
"""
from __future__ import annotations

import argparse
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

from romaji import fullwidth_text, pascal_text, romaji_variants

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DIST = ROOT / "dist"

# ATOK のよみに使える文字（ひらがな・半角英数・一部の半角記号）。
# 括弧やピリオド、感嘆符などは使えないため、よみの設計から外してある。
ALLOWED_SYMBOLS = set("#$%&*+-/:;<=>@_'^~`")
# ATOK のよみは全角の英数・カタカナ・一部の記号も受け付ける。ローマ字入力で
# かなにならずに残った英字（てｓｔ の ｓｔ）がここに該当する。
ALLOWED_FULLWIDTH = set("＃＄％＆＊＋－／：；＜＝＞＠￥＿・’＾～｀〜")
READING_MAX = 32   # ATOK for Windows のよみ上限
WORD_MAX = 100     # ATOK for Windows の単語上限


# --------------------------------------------------------------------------
# エントリ
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Entry:
    reading: str   # プレフィックスを含まないよみ
    word: str      # 変換後の文字列
    group: str     # "emoji" / "math"
    category: str  # 分類（master.tsv とコメント用）
    note: str = ""
    source: str = ""   # tex-symbols.tsv の出典（latex / unicode-math）
    prefixed: bool = True  # False ならプレフィックス（：）を付けずに登録する


# 収録量の段階。語数が多いと取り込みと ATOK Sync が重くなるので、
# よく使うものから順に削れるようにしてある。
LEVELS = {
    # 日常的に使う範囲。伝統的な LaTeX/AMS 名の記号だけ。
    "core": {
        "tex_sources": ("latex",),     # unicode-math 固有の異体字を落とす
        "tex_alphabet": (),            # 書体は文字そのもののよみで引く
        "function_styles": 4,          # 素のよみ it/bf/sf/tt のみ
        "function_prefixed": False,
        "digit_max": 9,                # 2 桁の上付き・下付きを作らない
    },
    # unicode-math 固有の記号も入れる。
    "standard": {
        "tex_sources": ("latex", "unicode-math"),
        "tex_alphabet": (),
        "function_styles": 4,
        "function_prefixed": True,
        "digit_max": 30,
    },
    # 関数名の書体別名も含めて全部。
    "full": {
        "tex_sources": ("latex", "unicode-math"),
        "tex_alphabet": (),
        "function_styles": None,
        "function_prefixed": True,
        "digit_max": 99,
    },
}


def normalize_reading(reading: str) -> str:
    """よみを ATOK が受け付ける形に正規化する。

    ATOK のよみは半角英字の大小を区別しないため、ASCII はすべて小文字に畳む。
    大文字・小文字の打ち分けではなく「同じよみの別候補」として出し分ける。
    """
    r = reading.strip().lower()
    # ATOK のよみに "ゔ" は使えないので "う゛" に展開する
    r = r.replace("ゔ", "う゛")
    return r


def finalize_reading(reading: str) -> str:
    """出力直前の整形。大文字小文字はそのまま残す。

    pascal モードのよみ（Infty）は大文字で始まることに意味があるので、
    normalize_reading と違って小文字化しない。
    """
    return reading.strip().replace("ゔ", "う゛")


def check(e: Entry) -> str | None:
    """ATOK の制約に反していれば理由を返す。問題なければ None。"""
    if not e.reading or not e.word:
        return "よみまたは単語が空"
    for ch in e.reading:
        if ch in ALLOWED_SYMBOLS:
            continue
        if ch.isascii() and ch.isalnum():
            continue
        if ch in ALLOWED_FULLWIDTH:
            continue
        # 全角英数・カタカナ
        if "０" <= ch <= "９" or "Ａ" <= ch <= "Ｚ"                 or "ａ" <= ch <= "ｚ" or "ァ" <= ch <= "ヿ":
            continue
        # ひらがな・長音・濁点
        if "ぁ" <= ch <= "ゟ" or ch == "ー":
            continue
        return f"よみに使えない文字 {ch!r}"
    if len(e.reading) > READING_MAX:
        return f"よみが{READING_MAX}文字超"
    if len(e.word) > WORD_MAX:
        return f"単語が{WORD_MAX}文字超"
    return None


def split_valid(entries: list[Entry]) -> tuple[list[Entry], list[tuple[Entry, str]]]:
    """ATOK に登録できるものと、できないものに分ける。

    TeX には \\^( のように括弧を含むコマンド名があり、ATOK のよみには
    使えない。そういう行は黙って落とし、dist/rejected.tsv に理由を残す。
    """
    ok: list[Entry] = []
    bad: list[tuple[Entry, str]] = []
    for e in entries:
        reason = check(e)
        if reason:
            bad.append((e, reason))
        else:
            ok.append(e)
    return ok, bad


# --------------------------------------------------------------------------
# TSV の読み込み
# --------------------------------------------------------------------------

def load_tsv(path: Path, group: str) -> list[Entry]:
    """データ TSV を読む。

    書式: よみ(カンマ区切りで複数可)<TAB>単語<TAB>分類<TAB>備考<TAB>出典
    "#" で始まる行と空行は無視する。出典は tex-symbols.tsv だけが持つ。
    """
    entries: list[Entry] = []
    if not path.exists():
        return entries
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) < 2:
            print(f"warn: {path.name}:{lineno} 列が足りません: {line!r}", file=sys.stderr)
            continue
        readings, word = cols[0], cols[1]
        category = cols[2] if len(cols) > 2 else ""
        note = cols[3] if len(cols) > 3 else ""
        source = cols[4] if len(cols) > 4 else ""
        for r in readings.split(","):
            r = normalize_reading(r)
            if r:
                entries.append(Entry(r, word, group, category, note, source))
    return entries


def filter_tex(entries: list[Entry], cfg: dict) -> list[Entry]:
    """tex-symbols.tsv の行を収録段階に応じて間引く。

    数学英数字（𝔸 𝒜 …）は自前の生成のほうがよみが整っているので、
    段階によっては TeX 表の側を落とす。
    """
    out: list[Entry] = []
    for e in entries:
        allowed = (cfg["tex_alphabet"] if e.category == "数学英数字"
                   else cfg["tex_sources"])
        if e.source in allowed:
            out.append(e)
    return out


# --------------------------------------------------------------------------
# Unicode から機械生成する部分
# --------------------------------------------------------------------------

def _lookup(*names: str) -> str | None:
    """Unicode 名で文字を引く。最初に見つかったものを返す。"""
    for name in names:
        try:
            return unicodedata.lookup(name)
        except KeyError:
            continue
    return None


DIGIT_NAMES = ["ZERO", "ONE", "TWO", "THREE", "FOUR",
               "FIVE", "SIX", "SEVEN", "EIGHT", "NINE"]


def gen_superscript(digit_max: int = 99) -> list[Entry]:
    """上付き文字。よみは "^" に続けて元の文字（例: :^2 -> ²、:^-1 -> ⁻¹）。"""
    out: list[Entry] = []

    def add(reading: str, word: str, note: str) -> None:
        out.append(Entry(f"^{reading}", word, "math", "上付き", note))

    digits = []
    for i, name in enumerate(DIGIT_NAMES):
        ch = _lookup(f"SUPERSCRIPT {name}")
        if ch:
            digits.append(ch)
            add(str(i), ch, f"上付き {i}")
    minus = _lookup("SUPERSCRIPT MINUS")
    plus = _lookup("SUPERSCRIPT PLUS SIGN")
    for reading, word, note in (
        ("+", plus, "上付き +"),
        ("-", minus, "上付き -"),
        ("=", _lookup("SUPERSCRIPT EQUALS SIGN"), "上付き ="),
        ("lparen", _lookup("SUPERSCRIPT LEFT PARENTHESIS"), "上付き ("),
        ("rparen", _lookup("SUPERSCRIPT RIGHT PARENTHESIS"), "上付き )"),
    ):
        if word:
            add(reading, word, note)

    # 2 桁の数字（:^10 .. :^99）と負の指数（:^-1 .. :^-20）
    if len(digits) == 10:
        for n in range(10, digit_max + 1):
            word = digits[n // 10] + digits[n % 10]
            add(str(n), word, f"上付き {n}")
        if minus:
            for n in list(range(1, 21)) + [100]:
                word = minus + "".join(digits[int(d)] for d in str(n))
                add(f"-{n}", word, f"上付き -{n}")
            add("-n", minus + "ⁿ", "上付き -n")
        add("100", digits[1] + digits[0] + digits[0], "上付き 100")

    # 英字（小文字・大文字の両方を同じよみの候補として登録する）
    for c in "abcdefghijklmnopqrstuvwxyz":
        lower = _lookup(f"SUPERSCRIPT LATIN SMALL LETTER {c.upper()}",
                        f"MODIFIER LETTER SMALL {c.upper()}")
        upper = _lookup(f"MODIFIER LETTER CAPITAL {c.upper()}")
        if lower:
            add(c, lower, f"上付き {c}")
        if upper:
            add(c, upper, f"上付き {c.upper()}")
    return out


def gen_subscript(digit_max: int = 99) -> list[Entry]:
    """下付き文字。よみは "_" に続けて元の文字（例: :_1 -> ₁、:_i -> ᵢ）。"""
    out: list[Entry] = []

    def add(reading: str, word: str, note: str) -> None:
        out.append(Entry(f"_{reading}", word, "math", "下付き", note))

    digits = []
    for i, name in enumerate(DIGIT_NAMES):
        ch = _lookup(f"SUBSCRIPT {name}")
        if ch:
            digits.append(ch)
            add(str(i), ch, f"下付き {i}")
    minus = _lookup("SUBSCRIPT MINUS")
    for reading, word, note in (
        ("+", _lookup("SUBSCRIPT PLUS SIGN"), "下付き +"),
        ("-", minus, "下付き -"),
        ("=", _lookup("SUBSCRIPT EQUALS SIGN"), "下付き ="),
        ("lparen", _lookup("SUBSCRIPT LEFT PARENTHESIS"), "下付き ("),
        ("rparen", _lookup("SUBSCRIPT RIGHT PARENTHESIS"), "下付き )"),
    ):
        if word:
            add(reading, word, note)

    if len(digits) == 10:
        for n in range(10, digit_max + 1):
            add(str(n), digits[n // 10] + digits[n % 10], f"下付き {n}")
        if minus:
            for n in range(1, 11):
                add(f"-{n}", minus + "".join(digits[int(d)] for d in str(n)),
                    f"下付き -{n}")

    for c in "abcdefghijklmnopqrstuvwxyz":
        ch = _lookup(f"LATIN SUBSCRIPT SMALL LETTER {c.upper()}")
        if ch:
            add(c, ch, f"下付き {c}")
    for name, reading in (("BETA", "beta"), ("GAMMA", "gamma"), ("RHO", "rho"),
                          ("PHI", "phi"), ("CHI", "chi")):
        ch = _lookup(f"GREEK SUBSCRIPT SMALL LETTER {name}")
        if ch:
            add(reading, ch, f"下付き {reading}")
    return out


GREEK = [
    # (LaTeX 名, Unicode 名, 日本語よみ)
    ("alpha", "ALPHA", "あるふぁ"),
    ("beta", "BETA", "べーた"),
    ("gamma", "GAMMA", "がんま"),
    ("delta", "DELTA", "でるた"),
    ("epsilon", "EPSILON", "いぷしろん"),
    ("zeta", "ZETA", "ぜーた"),
    ("eta", "ETA", "いーた"),
    ("theta", "THETA", "しーた"),
    ("iota", "IOTA", "いおた"),
    ("kappa", "KAPPA", "かっぱ"),
    ("lambda", "LAMDA", "らむだ"),
    ("mu", "MU", "みゅー"),
    ("nu", "NU", "にゅー"),
    ("xi", "XI", "くさい"),
    ("omicron", "OMICRON", "おみくろん"),
    ("pi", "PI", "ぱい"),
    ("rho", "RHO", "ろー"),
    ("sigma", "SIGMA", "しぐま"),
    ("tau", "TAU", "たう"),
    ("upsilon", "UPSILON", "うぷしろん"),
    ("phi", "PHI", "ふぁい"),
    ("chi", "CHI", "かい"),
    ("psi", "PSI", "ぷさい"),
    ("omega", "OMEGA", "おめが"),
]


def gen_greek() -> list[Entry]:
    """ギリシャ文字。小文字・大文字を同じよみの候補として並べる。"""
    out: list[Entry] = []
    for latex, uname, kana in GREEK:
        lower = _lookup(f"GREEK SMALL LETTER {uname}")
        upper = _lookup(f"GREEK CAPITAL LETTER {uname}")
        for reading in (latex, kana):
            if lower:
                out.append(Entry(reading, lower, "math", "ギリシャ文字",
                                 f"小文字 {latex}"))
            if upper:
                out.append(Entry(reading, upper, "math", "ギリシャ文字",
                                 f"大文字 {latex}"))
    # 異体字
    for latex, uname, note in (
        ("varepsilon", "GREEK LUNATE EPSILON SYMBOL", "異体 epsilon"),
        ("vartheta", "GREEK THETA SYMBOL", "異体 theta"),
        ("varphi", "GREEK PHI SYMBOL", "異体 phi"),
        ("varpi", "GREEK PI SYMBOL", "異体 pi"),
        ("varrho", "GREEK RHO SYMBOL", "異体 rho"),
        ("varsigma", "GREEK SMALL LETTER FINAL SIGMA", "語末 sigma"),
        ("varkappa", "GREEK KAPPA SYMBOL", "異体 kappa"),
        ("digamma", "GREEK SMALL LETTER DIGAMMA", "digamma"),
        ("nabla", "NABLA", "ナブラ"),
    ):
        ch = _lookup(uname)
        if ch:
            out.append(Entry(latex, ch, "math", "ギリシャ文字", note))
    return out


# 数学英数字記号のスタイル（Unicode の 13 書体すべて）。
#   prefixes   : よみに使う接頭辞。LaTeX の \mathbb、unicode-math の \Bbb、
#                Julia REPL の \bb のように流儀が分かれるので全部受ける。
#   unicode    : Unicode 名に現れるスタイル名
#   letterlike : 穴あき部分を埋める Letterlike Symbols 側のスタイル名
#   kana       : 日本語よみの接頭辞（大文字だけに張る）
#   label      : 分類に出す名前
STYLES = [
    (["bb", "mathbb", "Bbb"],
     "DOUBLE-STRUCK", "DOUBLE-STRUCK", ["くろばんふとじ", "にじゅうせん"], "mathbb"),
    (["cal", "mathcal", "scr", "mathscr", "mscr"],
     "SCRIPT", "SCRIPT", ["すくりぷと", "ひっきたい"], "mathcal"),
    (["bfcal", "mathbfcal", "bscr", "mathbfscr", "mbfscr"],
     "BOLD SCRIPT", None, [], "mathbfcal"),
    (["frak", "mathfrak", "mfrak"],
     "FRAKTUR", "BLACK-LETTER", ["ふらくとぅーる", "ひげもじ"], "mathfrak"),
    (["bffrak", "mathbffrak", "bfrak", "mbffrak"],
     "BOLD FRAKTUR", None, [], "mathbffrak"),
    (["bf", "mathbf", "mbf"],
     "BOLD", None, ["すうがくふとじ"], "mathbf"),
    (["it", "mathit", "mit"],
     "ITALIC", None, ["すうがくしゃたい"], "mathit"),
    (["bfit", "mathbfit", "bi", "mbfit"],
     "BOLD ITALIC", None, [], "mathbfit"),
    (["sf", "mathsf", "sans", "msans"],
     "SANS-SERIF", None, ["さんせりふ"], "mathsf"),
    (["sfbf", "mathsfbf", "bsans", "mbfsans"],
     "SANS-SERIF BOLD", None, [], "mathsfbf"),
    (["sfit", "mathsfit", "isans", "mitsans"],
     "SANS-SERIF ITALIC", None, [], "mathsfit"),
    (["sfbfit", "mathsfbfit", "bisans", "mbfitsans"],
     "SANS-SERIF BOLD ITALIC", None, [], "mathsfbfit"),
    (["tt", "mathtt", "mtt"],
     "MONOSPACE", None, ["とうはばもじ"], "mathtt"),
]

# 数学英数字記号ブロックにある、ギリシャ文字の異体字と記号。
# 太字・斜体などの書体ごとに別の符号位置が用意されている。
GREEK_VARIANTS = [
    ("varepsilon", "EPSILON SYMBOL"),
    ("vartheta", "THETA SYMBOL"),
    ("varkappa", "KAPPA SYMBOL"),
    ("varphi", "PHI SYMBOL"),
    ("varrho", "RHO SYMBOL"),
    ("varpi", "PI SYMBOL"),
    ("nabla", "NABLA"),
    ("partial", "PARTIAL DIFFERENTIAL"),
]

# 数学英数字記号ブロックの穴を埋める特例
MATH_HOLES = {
    ("ITALIC", "SMALL", "H"): "PLANCK CONSTANT",  # ℎ
}


def _math_letter(style: str, letterlike: str | None, case: str, letter: str) -> str | None:
    names = [f"MATHEMATICAL {style} {case} {letter}"]
    if letterlike:
        names.append(f"{letterlike} {case} {letter}")
    special = MATH_HOLES.get((style, case, letter))
    if special:
        names.append(special)
    return _lookup(*names)


def gen_math_alphabet(cfg: dict | None = None) -> list[Entry]:
    """数学英数字記号（𝔸 ℝ 𝒜 𝔄 𝐀 𝐴 …）。

    よみは元の文字そのものにします。書体は覚えるものではなく選ぶものと考えて、
    13 書体ぶんを同じよみの候補として並べます。

      :B      -> 𝔹 ℬ 𝔅 𝐁 𝐵 𝑩 𝖡 𝗕 𝘉 𝘽 𝙱 …（小文字も同じよみ）
      :1      -> 𝟙 𝟏 𝟣 𝟭 𝟷
      :Alpha  -> α Α 𝛂 𝚨 𝛼 𝛢 …
    """
    out: list[Entry] = []
    for _prefixes, uname, letterlike, _kanas, latex in STYLES:
        for c in "abcdefghijklmnopqrstuvwxyz":
            upper = _math_letter(uname, letterlike, "CAPITAL LETTER", c.upper()) \
                or _math_letter(uname, letterlike, "CAPITAL", c.upper())
            lower = _math_letter(uname, letterlike, "SMALL LETTER", c.upper()) \
                or _math_letter(uname, letterlike, "SMALL", c.upper())
            if upper:
                out.append(Entry(c, upper, "math", "数学英数字",
                                 f"{latex} 大文字 {c.upper()}"))
            if lower:
                out.append(Entry(c, lower, "math", "数学英数字",
                                 f"{latex} 小文字 {c}"))
        # 数字（存在する書体だけ）
        for i, dname in enumerate(DIGIT_NAMES):
            ch = _lookup(f"MATHEMATICAL {uname} DIGIT {dname}")
            if ch:
                out.append(Entry(str(i), ch, "math", "数学英数字",
                                 f"{latex} 数字 {i}"))
        # ギリシャ文字（太字・斜体などに存在する）
        for glatex, gname, _gkana in GREEK:
            upper = _lookup(f"MATHEMATICAL {uname} CAPITAL {gname}")
            lower = _lookup(f"MATHEMATICAL {uname} SMALL {gname}")
            if upper:
                out.append(Entry(glatex, upper, "math", "数学英数字",
                                 f"{latex} 大文字 {glatex}"))
            if lower:
                out.append(Entry(glatex, lower, "math", "数学英数字",
                                 f"{latex} 小文字 {glatex}"))
        # ギリシャ文字の異体字と、太字などが用意されている ∇ ∂
        for vlatex, vname in GREEK_VARIANTS:
            ch = _lookup(f"MATHEMATICAL {uname} {vname}")
            if ch:
                out.append(Entry(vlatex, ch, "math", "数学英数字",
                                 f"{latex} {vlatex}"))
    return out


# アクセント付きラテン文字のよみ。HTML の文字実体参照と同じ
# <元の文字><アクセント名> の形にしてある（é = eacute、ñ = ntilde）。
ACCENTS = [
    ("acute", "ACUTE"),
    ("grave", "GRAVE"),
    ("circ", "CIRCUMFLEX"),
    ("uml", "DIAERESIS"),
    ("tilde", "TILDE"),
    ("macr", "MACRON"),
    ("breve", "BREVE"),
    ("caron", "CARON"),
    ("ring", "RING ABOVE"),
    ("dot", "DOT ABOVE"),
    ("cedil", "CEDILLA"),
    ("ogon", "OGONEK"),
    ("strok", "STROKE"),
    ("dblac", "DOUBLE ACUTE"),
    ("horn", "HORN"),
    ("hook", "HOOK ABOVE"),
    ("dotb", "DOT BELOW"),
]

# 合字や特殊な字。関係の深い文字のよみに入れる。
ACCENT_SPECIALS = [
    ("a", "LATIN SMALL LETTER AE", "LATIN CAPITAL LETTER AE"),
    ("o", "LATIN SMALL LIGATURE OE", "LATIN CAPITAL LIGATURE OE"),
    ("s", "LATIN SMALL LETTER SHARP S", None),
    ("d", "LATIN SMALL LETTER ETH", "LATIN CAPITAL LETTER ETH"),
    ("t", "LATIN SMALL LETTER THORN", "LATIN CAPITAL LETTER THORN"),
    ("i", "LATIN SMALL LETTER DOTLESS I", None),
    ("n", "LATIN SMALL LETTER ENG", "LATIN CAPITAL LETTER ENG"),
    ("e", "LATIN SMALL LETTER SCHWA", "LATIN CAPITAL LETTER SCHWA"),
]


def gen_accents() -> list[Entry]:
    """アクセント付きのラテン文字（é è ê ë ñ ü å ø ç …）。

    よみは元の文字そのものにします。アクセントの名前は覚えるものではなく、
    その文字のアクセント付きを候補として並べます。

      :E -> È É Ê Ë Ē Ĕ Ė Ę Ě …（小文字も同じよみ）
    """
    out: list[Entry] = []
    for c in "abcdefghijklmnopqrstuvwxyz":
        for key, uname in ACCENTS:
            lower = _lookup(f"LATIN SMALL LETTER {c.upper()} WITH {uname}")
            upper = _lookup(f"LATIN CAPITAL LETTER {c.upper()} WITH {uname}")
            for word, label in ((upper, "大文字"), (lower, "小文字")):
                if word:
                    out.append(Entry(c, word, "math", "アクセント付き文字",
                                     f"{label} {c} + {key}"))
    # 合字や特殊な字も、関係の深い文字のよみに入れる（æ は a、ß は s …）
    for base, lname, uname in ACCENT_SPECIALS:
        for name, label in ((uname, "大文字"), (lname, "小文字")):
            word = _lookup(name) if name else None
            if word:
                out.append(Entry(base, word, "math", "アクセント付き文字",
                                 f"{label} {name.lower()}"))
    return out


# 数学の関数名・作用素名。数学フォントで組んだ形を候補に出す。
# LaTeX の log 型関数（\sin \lim \det …）と、\operatorname で書く慣用のもの
# （argmax \DeclareMathOperator*、Aut、esssup、softmax など）をまとめてある。
FUNCTION_NAMES = [
    # 三角・双曲線（LaTeX 標準）
    "sin", "cos", "tan", "sec", "csc", "cot",
    "sinh", "cosh", "tanh", "coth", "sech", "csch", "cosec",
    "arcsin", "arccos", "arctan", "arcsec", "arccsc", "arccot",
    "arsinh", "arcosh", "artanh", "arcsinh", "arccosh", "arctanh",
    "atan2", "sinc", "cis",
    # 指数・対数（LaTeX 標準）
    "exp", "log", "ln", "lg",
    # 極限・上限下限（LaTeX 標準）
    "lim", "limsup", "liminf", "sup", "inf", "max", "min",
    "injlim", "projlim", "esssup", "essinf", "lub", "glb", "plim",
    "argmax", "argmin", "arg",
    # 線形代数・代数（LaTeX 標準 + \operatorname）
    "det", "dim", "rank", "tr", "trace", "ker", "coker", "im", "re",
    "span", "diag", "adj", "cof", "nullity", "proj",
    "aut", "end", "hom", "gal", "spec", "ext", "tor", "char", "ord",
    "id", "sgn", "sign", "res", "deg", "gcd", "lcm", "mod", "bmod", "pmod",
    # 解析・幾何
    "grad", "div", "curl", "lap", "supp", "vol", "diam", "dist", "area",
    "conv", "aff", "cone", "relint", "cl", "bd", "erf", "erfc",
    "dom", "cod", "ran", "rng",
    # 確率・統計・機械学習
    "pr", "var", "cov", "corr", "mean", "median", "mode", "sd",
    "softmax", "logsumexp", "sigmoid", "relu", "mse", "mae", "kl",
]

# TeX が細空き（\,）を入れて組む複合作用素。"arg max" の形も候補に出す。
MULTIWORD = {
    "argmax": "arg max",
    "argmin": "arg min",
    "limsup": "lim sup",
    "liminf": "lim inf",
    "injlim": "inj lim",
    "projlim": "proj lim",
    "esssup": "ess sup",
    "essinf": "ess inf",
}
THIN_SPACE = " "

# 関数名に使うスタイル（よみの接頭辞, Unicode スタイル名）
FUNCTION_STYLES = [
    (["it", "mathit"], "ITALIC"),
    (["bf", "mathbf"], "BOLD"),
    (["sf", "mathsf", "sans"], "SANS-SERIF"),
    (["tt", "mathtt"], "MONOSPACE"),
    (["bb", "mathbb"], "DOUBLE-STRUCK"),
    (["frak", "mathfrak"], "FRAKTUR"),
    (["cal", "mathcal", "scr"], "SCRIPT"),
]

# 素のよみ（:sin）でも候補に出すスタイル
BARE_FUNCTION_STYLES = {"it", "bf", "sf", "tt"}


def _to_math_font(text: str, uname: str, letterlike: str | None) -> str | None:
    """ASCII 文字列をまるごと数学フォントの文字列に変換する。"""
    out = []
    for ch in text:
        if ch.isalpha():
            case = "CAPITAL LETTER" if ch.isupper() else "SMALL LETTER"
            m = _math_letter(uname, letterlike, case, ch.upper()) \
                or _math_letter(uname, letterlike,
                                "CAPITAL" if ch.isupper() else "SMALL", ch.upper())
        elif ch.isdigit():
            m = _lookup(f"MATHEMATICAL {uname} DIGIT {DIGIT_NAMES[int(ch)]}")
        else:
            m = ch
        if m is None:
            return None
        out.append(m)
    return "".join(out)


def gen_math_functions(cfg: dict | None = None) -> list[Entry]:
    """sin / cos / log などの関数名を数学フォントで組んだもの。

      :sin   -> 𝑠𝑖𝑛（斜体）, 𝐬𝐢𝐧（太字）, 𝗌𝗂𝗇（サンセリフ）, 𝚜𝚒𝚗（等幅）
      :itsin -> 𝑠𝑖𝑛 だけ
    """
    out: list[Entry] = []
    cfg = cfg or LEVELS["full"]
    letterlike = {"DOUBLE-STRUCK": "DOUBLE-STRUCK", "FRAKTUR": "BLACK-LETTER",
                  "SCRIPT": "SCRIPT"}
    styles = FUNCTION_STYLES[:cfg["function_styles"]] if cfg["function_styles"] \
        else FUNCTION_STYLES
    for name in FUNCTION_NAMES:
        for prefixes, uname in styles:
            word = _to_math_font(name, uname, letterlike.get(uname))
            if not word:
                continue
            if cfg["function_prefixed"]:
                for p in prefixes:
                    out.append(Entry(f"{p}{name}", word, "math", "関数名",
                                     f"{name} ({prefixes[0]})"))
            # 素のよみでも主要スタイルを候補に出す
            if prefixes[0] in BARE_FUNCTION_STYLES:
                out.append(Entry(name, word, "math", "関数名",
                                 f"{name} ({prefixes[0]})"))
        # TeX が "arg max" のように細空きで組むものは、その形も斜体で用意する
        spaced = MULTIWORD.get(name)
        if spaced:
            word = _to_math_font(spaced.replace(" ", THIN_SPACE), "ITALIC", None)
            if word:
                out.append(Entry(name, word, "math", "関数名",
                                 f"{spaced} (it・細空き)"))
                if cfg["function_prefixed"]:
                    out.append(Entry(f"it{name}", word, "math", "関数名",
                                     f"{spaced} (it・細空き)"))
    return out


# --------------------------------------------------------------------------
# 出力
# --------------------------------------------------------------------------

ATOK_HEADER = "!!ATOK_TANGO_TEXT_HEADER_1"


def dedupe_sort(entries: list[Entry]) -> list[Entry]:
    seen: set[tuple[bool, str, str]] = set()
    out: list[Entry] = []
    for e in sorted(entries, key=lambda e: (e.reading, e.word)):
        key = (e.prefixed, e.reading, e.word)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def write_atok(entries: list[Entry], path: Path, *, prefix: str, pos: str,
               header: bool, encoding: str) -> None:
    """ATOK の単語一括処理で読み込める単語ファイルを書き出す。

    既定は UTF-16LE(BOM 付き) / 改行 CR+LF。ATOK のユーザー辞書テキストは
    Unicode(UTF-16) と案内されており、絵文字などの BMP 外の文字を通すには
    この組み合わせが必要になる。
    """
    lines: list[str] = []
    if header:
        lines.append(ATOK_HEADER)
        lines.append("!!")
    for e in entries:
        p = prefix if e.prefixed else ""
        lines.append(f"{p}{e.reading}\t{e.word}\t{pos}\t")
    text = "\r\n".join(lines) + "\r\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    if encoding == "utf-16":
        path.write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    elif encoding == "utf-8-sig":
        path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    else:
        path.write_bytes(text.encode(encoding))


def write_master(entries: list[Entry], path: Path, prefix: str) -> None:
    """人間が読む・差分を見るための一覧（UTF-8）。"""
    lines = ["# よみ\t単語\t分類\t備考"]
    for e in entries:
        p = prefix if e.prefixed else ""
        lines.append(f"{p}{e.reading}\t{e.word}\t{e.category}\t{e.note}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_probe(path: Path, prefix: str, encoding: str) -> None:
    """ATOK が何を受け付けるかを切り分けるための小さな試験用ファイル。

    どの行が登録に失敗したかを ATOK の出力ファイルで確認すると、
    よみに使える文字・品詞名・サロゲートペアの可否が分かる。
    """
    rows = [
        # (よみ, 単語, 品詞, 何を試しているか)
        (f"{prefix}てすと1", "α", "顔文字*", "BMP内の記号 / 品詞 顔文字*"),
        (f"{prefix}てすと2", "α", "顔文字", "品詞名に * を付けない場合"),
        (f"{prefix}てすと3", "α", "記号", "品詞 記号"),
        (f"{prefix}てすと4", "α", "名詞", "品詞 名詞"),
        (f"{prefix}てすと5", "α", "短縮読み", "品詞 短縮読み（公式表記）"),
        (f"{prefix}てすと6", "😀", "顔文字*", "サロゲートペア(絵文字)"),
        (f"{prefix}てすと7", "❤️", "顔文字*", "異体字セレクタ付き絵文字"),
        (f"{prefix}てすと8", "𝑠𝑖𝑛", "顔文字*", "複数文字の数学フォント"),
        (f"{prefix}てすと9", "ℝ", "顔文字*", "BMP内の数学記号"),
        ("てすと10", "α", "顔文字*", "プレフィックスなしのよみ"),
        (f"{prefix}test11", "α", "顔文字*", "半角英字のよみ"),
        (f"{prefix}^2", "²", "顔文字*", "よみに ^ を含む"),
        (f"{prefix}_2", "₂", "顔文字*", "よみに _ を含む"),
        (f"{prefix}test-14", "α", "顔文字*", "よみに - を含む"),
        # ATOK は品詞名の代わりに品詞番号も受け付ける（顔文字=70、短縮読み=74）
        (f"{prefix}てすと15", "α", "70", "品詞番号 70 (顔文字)"),
        (f"{prefix}てすと16", "α", "74", "品詞番号 74 (短縮読み)"),
    ]
    lines = [ATOK_HEADER, "!!", "!! 動作確認用。登録できた行・できなかった行を確認する。"]
    for reading, word, pos, why in rows:
        lines.append(f"!! {why}")
        lines.append(f"{reading}\t{word}\t{pos}\t")
    text = "\r\n".join(lines) + "\r\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if encoding == "utf-16":
        path.write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    else:
        path.write_bytes(text.encode(encoding))


def write_probe2(path: Path, pos: str, encoding: str) -> None:
    """半角英字のよみが「かな入力のまま打てるか」を切り分ける試験用ファイル。

    TeX 名のよみ（:infty、:bbr …）は半角英字なので、ひらがな入力モードで
    そのまま打てるかどうかが生死を分ける。ローマ字入力では "test" が
    「てｓｔ」のように化けるため、同じ単語を綴り違いで登録しておき、
    実際に ":test" と打って**どのギリシャ文字が出たか**で、ATOK の読みバッファが
    どの綴りになっているかを特定する。
    """
    full = str.maketrans({chr(c): chr(c - 0x20 + 0xFF00) for c in range(0x21, 0x7F)})
    rows = [
        # (よみ, 単語, 何を試しているか)
        (":ぷろーぶ", "α", "半角コロン + ひらがな"),
        ("：ぷろーぶ", "β", "全角コロン + ひらがな"),
        (":test", "γ", "半角コロン + 半角英字"),
        (":" + "test".translate(full), "δ", "半角コロン + 全角英字"),
        ("：test", "ε", "全角コロン + 半角英字"),
        ("：" + "test".translate(full), "ζ", "全角コロン + 全角英字"),
        (":て" + "st", "η", "半角コロン + かな + 半角英字"),
        (":て" + "st".translate(full), "θ", "半角コロン + かな + 全角英字"),
        ("：て" + "st".translate(full), "ι", "全角コロン + かな + 全角英字"),
    ]
    lines = [
        ATOK_HEADER, "!!",
        "!! 英字よみの綴り判定用。",
        "!! 使い方: 取り込んだあと、ひらがな入力のまま ':test' と打って変換する。",
        "!!         出てきたギリシャ文字が、ATOK が実際に見ているよみを示す。",
        "!!         α/β が出たら かなよみは問題なし、γ〜ζ なら英字よみがそのまま使える、",
        "!!         η〜ι なら英字が化けている（TeX 名のよみは打てない）。",
    ]
    for reading, word, why in rows:
        lines.append(f"!! {word} = {why}")
        lines.append(f"{reading}\t{word}\t{pos}\t")
    text = "\r\n".join(lines) + "\r\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if encoding == "utf-16":
        path.write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    else:
        path.write_bytes(text.encode(encoding))


# --------------------------------------------------------------------------

def write_probe5(path: Path, prefix: str, pos: str, encoding: str) -> None:
    """大文字始まりのよみが、英字のまま変換できるかを確かめる。

    ATOK のひらがな入力は、大文字から始まる綴りをローマ字変換しない
    （zenn.dev/amane の記事による）。これが成り立つなら、TeX 名をそのまま
    よみにできて、ローマ字変換の再現もモード切替も要らなくなる。

    同じ打鍵に別の記号を割り当ててあるので、何が出たかで綴りが分かる。
    """
    rows = [
        # (よみ, 単語, 何を試しているか)
        (f"{prefix}Infty", "∞", "全角コロン + 大文字始まり"),
        (f"{prefix}infty", "∝", "全角コロン + 小文字（ローマ字変換される想定）"),
        ("Infty", "ℵ", "プレフィックスなし + 大文字始まり"),
        ("INFTY", "ℶ", "全部大文字"),
        (f"{prefix}_I", "ᵢ", "記号のあとの大文字"),
        (f"{prefix}Bbr", "ℝ", "書体のよみ（大文字始まり）"),
    ]
    lines = [
        ATOK_HEADER, "!!",
        "!! 大文字始まりのよみの判定用。ひらがな入力のまま次を打って変換する。",
        "!!   :Infty  -> ∞ なら 全角コロン + 大文字始まり が有効",
        "!!            -> ∝ なら 小文字のよみに一致している（大小を区別しない）",
        "!!   Infty   -> ℵ ならプレフィックス無しでも引ける",
        "!!   INFTY   -> ℶ なら全部大文字でも引ける",
        "!!   :_I     -> ᵢ なら記号 + 大文字の組み合わせも使える",
        "!!   :Bbr    -> ℝ なら書体のよみもこの方式でいける",
    ]
    for reading, word, why in rows:
        lines.append(f"!! {why}")
        lines.append(f"{reading}\t{word}\t{pos}\t")
    text = "\r\n".join(lines) + "\r\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if encoding == "utf-16":
        path.write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    else:
        path.write_bytes(text.encode(encoding))


def write_probe4(path: Path, prefix: str, pos: str, encoding: str) -> None:
    """ATOK が変換に使うのは「かなのよみ」か「全角英数のよみ」かを確定させる。

    同じ打鍵に対して、かな側のよみと全角英数側のよみに**別の記号**を割り当てて
    おき、どちらが出るかで判別する。入力モードを変えて 2 回試すと、
    モードによって読みが変わるのかどうかも分かる。
    """
    cases = [
        # (TeX 名, かなのよみに割り当てる記号, 全角英数のよみに割り当てる記号)
        ("infty", "∞", "∝"),
        ("bbr", "ℝ", "ℚ"),
        ("sum", "∑", "∏"),
    ]
    lines = [
        ATOK_HEADER, "!!",
        "!! どちらのよみが使われるかの判別用。",
        "!! 使い方: :infty :bbr :sum を、ひらがなモードと全角英数モードの両方で打つ。",
        "!!   ∞ ℝ ∑ が出た → かなのよみ（--reading kana）が使われている",
        "!!   ∝ ℚ ∏ が出た → 全角英数のよみ（--reading zenkaku）が使われている",
        "!!   何も出ない   → どちらのよみも一致していない",
    ]
    for name, kana_word, zen_word in cases:
        kana_reading = normalize_reading(romaji_variants(name)[0])
        zen_reading = normalize_reading(fullwidth_text(name))
        lines.append(f"!! {prefix}{name}: かな {prefix}{kana_reading} -> {kana_word}")
        lines.append(f"{prefix}{kana_reading}\t{kana_word}\t{pos}\t")
        lines.append(f"!! {prefix}{name}: 全角 {prefix}{zen_reading} -> {zen_word}")
        lines.append(f"{prefix}{zen_reading}\t{zen_word}\t{pos}\t")
    text = "\r\n".join(lines) + "\r\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if encoding == "utf-16":
        path.write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    else:
        path.write_bytes(text.encode(encoding))


def write_probe3(path: Path, prefix: str, pos: str, encoding: str) -> None:
    """TeX 名のよみが「打った綴り」で一致するかを確かめる試験用ファイル。

    romaji.py が予測した綴りで登録してある。ひらがな入力のまま
    `:infty` のように TeX 名を打って、記号に変換できるかを見る。
    外れた行は、画面に出たよみの綴りを教えてもらえれば表を直せる。
    """
    # (TeX 名, 記号, 何の綴りを試しているか)
    cases = [
        ("infty", "∞", "n+子音、残る子音 fty"),
        ("int", "∫", "n+子音、末尾の t"),
        ("to", "→", "きれいにかなになる例"),
        ("in", "∈", "母音+n"),
        ("sum", "∑", "su+残る m"),
        ("sin", "𝑠𝑖𝑛", "全部かなになる例"),
        ("leq", "≤", "l の扱い（ぇ か れ か）"),
        ("lambda", "λ", "la の扱い"),
        ("alpha", "α", "al、ph の扱い"),
        ("phi", "φ", "ph の扱い"),
        ("psi", "ψ", "ps の扱い"),
        ("xi", "ξ", "x の扱い"),
        ("chi", "χ", "ch の扱い"),
        ("theta", "θ", "th の扱い"),
        ("cup", "∪", "c の扱い"),
        ("ll", "≪", "同じ子音の重なり"),
        ("nabla", "∇", "na+bl"),
        ("partial", "∂", "長めの混在"),
        ("rightarrow", "⟶", "最も長い例"),
        ("bbr", "ℝ", "書体のよみ bb+r"),
        ("mathbb", "𝔸", "書体のよみ mathbb"),
        ("argmax", "𝑎𝑟𝑔𝑚𝑎𝑥", "関数名"),
        ("_i", "ᵢ", "下付き（_ + 母音）"),
        ("^2", "²", "上付き（記号 + 数字）"),
    ]
    lines = [
        ATOK_HEADER, "!!",
        "!! TeX 名のよみの綴り判定用。",
        "!! 使い方: 取り込んだあと、ひらがな入力のまま下の TeX 名を",
        "!!         プレフィックス付きで打って変換する（例: :infty）。",
        "!!         変換できた名前と、できなかった名前を教えてほしい。",
        "!!         できなかったものは、画面に出たよみの綴りも知りたい。",
    ]
    for name, word, why in cases:
        typed = normalize_reading(romaji_variants(name)[0])
        lines.append(f"!! {prefix}{name} -> 予測よみ {prefix}{typed} / {why}")
        lines.append(f"{prefix}{typed}\t{word}\t{pos}\t")
    text = "\r\n".join(lines) + "\r\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if encoding == "utf-16":
        path.write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    else:
        path.write_bytes(text.encode(encoding))


READING_MODES = ("pascal", "kana", "zenkaku", "ascii")


def expand_readings(entries: list[Entry], modes: list[str]) -> list[Entry]:
    """よみを「その入力モードで実際に打てる綴り」に変換する。

    同じ `infty` という打鍵でも、ATOK の読みバッファは入力モードで変わる。

      pascal  : 全角ひらがな入力で大文字始まり → `Infty`（英字のまま残る）
      kana    : 全角ひらがな入力で小文字始まり → `いんｆｔｙ`（ローマ字変換が起きる）
      zenkaku : 全角英数入力                   → `ｉｎｆｔｙ`
      ascii   : 半角英数入力                   → `infty`（ATOK では変換できない）

    複数指定すると、どの打ち方でも引けるように全部登録する。
    """
    out: list[Entry] = []
    for e in entries:
        if not any(c.isascii() for c in e.reading):
            out.append(e)
            continue
        variants: list[str] = []
        if "pascal" in modes:
            variants.append(pascal_text(e.reading))
        if "kana" in modes:
            if any(c.isascii() and c.isalpha() for c in e.reading):
                # まだ確かめていないローマ字規則の分も、ありうる綴りを全部登録する
                variants += romaji_variants(e.reading)
            else:
                variants.append(e.reading)
        # 全角英数モードで打てるのは ASCII だけのよみに限られる
        if "zenkaku" in modes and all(c.isascii() for c in e.reading):
            variants.append(fullwidth_text(e.reading))
        if "ascii" in modes:
            variants.append(e.reading)
        # どのモードでも綴りが作れなかったもの（かな + 数字のよみを
        # zenkaku だけで作ろうとした場合など）は、そのまま残す
        if not variants:
            variants.append(e.reading)
        for variant in dict.fromkeys(variants):
            reading = finalize_reading(variant)
            if reading:
                out.append(Entry(reading, e.word, e.group, e.category,
                                 e.note, e.source, e.prefixed))
    return out


def collect(cfg: dict) -> tuple[list[Entry], list[Entry]]:
    emoji = load_tsv(DATA / "emoji.tsv", "emoji")

    math: list[Entry] = []
    math += load_tsv(DATA / "symbols.tsv", "math")
    math += filter_tex(load_tsv(DATA / "tex-symbols.tsv", "math"), cfg)
    math += gen_greek()
    math += gen_superscript(cfg["digit_max"])
    math += gen_subscript(cfg["digit_max"])
    math += gen_math_alphabet(cfg)
    math += gen_math_functions(cfg)
    math += gen_accents()
    return dedupe_sort(emoji), dedupe_sort(math)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ATOK 用 Unicode 辞書を生成する")
    p.add_argument("--prefix", default="：",
                   help="よみの先頭に付ける印（既定: 全角コロン '：'。"
                        "ひらがな入力でコロンキーを押すと全角になるため）")
    p.add_argument("--reading", default="pascal",
                   help="どの入力モードから引けるようにするか。カンマ区切りで"
                        "kana（全角ひらがな入力）/ zenkaku（全角英数入力）/"
                        " ascii（半角英数入力。ATOK では変換できない）。"
                        "既定: pascal")
    p.add_argument("--level", default="core", choices=list(LEVELS),
                   help="収録量。core=日常的に使う範囲（既定）、"
                        "standard=unicode-math 固有の記号と 13 書体も入れる、"
                        "full=別名も全部")
    p.add_argument("--pos", default="顔文字",
                   help="品詞名、または品詞番号（既定: '顔文字'。"
                        "顔文字=70、短縮読み=74、単漢字=41、独立語=18）")
    p.add_argument("--no-header", action="store_true",
                   help="先頭の !!ATOK_TANGO_TEXT_HEADER_1 を出力しない")
    p.add_argument("--encoding", default="utf-16",
                   choices=["utf-16", "utf-8", "utf-8-sig", "cp932"],
                   help="出力の文字コード（既定: utf-16 = UTF-16LE + BOM）")
    p.add_argument("--out", default=str(DIST), help="出力先ディレクトリ")
    args = p.parse_args(argv)

    out_dir = Path(args.out)
    emoji, math = collect(LEVELS[args.level])
    modes = [m.strip() for m in args.reading.split(",") if m.strip()]
    unknown = [m for m in modes if m not in READING_MODES]
    if unknown or not modes:
        p.error(f"--reading に使えるのは {READING_MODES} です: {args.reading}")
    emoji = dedupe_sort(expand_readings(emoji, modes))
    math = dedupe_sort(expand_readings(math, modes))
    emoji, bad_emoji = split_valid(emoji)
    math, bad_math = split_valid(math)
    bad = bad_emoji + bad_math
    allv = dedupe_sort(emoji + math)

    common = dict(prefix=args.prefix, pos=args.pos,
                  header=not args.no_header, encoding=args.encoding)
    write_atok(emoji, out_dir / "atok-emoji.txt", **common)
    write_atok(math, out_dir / "atok-math.txt", **common)
    write_atok(allv, out_dir / "atok-all.txt", **common)
    write_probe(out_dir / "atok-probe.txt", args.prefix, args.encoding)
    write_probe2(out_dir / "atok-probe2.txt", args.pos, args.encoding)
    write_probe3(out_dir / "atok-probe3.txt", args.prefix, args.pos, args.encoding)
    write_probe4(out_dir / "atok-probe4.txt", args.prefix, args.pos, args.encoding)
    write_probe5(out_dir / "atok-probe5.txt", args.prefix, args.pos, args.encoding)
    write_master(allv, out_dir / "master.tsv", args.prefix)

    if bad:
        lines = ["# ATOK に登録できず除外したもの", "# よみ\t単語\t理由"]
        for e, reason in sorted(bad, key=lambda x: x[0].reading):
            lines.append(f"{e.reading}\t{e.word}\t{reason}")
        (out_dir / "rejected.tsv").write_text("\n".join(lines) + "\n",
                                              encoding="utf-8")

    # よみ 1 つあたりの候補数の分布（多すぎると変換時に邪魔になる）
    per_reading = Counter(e.reading for e in allv)
    dist = Counter(per_reading.values())
    spread = " ".join(f"{n}個:{c}" for n, c in sorted(dist.items()))

    print(f"絵文字   : {len(emoji):>6} 語")
    print(f"数学記号 : {len(math):>6} 語")
    print(f"合計     : {len(allv):>6} 語  (よみ {len(per_reading)} 種)")
    print(f"候補数   : {spread}")
    print(f"多い順   : " + ", ".join(
        f"{args.prefix}{r}={n}" for r, n in per_reading.most_common(6)))
    if bad:
        reasons = Counter(r for _, r in bad)
        print(f"除外     : {len(bad)} 語 ({dict(reasons)})"
              f" -> {out_dir / 'rejected.tsv'}")
    print(f"出力先   : {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
