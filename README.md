# ATOK Unicode 辞書

ATOK から Unicode の絵文字・数学記号・アクセント付き文字を変換で入力するための、
ATOK 用単語辞書を生成します。

ATOK は `(^_^)` 系の顔文字は得意ですが、`ℝ` `∑` `𝒜` `x²` `é` のような文字は
ほとんど変換候補に出てきません。その部分を単語辞書で補います。

```text
:わらう    → 😀        :Infty    → ∞        :B      → 𝔹 ℬ 𝔅 𝐁 𝐵 …
:いいね    → 👍        :Leqslant → ⩽        :E      → È É Ê Ë Ē …
:はーと    → ❤️ 💙 💚 …  :Alpha    → α Α 𝛂 …   :^2     → ²
:ゆびさし  → 👉 👈 👆 👇  :Mapsto   → ↦        :Argmax → 𝑎𝑟𝑔𝑚𝑎𝑥
```

既定のビルドで 4,305 語（よみ 2,357 種）です。内訳は絵文字 306 字、
数学・技術記号とアクセント付き文字が 3,766 語です。

## よみの考え方

よみはすべてコロンキーで始まります。通常の日本語変換には混ざらないので、
`わらう` と打てば従来どおり「笑う」が出ます。ひらがな入力でコロンキーを押すと
全角の `：` になるため、辞書側のよみも全角コロンで登録しています。

よみの作り方は次の 2 つに分けています。

- **名前があるものは名前で引く。** TeX のコマンド名や絵文字の呼び方です。
  `\infty` なら `:Infty`、😀 なら `:わらう` のように打ちます。
- **属性が違うだけのものは候補で選ぶ。** 書体・アクセント・色・向きのように、
  同じ対象の見た目が違うだけのものには別々のよみを作りません。元の文字や
  対象の名前だけを打って、候補から選びます。

後者の方針は、覚えるよみを増やさないためのものです。`:Bbr` `:Mathbbr` のような
書体ごとのよみや、`:あおはーと` `:みどりはーと` のような色ごとのよみは作りません。

### 絵文字

意味からそのまま引きます。`:かなしい` `:はくしゅ` `:ろけっと` `:ぱんだ` など。
1 つの絵文字に複数の呼び方を割り当ててあるので、思いついた言葉で大抵当たります。

色や向きだけが違うものは、1 つのよみにまとめてあります。

```text
:はーと   → ❤️ 💓 💖 💙 💚 💛 💜 🖤 🤍
:ゆびさし → 👆 👇 👈 👉
:ぐらふ   → 📈 📉 📊
:かぎ     → 🔐 🔑 🔒 🔓
:つき     → 🌕 🌙
```

### 記号 — TeX のコマンド名

バックスラッシュをコロンに置き換えて打ちます。`\infty` なら `:Infty`、
`\leqslant` なら `:Leqslant` です。amssymb の記号から unicode-math の異体字まで、
Unicode に文字があるものはおおむね収録しています。

| よみ | 結果 | よみ | 結果 |
|---|---|---|---|
| `:Sum` | ∑ | `:Int` `:Oint` `:Iiint` | ∫ ∮ ∭ |
| `:Partial` `:Nabla` | ∂ ∇ | `:Infty` | ∞ |
| `:Leq` `:Geq` | ≤ ≥ | `:Leqslant` `:Nleq` `:Lesssim` | ⩽ ≰ ≲ |
| `:In` `:Subseteq` | ∈ ⊆ | `:Varnothing` `:Complement` | ∅ ∁ |
| `:Forall` `:Exists` | ∀ ∃ | `:Vdash` `:Models` | ⊢ ⊨ |
| `:To` `:Mapsto` | → ↦ | `:Iff` `:Implies` | ⟺ ⟹ |
| `:Hbar` `:Ell` `:Aleph` | ℏ ℓ ℵ | `:Hat` `:Vec` `:Bar` | ̂ ⃗ ̄（結合文字） |

