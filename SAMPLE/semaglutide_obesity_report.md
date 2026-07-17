# セマグルチドの肥満治療への適用に関するエビデンスレビュー
## ―― 2020年以降の高エビデンスレベル論文 20件 ――

**検索日:** 2026年7月17日
**データベース:** PubMed（NCBI E-utilities 経由）
**対象期間:** 2020年1月1日以降（出版日基準）
**選定件数:** 20件（ランダム化比較試験 18件、システマティックレビュー／メタ解析 2件）
**付属ファイル:** `semaglutide_obesity_20refs.csv`（文献リスト・全20件のメタデータ）

---

## 1. エグゼクティブサマリー

2020年以降、セマグルチドの肥満治療への適用は「体重を減らす薬」から「肥満関連アウトカムを改善する薬」へとエビデンスの重心が移った。本レビューで選定した20件は、その変遷を4つの段階で示している。

1. **有効性の確立（STEP 1〜8, 2021–2022）** — 週1回皮下投与セマグルチド2.4 mgは、糖尿病を伴わない過体重・肥満成人で68週時点に平均 **−14.9%** の体重減少をもたらし、プラセボとの差は −12.4ポイントであった [1]。この効果量は既存薬リラグルチド3.0 mgの約2.5倍であり [7]、2年間持続する [5]。

2. **投与経路・用量の拡張（OASIS, STEP UP, 2023–2025）** — 経口50 mg [10]・経口25 mg [11] が注射剤に匹敵する減量を示し、高用量7.2 mgは2.4 mgをさらに3.1ポイント上回った [9]。

3. **ハードアウトカムへの到達（SELECT, STEP-HFpEF, 2023–2024）** — SELECT試験は17,604例で主要心血管イベントを **20%減少**（HR 0.80）させ [12]、肥満治療薬として初めて心血管アウトカムの改善を証明した。HFpEF [14][15] や変形性膝関節症 [16] でも症状改善が示された。

4. **次世代治療との比較（2025）** — チルゼパチドはセマグルチドを直接比較で上回り（−20.2% vs −13.7%）[17]、カグリリンチド併用は −20.4% に達した [18]。セマグルチドは「基準薬」の位置づけへ移行しつつある。

**安全性の一貫した所見:** 消化器系有害事象が最も多く（経口50 mgで80%、注射剤で概ね70〜80%台）、多くは軽度〜中等度かつ用量漸増期に集中する。Cochraneレビューは減量効果を「高い確実性」と評価する一方、重篤な有害事象への影響は「非常に低い確実性」にとどまると結論している [19]。

---

## 2. 検索方法（検索式）

### 2.1 統制語（MeSH）の同定

検索に先立ち、MeSHデータベースで統制語を確認した。

| 概念 | MeSH記述子 | MeSH UI | ツリー番号 | 主な同義語（Entry Terms） |
|---|---|---|---|---|
| セマグルチド | `Semaglutide` | D000099194 | D06.472.317.680.500.751 | Ozempic, Rybelsus, Wegovy |
| 肥満 | `Obesity` | D009765 | C18.654.726.750.500 / C23.888.144.699.500 | — |

`Semaglutide` の scope note に "for OBESITY MANAGEMENT" が明記されており、本トピックに対する統制語として妥当と判断した。フリーテキスト検索ではなく MeSH 検索を採用することで、商品名（Wegovy 等）や表記ゆれを自動的に包含している。

### 2.2 検索式1 — ランダム化比較試験（主検索）

```
"Semaglutide"[MeSH Terms] AND "Obesity"[MeSH Terms]
AND "Randomized Controlled Trial"[Publication Type]
AND hasabstract
AND (2020/01/01:3000[pdat])
```

**ヒット件数: 97件**

