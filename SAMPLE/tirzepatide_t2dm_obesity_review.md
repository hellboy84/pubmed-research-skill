# チルゼパチド（tirzepatide）の2型糖尿病・肥満治療における有効性 ― PubMed文献調査レポート

**作成日：** 2026-07-18
**対象データベース：** PubMed（NCBI E-utilities 経由）
**対象疾患：** 2型糖尿病（T2DM）および肥満・過体重
**対象期間：** 2021年1月1日 ～ 2026年12月31日（発行日 `[dp]` 基準）
**除外条件：** 動物実験のみの論文（PubMed の "animals NOT humans" ヘッジで除外）
**関連成果物：** `tirzepatide_t2dm_obesity_list.csv`（臨床研究セット 720 件の一覧）

---

## 0. 要約

チルゼパチドは、グルコース依存性インスリン分泌刺激ポリペプチド（GIP）受容体と GLP-1 受容体の**デュアルアゴニスト**であり、2型糖尿病（T2DM）治療薬として第3相 **SURPASS** 試験プログラムで評価された。SURPASS-1～6 の一次論文はいずれも、HbA1c 低下と体重減少の両面でプラセボ・基礎/追加インスリン・および既存 GLP-1 受容体作動薬（セマグルチド、デュラグルチド）に対する優越性または非劣性を示した (1)–(9)。2025年には心血管アウトカム試験 **SURPASS-CVOT**（tirzepatide vs dulaglutide）の一次結果が報告され、主要評価項目（MACE）でデュラグルチドに対する非劣性が示された (10)。肥満に対しては **SURMOUNT** プログラムで最大約 21% の体重減少が示され、対照試験ではセマグルチドを上回る減量効果が確認された (15)–(17)。一方で、**消化器系有害事象（悪心・下痢・嘔吐等）を中心とする副作用**、膵炎・胆道系リスク、注射・用量漸増の負担などのデメリットも一貫して報告されており、ベネフィットとリスクの総合評価が求められる (18)(19)。本レポートは、実際に PubMed で実行した検索式、ヒット件数、主要試験の整理、有効性および副作用の要点、引用文献（Vancouver 形式）をまとめる。有効性・副作用の総括は「第2.5章」を参照。

---

## 1. PubMed 検索式と設計意図・ヒット件数

### 1-1. 検索設計の基本方針

- **MeSH と自由語（Title/Abstract）の OR 併用：** MeSH のインデックス付与は発行から数週間～数か月遅れるため、MeSH 単独では最新論文を取りこぼす。チルゼパチドは 2021 年以降に文献が急増した新しい薬剤であり、**再現率（recall）を確保するため MeSH 語と自由語（薬剤名の同義語・商品名を含む）を OR 結合**した。
- **動物実験の除外は「ヘッジ」で実施：** `humans[MeSH Terms]`（＝`--species humans`）を AND すると、MeSH 未付与の新規論文まで一律に除外され、上で確保した再現率が失われる。そこで **`NOT (animals[mh] NOT humans[mh])`**（`--exclude-animals`）を使用。これは「動物のみ」の論文だけを差し引き、MeSH 未付与の論文は残す。
  - 本トピックでの実測（本スキルの検証値）：`tirzepatide[tiab]` 2,249 件 → `--species humans` で 1,216 件（未索引論文をほぼ全滅）→ `--exclude-animals` で 2,180 件（動物のみ 69 件だけを除外）。
- **NOT の結合先に注意：** PubMed は `A AND NOT B` を `A AND B` と誤読し、除外したい集合をそのまま返す。`--exclude-animals` は `(...) NOT (...)` の形でクエリ全体に NOT を結合するため、この罠を回避できる（`queryTranslation` で結合を確認済み）。
- **チルゼパチドの同義語：** MeSH descriptor `Tirzepatide`（D000098860）のエントリー用語に基づき、開発コード **LY3298176**、商品名 **Mounjaro / Zepbound** を自由語として OR に追加した。
- **疾患の概念（T2DM ＋ 肥満）：** 有効性の評価対象が2型糖尿病と肥満の両方であるため、疾患節を両者の OR で構成した。
  - **T2DM：** MeSH `Diabetes Mellitus, Type 2`（D003924）＋自由語 `type 2 diabetes`、`type 2 diabetes mellitus`、`type II diabetes`、`T2DM`、`non-insulin-dependent diabetes`。
  - **肥満・過体重：** MeSH `Obesity`、`Overweight` ＋自由語 `obesity`、`overweight`、`weight loss`、`weight reduction`、`weight management`、`body weight`。
  - この拡張により、糖尿病を合併しない純粋な肥満試験（例：SURMOUNT-1、SURMOUNT-5）も結果セットに含まれるようになった（T2DM 語のみの旧設計では脱落していた）。