伝統的な LaTeX 名（`:Le` `:To` `:Land` `:Ne`）、unicode-math の名前
（`:Leqslant`）、よく使う記号の日本語よみ（`:そうわ` `:せきぶん` `:むげんだい`）の
いずれでも引けます。

大文字と小文字は打ち分けません。ATOK のよみは半角英字の大小を区別しないため、
`\alpha` と `\Alpha`、`\rightarrow` と `\Rightarrow` のような組は同じよみの
別候補として登録してあります。

### 冪乗（上付き）・添字（下付き）

TeX と同じく `^` と `_` に続けて文字を打ちます。

| よみ | 結果 | よみ | 結果 |
|---|---|---|---|
| `:^2` | ² | `:_2` | ₂ |
| `:^-1` | ⁻¹ | `:_-1` | ₋₁ |
| `:^N` `:^T` | ⁿ ᵗ ᵀ | `:_N` `:_I` | ₙ ᵢ |
| `:^Alpha` | ᵅ | `:_Beta` | ᵦ |
| `:^+` `:^-` `:^=` | ⁺ ⁻ ⁼ | `:_+` `:_-` `:_=` | ₊ ₋ ₌ |

数字は 0〜9（`--level` を上げると 2 桁まで）、英字とギリシャ文字は Unicode に
存在するものすべてです。`q` の上付きのように Unicode にない組み合わせは
登録されません。

### 英字・数字・ギリシャ文字の書体

元の文字をそのまま打ち、13 書体ぶんの候補から選びます。書体名を覚える必要は
ありません。

```text
:B     → 𝔹 ℬ 𝔅 𝐁 𝐵 𝑩 𝖡 𝗕 𝘉 𝘽 𝙱 …（小文字も同じよみ）
:1     → 𝟙 𝟏 𝟣 𝟭 𝟷
:Alpha → α Α 𝛂 𝚨 𝛼 𝛢 𝜶 𝜜 𝝰 𝝖 𝞪 𝞐
```

収録しているのは二重線体・筆記体・太字筆記体・ひげ文字・太字ひげ文字・太字・
斜体・太字斜体・サンセリフ・サンセリフ太字・サンセリフ斜体・サンセリフ太字斜体・
等幅の 13 書体です。Unicode の穴（ℝ ℂ ℕ ℙ ℚ ℤ ℍ、ℬ ℰ ℱ ℋ ℐ ℒ ℳ ℛ、
ℭ ℌ ℑ ℜ ℨ、ℎ）は Letterlike Symbols の文字で埋めてあります。

数字の書体は二重線体・太字・サンセリフ・サンセリフ太字・等幅の 5 種、
ギリシャ文字の書体は太字・斜体・太字斜体・サンセリフ太字・サンセリフ太字斜体の
5 種です。これは Unicode に符号位置があるものがこれだけ、という理由によります。
`∇` `∂` と `varepsilon` `vartheta` などの異体字にも書体版があります。

### アクセント付きのラテン文字

これも元の文字を打って候補から選びます。

```text
:E → È É Ê Ë Ē Ĕ Ė Ę Ě Ȩ Ɇ Ẹ Ẻ Ẽ（小文字も同じよみ）
:A → À Á Â Ã Ä Å Ā Ă Ą Ǎ Ȧ Ạ Ả Æ …
:O → Ò Ó Ô Õ Ö Ø Ō Ŏ Ő Ơ Ọ Ỏ Œ …
```

収録しているアクセントは acute、grave、circumflex、diaeresis、tilde、macron、
breve、caron、ring、dot above、cedilla、ogonek、stroke、double acute と、
ベトナム語の horn、hook above、dot below です。æ œ ß ð þ ŋ ə ı は関係の深い
文字のよみに入れてあります（æ は `:A`、ß は `:S`）。

母音は候補が多くなります（`:O` で 58 個、`:E` で 56 個）。これは書体の候補と
同じよみに並ぶためです。

