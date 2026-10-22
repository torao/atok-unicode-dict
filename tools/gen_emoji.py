#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mozc の絵文字データを data/emoji-auto.tsv に変換する。

Mozc（Google 日本語入力のオープンソース版）と同じ規則で絵文字を変換できるように、
Mozc の絵文字データにある読みをそのまま使う。Mozc の EmojiRewriter の規則は次の 2 つ。

  - 読みが絵文字データの読みと一致したら、その絵文字を候補に出す
  - 読みが「えもじ」なら、すべての絵文字を候補に出す

入力（vendor/ に置く）:

  mozc-emoji_data.tsv   Mozc の絵文字データ（BSD 3-Clause）
                        https://github.com/google/mozc/blob/master/src/data/emoji/emoji_data.tsv

使い方（ダウンロードしたファイルは引数で渡す）:

  python -I tools/gen_emoji.py vendor/mozc-emoji_data.tsv -o data/emoji-auto.tsv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 読みが「えもじ」のとき、すべての絵文字を候補に出す（Mozc の kEmojiKey）
ALL_EMOJI_KEY = "えもじ"


def fullwidth_ascii_to_halfwidth(text: str) -> str:
    """全角英数記号を半角にする。

    Mozc は読みを照合する前にこの変換をかける（FullWidthAsciiToHalfWidthAscii）。
    データには「Ａ」と「A」のように両方の読みがあるので、半角にそろえて重複を除く。
    """
    return "".join(chr(ord(c) - 0xFEE0) if "！" <= c <= "～" else c
                   for c in text)


def parse_version(v: str) -> tuple[int, ...]:
    """'E15.1' -> (15, 1)"""
    return tuple(int(x) for x in v.lstrip("E").split("."))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mozc", type=Path, help="vendor/mozc-emoji_data.tsv")
    p.add_argument("-o", "--out", type=Path, required=True)
    p.add_argument("--max-version", default=None,
                   help="収録する絵文字の版の上限（例: 15.1）。既定では Mozc と同じく"
                        "すべて収録する")
    args = p.parse_args(argv)
    max_version = parse_version(args.max_version) if args.max_version else None

    command = f"python -I tools/gen_emoji.py {args.mozc.as_posix()} -o {args.out.as_posix()}"
    if args.max_version:
        command += f" --max-version {args.max_version}"
    lines = [
        "# 絵文字の一覧と読み（自動生成。手で編集しないこと）",
        "#",
        f"# 生成: {command}",
        "# 出典: Mozc src/data/emoji/emoji_data.tsv (BSD 3-Clause)",
        "#",
        "# よみ\t絵文字\t分類\t備考",
    ]
    count = 0
    skipped = 0
    for line in args.mozc.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        cols = line.split("\t")
        if len(cols) < 7:
            continue
        emoji, readings, descriptions, version = cols[1], cols[2], cols[5], cols[6]
        if max_version and version and parse_version(version) > max_version:
            skipped += 1
            continue
        words = [fullwidth_ascii_to_halfwidth(w) for w in readings.split()]
        words = list(dict.fromkeys(words + [ALL_EMOJI_KEY]))
        # 読みの区切りにカンマを使うので、カンマを含む読みは除く
        words = [w for w in words if "," not in w]
        note = descriptions.replace("\t", " ")
        lines.append(f"{','.join(words)}\t{emoji}\t絵文字\t{note}")
        count += 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"絵文字 {count} 字" + (f"（版の上限で {skipped} 字を除外）" if skipped else ""),
          file=sys.stderr)
    print(f"出力 {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
