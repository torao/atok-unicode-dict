#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TeX コマンド名 → Unicode の対応表を data/tex-symbols.tsv に変換する。

入力（vendor/ に置く。どちらか一方でも動く）:

  latex_symbols.jl        Julia REPL の LaTeX タブ補完テーブル（MIT）
                          https://github.com/JuliaLang/julia
                          → \\alpha \\leq \\to \\bbR \\^2 \\_i など、
                            実際に TeX で打つ伝統的なコマンド名。
  unicode-math-table.tex  unicode-math パッケージの記号表（LPPL 1.3c）
                          https://github.com/wspr/unicode-math
                          → \\leqslant \\mscrA \\BbbR など unicode-math の名前。

使い方（ダウンロードしたファイルは引数で渡す）:

  python -I tools/gen_tex_symbols.py vendor/latex_symbols.jl \\
      vendor/unicode-math-table.tex -o data/tex-symbols.tsv
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

# unicode-math の数学英数字記号の命名。これらは build.py が
# :bb / :cal / :frak … のよみで生成するが、TeX の名前でも引けるよう残す。
UM_ALPHABET_RE = re.compile(
    r"^(mup|mbfit|mbfscr|mbffrak|mbfsans|mbfitsans|mitsans|mbf|mit|mscr|"
    r"mfrak|msans|mtt|Bbbi|Bbb)[A-Za-z]"
)

# unicode-math の数式クラス → 分類名
UM_CLASS = {
    "mathord": "記号",
    "mathalpha": "文字",
    "mathrel": "関係子",
    "mathbin": "演算子",
    "mathop": "大型演算子",
    "mathopen": "括弧",
    "mathclose": "括弧",
    "mathfence": "括弧",
    "mathpunct": "区切り",
    "mathaccent": "アクセント",
    "mathaccentwide": "アクセント",
    "mathaccentoverlay": "アクセント",
    "mathbotaccent": "アクセント",
    "mathover": "アクセント",
    "mathunder": "アクセント",
    "mathopenfence": "括弧",
    "mathclosefence": "括弧",
}

JULIA_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0",
                 "\\": "\\", '"': '"', "'": "'", "a": "\a", "b": "\b",
                 "f": "\f", "v": "\v", "e": "\x1b"}


def unescape_julia(s: str) -> str:
    """Julia/C 風の文字列エスケープを展開する。"""
    out: list[str] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        i += 1
        if i >= len(s):
            break
        kind = s[i]
        if kind in ("u", "U", "x"):
            width = {"u": 4, "U": 8, "x": 2}[kind]
            i += 1
            digits = ""
            while i < len(s) and len(digits) < width and s[i] in "0123456789abcdefABCDEF":
                digits += s[i]
                i += 1
            if digits:
                out.append(chr(int(digits, 16)))
        else:
            out.append(JULIA_ESCAPES.get(kind, kind))
            i += 1
    return "".join(out)


# "\\alpha" => "α",  /  bold*"Alpha" => "𝚨",  # comment
JULIA_ENTRY_RE = re.compile(
    r"""^\s*
    (?:  "(?P<lit>(?:\\.|[^"\\])*)"
       | (?P<const>[A-Za-z_][A-Za-z0-9_]*)\s*\*\s*"(?P<rest>(?:\\.|[^"\\])*)"
    )
    \s*=>\s*"(?P<val>(?:\\.|[^"\\])*)"\s*,
    (?:\s*\#\s*(?P<note>.*))?$""",
    re.VERBOSE,
)
JULIA_CONST_RE = re.compile(r'^const\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"((?:\\.|[^"\\])*)"')


def parse_julia(path: Path) -> list[tuple[str, str, str, str]]:
    """(TeXコマンド名, 文字, 分類, 備考) を返す。"""
    consts: dict[str, str] = {}
    rows: list[tuple[str, str, str, str]] = []
    reverse_section = False

    for line in path.read_text(encoding="utf-8").splitlines():
        m = JULIA_CONST_RE.match(line)
        if m:
            consts[m.group(1)] = unescape_julia(m.group(2))
            continue
        # ファイル末尾の「文字 → コマンド名」の逆引き表は読み飛ばす
        if line.startswith("const symbols_latex_canonical"):
            reverse_section = True
            continue
        if reverse_section:
            continue

        m = JULIA_ENTRY_RE.match(line)
        if not m:
            continue
        if m.group("lit") is not None:
            name = unescape_julia(m.group("lit"))
        else:
            prefix = consts.get(m.group("const"))
            if prefix is None:
                continue
            name = prefix + unescape_julia(m.group("rest"))
        word = unescape_julia(m.group("val"))
        note = (m.group("note") or "").strip()
        if not name.startswith("\\"):
            continue
        rows.append((name[1:], word, "", note))
    return rows