### 関数名・作用素名（120 語）

LaTeX の log 型関数（`\sin` `\lim` `\det` `\gcd` など）と、`\operatorname` で
書く慣用のもの（`argmax` `Aut` `esssup` `softmax` など）を、数学フォントで
組んだ形で登録しています。

```text
:Sin    → 𝑠𝑖𝑛 / 𝐬𝐢𝐧 / 𝗌𝗂𝗇 / 𝚜𝚒𝚗
:Argmax → 𝑎𝑟𝑔𝑚𝑎𝑥 / 𝑎𝑟𝑔 𝑚𝑎𝑥（TeX が細空きで組む形）/ …
```

収録しているのは三角・双曲線関数、指数対数、極限と上下限（`limsup` `injlim`
`esssup` `argmax` `plim` など）、線形代数と代数（`det` `tr` `rank` `ker` `coker`
`span` `Aut` `End` `Hom` `Gal` `Spec` など）、解析と幾何（`grad` `div` `curl`
`supp` `vol` `diam` `conv` `erf` など）、確率統計と機械学習（`Pr` `var` `cov`
`median` `softmax` `logsumexp` `sigmoid` `relu` など）です。

TeX では作用素は立体で組むのが正しいのですが、Unicode の立体は素の ASCII
そのものなので、見た目で区別が付く斜体やサンセリフを候補にしています。

## 導入

### 1. 単語ファイルを入手する

単語ファイルはリポジトリには置いていません。GitHub Actions がタグごとに
ビルドして [Releases](../../releases) に添付します。

| 添付ファイル | 中身 |
|---|---|
| `atok-math.txt` | 数学・技術記号とアクセント付き文字 |
| `atok-emoji.txt` | 絵文字 |
| `atok-all.txt` | 両方 |
| `atok-dict-core.zip` | 既定ビルド一式（単語ファイル、動作確認用ファイル、`master.tsv`） |
| `atok-dict-standard.zip` / `atok-dict-full.zip` | 収録量を増やした版 |
| `atok-dict-core-kana.zip` | 大文字始まりのよみが使えない環境向け |

中身が重複するので、入れるのは `atok-math.txt` `atok-emoji.txt` か
`atok-all.txt` のどちらかにしてください。

### 2. ATOK の設定を 1 つ変える

英字のよみは `:Infty` のように大文字で始まります。大文字を打つと
「shiftキー＋A〜Zで英語入力に切り替える」が働いて英語入力モードに入り、
初期設定ではそこでスペースバーが変換ではなく空白の入力になります。

ATOK プロパティ（Ctrl+F12）→［入力・変換］タブ →［英語］の
「英語入力ではスペースバーで空白を入力する」をオフにしてください。
設定を変えない場合は、スペースの代わりに変換キーを押しても変換できます。

### 3. 専用の辞書を作って取り込む

標準のユーザー辞書に混ぜると、あとから外すのが面倒になります。

1. 辞書ユーティリティの［辞書］→［新規作成］で `unicode-math.dic` などを作る
2. ATOK プロパティ →［辞書・学習］で、辞書セット一覧から**標準辞書セット**を
   選び、［辞書の追加・削除］でその辞書を追加する
3. 辞書ユーティリティの［一括処理］→［単語一括処理］で、**登録先にその辞書を
   指定して** `atok-math.txt` を読み込む
4. 辞書ユーティリティでその `.dic` を開き、語数が合っているか確かめる

辞書セットの選び方には注意が必要です。スペースバーで変換されるのは
基本辞書セット（標準辞書セット）だけで、辞書セット 2〜5 は Ctrl+2〜5 または
F2〜F5、辞書セット 6 は Ctrl+Shift+6、**辞書セット 7〜0 はインストール直後は
キーが割り付けられていません**。辞書セット 7〜0 に入れた場合は、
［スペース変換で候補に追加する］をオンにするか、キーカスタマイズで変換キーを
割り付ける必要があります。

