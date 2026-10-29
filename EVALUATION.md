# Evaluation

## Method

- **Test set:** 20 questions in `test_set.json`: 8 answerable, 6 not answerable, 6 ambiguous or conflicting.
- **Run:** `python evaluate.py` sends each question once, at temperature 0, with the full corpus in the system prompt.
- **Auto-grading:** each question lists required figures (`must_include`; every group must match) and forbidden patterns (`must_not_include`). Numbers are normalized first (commas removed, "million" → "m"). Unanswerable questions also need refusal language. Citations are checked separately.
- **Manual review:** regex grading can't judge whether an answer is *reasoned* correctly. Read every row in `results/*.md`, set `"manual": "pass"|"fail"` plus a `manual_note` in the JSON, then run `python evaluate.py --regrade results/<file>.json`.
- **Grader check:** before any model run, the grader was tested on 20 hand-written correct answers (all passed) and 7 deliberately wrong ones (all failed).

**Targets:** at least 80% correct on answerable questions and 100% correct refusal on unanswerable ones. The actual numbers are reported below either way.

## Results

**Run 1:** `gpt-4.1-mini` on Azure AI Foundry, 2026-10-28, temperature 0, one pass per question. All 20 answers were reviewed by hand. Full answers are in `results/results_20261028_232901.md`.

| Group | Correct | Cited (where required) | Target |
|---|---|---|---|
| Answerable (8) | **8/8 (100%)** | 8/8 | ≥ 80% ✅ |
| Not answerable (6) | **5/6 (83%)** | 6/6 | 100% ❌ |
| Ambiguous / conflicting (6) | **1/6 (17%)** | 6/6 | – |
| **All (20)** | **14/20 (70%)** | 20/20 | |

**Summary:** the assistant is reliable for single-figure lookups, and refuses well when it has nothing to go on. It misses the two things this project set out to test. It never reported a conflict between sources: 0 of 4 conflict questions. And it computed a personal tax bill when it had enough numbers to do so.

## Failure analysis

| ID | What the model did | Cause |
|---|---|---|
| U3 | Calculated (1,400,000 / 1,015,000) × $323 ≈ **$446** for the user's house, labelled "an estimate". | **Refusal.** The rule against tax calculations lost out to the user's direct request, because the inputs for a plausible-looking calculation were available. A hedge like "this is an estimate" doesn't make the calculation acceptable. |
| C1 | Gave the plan's $78,052,820 with correct arithmetic. Didn't mention the presentation's $77,986,398. | **Conflict handling.** It found one valid answer and stopped. It didn't check the other sources for the same item. |
| C2 | Gave 69.5% only. | **Conflict handling.** Same pattern. The ~69% figure only appears if you combine numbers from two documents, and the model never tried. |
| C5 | Answered **$68,153,143**, which is wrong. That's the *base-only* column of the presentation's 2025 row; the total is $68,199,761. It also missed the plan's $68,398,300. | **Extraction and table reading, plus conflict handling.** The slide 10 table is text with columns separated only by whitespace, and the model took the first number in the row. It also didn't calculate the plan-side net, though it did that same subtraction correctly for 2026 in C1. |
| C6 | Gave the expenditure-side $385,951,390 only. | **Conflict handling.** Here both figures are in the same document, on facing pages. |
| C3 | Gave the correct $394,060,040, but didn't say it was assuming the City of Victoria, BC. It also labelled the $385,951,390 base total as "operating expenditures". | **Ambiguity.** The model treats the system prompt's scope as settled, so it never states the assumption to the user. |

**Borderline passes:**
- **U1:** it opens with "the forecast for 2027 is $94,989,170 (2026 budget) plus the forecasted increase" before refusing correctly. A reader who stops after the first sentence is misled.
- **A2:** the citation came out malformed as `[$Financial Plan p. 4]`.

**Pattern:** 5 of the 6 failures involve the same behaviour. The model answers from the first source that fits and doesn't cross-check. Rule 5 in the prompt ("report both figures") only fires when the model notices a conflict, and it never goes looking for one. A likely fix is to require an explicit check of all three sources for every figure, or to list the known overlaps in the prompt. That fix hasn't been tested yet.

## Grader corrections after run 1

