# Third-party notices

`data/tex-symbols.tsv` and the dictionary files generated from it
(`atok-math.txt`, `atok-all.txt`) contain data derived from the following works.
`data/tex-symbols.tsv` is a table of TeX command names and Unicode code points
extracted by `tools/gen_tex_symbols.py`; it does not contain the original files.

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