不要になったら、辞書セットから外すだけで無効化できます。

変換できないときは、次の順に確かめると原因を絞れます。

1. その `.dic` を辞書ユーティリティで開き、語が入っているか見る。
   空なら手順 3 の登録先を間違えています
2. 語が入っているなら、辞書セットが基本辞書セットかを確かめる
3. それでも変換できないなら、`atok-probe*.txt` で切り分ける（後述）

### 4. ATOK Passport を使っている場合

ATOK Passport は ATOK Sync One でデータをクラウド同期します。公式ヘルプに
よると、インストール直後の設定では「登録単語・用例（学習情報を含む）」
「確定履歴」「ユーザー作成省入力データ」「ユーザー作成辞書」が自動で
同期されます。自分で作った `.dic` も同期対象に入ります。

数千語を入れると、それが丸ごとサーバーと他の端末へ流れます。Android 版は
標準辞書セットのユーザー辞書だけが対象で、よみ 16 文字・単語 全角 25 文字と
いう別の上限もあるため、一部だけ同期されて食い違います。

気になる場合は、取り込む前に ATOK Sync One の［設定を変更する］で
「学習・登録の同期」の自動実行を切り、Windows で使い勝手を確かめてから
同期を戻すかどうかを決めてください。同期がおかしくなった場合は
［データを修復する］があります。

### 動作確認用のファイル

`atok-probe*.txt` は、ATOK が何を受け付けるかを少ない行数で切り分けるための
ファイルです。本番の辞書を入れる前や、変換できないときに使います。

| ファイル | 分かること |
|---|---|
| `atok-probe.txt` | 品詞名・品詞番号、絵文字やサロゲートペアの可否、よみに使える文字 |
| `atok-probe2.txt` | 英字のよみが打ったときにどう化けるか |
| `atok-probe3.txt` | TeX 名をローマ字入力したときの綴りの予測が当たるか |
| `atok-probe4.txt` | かなのよみと全角英数のよみのどちらが引かれるか |
| `atok-probe5.txt` | 大文字始まりのよみが使えるか |

読み込むときは、辞書ユーティリティの［単語一括処理］で**［出力ファイル］を
設定してください**。登録できなかった行がそこに出ます。

## ビルド

Python 3.10 以上が必要です。外部ライブラリは使いません。

```bash
python build.py
```

`dist/` に次が出ます（`dist/` は `.gitignore` 済みです）。

| ファイル | 中身 |
|---|---|
| `atok-emoji.txt` | 絵文字（539 語） |
| `atok-math.txt` | 数学・技術記号とアクセント付き文字（3,766 語） |
| `atok-all.txt` | 両方（4,305 語） |
| `atok-probe.txt` 〜 `atok-probe5.txt` | 動作確認用 |
| `master.tsv` | 全エントリの一覧（UTF-8） |
| `rejected.tsv` | ATOK のよみに使えず落とした語 |

文字コードは UTF-16LE + BOM、改行は CR+LF です。絵文字や `𝒜` のような
BMP 外の文字を通すために必要です。

### 収録量を選ぶ

語数が多いと取り込みにも ATOK Sync にも影響するので、`--level` と `--reading`
で増減できます。組み合わせた語数は次のとおりです。

| | `--reading pascal`（既定） | `--reading kana` | 両方 |
|---|---|---|---|
| `--level core`（既定） | 4,305 | 4,552 | 7,951 |
| `--level standard` | 5,768 | 6,180 | 11,000 |
| `--level full` | 6,734 | 7,248 | 12,896 |

`core` が落としているのは使う機会の少ない異体字と別名だけで、伝統的な
LaTeX/AMS の記号はすべて残ります（`:Leqslant` `:Lesssim` `:Varnothing` も
入っています）。