The first auto-grade had U3 as a **pass**, because the regex didn't match the form the calculation actually took, and A2 as **uncited**, because of the stray `$`. Both patterns are fixed in `test_set.json` and `evaluate.py`, and the auto-grades now match the manual review on all 20 questions. This shows why manual review is part of the method: regex grading alone overstated refusal accuracy at 100%, when the real figure was 83%.

## Verified reference figures

Each figure was checked against the extracted text of its source page.

| Item | Value | Source |
|---|---|---|
| Total operating budget 2026 | $394,060,040 (+8.87% from $361,938,940) | FP p. 3 and p. 4 |
| Victoria Police expenditure 2026 | $94,989,170 (+13.87% from $83,417,340) | FP p. 4 |
| Victoria Police revenue 2026 | $16,936,350 (2025: $15,019,040) | FP p. 3 |
| Victoria Police net 2026 | $78,052,820 (calculated) | FP pp. 3–4 |
| Council forecast 2027 | $1,129,570 (+19.50%) | FP p. 6 |
| Police capital 2026 (computer + furniture + vehicles) | $500,000 + $400,000 + $800,000 = $1,700,000 | FP p. 124 |
| VicPD total 2026 budget (Victoria share) | $77,986,398; total increase $9,786,637 | VicPD slide 10 |
| Tax increase | 7.28% = 5.06% police + 2.22% other; police = 69.5% | Tax Notice pp. 1, 3 |
| Levy increase | $14.185 million | Tax Notice p. 3 |

## Conflicts found in the sources

These four items have conflicting figures. The first two were in the original scope. The last two turned up while checking figures, and the test set now includes them as C5 and C6.

| ID | Item | Source A | Source B | Gap |
|---|---|---|---|---|
| C1 | VicPD net 2026 | FP: $78,052,820 (calculated); Mayor: $78.05M | VicPD slide 10: $77,986,398 | $66,422 |
| C2 | Police share of tax increase | Tax Notice: 69.5% (5.06 ÷ 7.28) | $9,786,637 ÷ $14.185M ≈ 69.0% | ~0.5 points |
| C5 | VicPD net 2025 | FP: $83,417,340 − $15,019,040 = $68,398,300 | VicPD slide 10: 2025 approved $68,199,761 | $198,539 |
| C6 | "Total base budget" 2026 | FP p. 3 (revenues): $384,251,390, +7.84% | FP p. 4 (expenditures): $385,951,390, +7.87% | $1.7M, offset in one-time totals |

Two more figures don't match the plan's lines but aren't in the test set, because the gap may just come from a different definition:

- Mayor's letter: "$24.8 million to fire services". FP p. 4 lists Fire expenditure as $24,468,330.
- Mayor's letter: "$9.1 million to community safety and bylaw services". FP p. 4 lists $9,403,800 expenditure, and $8,624,320 net of the p. 3 revenue.

## Corrections to the original scope

- **The police section is pp. 123–124, not pp. 122–124.** Page 122 is Environmental Remediation.
- **The Financial Plan has no separate police operating section.** Police operating figures appear only as summary lines on pp. 3–4. Pages 123–124 cover capital only, so there is no police operating forecast for 2027–2030 in the corpus (tested by U1).
- **The presentation is 9 PDF pages holding 18 slides,** two per page. The extractor splits them so citations point to slides.
- **The reference figure "total base operating budget $384,251,390" is the revenue-side figure only.** See C6.

## Limitations

- **Narrow corpus.** About 30 pages of the 124-page plan. Questions about other departments get a refusal, even though the full plan has the answer.
- **Chart content is missing.** Slide 13 ("VicPD Budget Share of Municipal Expenditures") is a chart with no text layer, and the pie charts on Tax Notice p. 3 survive only as labels and percentages.
- **Table extraction is fragile.** The slide 10 table came out with columns fused together ("9.51%68,153,143$") and needed a regex fix. Other tables were not checked cell by cell.
- **Single run per question.** Temperature 0 cuts variance but doesn't remove it. Run several times before drawing conclusions about small differences.
- **The regex grader is lenient on reasoning.** It checks that the right numbers appear, not that they're labelled correctly. That's why manual review is required.
- **Small sample.** 20 questions can't support strong statistical claims. Read one failure as one failure, not as a rate.
- **No adversarial or multi-turn testing.** The bot is single-turn and the test set doesn't include prompt injection.
