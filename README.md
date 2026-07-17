# pubmed-research-skill

PubMed の文献検索・取得・CSV 出力を AI にまかせるための
[Agent Skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) です。

- 例えば、「〇〇に関するRCT論文を2020年以降で50件探して、引用文献付きのレポートにして/ 使用した検索式もレポートに含めて / 使用した文献リストをCSV でも用意して」と頼めば、AI が PubMed を検索し、抄録や全文が取得できるものはその全文も取得したうえで、レポートと文献リストを作成してくれます。
- PubMedの検索には、語の掛け合わせやMeSHの使用、期間の指定、文献種類の指定、検索フィールドの限定、などの人力で検索式を作成する際の一般的なテクニックが使用されます。
- 検索式の妥当性は使用するAIの賢さに依存します。

## 本Skillに含まれる11個のツール

AI が内容に応じて自動で使い分けます。

| ツール | 用途 |
|--------|------|
| `search` | PubMed 検索（フィルタ、日付範囲、ページング） |
| `fetch` | PMID から詳細情報（抄録、著者、雑誌、MeSH、助成情報） |
| `fulltext` | オープンアクセス全文の取得（PMC → Europe PMC → Unpaywall の順に探索） |
| `epmc-search` | Europe PMC 検索（プレプリント、特許など PubMed に出ない文献） |
| `convert-ids` | DOI / PMID / PMCID の相互変換 |
| `related` | 関連論文・被引用論文・参考文献の一覧 |
| `cite` | 引用文献の書式化（既定は Vancouver、APA/MLA/BibTeX/RIS も可） |
| `lookup-cite` | 雑誌名・年・巻・ページなどの断片情報から PMID を特定 |
| `mesh` | MeSH（統制語彙）の検索 |
| `spell` | 検索語のスペルチェック |
| `to_csv` | 検索結果を CSV に書き出し（Excel 用、UTF-8 BOM 付き） |

CSV の列は PMID・タイトル・著者・筆頭著者・雑誌名・雑誌略称・年・巻・号・ページ・DOI・
PMCID・出版タイプ・MeSH 用語・キーワード・抄録・URL です。

## インストール

1. このフォルダの `.claude/skills/pubmed-research` を、使いたいプロジェクトの
   `.claude/skills/` 配下（または全プロジェクトで使うなら `~/.claude/skills/`）に置きます。(Claude Codeで使用する場合。その他Codex等で使用する場合はその仕様に従えば使用できます。)
2. 依存パッケージを入れます（Python 3.9 以上）。

```bash
pip install -r .claude/skills/pubmed-research/requirements.txt
```

`requests` と `pypdf`（オープンアクセス PDF からの本文抽出用）が入ります。`lxml` は任意で、
入っていれば自動的に使われます。

## 設定（任意）

そのままでも動きます（NCBI の未認証レート 3 リクエスト/秒）が、速度を上げたい場合や全文
取得を強化したい場合は、`.env.example` を コピーして`.env` に変更したうえで、以下の設定をします。なお、`.env` に情報を記入した状態でこの skill のコピーを他の人に渡したりはしないでください。(あなた専用の設定が他の人にも使用されてしまいます。)

- `NCBI_API_KEY` — レート上限が 10 リクエスト/秒に上がります（[NCBI アカウント](https://www.ncbi.nlm.nih.gov/account/)から無料で取得）
- `UNPAYWALL_EMAIL` — `fulltext` の Unpaywall 検索（PMC にない論文の全文探索）が有効になります。自分の連絡先のメールアドレスを設定して下さい。
- `NCBI_EMAIL` — NCBI への連絡先表明（推奨されているマナー）です。自分の連絡先のメールアドレスを設定して下さい。

## 使い方

スキルを置いたワークスペースで、AI に日本語で話しかけるだけです。

> GLP-1 受容体作動薬の心血管アウトカムに関する RCT を 2020 年以降で 50 件探して、CSV にまとめて

> PMID 32109013 の全文を取ってきて、Methods だけ要約して

> N Engl J Med 2020年 382巻 727ページの論文の PMID を調べて、Vancouver 形式の引用を作って

> 「2型糖尿病」の正式な MeSH 用語を調べてから、それで検索して

## 出典・謝辞

このスキルは、以下の 2 つのプロジェクトをもとにしています。

**[`cyanheads/pubmed-mcp-server`](https://github.com/cyanheads/pubmed-mcp-server)**
（Copyright 2025 Casey Hand @cyanheads、Apache License 2.0）

同 MCP サーバーの 10 個のツール構成を Python で独立に再実装したものです。同プロジェクトは
TypeScript 製で、ソースコードの複製は一切していません。ただし公開ソースを参照しており、
次の設計は同プロジェクトに由来します。

- 10 個のツールの構成とその意味づけ
- `fulltext` の探索順（PMC E-utilities → Europe PMC fullTextXML → Unpaywall）と
  `contentFormat` のラベル（`jats-text`, `pdf-text`, `html-markdown`）
- `related` の探索順（NCBI ELink → Europe PMC → OpenAlex）、Europe PMC 段を
  `cited_by`/`references` に限定する方針、未知の PMID と関連論文なしを区別する ESummary 照会
- OpenAlex へのフォールバック方針（`related_works`, `referenced_works`, `cites:` フィルタを
  バッチで PMID に解決）

**[`hellboy84/PubMed2ExcelConverter`](https://github.com/hellboy84/PubMed2ExcelConverter)**
（作者自身のツール）

11 個目のツールである CSV 出力（`to_csv`）の列レイアウトは、同ツールの出力形式に
合わせています。

## データソースと利用条件

このスキルは論文データを同梱しておらず、実行のたびに以下のサービスから取得します。
取得したデータの扱いは、各サービスの利用規約と出版社の著作権に従ってください。本スキルが
Apache License 2.0 であることは、取得したデータを自由に使ってよいという意味ではありません。

| ソース | 利用条件 |
|--------|----------|
| NCBI E-utilities | https://www.ncbi.nlm.nih.gov/books/NBK25497/ （レート制限: 3 req/s、API キーありで 10 req/s） |
| Europe PMC | https://europepmc.org/Copyright |
| Unpaywall | https://unpaywall.org/legal |
| OpenAlex | https://openalex.org/ （データは CC0 で公開） |

論文のメタデータおよび全文の著作権・ライセンスは、各出版社および著者に帰属します。

## ライセンス

Apache License 2.0 — [LICENSE](LICENSE) および [NOTICE](NOTICE) を参照してください。