MeSH 用語は事前に `mesh` サブコマンドで実在を確認した。すべての検索で `phrasesNotFound` は空（＝索引に存在しない語による取りこぼしなし）であることを確認している。

### 1-2. 実行した検索式とヒット件数

#### 【検索A】網羅的検索（薬剤 × 疾患、動物のみ除外） ― **1,943 件**

🔗 [この検索を PubMed で開く](https://pubmed.ncbi.nlm.nih.gov/?term=%28%28%28%22Tirzepatide%22%5Bmh%5D+OR+tirzepatide%5Btiab%5D+OR+LY3298176%5Btiab%5D+OR+Mounjaro%5Btiab%5D+OR+Zepbound%5Btiab%5D%29+AND+%28%22Diabetes+Mellitus%2C+Type+2%22%5Bmh%5D+OR+%22type+2+diabetes%22%5Btiab%5D+OR+%22type+2+diabetes+mellitus%22%5Btiab%5D+OR+%22type+II+diabetes%22%5Btiab%5D+OR+T2DM%5Btiab%5D+OR+%22non-insulin-dependent+diabetes%22%5Btiab%5D+OR+%22Obesity%22%5Bmh%5D+OR+%22Overweight%22%5Bmh%5D+OR+obesity%5Btiab%5D+OR+overweight%5Btiab%5D+OR+%22weight+loss%22%5Btiab%5D+OR+%22weight+reduction%22%5Btiab%5D+OR+%22weight+management%22%5Btiab%5D+OR+%22body+weight%22%5Btiab%5D%29%29+AND+%282021%2F01%2F01%3A2026%2F12%2F31%5Bpdat%5D%29%29+NOT+%28animals%5Bmh%5D+NOT+humans%5Bmh%5D%29)

設計意図：チルゼパチド × （T2DM ＋ 肥満）に関する文献全体像（総説・レター・解析含む）を把握するための最大再現率の検索。

PubMed に送信した実際の translated query（`queryTranslation`）：

```
(("Tirzepatide"[MeSH Terms] OR "Tirzepatide"[Title/Abstract] OR "LY3298176"[Title/Abstract]
  OR "Mounjaro"[Title/Abstract] OR "Zepbound"[Title/Abstract])
 AND ("diabetes mellitus, type 2"[MeSH Terms] OR "type 2 diabetes"[Title/Abstract]
  OR "type 2 diabetes mellitus"[Title/Abstract] OR "type II diabetes"[Title/Abstract]
  OR "T2DM"[Title/Abstract] OR "non-insulin-dependent diabetes"[Title/Abstract]
  OR "Obesity"[MeSH Terms] OR "Overweight"[MeSH Terms] OR "obesity"[Title/Abstract]
  OR "overweight"[Title/Abstract] OR "weight loss"[Title/Abstract]
  OR "weight reduction"[Title/Abstract] OR "weight management"[Title/Abstract]
  OR "body weight"[Title/Abstract])
 AND 2021/01/01:2026/12/31[Date - Publication])
NOT ("animals"[MeSH Terms] NOT "humans"[MeSH Terms])
```

> **参考（疾患別内訳）：** T2DM 語のみ 1,122 件、肥満語のみ 1,692 件、両者 OR で **1,943 件**（重複を除いた和集合）。肥満の literature は T2DM を上回る規模に達している。

#### 【検索B】臨床研究セット（有効性・臨床試験に絞り込み） ― **720 件**（CSV 出力対象）

🔗 [この検索を PubMed で開く](https://pubmed.ncbi.nlm.nih.gov/?term=%28%28%28%22Tirzepatide%22%5Bmh%5D+OR+tirzepatide%5Btiab%5D+OR+LY3298176%5Btiab%5D+OR+Mounjaro%5Btiab%5D+OR+Zepbound%5Btiab%5D%29+AND+%28%22Diabetes+Mellitus%2C+Type+2%22%5Bmh%5D+OR+%22type+2+diabetes%22%5Btiab%5D+OR+%22type+2+diabetes+mellitus%22%5Btiab%5D+OR+%22type+II+diabetes%22%5Btiab%5D+OR+T2DM%5Btiab%5D+OR+%22non-insulin-dependent+diabetes%22%5Btiab%5D+OR+%22Obesity%22%5Bmh%5D+OR+%22Overweight%22%5Bmh%5D+OR+obesity%5Btiab%5D+OR+overweight%5Btiab%5D+OR+%22weight+loss%22%5Btiab%5D+OR+%22weight+reduction%22%5Btiab%5D+OR+%22weight+management%22%5Btiab%5D+OR+%22body+weight%22%5Btiab%5D%29+AND+%28%22Randomized+Controlled+Trial%22%5Bpt%5D+OR+%22Clinical+Trial%22%5Bpt%5D+OR+%22Controlled+Clinical+Trial%22%5Bpt%5D+OR+%22Pragmatic+Clinical+Trial%22%5Bpt%5D+OR+randomized%5Btiab%5D+OR+randomised%5Btiab%5D+OR+placebo%5Btiab%5D+OR+%22double-blind%22%5Btiab%5D+OR+%22open-label%22%5Btiab%5D+OR+%22phase+3%22%5Btiab%5D+OR+%22phase+2%22%5Btiab%5D+OR+SURPASS%5Btiab%5D+OR+SURMOUNT%5Btiab%5D+OR+%22clinical+trial%22%5Btiab%5D%29%29+AND+%282021%2F01%2F01%3A2026%2F12%2F31%5Bpdat%5D%29%29+NOT+%28animals%5Bmh%5D+NOT+humans%5Bmh%5D%29)

設計意図：検索Aに **臨床試験の Publication Type と臨床試験を示す自由語**を OR で追加し、「臨床研究・有効性」の証拠ベースに絞り込む。Publication Type（`Randomized Controlled Trial`[pt] 等）は手作業で付与されるため索引遅延の影響を受ける。そこで **`randomized` / `placebo` / `double-blind` / `open-label` / `phase 2/3` / `SURPASS` / `SURMOUNT` 等の自由語を OR に併用**して再現率を補った。

検索A のクエリに、以下の臨床試験フィルタ節を AND 結合：

```
AND ("Randomized Controlled Trial"[Publication Type] OR "Clinical Trial"[Publication Type]
  OR "Controlled Clinical Trial"[Publication Type] OR "Pragmatic Clinical Trial"[Publication Type]
  OR "randomized"[Title/Abstract] OR "randomised"[Title/Abstract] OR "placebo"[Title/Abstract]
  OR "double-blind"[Title/Abstract] OR "open-label"[Title/Abstract] OR "phase 3"[Title/Abstract]
  OR "phase 2"[Title/Abstract] OR "SURPASS"[Title/Abstract] OR "SURMOUNT"[Title/Abstract]
  OR "clinical trial"[Title/Abstract])
```

この 720 件を発行日降順で取得し、CSV（`tirzepatide_t2dm_obesity_list.csv`）に出力した。SURMOUNT-1（PMID 35658024、糖尿病を合併しない肥満の旗艦試験）を含む純粋な肥満試験も、この拡張により結果セットに正しく含まれることを確認済み。

#### 【検索C】RCT 精密検索（Publication Type = RCT のみ） ― **120 件**

🔗 [この検索を PubMed で開く](https://pubmed.ncbi.nlm.nih.gov/?term=%28%28%28%22Tirzepatide%22%5Bmh%5D+OR+tirzepatide%5Btiab%5D+OR+LY3298176%5Btiab%5D+OR+Mounjaro%5Btiab%5D+OR+Zepbound%5Btiab%5D%29+AND+%28%22Diabetes+Mellitus%2C+Type+2%22%5Bmh%5D+OR+%22type+2+diabetes%22%5Btiab%5D+OR+%22type+2+diabetes+mellitus%22%5Btiab%5D+OR+%22type+II+diabetes%22%5Btiab%5D+OR+T2DM%5Btiab%5D+OR+%22non-insulin-dependent+diabetes%22%5Btiab%5D+OR+%22Obesity%22%5Bmh%5D+OR+%22Overweight%22%5Bmh%5D+OR+obesity%5Btiab%5D+OR+overweight%5Btiab%5D+OR+%22weight+loss%22%5Btiab%5D+OR+%22weight+reduction%22%5Btiab%5D+OR+%22weight+management%22%5Btiab%5D+OR+%22body+weight%22%5Btiab%5D%29+AND+%22Randomized+Controlled+Trial%22%5Bpt%5D%29+AND+%282021%2F01%2F01%3A2026%2F12%2F31%5Bpdat%5D%29%29+NOT+%28animals%5Bmh%5D+NOT+humans%5Bmh%5D%29)

設計意図：ランドマーク試験（一次 RCT 論文）を高精度で同定するための参照用検索。検索A に `"Randomized Controlled Trial"[Publication Type]` のみを AND 結合。ここから SURPASS／SURMOUNT 各試験の一次論文を特定した（後述）。

### 1-3. 発行年の分布（検索B：臨床研究セット 720 件）

| 発行年 | 件数 |
|---|---:|
| 2021 | 10 |
| 2022 | 41 |
| 2023 | 85 |
| 2024 | 111 |
| 2025 | 239 |
| 2026 | 234 |
| **合計** | **720** |

一次ピボタル試験は 2021～2023 年に集中し、2024 年以降は post-hoc 解析・サブグループ解析・メタ解析・実臨床データが大半を占める。この時系列は「ピボタル試験 → 追加解析・実装研究」というエビデンス成熟の典型的パターンを示している。肥満を加えたことで 2024～2026 年の増加が顕著となり、これは近年 tirzepatide の減量適応・実臨床データが急増していることを反映している。

---

## 2. 主要な試験プログラム／ランドマーク試験の整理

### 2-1. SURPASS プログラム（T2DM 対象の第3相）

チルゼパチドの T2DM 適応は、グローバル第3相 **SURPASS-1～6** と地域試験（日本：J-mono / J-combo、アジア太平洋：AP-Combo）、および心血管アウトカム試験 **SURPASS-CVOT** で構成される。用量は原則 5 / 10 / 15 mg の週1回皮下注。主要評価項目はいずれも HbA1c のベースラインからの変化。

| 試験 | 比較対照・背景治療 | 期間 | 主な対象・N | 主要な有効性所見 | 文献 (PMID) |
|---|---|---|---|---|---|
| **SURPASS-1** | プラセボ（単剤療法） | 40週 | 食事・運動のみで不十分な T2DM、N=478 | 全用量でプラセボに優越。HbA1c・体重ともに用量依存的に低下 | (1) (34186022) |
| **SURPASS-2** | セマグルチド 1 mg（head-to-head） | 40週 | メトホルミン併用、N=1,879 | HbA1c 変化 −2.01/−2.24/−2.30%（tirzepatide 5/10/15 mg）vs −1.86%（sema）。**全用量で非劣性かつ優越** | (2) (34170647) |
| **SURPASS-3** | インスリン デグルデク（基礎） | 52週 | メトホルミン±SGLT2i、N=1,444 | HbA1c・体重ともにデグルデクに優越。デグルデクは体重増加、tirzepatide は体重減少 | (3) (34370970) |
| **SURPASS-4** | インスリン グラルギン（心血管高リスク） | ≥52週 | 心血管高リスク T2DM、N=2,002 | HbA1c でグラルギンに非劣性・優越。心血管安全性シグナルなし | (4) (34672967) |
| **SURPASS-5** | プラセボ（基礎インスリン グラルギンに追加） | 40週 | グラルギン治療中で不十分、N=475 | プラセボ追加に対し HbA1c・体重を有意に改善 | (5) (35133415) |
| **SURPASS-6** | インスリン リスプロ（食前インスリン、基礎に追加） | 52週 | 基礎インスリン治療中、N=1,428（phase 3b） | リスプロ追加に対し HbA1c 低下で非劣性かつ優越、体重は減少 vs 増加 | (6) (37786396) |

**地域・アジア試験**

| 試験 | 比較対照・背景 | 対象 | 主な所見 | 文献 (PMID) |
|---|---|---|---|---|
| **SURPASS J-mono**（日本） | デュラグルチド 0.75 mg（単剤） | 日本人 T2DM | デュラグルチドに対し HbA1c・体重で優越 | (7) (35914543) |
| **SURPASS J-combo**（日本） | 経口血糖降下薬1剤に追加（対照群なしの用量評価） | 日本人 T2DM | 経口薬併用下で良好な HbA1c・体重反応と安全性 | (8) (35914542) |
| **SURPASS-AP-Combo**（アジア太平洋） | インスリン グラルギン（2次/3次治療） | 中国等アジア太平洋 T2DM、N≈917 | グラルギンに対し HbA1c 低下で優越、体重減少 | (9) (37231074) |

### 2-2. SURPASS-CVOT（心血管アウトカム試験）

T2DM 治療薬にとって心血管アウトカムの検証は臨床的位置づけを左右する重要ステップである。

- **設計・ベースライン論文**（2024, Am Heart J, PMID 37758044）：アテローム動脈硬化性心血管疾患を有する T2DM を対象に、**tirzepatide（最大15 mg）vs デュラグルチド 1.5 mg** を比較する二重盲検・実薬対照・非劣性試験。デュラグルチド（REWIND で心血管イベント抑制が示された薬剤）を能動対照に置いた点が特徴 (11)。
- **一次結果**（2025, N Engl J Med, PMID 41406444）：13,299 例をランダム化（modified ITT：tirzepatide 6,586 例／dulaglutide 6,579 例）。主要評価項目は 3-point MACE（心血管死・心筋梗塞・脳卒中）。**非劣性マージン（HR 上限 1.05）を満たし、tirzepatide のデュラグルチドに対する非劣性を達成**（優越性の閾値は HR 上限 <1.00）。加えて心腎アウトカム・体重・血糖の副次評価で良好な結果が報告された (10)。

### 2-3. SURMOUNT プログラム（肥満対象）

**SURMOUNT** は肥満・過体重を対象とした別の第3相プログラム（SURMOUNT-1～5、REAL、MAINTAIN、MMO 等）であり、T2DM の有無を問わず体重管理を主要評価項目とする。本検索でも SURMOUNT 由来の論文が多数ヒットした。主要試験の減量効果は以下のとおり。

| 試験 | 対照・対象 | 期間 | 主要な有効性所見 | 文献 (PMID) |
|---|---|---|---|---|
| **SURMOUNT-1** | プラセボ／糖尿病**なし**の肥満、N=2,539 | 72週 | 体重変化 −15.0/−19.5/−20.9%（5/10/15 mg）vs プラセボ −3.1%。全用量でプラセボに優越 | (15) (35658024) |
| **SURMOUNT-2** | プラセボ／T2DM **合併**の肥満、N=938 | 72週 | T2DM 合併肥満でも 10/15 mg でプラセボに対し有意な体重減少・血糖改善 | (16) (37385275) |
| **SURMOUNT-5** | セマグルチド 2.4 mg（head-to-head）／糖尿病なしの肥満、N=751 | 72週 | 体重変化 −20.2% vs セマグルチド −13.7%（p<0.001）。腹囲もより大きく減少 | (17) (40353578) |

T2DM の**血糖**有効性は SURPASS が主エビデンスであり、SURMOUNT は**体重・代謝**アウトカムおよび T2DM 合併肥満例での知見を補完する。両プログラムを通じて、tirzepatide は「血糖低下と体重減少を同時に達成する」という一貫した特徴を示す。

### 2-4. エビデンスの発展（post-hoc・統合解析）

720 件の多くは一次試験に基づく追加解析であり、有効性の頑健性を裏付ける。代表例：

- **SURPASS-1～5 統合解析**：血糖目標（HbA1c <7.0%、≤6.5%、<5.7%）の達成率が低血糖・体重増加を伴わず高いことを示す (12)（PMID 36514843）。
- **ベースライン非依存性**（SURPASS-1～5、2025）：有効性・安全性が年齢・BMI・罹病期間等のベースライン特性によらず一貫 (13)（PMID 39531161）。
- **ネットワークメタ解析**（2026）：tirzepatide と GLP-1 受容体作動薬の心血管アウトカムの比較 (14)（PMID 41761267）。

---

## 2.5. 有効性の総括 ― 検索から何がわかったか

本検索（2021年以降の臨床研究）から読み取れる、チルゼパチドの有効性に関する要点を以下にまとめる。

### 2型糖尿病（血糖・体重）

- **HbA1c 低下は既存治療を上回る。** SURPASS-1～6 を通じ、tirzepatide は**プラセボ、基礎インスリン（デグルデク・グラルギン）、食前インスリン（リスプロ）、および GLP-1 受容体作動薬（セマグルチド 1 mg、デュラグルチド 0.75 mg）に対して HbA1c 低下で非劣性かつ多くは優越**を示した (1)–(9)。とくに GLP-1 単剤（セマグルチド）との直接比較 SURPASS-2 では、10・15 mg で明確な優越性が示され、デュアルアゴニストの上乗せ効果が裏付けられた (2)。
- **血糖と体重を同時に改善する。** すべての SURPASS 試験で HbA1c 低下と**体重減少**が並行して得られ、インスリン群が体重増加を示すのと対照的であった。厳格な血糖目標（HbA1c <5.7%＝正常血糖域）への到達も、**低血糖や体重増加を伴わずに**高率で達成された (12)。
- **効果は幅広い患者背景で一貫。** 年齢・BMI・罹病期間・ベースライン HbA1c などによらず有効性・安全性が保たれることが統合解析で示され、東アジア人（日本・中国・アジア太平洋）を対象とした地域試験でも同様の結果が再現された (7)(8)(9)(13)。
- **心血管安全性が確認された。** SURPASS-CVOT により、確立した心血管疾患を有する T2DM において、心血管イベント抑制が実証済みのデュラグルチドに対して **MACE で非劣性**が示され、心血管安全性の懸念がないことが確認された (10)(11)。

### 肥満（体重管理）

- **減量効果は GLP-1 単剤を上回る。** 糖尿病のない肥満を対象とした SURMOUNT-1 では 72週で最大 **−20.9%**（15 mg）の体重減少が得られ (15)、セマグルチド 2.4 mg との直接比較 SURMOUNT-5 では **−20.2% vs −13.7%** と tirzepatide が有意に優れた (17)。
- **T2DM 合併肥満でも有効。** SURMOUNT-2 では、一般に減量が得られにくいとされる T2DM 合併肥満例でも、プラセボに対し有意な体重減少と血糖改善が示された (16)。

### 副作用・服用上のデメリット

有効性の裏返しとして、以下の安全性・負担面のデメリットが臨床試験・メタ解析で一貫して報告されている。有効性と併せて総合的に評価する必要がある。

- **消化器系有害事象が最も多い。** 悪心（12～23%）、下痢（13～22%）、嘔吐（5～10%）、食欲低下（9～11%）、便秘が主で、いずれもプラセボ・インスリン・GLP-1 単剤より高頻度。多くは**軽度～中等度で、用量漸増期に集中**して一過性に経過する (2)(4)(18)。ただし患者にとっては継続の障壁となり、**有害事象による投与中止は約 4～7%**にみられる (15)。
- **低血糖は単剤では少ないが、併用で増える。** 単剤やインスリンとの比較では低血糖はむしろインスリン群より低頻度だが、**スルホニル尿素薬やインスリンと併用**すると低血糖リスクが上昇する。これらとの併用時は併用薬の減量を要する (4)。
- **膵炎・胆道系疾患のリスク。** GLP-1／GIP 系薬剤に共通する懸念として、**急性膵炎および胆石症・胆嚢炎などの胆道系イベント**の報告がある。メタ解析では、急性の大幅な体重減少に伴い胆嚢・胆道系イベントが対照より増加する傾向が示されており、注意が必要 (19)。
- **投与形態・漸増の負担。** **週1回の皮下注射**製剤であり、経口薬に比べ手技・保管の負担がある。消化器症状を抑えるため 2.5 mg から数週ごとに漸増する必要があり、目標用量到達まで時間を要する (1)(6)。
- **除脂肪量（筋肉量）減少・中止後のリバウンド。** 大幅な体重減少に伴い脂肪だけでなく**除脂肪量（筋肉量）も一部減少**すること、また**投与を中止すると体重が再増加**しやすいことが体組成解析・中止試験で示されており、長期・継続的な使用と生活習慣介入の併用が前提となる。
- **規制上の警告・禁忌（クラス共通）。** 添付文書では、**甲状腺髄様癌（MTC）・多発性内分泌腫瘍症2型（MEN2）の既往・家族歴**が禁忌とされる（げっ歯類での甲状腺 C 細胞腫瘍所見に基づくクラス警告）。また妊娠中の使用は推奨されない。
- **長期・実臨床データの制約とコスト。** 心血管アウトカムは 2025 年に SURPASS-CVOT で示されたばかりで、超長期の安全性・アウトカムデータは蓄積途上。高薬価による経済的負担も実装上の課題である。

### 総合（ベネフィットとリスクのバランス）

チルゼパチドは **GIP／GLP-1 デュアルアゴニズム**により、次の3点を**単剤で同時に**達成できる点に最大の臨床的価値がある。

1. 既存の血糖降下薬や GLP-1 受容体作動薬（セマグルチド）を上回る **HbA1c 低下**（T2DM）(1)–(9)
2. 臨床的に意義のある **体重減少**（肥満で最大約 21%、セマグルチドを上回る）(15)–(17)
3. 心血管疾患を有する T2DM で **心血管イベントの増加を伴わないこと**（デュラグルチドに対する MACE 非劣性として確認）(10)(11)

一方で、**消化器症状を中心とする有害事象**、膵炎・胆道系リスク、注射・漸増の負担、除脂肪量減少や中止後リバウンドといったデメリットを伴う。総じて、「血糖と体重の同時改善」という高い有効性が、主に一過性・管理可能な消化器系有害事象と引き換えに得られる薬剤と位置づけられ、適応・併用薬・患者背景を踏まえたベネフィット／リスク評価が求められる。T2DM では SURPASS が血糖有効性の、肥満では SURMOUNT が減量有効性の中核エビデンスを提供している。

---

## 3. 引用文献リスト（Vancouver 形式）

本レポートの記述に用いた文献。ICMJE 準拠（著者6名まで＋et al.）。

1. Rosenstock J, Wysham C, Frías JP, Kaneko S, Lee CJ, Fernández Landó L, et al. Efficacy and safety of a novel dual GIP and GLP-1 receptor agonist tirzepatide in patients with type 2 diabetes (SURPASS-1): a double-blind, randomised, phase 3 trial. Lancet. 2021;398(10295):143-155. doi:10.1016/S0140-6736(21)01324-6.

2. Frías JP, Davies MJ, Rosenstock J, Pérez Manghi FC, Fernández Landó L, Bergman BK, et al. Tirzepatide versus Semaglutide Once Weekly in Patients with Type 2 Diabetes. N Engl J Med. 2021;385(6):503-515. doi:10.1056/NEJMoa2107519.

3. Ludvik B, Giorgino F, Jódar E, Frias JP, Fernández Landó L, Brown K, et al. Once-weekly tirzepatide versus once-daily insulin degludec as add-on to metformin with or without SGLT2 inhibitors in patients with type 2 diabetes (SURPASS-3): a randomised, open-label, parallel-group, phase 3 trial. Lancet. 2021;398(10300):583-598. doi:10.1016/S0140-6736(21)01443-4.

4. Del Prato S, Kahn SE, Pavo I, Weerakkody GJ, Yang Z, Doupis J, et al. Tirzepatide versus insulin glargine in type 2 diabetes and increased cardiovascular risk (SURPASS-4): a randomised, open-label, parallel-group, multicentre, phase 3 trial. Lancet. 2021;398(10313):1811-1824. doi:10.1016/S0140-6736(21)02188-7.

5. Dahl D, Onishi Y, Norwood P, Huh R, Bray R, Patel H, et al. Effect of Subcutaneous Tirzepatide vs Placebo Added to Titrated Insulin Glargine on Glycemic Control in Patients With Type 2 Diabetes: The SURPASS-5 Randomized Clinical Trial. JAMA. 2022;327(6):534-545. doi:10.1001/jama.2022.0078.

6. Rosenstock J, Frías JP, Rodbard HW, Tofé S, Sears E, Huh R, et al. Tirzepatide vs Insulin Lispro Added to Basal Insulin in Type 2 Diabetes: The SURPASS-6 Randomized Clinical Trial. JAMA. 2023;330(17):1631-1640. doi:10.1001/jama.2023.20294.

7. Inagaki N, Takeuchi M, Oura T, Imaoka T, Seino Y. Efficacy and safety of tirzepatide monotherapy compared with dulaglutide in Japanese patients with type 2 diabetes (SURPASS J-mono): a double-blind, multicentre, randomised, phase 3 trial. Lancet Diabetes Endocrinol. 2022;10(9):623-633. doi:10.1016/S2213-8587(22)00188-7.

8. Kadowaki T, Chin R, Ozeki A, Imaoka T, Ogawa Y. Safety and efficacy of tirzepatide as an add-on to single oral antihyperglycaemic medication in patients with type 2 diabetes in Japan (SURPASS J-combo): a multicentre, randomised, open-label, parallel-group, phase 3 trial. Lancet Diabetes Endocrinol. 2022;10(9):634-644. doi:10.1016/S2213-8587(22)00187-5.

9. Gao L, Lee BW, Chawla M, Kim J, Huo L, Du L, et al. Tirzepatide versus insulin glargine as second-line or third-line therapy in type 2 diabetes in the Asia-Pacific region: the SURPASS-AP-Combo trial. Nat Med. 2023;29(6):1500-1510. doi:10.1038/s41591-023-02344-1.

10. Nicholls SJ, Pavo I, Bhatt DL, Buse JB, Del Prato S, Kahn SE, et al. Cardiovascular Outcomes with Tirzepatide versus Dulaglutide in Type 2 Diabetes. N Engl J Med. 2025;393(24):2409-2420. doi:10.1056/NEJMoa2505928.

11. Nicholls SJ, Bhatt DL, Buse JB, Prato SD, Kahn SE, Lincoff AM, et al. Comparison of tirzepatide and dulaglutide on major adverse cardiovascular events in participants with type 2 diabetes and atherosclerotic cardiovascular disease: SURPASS-CVOT design and baseline characteristics. Am Heart J. 2024;267:1-11. doi:10.1016/j.ahj.2023.09.007.

12. Lingvay I, Cheng AY, Levine JA, Gomez-Valderas E, Allen SE, Ranta K, et al. Achievement of glycaemic targets with weight loss and without hypoglycaemia in type 2 diabetes with the once-weekly glucose-dependent insulinotropic polypeptide and glucagon-like peptide-1 receptor agonist tirzepatide: A post hoc analysis of the SURPASS-1 to -5 studies. Diabetes Obes Metab. 2023;25(4):965-974. doi:10.1111/dom.14943.

13. De Block C, Peleshok J, Wilding JPH, Kwan AYM, Rasouli N, Maldonado JM, et al. Post Hoc Analysis of SURPASS-1 to -5: Efficacy and Safety of Tirzepatide in Adults with Type 2 Diabetes are Independent of Baseline Characteristics. Diabetes Ther. 2025;16(1):43-71. doi:10.1007/s13300-024-01660-0.

14. Shokravi A, Seth J, Mancini GBJ. Comparative efficacy of tirzepatide and glucagon-like peptide-1 receptor agonists on cardiovascular outcomes in patients with type 2 diabetes: a systematic review and network meta-analysis. Cardiovasc Diabetol. 2026;25(1). doi:10.1186/s12933-026-03113-3.

15. Jastreboff AM, Aronne LJ, Ahmad NN, Wharton S, Connery L, Alves B, et al. Tirzepatide Once Weekly for the Treatment of Obesity. N Engl J Med. 2022;387(3):205-216. doi:10.1056/NEJMoa2206038.

16. Garvey WT, Frias JP, Jastreboff AM, le Roux CW, Sattar N, Aizenberg D, et al. Tirzepatide once weekly for the treatment of obesity in people with type 2 diabetes (SURMOUNT-2): a double-blind, randomised, multicentre, placebo-controlled, phase 3 trial. Lancet. 2023;402(10402):613-626. doi:10.1016/S0140-6736(23)01200-X.

17. Aronne LJ, Horn DB, le Roux CW, Ho W, Falcon BL, Gomez Valderas E, et al. Tirzepatide as Compared with Semaglutide for the Treatment of Obesity. N Engl J Med. 2025;393(1):26-36. doi:10.1056/NEJMoa2416394.

18. Tong K, Yin S, Yu Y, Yang X, Hu G, Zhang F, et al. Gastrointestinal adverse events of tirzepatide in the treatment of type 2 diabetes mellitus: A meta-analysis and trials sequential analysis. Medicine (Baltimore). 2023;102(43):e35488. doi:10.1097/MD.0000000000035488.

19. Zeng Q, Xu J, Mu X, Shi Y, Fan H, Li S. Safety issues of tirzepatide (pancreatitis and gallbladder or biliary disease) in type 2 diabetes and obesity: a systematic review and meta-analysis. Front Endocrinol (Lausanne). 2023;14:1214334. doi:10.3389/fendo.2023.1214334.

---

## 付記：方法論上の注意と限界

- **検索の再現性：** 上記の translated query（`queryTranslation`）はレポート作成時（2026-07-18）のもの。PubMed のインデックスは日々更新されるため、再実行時に件数が変動しうる。報告した件数は送信クエリ（`query`）ではなく実際に PubMed が解釈した `queryTranslation` に基づく。
- **除外の性質：** 「動物のみ」除外は MeSH ヘッジによるもので、ヒト対象であることを MeSH タグで積極的に要求してはいない（再現率優先）。厳密にヒトタグ付き論文のみに限定したい場合は `humans[MeSH Terms]` を AND する別設計となる。
- **CSV の範囲：** 添付 CSV（`tirzepatide_t2dm_obesity_list.csv`）は検索B（臨床研究セット 720 件、T2DM ＋ 肥満）の全件。自由語フィルタ（`randomized`, `placebo`, `trial` 等）を含むため、一部に総説・メタ解析・実装研究が含まれる。純粋な一次 RCT のみを見る場合は検索C（RCT 120 件）を参照。
- **改訂履歴：** 初版は疾患節を T2DM 語のみとしたため肥満単独試験（SURMOUNT-1 等）が結果に含まれず、本文では別途の補助検索で得た文献を引用していた。本版では疾患節に肥満・過体重を OR で追加し、検索式・件数・CSV を更新（459→720 件）。これにより本文の引用文献はすべて検索B の結果セット内に含まれる。
- **有効性の焦点：** 本レポートは血糖（HbA1c）と体重を中心とする有効性に主眼を置いた。安全性（消化器系有害事象、低血糖等）や心腎の詳細アウトカムは各一次論文・追加解析を参照のこと。
