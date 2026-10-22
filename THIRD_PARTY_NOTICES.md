# Third-party notices

This project contains data derived from the following works.

| File | Derived from |
|---|---|
| `data/emoji-auto.tsv`, `atok-emoji.txt`, `atok-all.txt` | Mozc `emoji_data.tsv` |
| `data/tex-symbols.tsv`, `atok-math.txt`, `atok-all.txt` | Julia `latex_symbols.jl`, unicode-math `unicode-math-table.tex` |

`data/emoji-auto.tsv` and `data/tex-symbols.tsv` are tables extracted by
`tools/gen_emoji.py` and `tools/gen_tex_symbols.py`. They do not contain the
original files.

## Mozc — `src/data/emoji/emoji_data.tsv`

<https://github.com/google/mozc/blob/master/src/data/emoji/emoji_data.tsv>

The list of emoji and their hiragana readings are taken from this file.

```text
Copyright 2010-2018, Google Inc.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
  * Redistributions in binary form must reproduce the above
    copyright notice, this list of conditions and the following disclaimer
    in the documentation and/or other materials provided with the
    distribution.
  * Neither the name of Google Inc. nor the names of its
    contributors may be used to endorse or promote products derived from
    this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

## Julia — `stdlib/REPL/src/latex_symbols.jl`

<https://github.com/JuliaLang/julia/blob/master/stdlib/REPL/src/latex_symbols.jl>

```text
MIT License

Copyright (c) 2009-2025: Jeff Bezanson, Stefan Karpinski, Viral B. Shah, and other contributors: https://github.com/JuliaLang/julia/contributors

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

The symbol list in `latex_symbols.jl` was originally generated from the W3C
[XML Entity Definitions for Characters](https://www.w3.org/TR/xml-entity-names/).

## unicode-math — `unicode-math-table.tex`

<https://github.com/wspr/unicode-math>

The unicode-math package is maintained by Will Robertson and may be modified
and distributed under the terms and conditions of the
[LaTeX Project Public License](https://www.latex-project.org/lppl/),
version 1.3c or greater.

This project uses only the command names, code points, math classes and
descriptions listed in `unicode-math-table.tex`. It does not redistribute the
file itself or any modified version of it.

## Unicode Character Database

Character names used to generate the math alphanumeric, accented, superscript
and subscript entries are taken from Python's `unicodedata` module, which is
based on the Unicode Character Database.
Unicode data is provided under the
[Unicode License v3](https://www.unicode.org/license.txt).