| | core | standard | full |
|---|---|---|---|
| TeX 記号表 | 伝統的な LaTeX/AMS 名 1,548 件 | + unicode-math 固有の 346 件 | 同左 |
| 書体 | 13 書体すべて | 13 書体すべて | 13 書体すべて |
| 関数名 | 素のよみのみ（`:Sin`） | + `:Itsin` `:Bfsin` | + 7 書体ぶんの別名 |
| 上付き・下付き | 1 桁まで | 2 桁 30 まで | 2 桁 99 まで |

### そのほかのオプション

```bash
python build.py --reading pascal        # 大文字始まりの英字よみ :Infty（既定）
python build.py --reading kana          # ローマ字変換後のかなのよみ :いんｆｔｙ
python build.py --reading pascal,kana   # 両方
python build.py --prefix ':'            # プレフィックスを半角コロンにする
python build.py --pos 70                # 品詞を番号で指定する（70 = 顔文字）
python build.py --no-header             # 先頭の !!ATOK_TANGO_TEXT_HEADER_1 を出さない
python build.py --encoding utf-8        # 文字コードを変える
```

`--reading kana` は、大文字始まりのよみが使えない環境向けです。ひらがな入力で
`infty` と打つと ATOK の読みは `いんｆｔｙ` になるので、その綴りで登録します。
綴りの予測は [`romaji.py`](romaji.py) が行っていて、`python romaji.py <TeX名>`
で確認できます。

## リリース

タグを打つと [`.github/workflows/release.yml`](.github/workflows/release.yml) が
各段階をビルドし、検査して Release に添付します。

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub の Actions 画面から `release` ワークフローを手動実行し、タグ名を
入力することもできます。リリースノートには各段階の語数が入ります。

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) は push と
プルリクエストごとに走り、全段階をビルドして
[`tools/verify_dist.py`](tools/verify_dist.py) で検査します。検査の内容は、
UTF-16LE の BOM と CR+LF 改行とヘッダー行、タブ区切りの欄数、よみ 32 文字と
単語 100 文字の上限、よみに使えない文字の混入、同じ（よみ, 単語）の重複です。
ローカルでも `python tools/verify_dist.py dist` で同じ検査ができます。

## データの構成

| データ | 持ち方 |
|---|---|
| 絵文字 306 字 | `data/emoji.tsv`（手書き） |
| 記号の日本語よみ・技術記号・図形 | `data/symbols.tsv`（手書き） |
| TeX コマンド名と Unicode の対応 4,005 件 | `data/tex-symbols.tsv`（自動生成・コミット済み） |
| 書体・アクセント・上付き下付き・ギリシャ文字・関数名 | `build.py` が `unicodedata` から生成 |
| 英字よみからローマ字入力後の綴りへの変換 | `romaji.py` |

`data/tex-symbols.tsv` を作り直すときだけ、元の表をダウンロードします。

```bash
mkdir -p vendor
curl -sLo vendor/latex_symbols.jl \
  https://raw.githubusercontent.com/JuliaLang/julia/master/stdlib/REPL/src/latex_symbols.jl
curl -sLo vendor/unicode-math-table.tex \
  https://raw.githubusercontent.com/wspr/unicode-math/master/unicode-math-table.tex
python -I tools/gen_tex_symbols.py vendor/unicode-math-table.tex vendor/latex_symbols.jl \
  -o data/tex-symbols.tsv
python build.py
```

`vendor/` は `.gitignore` 済みです。生成物の `data/tex-symbols.tsv` だけを
コミットします。

## 語を足す・削る

`data/emoji.tsv` と `data/symbols.tsv` を編集して `python build.py` し直します。

```text
よみ1,よみ2,よみ3<TAB>単語<TAB>分類<TAB>備考
```

`#` で始まる行はコメントです。よみがほかの行とぶつかっても構いません。
同じよみの候補として並ぶだけです。色や向きだけが違う文字を足すときは、
別のよみを作らずに既存のよみへ並べてください。