UM_ENTRY_RE = re.compile(
    r'^\\UnicodeMathSymbol\{"([0-9A-Fa-f]+)\}\{\\([A-Za-z]+)\s*\}'
    r"\{\\([A-Za-z]+)\}\{([^}]*)\}"
)


def parse_unicode_math(path: Path) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = UM_ENTRY_RE.match(line)
        if not m:
            continue
        cp, name, cls, desc = m.groups()
        word = chr(int(cp, 16))
        category = UM_CLASS.get(cls, "記号")
        rows.append((name, word, category, desc.strip()))
    return rows


def classify(word: str, note: str) -> str:
    """Julia 側の行に分類を与える。"""
    if len(word) == 1:
        cat = unicodedata.category(word)
        if cat.startswith("M"):
            return "アクセント"
        name = unicodedata.name(word, "")
        if "SUPERSCRIPT" in name or name.startswith("MODIFIER LETTER"):
            return "上付き"
        if "SUBSCRIPT" in name:
            return "下付き"
        if "MATHEMATICAL" in name or "DOUBLE-STRUCK" in name \
                or "SCRIPT CAPITAL" in name or "BLACK-LETTER" in name:
            return "数学英数字"
        if "GREEK" in name:
            return "ギリシャ文字"
        if "ARROW" in name:
            return "矢印"
    return "記号"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("inputs", nargs="+", type=Path,
                   help="vendor/latex_symbols.jl と vendor/unicode-math-table.tex")
    p.add_argument("-o", "--out", type=Path, required=True)
    args = p.parse_args(argv)

    rows: list[tuple[str, str, str, str, str]] = []
    sources: list[str] = []
    # 伝統的な LaTeX/AMS 名の集合。両方の表に載っている名前は latex 扱いにする
    # （unicode-math 側を先に読んで分類を取りたいので、出典は名前で後から決める）。
    latex_names: set[str] = set()
    for path in args.inputs:
        if not path.exists():
            print(f"skip: {path} が無い", file=sys.stderr)
            continue
        if path.suffix == ".jl":
            got = parse_julia(path)
            latex_names.update(n.lower() for n, _, _, _ in got)
            rows += [(n, w, classify(w, note), note, "latex")
                     for n, w, _, note in got]
        else:
            rows += [(n, w, c, d, "unicode-math")
                     for n, w, c, d in parse_unicode_math(path)]
        sources.append(f"{path.name} ({len(rows)} 件まで)")
        print(f"{path.name}: 累計 {len(rows)} 件", file=sys.stderr)

    # 絞り込み
    seen: set[tuple[str, str]] = set()
    kept: list[tuple[str, str, str, str, str]] = []
    skipped = {"ascii": 0, "alphabet": 0, "arabic": 0, "dup": 0, "empty": 0}
    for name, word, category, note, src in rows:
        if not word:
            skipped["empty"] += 1
            continue
        # ASCII だけの記号（\lparen → "(" など）は辞書に入れても意味がない
        if all(ord(c) < 0x80 for c in word):
            skipped["ascii"] += 1
            continue
        if UM_ALPHABET_RE.match(name):
            # unicode-math の数学英数字記号は名前が機械的で数が多いので、
            # 大文字・小文字の 1 文字ものだけ残す
            if len(word) != 1:
                skipped["alphabet"] += 1
                continue
            category = "数学英数字"
        if len(word) == 1 and "ARABIC" in unicodedata.name(word, ""):
            skipped["arabic"] += 1
            continue
        key = (name.lower(), word)
        if key in seen:
            skipped["dup"] += 1
            continue
        seen.add(key)
        if not note and len(word) == 1:
            note = unicodedata.name(word, "").lower()
        if name.lower() in latex_names:
            src = "latex"
        kept.append((name, word, category or "記号", note, src))

    kept.sort(key=lambda r: (r[0].lower(), r[1]))

    lines = [
        "# TeX コマンド名 → Unicode（自動生成。手で編集しないこと）",
        "#",
        "# 生成: python -I tools/gen_tex_symbols.py " +
        " ".join(str(p) for p in args.inputs) + f" -o {args.out}",
        "# 出典:",
        "#   Julia REPL latex_symbols.jl (MIT) https://github.com/JuliaLang/julia",
        "#     さらにその元は W3C XML Entity Definitions for Characters",
        "#   unicode-math-table.tex (LPPL 1.3c) https://github.com/wspr/unicode-math",
        "#",
        "# 出典 latex = 伝統的な LaTeX/AMS 名、unicode-math = unicode-math 固有",
        "# よみ\t単語\t分類\t備考\t出典",
    ]
    for name, word, category, note, src in kept:
        note = note.replace("\t", " ")
        lines.append(f"{name}\t{word}\t{category}\t{note}\t{src}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"採用 {len(kept)} 件 / 除外 {skipped}", file=sys.stderr)
    print(f"出力 {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
