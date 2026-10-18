#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成した単語ファイルが ATOK の仕様を満たしているか検査する。

CI でビルド結果を自動チェックするために使う。

    python tools/verify_dist.py dist
    python tools/verify_dist.py build/core build/standard
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HEADER = "!!ATOK_TANGO_TEXT_HEADER_1"
READING_MAX = 32
WORD_MAX = 100
BOM = b"\xff\xfe"


def check_file(path: Path) -> list[str]:
    """1 つの単語ファイルを検査して、問題のリストを返す。"""
    problems: list[str] = []
    raw = path.read_bytes()

    if not raw.startswith(BOM):
        problems.append("UTF-16LE の BOM で始まっていない")
        return problems
    try:
        text = raw[2:].decode("utf-16-le")
    except UnicodeDecodeError as e:
        problems.append(f"UTF-16LE として読めない: {e}")
        return problems
    if "\r\n" not in text:
        problems.append("改行が CR+LF になっていない")

    lines = text.split("\r\n")
    if not lines or lines[0] != HEADER:
        problems.append(f"先頭行が {HEADER} ではない: {lines[0]!r}")

    seen: set[tuple[str, str]] = set()
    entries = 0
    for n, line in enumerate(lines, 1):
        if not line or line.startswith("!!"):
            continue
        cols = line.split("\t")
        if len(cols) < 3:
            problems.append(f"{n}行目: 列が足りない: {line!r}")
            continue
        reading, word, pos = cols[0], cols[1], cols[2]
        entries += 1
        if not reading or not word or not pos:
            problems.append(f"{n}行目: 空の欄がある: {line!r}")
        if len(reading) > READING_MAX:
            problems.append(f"{n}行目: よみが{READING_MAX}文字超: {reading!r}")
        if len(word) > WORD_MAX:
            problems.append(f"{n}行目: 単語が{WORD_MAX}文字超: {reading!r}")
        for bad in "()!?。、 ":
            if bad in reading:
                problems.append(f"{n}行目: よみに使えない文字 {bad!r}: {reading!r}")
        key = (reading, word)
        if key in seen:
            problems.append(f"{n}行目: 重複: {reading!r} -> {word!r}")
        seen.add(key)

    if entries == 0:
        problems.append("登録単語が 1 件も無い")
    return problems


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dirs", nargs="+", type=Path, help="検査する出力ディレクトリ")
    args = p.parse_args(argv)

    total_problems = 0
    checked = 0
    for d in args.dirs:
        for path in sorted(d.glob("atok-*.txt")):
            checked += 1
            problems = check_file(path)
            if problems:
                total_problems += len(problems)
                print(f"NG {path}")
                for msg in problems[:20]:
                    print(f"     {msg}")
                if len(problems) > 20:
                    print(f"     ほか {len(problems) - 20} 件")
            else:
                size = path.stat().st_size
                print(f"OK {path} ({size:,} bytes)")

    if checked == 0:
        print("検査対象のファイルが見つからない", file=sys.stderr)
        return 1
    print(f"\n{checked} ファイル検査、問題 {total_problems} 件")
    return 1 if total_problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