`data/tex-symbols.tsv` は自動生成なので直接は編集しません（足したい TeX 名は
`data/symbols.tsv` 側に書きます）。書体や関数名を増やすときは `build.py` の
`STYLES` `FUNCTION_NAMES` `GREEK` `ACCENTS` を変更します。

よみに使えるのは、ひらがな、半角英数、全角英数、カタカナと
`# $ % & * + - / : ; < = > @ _ ' ^ ~ \`` です。括弧・ピリオド・感嘆符は
使えません。使えない語はビルド時に落ちて `dist/rejected.tsv` に理由付きで
残ります。よみは 32 文字、単語は 100 文字が ATOK for Windows の上限です。

## ATOK の仕様について確かめたこと

ATOK Passport（Windows）で実機確認した結果です。

### 単語ファイルの形式

| 項目 | 結果 |
|---|---|
| 品詞 `顔文字*` / `顔文字` / `名詞` | 登録できる |
| 品詞 `記号` | 登録されない |
| 品詞 `短縮よみ` | 登録されない。公式の表記は「短縮読み」 |
| 絵文字（サロゲートペア）😀 | 問題なし |
| 異体字セレクタ付き ❤️ | 問題なし |
| 複数文字の数学フォント 𝑠𝑖𝑛 | 問題なし |
| BMP 内の数学記号 ℝ | 問題なし |
| よみの `^` `_` + 数字 | 問題なし |

品詞は番号でも指定できます。顔文字 = 70、短縮読み = 74、単漢字 = 41、
独立語 = 18 です。品詞名で弾かれる場合は `--pos 70` のように指定します。

### 入力モードとよみ

ATOK が変換に使うのは画面の表示ではなく、ローマ字変換後の読みです。
全角英数モードで `infty` と打つと画面には `ｉｎｆｔｙ` と出ますが、
引かれるのは `いんｆｔｙ` のほうです。`--reading zenkaku` で作った
全角英数のよみは、どのモードから打っても一致しませんでした。

| 入力モード | スペースで変換 | 読みバッファ |
|---|---|---|
| 全角ひらがな | できる | `：いんｆｔｙ` |
| 全角カタカナ / 半角カタカナ | できる | かなと同じ |
| 全角英数 | できる | `：いんｆｔｙ`（表示は `：ｉｎｆｔｙ`） |
| 半角英数 | できない | 変換されず半角空白が入る |

半角英数モードで変換できないのは仕様です。後変換（F6〜F10）は読みを別の
文字種にする機能で方向が逆、再変換（Shift+変換）は確定済みの文字列を
戻す機能で、どちらも英字から辞書を引く用途には使えません。