[PubMedで実行](https://pubmed.ncbi.nlm.nih.gov/?term=%22Semaglutide%22%5BMeSH+Terms%5D+AND+%22Obesity%22%5BMeSH+Terms%5D+AND+%22Randomized+Controlled+Trial%22%5BPublication+Type%5D+AND+hasabstract+AND+%282020%2F01%2F01%3A3000%5Bpdat%5D%29)

### 2.3 検索式2 — システマティックレビュー／メタ解析（補完検索）

```
"Semaglutide"[MeSH Terms] AND "Obesity"[MeSH Terms]
AND ("Meta-Analysis"[Publication Type] OR "Systematic Review"[Publication Type])
AND hasabstract
AND (2020/01/01:3000[pdat])
```

**ヒット件数: 79件**

### 2.4 実行コマンド（再現用）

本検索は `pubmed-research` スキル（NCBI E-utilities ラッパー）で実行した。

```bash
# 検索式1: RCT
python scripts/pubmed.py search --mesh "Semaglutide" "Obesity" \
    --pubtype "Randomized Controlled Trial" \
    --min-date 2020/01/01 --has-abstract \
    --limit 40 --sort relevance --summaries

# 検索式2: SR/メタ解析
python scripts/pubmed.py search --mesh "Semaglutide" "Obesity" \
    --pubtype "Meta-Analysis" "Systematic Review" \
    --min-date 2020/01/01 --has-abstract \
    --limit 25 --sort relevance --summaries

# 選定20件のメタデータ取得 → CSV出力
python scripts/pubmed.py fetch <20 PMIDs> | python scripts/to_csv.py -o semaglutide_obesity_20refs.csv

# Vancouver形式引用の生成
python scripts/pubmed.py cite <20 PMIDs> --style vancouver
```

### 2.5 選定基準

計176件の候補から、以下の方針で20件を選定した。

- **包含:** ① 肥満・過体重を対象集団または主要評価項目に含む第3相以上のRCT、② 追跡期間・症例数・掲載誌の観点からランドマークと位置づけられる試験、③ エビデンスを統合する高品質なシステマティックレビュー
- **優先:** NEJM / Lancet / JAMA / Nature Medicine / Lancet Diabetes & Endocrinology / Cochrane などの高インパクト誌
- **網羅性の確保:** 用量・投与経路・対象集団（成人／小児／東アジア人／併存疾患）・アウトカム（体重／心血管／心不全／疼痛）が偏らないよう分野横断的に配分
- **除外:** 事後解析のうち独立した臨床的価値が乏しいもの、症例数の小さい探索的試験、対象が肥満以外に限定されるもの

### 2.6 選定20件の内訳

| カテゴリ | 件数 | 該当文献 |
|---|---|---|
| STEP試験群（中心的有効性） | 8 | [1][2][3][4][5][6][7][8] |
| 高用量・経口製剤 | 3 | [9][10][11] |
| 心血管・心不全・疼痛アウトカム | 5 | [12][13][14][15][16] |
| 他剤比較・併用療法 | 2 | [17][18] |
| エビデンス統合（SR/メタ解析） | 2 | [19][20] |

---

## 3. 主要知見

### 3.1 STEP試験群 ―― 有効性の確立（2021–2022）

STEP（Semaglutide Treatment Effect in People with obesity）プログラムは、セマグルチド2.4 mg週1回の肥満適応を確立した第3相試験群である。

**STEP 1**（NEJM 2021）は、糖尿病を伴わないBMI 30以上（または27以上＋合併症1つ以上）の成人1,961例を2:1でランダム化し、68週投与した。体重変化は **セマグルチド群 −14.9% / プラセボ群 −2.4%**、推定治療差 **−12.4ポイント**（95%CI −13.4〜−11.5, P<0.001）であった [1]。これが以降のすべての比較の基準値となる。

**STEP 2**（Lancet 2021）は2型糖尿病を併存する1,210例が対象。体重変化は **−9.6% vs −3.4%**（差 −6.2ポイント, 95%CI −7.3〜−5.2, p<0.0001）、5%以上減量達成は68.8% vs 28.5%（OR 4.88）[2]。**糖尿病併存例では減量効果が非併存例より小さくなる**という、以降繰り返し確認される現象を最初に示した。

**STEP 3**（JAMA 2021）は集中的行動療法＋低カロリー食を併用した611例で **−16.0% vs −5.7%**（差 −10.3ポイント）[3]。行動療法の上乗せでプラセボ群も5.7%減少するが、薬剤の追加効果は依然として大きい。

**STEP 4**（JAMA 2021）は治療中止の影響を検証した。20週間の導入期（平均10.6%減量）後に803例をランダム化し、20〜68週の体重変化は **継続群 −7.9% / プラセボ切替群 +6.9%**（差 −14.8ポイント, 95%CI −16.0〜−13.5）[4]。**中止すると体重は明確に再増加する**ことを示し、肥満治療が長期継続を前提とすることの根拠となった。

**STEP 5**（Nature Medicine 2022）は104週の長期成績で **−15.2% vs −2.6%**（差 −12.6ポイント）[5]。68週時点の効果が2年間維持されることを示した。

**STEP 6**（Lancet Diabetes Endocrinol 2022）は **日本・韓国の28施設・401例を対象とした東アジア人集団の試験**である。2.4 mg群 −13.2%、1.7 mg群 −9.6%、プラセボ群 −2.1%（2.4 mg vs プラセボの差 −11.1ポイント, 95%CI −12.9〜−9.2）[6]。日本人を含む集団で国際共同試験と整合する効果が確認されており、**国内診療におけるエビデンスの外挿可能性を担保する重要な試験**である。

**STEP 8**（JAMA 2022）はリラグルチド3.0 mgとの直接比較（オープンラベル、338例）。**−15.8% vs −6.4%**（差 −9.4ポイント, 95%CI −12.0〜−6.8）、15%以上減量は55.6% vs 12.0%（OR 7.9）[7]。既存GLP-1受容体作動薬に対する優越性を頭対頭で証明した。

**STEP TEENS**（NEJM 2022）は12〜18歳未満の青年201例が対象。BMI変化は **−16.1% vs +0.6%**（差 −16.7ポイント, 95%CI −20.3〜−13.2）[8]。小児・青年期肥満への適応拡大の根拠となった。

### 3.2 高用量・経口製剤 ―― 投与選択肢の拡張（2023–2025）

**STEP UP**（Lancet Diabetes Endocrinol 2025）は高用量7.2 mgを検証（1,407例）。**7.2 mg −18.7% / 2.4 mg −15.6% / プラセボ −3.9%**。7.2 mg vs 2.4 mgの差は −3.1ポイント（95%CI −4.7〜−1.6, p<0.0001）で、25%以上の減量達成オッズ比は127.4に達した [9]。**用量反応関係が2.4 mgで頭打ちになっていない**ことを示す。

**OASIS 1**（Lancet 2023）は1日1回経口50 mg（667例、68週）で **−15.1% vs −2.4%**（差 −12.7ポイント）[10]。注射剤STEP 1（−14.9%）とほぼ同等であり、経口投与でも同水準の減量が可能であることを示した。消化器系有害事象は80%に発生。

**OASIS 4**（NEJM 2025）は経口25 mg（307例、64週）で **−13.6% vs −2.2%**（差 −11.4ポイント）、消化器系有害事象は74.0% vs 42.2% [11]。50 mgよりわずかに減量幅は小さいが、忍容性とのバランスをとる選択肢を提供する。

### 3.3 アウトカム試験 ―― 体重から予後・症状へ（2023–2025）

**SELECT**（NEJM 2023）は本領域で最も重要な試験である。心血管疾患既往を有し糖尿病を伴わない過体重・肥満患者 **17,604例** を平均39.8か月追跡し、主要心血管イベント（心血管死・非致死性心筋梗塞・非致死性脳卒中）は **6.5% vs 8.0%、HR 0.80**（95%CI 0.72〜0.90, P<0.001）[12]。**肥満治療薬が心血管アウトカムを改善することを初めて証明**した。ただし有害事象による治療中止は16.6% vs 8.2%と約2倍であった。

**SELECT長期体重解析**（Nature Medicine 2024）は事前規定解析として、減量が65週まで進行し **4年間（208週）維持**されることを示した（**−10.2% vs −1.5%**、ウエスト周囲長 −7.7 cm vs −1.3 cm）[13]。性別・人種・体格・地域を問わず臨床的に意味のある減量が得られた。

**STEP-HFpEF**（NEJM 2023）は肥満関連HFpEF患者を対象に、KCCQ-CSS（症状スコア）**+16.6 vs +8.7**（差 7.8点, 95%CI 4.8〜10.9）、体重 −13.3% vs −2.6%、6分間歩行距離 +21.5 m vs +1.2 m、CRP −43.5% vs −7.3% [14]。注目すべきは**重篤な有害事象がセマグルチド群でむしろ少ない**（13.3% vs 26.7%）点である。

**STEP-HFpEF DM**（NEJM 2024）は同じ設計を2型糖尿病併存例616例に適用し、KCCQ-CSS **+13.7 vs +6.4**（差 7.3点）、体重 −9.8% vs −3.4% [15]。糖尿病併存例では減量幅は縮小するが、**症状改善は同等に得られる**ことから、効果が減量のみを介したものではないことが示唆される。

**STEP 9**（NEJM 2024）は肥満＋中等度〜重度の変形性膝関節症407例で、体重 −13.7% vs −3.2%、WOMAC疼痛スコア **−41.7 vs −27.5**（P<0.001）、SF-36身体機能 +12.0 vs +6.5 [16]。疼痛という患者立脚型アウトカムの改善を示した。

### 3.4 他剤比較・併用療法 ―― 基準薬としての位置づけ（2025）

**SURMOUNT-5**（NEJM 2025）はチルゼパチドとの直接比較（751例、72週、オープンラベル）。**チルゼパチド −20.2% / セマグルチド −13.7%**（P<0.001）、ウエスト周囲長 −18.4 cm vs −13.0 cm [17]。**セマグルチドは直接比較で劣後**し、治療アルゴリズム上の位置づけの再考を迫る結果となった。

**REDEFINE 1**（NEJM 2025）はアミリン類似体カグリリンチドとの配合剤を3,417例で検証。**−20.4% vs プラセボ −3.0%**（差 −17.3ポイント, 95%CI −18.1〜−16.6）[18]。消化器系有害事象は79.6% vs 39.9%。セマグルチド単剤の上限を超える減量を、併用戦略で達成しうることを示した。

### 3.5 エビデンス統合

**Cochraneレビュー**（2025）は本トピックで最も方法論的に厳格な統合である。中期（6〜17か月）追跡で体重は **平均差 −10.73%**（95%CI −12.24〜−9.21; 15試験, 8,651例, **高い確実性**）、5%以上減量達成は **RR 2.68**（95%CI 2.30〜3.12; 12試験, 7,458例, **高い確実性**）[19]。一方、**重篤な有害事象は RR 1.01（95%CI 0.78〜1.29）だが確実性は「非常に低い」** と評価され、中止に至る有害事象は RR 1.84（95%CI 1.53〜2.21, 中等度の確実性）であった。QOLへの影響は「ほとんど差がない可能性が高い」とされる。**減量効果は確立しているが、安全性の長期評価は依然として不確実**という、現時点でのエビデンスの偏りを明確に示している。

**Annals of Internal Medicineのシステマティックレビュー**（2025）は26 RCT・15,491例を統合し、薬剤間の相対的位置づけを提示した [20]。

| 薬剤 | 最大減量率（vs プラセボ） | 投与期間 |
|---|---|---|
| レタトルチド 12 mg週1回 | −22.1%（95%CI 19.3〜24.9） | 48週 |
| チルゼパチド 15 mg週1回 | −17.8%（95%CI 16.3〜19.3） | 72週 |
| **セマグルチド 2.4 mg週1回** | **−13.9%（95%CI 11.0〜16.7）** | **68週** |
| リラグルチド 3.0 mg1日1回 | −5.8%（95%CI 3.6〜8.0） | 26週 |

セマグルチドはリラグルチドを大きく上回るが、チルゼパチド・レタトルチドには及ばない、という階層が示されている。

---

## 4. 総括と臨床的示唆

1. **減量効果は確立している。** 一貫して13〜15%（高用量で約19%）の減量が、複数の独立した第3相試験と高い確実性のCochrane評価で支持されている [1][9][19]。
2. **効果は治療継続を前提とする。** 中止により体重は明確に再増加し [4]、肥満は高血圧や脂質異常症と同様、慢性疾患としての継続管理を要する。
3. **糖尿病併存例では減量幅が小さい。** STEP 2 [2]、STEP-HFpEF DM [15] で一貫して確認される。期待値設定に反映すべき所見である。
4. **体重以外のアウトカムが改善する。** 心血管イベント [12]、心不全症状 [14][15]、膝関節痛 [16] への効果は、代理指標を超えた臨床的価値を示す。
5. **日本人を含む東アジア人でも同等の効果が期待できる。** STEP 6 [6] が国内適用の直接的根拠となる。
6. **セマグルチドはもはや最強の選択肢ではない。** チルゼパチド [17] や配合剤 [18] が上回るなか、位置づけは「標準的な基準薬」へと移行している。
7. **安全性評価は未成熟。** 消化器系有害事象の頻度は高く、重篤有害事象に関するエビデンスの確実性は「非常に低い」[19]。長期の市販後データが必要である。

---

## 5. 本レビューの限界

- **検索対象はPubMed単独。** Embase、Cochrane CENTRAL、医中誌Webは検索していないため、網羅性は限定的である。系統的レビューを目的とする場合は複数データベースの併用が必須となる。
- **MeSH索引への依存。** MeSHが未付与の最新論文（PubMed収載直後のもの）は検索式1・2から漏れる可能性がある。網羅性を高めるにはフリーテキスト検索（`semaglutide[tiab] AND (obesity[tiab] OR overweight[tiab])`）の併用が望ましい。
- **選定は単一評価者による。** 二重スクリーニングを行っておらず、選択バイアスを排除できていない。176件から20件への絞り込みは「代表性」を優先した判断であり、系統的レビューの選択手順とは異なる。
- **出版バイアス。** 選定文献の大半はNovo Nordisk社の資金提供による企業治験である。SURMOUNT-5 [17] はEli Lilly社の資金提供による。
- **公表バイアスの評価は未実施。** 各試験のバイアスリスク評価（RoB 2等）は行っていない。網羅的な質評価はCochraneレビュー [19] を参照されたい。
- **数値は抄録からの抽出。** 本文・補遺の詳細は確認していない。引用にあたっては原著の確認を推奨する。

---

## 6. 引用文献（Vancouver形式）

1. Wilding JPH, Batterham RL, Calanna S, Davies M, Van Gaal LF, Lingvay I, et al. Once-Weekly Semaglutide in Adults with Overweight or Obesity. N Engl J Med. 2021;384(11):989-1002. doi:10.1056/NEJMoa2032183. PMID: 33567185

2. Davies M, Færch L, Jeppesen OK, Pakseresht A, Pedersen SD, Perreault L, et al. Semaglutide 2·4 mg once a week in adults with overweight or obesity, and type 2 diabetes (STEP 2): a randomised, double-blind, double-dummy, placebo-controlled, phase 3 trial. Lancet. 2021;397(10278):971-984. doi:10.1016/S0140-6736(21)00213-0. PMID: 33667417

3. Wadden TA, Bailey TS, Billings LK, Davies M, Frias JP, Koroleva A, et al. Effect of Subcutaneous Semaglutide vs Placebo as an Adjunct to Intensive Behavioral Therapy on Body Weight in Adults With Overweight or Obesity: The STEP 3 Randomized Clinical Trial. JAMA. 2021;325(14):1403-1413. doi:10.1001/jama.2021.1831. PMID: 33625476

4. Rubino D, Abrahamsson N, Davies M, Hesse D, Greenway FL, Jensen C, et al. Effect of Continued Weekly Subcutaneous Semaglutide vs Placebo on Weight Loss Maintenance in Adults With Overweight or Obesity: The STEP 4 Randomized Clinical Trial. JAMA. 2021;325(14):1414-1425. doi:10.1001/jama.2021.3224. PMID: 33755728

5. Garvey WT, Batterham RL, Bhatta M, Buscemi S, Christensen LN, Frias JP, et al. Two-year effects of semaglutide in adults with overweight or obesity: the STEP 5 trial. Nat Med. 2022;28(10):2083-2091. doi:10.1038/s41591-022-02026-4. PMID: 36216945

6. Kadowaki T, Isendahl J, Khalid U, Lee SY, Nishida T, Ogawa W, et al. Semaglutide once a week in adults with overweight or obesity, with or without type 2 diabetes in an east Asian population (STEP 6): a randomised, double-blind, double-dummy, placebo-controlled, phase 3a trial. Lancet Diabetes Endocrinol. 2022;10(3):193-206. doi:10.1016/S2213-8587(22)00008-0. PMID: 35131037

7. Rubino DM, Greenway FL, Khalid U, O'Neil PM, Rosenstock J, Sørrig R, et al. Effect of Weekly Subcutaneous Semaglutide vs Daily Liraglutide on Body Weight in Adults With Overweight or Obesity Without Diabetes: The STEP 8 Randomized Clinical Trial. JAMA. 2022;327(2):138-150. doi:10.1001/jama.2021.23619. PMID: 35015037

8. Weghuber D, Barrett T, Barrientos-Pérez M, Gies I, Hesse D, Jeppesen OK, et al. Once-Weekly Semaglutide in Adolescents with Obesity. N Engl J Med. 2022;387(24):2245-2257. doi:10.1056/NEJMoa2208601. PMID: 36322838

9. Wharton S, Freitas P, Hjelmesæth J, Kabisch M, Kandler K, Lingvay I, et al. Once-weekly semaglutide 7·2 mg in adults with obesity (STEP UP): a randomised, controlled, phase 3b trial. Lancet Diabetes Endocrinol. 2025;13(11):949-963. doi:10.1016/S2213-8587(25)00226-8. PMID: 40961952

10. Knop FK, Aroda VR, do Vale RD, Holst-Hansen T, Laursen PN, Rosenstock J, et al. Oral semaglutide 50 mg taken once per day in adults with overweight or obesity (OASIS 1): a randomised, double-blind, placebo-controlled, phase 3 trial. Lancet. 2023;402(10403):705-719. doi:10.1016/S0140-6736(23)01185-6. PMID: 37385278

11. Wharton S, Lingvay I, Bogdanski P, Duque do Vale R, Jacob S, Karlsson T, et al. Oral Semaglutide at a Dose of 25 mg in Adults with Overweight or Obesity. N Engl J Med. 2025;393(11):1077-1087. doi:10.1056/NEJMoa2500969. PMID: 40934115

12. Lincoff AM, Brown-Frandsen K, Colhoun HM, Deanfield J, Emerson SS, Esbjerg S, et al. Semaglutide and Cardiovascular Outcomes in Obesity without Diabetes. N Engl J Med. 2023;389(24):2221-2232. doi:10.1056/NEJMoa2307563. PMID: 37952131

13. Ryan DH, Lingvay I, Deanfield J, Kahn SE, Barros E, Burguera B, et al. Long-term weight loss effects of semaglutide in obesity without diabetes in the SELECT trial. Nat Med. 2024;30(7):2049-2057. doi:10.1038/s41591-024-02996-7. PMID: 38740993

14. Kosiborod MN, Abildstrøm SZ, Borlaug BA, Butler J, Rasmussen S, Davies M, et al. Semaglutide in Patients with Heart Failure with Preserved Ejection Fraction and Obesity. N Engl J Med. 2023;389(12):1069-1084. doi:10.1056/NEJMoa2306963. PMID: 37622681

15. Kosiborod MN, Petrie MC, Borlaug BA, Butler J, Davies MJ, Hovingh GK, et al. Semaglutide in Patients with Obesity-Related Heart Failure and Type 2 Diabetes. N Engl J Med. 2024;390(15):1394-1407. doi:10.1056/NEJMoa2313917. PMID: 38587233

16. Bliddal H, Bays H, Czernichow S, Uddén Hemmingsson J, Hjelmesæth J, Hoffmann Morville T, et al. Once-Weekly Semaglutide in Persons with Obesity and Knee Osteoarthritis. N Engl J Med. 2024;391(17):1573-1583. doi:10.1056/NEJMoa2403664. PMID: 39476339

17. Aronne LJ, Horn DB, le Roux CW, Ho W, Falcon BL, Gomez Valderas E, et al. Tirzepatide as Compared with Semaglutide for the Treatment of Obesity. N Engl J Med. 2025;393(1):26-36. doi:10.1056/NEJMoa2416394. PMID: 40353578

18. Garvey WT, Blüher M, Osorto Contreras CK, Davies MJ, Winning Lehmann E, Pietiläinen KH, et al. Coadministered Cagrilintide and Semaglutide in Adults with Overweight or Obesity. N Engl J Med. 2025;393(7):635-647. doi:10.1056/NEJMoa2502081. PMID: 40544433

19. Bracchiglione J, Meza N, Franco JV, Escobar Liquitay CM, Novik AV, Ocara Vargas M, et al. Semaglutide for adults living with obesity. Cochrane Database Syst Rev. 2025;10(10):CD015092. doi:10.1002/14651858.CD015092.pub2. PMID: 41161683

20. Moiz A, Filion KB, Toutounchi H, Tsoukas MA, Yu OHY, Peters TM, et al. Efficacy and Safety of Glucagon-Like Peptide-1 Receptor Agonists for Weight Loss Among Adults Without Diabetes: A Systematic Review of Randomized Controlled Trials. Ann Intern Med. 2025;178(2):199-217. doi:10.7326/ANNALS-24-01590. PMID: 39761578

---

## 7. 付属ファイル

**`semaglutide_obesity_20refs.csv`** — 選定20件の全メタデータ（UTF-8 BOM付き、Excel対応）

収録カラム（18列）:
`PMID` / `Title` / `Authors` / `First Author` / `Journal` / `Journal Abbreviation` / `Year` / `Volume` / `Issue` / `Pages` / `DOI` / `PMCID` / `Publication Types` / `MeSH Terms` / `Keywords` / `Abstract` / `PubMed URL` / `PMC URL`

> **Excelで開く際の注意:** `Volume` / `Issue` / `Pages` 列は日付形式に自動変換される場合があります（例: `10-10` → `10月10日`）。回避するには、Excelの「データ」→「テキストまたはCSVから」でインポートし、該当列のデータ形式を「テキスト」に指定してください。

---

*本レポートは PubMed（NCBI E-utilities）を用いた検索結果に基づき、2026年7月17日時点の収載文献から作成した。記載の数値はすべて各論文の抄録から抽出したものであり、引用にあたっては原著の確認を推奨する。*