ただし、ひらがな入力でも**大文字から始まる綴りはローマ字変換されません**。
`infty` は `いんｆｔｙ` になりますが、`Infty` は `Infty` のまま残ります。
既定の `--reading pascal` はこれを使って、よみの先頭の英字だけを大文字に
しています。この挙動は
[かたぎりあまね「絵文字入力方法まとめ」](https://zenn.dev/amane/articles/f826fc6fbb9527)（CC BY 4.0）
で知りました。

### ローマ字入力の綴り

`--reading kana` で使う綴りの予測は、`atok-probe3.txt` で実機確認しました。

| 打ったもの | ATOK の読み | 分かったこと |
|---|---|---|
| `:test` | `てｓｔ` | かなにならない子音は全角英字で残る |
| `:infty` | `いんｆｔｙ` | `n` + 子音 は ん |
| `:leq` | `ぇｑ` | `l` + 母音 は小書き（ら行ではない） |
| `:lambda` | `ぁｍｂだ` | 同上。子音は吐き出される |
| `:theta` | `てぇた` | `th` は てゃ行 に割り当てられている |
| `:cup` | `くｐ` | `c` + 母音 は か行 |

これらは `romaji.py` の `CONFIRMED_OPTS` として固定しています。未確認なのは
末尾の `n`（ん / ｎ）、`x` + 母音（小書き / 英字のまま）、子音 3 連の促音
（っっ / っ）の 3 つで、どちらでも一致するように両方のよみを登録しています。
ローマ字テーブルを変更している場合は、ここがずれます。

## 既知の制限

- `:Hat` `:Vec` `:Bar` `:Dot` などのアクセント類は結合文字です。単体で入力すると
  直前の文字に合成されます（`x` を打ってから `:Vec` で `x⃗` になります）。
- `❤️` `⚠️` のような異体字セレクタ（U+FE0F）付きの絵文字は、貼り付け先の
  アプリがセレクタを落とすと白黒で表示されることがあります。
- ZWJ の複合絵文字（職業・家族・肌の色など）は環境差が大きいため収録していません。
- 数学フォントの文字は、貼り付け先のフォントによっては豆腐（□）になります。
- 母音のよみは候補が 50 個を超えます。書体とアクセントが同じよみに並ぶためです。

## 出典

ATOK の単語ファイル形式と辞書の扱い:

- [[015038] たくさんの単語を一度に登録したい](https://support.justsystems.com/faq/1032/app/servlet/qadoc?QID=015038) — ジャストシステム
- [[055942] 単語ファイルを作成する](https://support.justsystems.com/faq/1032/app/servlet/qadoc?QID=055942) — ジャストシステム
- [ATOKのユーザー辞書テキストの書式について](https://dz11.hatenadiary.jp/entry/2017/03/30/112634) — ヘッダー行、UTF-16、CR/LF、文字数制限
- [品詞の種類（その他）](https://atok.com/other/support/howtouse/mac/shrd/shrd_hinsi_other.htm) — 品詞名と品詞番号
- [辞書の使い方](https://atok.com/other/support/howtouse/mac/dc/pgs/dc_dc_use.htm) / [[019834] 辞書を追加する](https://support.justsystems.com/faq/1032/app/servlet/qadoc?QID=019834) — 辞書セットごとの変換キー
- [どこにいても同じ入力環境を再現する －ATOK Sync One－](https://atok.com/other/support/howtouse/mac/it/pgs/it_atok_sync.htm) — 同期の対象
- [[041359] スペースキーを押しても文字がアルファベットのままで変換できない](https://support.justsystems.com/faq/1032/app/servlet/qadoc?QID=041359)
- [[044845] ［shift］キーを押すと、英字入力モードに切り替わるようにする](https://support.justsystems.com/faq/1032/app/servlet/qadoc?QID=044845) — ［入力・変換］→［英語］の設定
- [入力した文字をカタカナ･アルファベットに変換する －後変換－](https://atok.com/other/support/howtouse/mac/ip/pgs/ip_kata_ato.htm)
- [キーの機能一覧：ATOKスタイル](https://atok.com/other/support/howtouse/mac/ap/pgs/ap_key.htm) / [[040816] ATOK標準のキー操作](https://support.justsystems.com/faq/1032/app/servlet/qadoc?QID=040816)
- [かたぎりあまね「絵文字入力方法まとめ」](https://zenn.dev/amane/articles/f826fc6fbb9527)（CC BY 4.0） — 大文字始まりのよみ
- [peaceiris/emoji-ime-dictionary](https://github.com/peaceiris/emoji-ime-dictionary) — ATOK 向け絵文字辞書の実装例

TeX コマンド名と Unicode の対応:

- [JuliaLang/julia `stdlib/REPL/src/latex_symbols.jl`](https://github.com/JuliaLang/julia/blob/master/stdlib/REPL/src/latex_symbols.jl)（MIT） — 伝統的な LaTeX 名。元は [W3C XML Entity Definitions for Characters](https://www.w3.org/TR/xml-entity-names/) の `unicode.xml`
- [wspr/unicode-math `unicode-math-table.tex`](https://github.com/wspr/unicode-math)（LPPL 1.3c） — unicode-math の記号名と数式クラス
- 字形と Unicode 名は Python の `unicodedata`（Unicode Character Database）から引いています
