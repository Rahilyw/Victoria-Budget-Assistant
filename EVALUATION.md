# Evaluation

## Summary

Three prompt versions were tested on `gpt-4.1-mini`. Every answer was reviewed by hand.

| | Original set (20), tuned on | Held-out set (18), not tuned on |
|---|---|---|
| v1 | 14 (1 run) | not run |
| v2 | 16, 18, 17 (avg **17.0**) | 16, 14, 15 (avg **15.0**) |
| v3 | 19, 18, 18 (avg **18.3**) | 14, 15, 16 (avg **15.0**) |

- **Lookups are reliable.** Answerable held-out questions scored 8/8 in all six passes.
- **Prompt tuning has stopped helping.** v3 beats v2 only on the questions it was tuned on. On held-out questions the two tie.
- **No configuration meets the 100% refusal target.** Every v2 and v3 pass presented a current-year figure as a future forecast at least once. v3 also invented figures twice ($99,000,000 and $99,989,000 as a 2027 police forecast, U1), which is the worst failure seen in any run.
- **Conflicts are reported when both figures are stated, and missed when one has to be derived.** Derived figures include a share of the tax increase, a net increase, or a number in the Mayor's letter.

**Recommendation:** stop editing the prompt. The next step is a code-side check that every number in an answer appears in the corpus or comes from shown arithmetic on corpus numbers. That would have caught every fabricated figure above. Details are under [Run 3](#run-3-held-out-set-and-prompt-v3).

## Method

- **Test set:** 20 questions in `test_set.json`: 8 answerable, 6 not answerable, 6 ambiguous or conflicting. These questions were used to design v2 and v3.
- **Held-out set:** 18 questions in `heldout_set.json` (8 / 5 / 5), written and checked against the sources *before* v3 was written. No prompt was changed in response to them.
- **Run:** `python evaluate.py [--prompt v1|v2|v3] [--set FILE] [--runs N]` sends each question once per pass, at temperature 0, with the full corpus in the system prompt.
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

## Run 2: prompt v2

### What changed

v2 (`SYSTEM_PROMPT_V2` in `assistant.py`; v1 is kept and can be run with `--prompt v1`) targets the run 1 failures:

| Run 1 failure | v2 change |
|---|---|
| Never cross-checked sources (C1, C2, C5, C6) | Says up front that the three documents overlap on police and tax figures. Adds a silent step: find the item in all three documents and on both p. 3 and p. 4, then compare. Every answer must end with a `Cross-check:` line. |
| Read the base-only column (C5) | When a table row has several columns, use Total unless the question asks for base or one-time. |
| Calculated a personal tax bill (U3) | Hard rule: never calculate, estimate or scale an individual's tax, even when asked directly. Point to the City's tax calculator. |
| Pseudo-answer before refusing (U1) | Refusals must *start* with the refusal sentence. |
| Didn't state the BC assumption (C3) | If a question says only "Victoria", start with "Assuming you mean the City of Victoria, British Columbia:". |

v2 was run twice to measure variance. Same model and temperature as run 1.

### Results

| Group | v1 | v2, pass 1 | v2, pass 2 |
|---|---|---|---|
| Answerable (8) | 8/8 | 7/8 | 7/8 |
| Not answerable (6) | 5/6 | 5/6 | **6/6** |
| Ambiguous / conflicting (6) | 1/6 | 4/6 | 5/6 |
| — of which conflicts (4) | 0/4 | 2/4 | 3/4 |
| **All (20)** | **14/20 (70%)** | **16/20 (80%)** | **18/20 (90%)** |

| ID | v1 | v2 p1 | v2 p2 | Notes |
|---|---|---|---|---|
| A2 | ✅ | ❌ | ❌ | **New failure caused by v2.** The cross-check compares the plan's police *expenditure* ($94.99M) to the presentation's *net* budget ($77.99M) and reports a "21.8% difference". That's a false conflict between two different measures. |
| U1 | ✅ | ❌ | ✅ | Pass 1 says "the 2027 forecast is $94,989,170", which is the 2026 figure presented as a forecast. This is the worst error in any run. |
| U3 | ❌ | ✅ | ✅ | Both passes refuse and point to the tax calculator. Fixed. |
| C1 | ❌ | ✅ | ✅ | Both report $78,052,820 vs $77,986,398 (gap $66,422). Fixed. |
| C2 | ❌ | ❌ | ❌ | Still reports 69.5% only. The ~69% figure has to be *derived* from two documents, and the model doesn't do it. |
| C3 | ❌ | ✅ | ✅ | States the BC assumption. Fixed. |
| C5 | ❌ | ❌ | ✅ | Both passes get the plan net right. Pass 1 still uses the base-only $68,153,143; pass 2 uses the Total column. |
| C6 | ❌ | ✅ | ✅ | Both report $384,251,390 and $385,951,390 (gap $1.7M). Citations were written as prose instead of brackets. |

All other questions passed in every run.

### What this shows

- **Explicit cross-checking mostly works.** Stated conflicts (C1, C6) were fixed in both passes. Conflicts that need arithmetic across documents (C2) were not fixed in either.
- **It also has a cost.** Forcing a cross-check on every answer made the model invent a conflict on A2, a question v1 answered cleanly. A rule that tells the model to look for disagreement makes it find disagreement, including between figures that measure different things.
- **Run-to-run variance is large.** At temperature 0, the two v2 passes differ on 2 of 20 questions (U1 and C5). One of them is a fabricated forecast. A single run can't be trusted for a change this size.
- **The results are optimistic.** v2 was written after seeing run 1's failures on these same 20 questions, and its prompt names the areas where the documents overlap. Improvements on a test set the prompt was tuned to don't show how it would do on new questions. A held-out set is needed before claiming v2 is better.

### Recommendation

v2 is better overall: refusals and stated conflicts improve and the tax-advice failure is gone. It's not ready to rely on yet. Next fixes to try:

1. Limit the cross-check to the *same measure* (net vs net, expenditure vs expenditure). Fixes A2.
2. Give the model the documents' relationships as data, e.g. a small table saying "presentation slide 10 Total = VicPD net". Don't rely on the model to infer them.
3. Write 10–20 held-out questions before changing the prompt again.
4. Run each configuration at least 3 times and report the range.

## Run 3: held-out set and prompt v3

### What changed

**Held-out set.** I wrote 18 new questions and checked each expected answer against the corpus before writing v3. Two of the held-out conflicts come from the Mayor's letter: fire (H-C1, $24.8M vs $24,468,330) and community safety and bylaw (H-C2, $9.1M vs $9,403,800). These were listed in "Conflicts found in the sources" earlier but never tested. To keep them a fair test, v3 contains nothing about the Mayor's letter.

**v3** (`SYSTEM_PROMPT_V3`) targets run 2's failures:
- A **MEASURES** section defining expenditure, revenue, net and capital, and stating that slide 10's Total column is on a net basis.
- A rule to compare like with like only ("a difference between different measures is not a conflict"). Aimed at A2.
- A year check ("never present a figure for one year as the figure for another"). Aimed at U1.
- Permission to derive a share of the tax increase from dollar amounts. Aimed at C2.

v2 and v3 were each run 3 times on both sets. v2 also has 3 passes on the original set (2 from run 2, 1 new).

### Results (manual review)

| Group | v2 original | v3 original | v2 held-out | v3 held-out |
|---|---|---|---|---|
| Answerable | 7, 7, 7 /8 | 8, 8, 8 /8 | 8, 8, 8 /8 | 8, 8, 8 /8 |
| Not answerable | 5, 6, 5 /6 | 6, 5, 5 /6 | 4, 4, 4 /5 | 3, 4, 4 /5 |
| Ambiguous / conflicting | 4, 5, 5 /6 | 5, 5, 5 /6 | 4, 2, 3 /5 | 3, 3, 4 /5 |
| **Total** | **16, 18, 17** | **19, 18, 18** | **16, 14, 15** | **14, 15, 16** |

Per question, counting passes out of 3 (only questions that failed at least once are shown):

| ID | v2 | v3 | What happened |
|---|---|---|---|
| A2 | 0/3 | **3/3** | v3's same-measure rule fixed the false expenditure-vs-net conflict. |
| U1 | 1/3 | 1/3 | v2 states the 2026 figure as the 2027 forecast. **v3 invents numbers instead:** "$99,989,000" and "$99,000,000", the second with a false claim that p. 4 shows a 2027 forecast. |
| C2 | 0/3 | 0/3 | Neither prompt derives the presentation-based share, even though v3 explicitly allows it. |
| C5 | 2/3 | 3/3 | v3 always reads the Total column. |
| H-U3 | 3/3 | 2/3 | v3 pass 1: "your tax increase will be proportionally higher than $427". |
| H-U5 | **0/3** | **0/3** | Every pass of both prompts opens with "the 2028 budget is forecasted to be $24,468,330", the 2026 figure, before refusing. v3's year check had no effect. |
| H-C1 | 3/3 | 3/3 | Both prompts report the Mayor's $24.8M and the plan's $24,468,330. Most passes guess at the reason ("likely includes related costs"), which no source says. |
| H-C2 | 1/3 | 0/3 | Most passes miss the Mayor's $9.1M and wrongly say the Tax Notice gives no figure. |
| H-C3 | 0/3 | 1/3 | v2 calls revenue vs expenditure a "conflict". v3 passes 1–2 label the *revenue* increase ($1,917,310) as the "net" increase and report a false discrepancy. v3 pass 3 gets the measures right. |
| H-C4 | 2/3 | 3/3 | v2 pass 2 calls revenue vs expenditure a conflict and miscalculates the gap. v3 labels every measure correctly. |

### What this shows

- **The original-set gain doesn't hold up.** v3 averages 18.3 vs v2's 17.0 on the 20 questions it was designed against. On 18 new questions both average 15.0. The prompt changes fixed the specific failures they targeted without making the assistant better in general.
- **Defining measures helps with labelling, not with arithmetic.** v3 stopped the expenditure-vs-net false conflicts (A2, H-C4), but on H-C3 it applied the "net" label to the wrong line. Giving the model the right vocabulary doesn't make it use it correctly.
- **Forecast questions are the weakest point, and v3 made them worse.** When asked about a year the documents don't cover, both prompts reach for the nearest figure. v2 relabels a real figure; v3 sometimes invents one. That's a different and worse kind of error, possibly because v3 allows the model to derive figures. A wrong year is visible in the citation; an invented number with a page reference looks fully grounded.
- **The Mayor's letter is a blind spot.** The model treats the letter's "$X to <service>" bullets as background rather than budget figures, so it misses or plays down conflicts with the plan (H-C2). When it does notice one (H-C1), it makes up a reason for the gap.
- **Variance is still large.** Same prompt, same model, temperature 0: totals vary by up to 2 points between passes. One run per configuration, as in run 1, isn't enough to rank prompts.

### Recommendation

Neither v2 nor v3 is ready to rely on. More prompt editing is unlikely to fix what's left, because the remaining failures are about checking, not instructions. Next steps, in order:

1. **Number grounding in code.** After each answer, pull out every figure and check that it appears in the corpus or comes from shown arithmetic on corpus figures. Block or flag any answer that fails. This catches the invented figures ($99M) and rounding changes, and doesn't depend on the model following rules.
2. **Year guard in code.** If a question names a year outside 2025–2026, and the item isn't in a stated forecast table (Council p. 6, police capital p. 124), return the refusal directly. This fixes U1 and H-U5 without the model.
3. **Precompute derived figures.** Calculate department nets, net increases and the police share of the tax increase in `extract.py`, and give them to the model as a labelled table with sources. The model has repeatedly failed to derive these itself (C2, H-C3).
4. **Keep v3 as the default for now.** It ties v2 on held-out questions and gives fewer false conflicts, but its two invented figures make step 1 the priority.
5. **Write a fresh held-out set** before testing these fixes. This one has now been seen.

## Grader corrections after run 1

The first auto-grade had U3 as a **pass**, because the regex didn't match the form the calculation actually took, and A2 as **uncited**, because of the stray `$`. Both patterns are fixed in `test_set.json` and `evaluate.py`, and the auto-grades now match the manual review on all 20 questions. This shows why manual review is part of the method: regex grading alone overstated refusal accuracy at 100%, when the real figure was 83%.

In run 2 the auto-grader overstated v2 again: it scored 18/20 and 19/20, against 16/20 and 18/20 after review. It missed the fabricated forecast in U1 (now caught by a new pattern) and the false conflict in A2 (not caught by any pattern, so that one is recorded as a manual override only). The C2 and C5 failures it did catch.

In run 3 the auto-grader matched the manual review on v3's original-set passes, because the U1 pattern added after run 2 caught both invented figures. It overstated everything else: v2's third original-set pass (18 vs 17, the A2 false conflict again) and every held-out pass (v2: 17/16/16 vs 16/14/15; v3: 16/17/16 vs 14/15/16). The misses were wrong-year forecasts with wording the patterns didn't cover (H-U5), mislabelled measures (H-C3, H-C4), and one scaling hint (H-U3). Over all 13 runs, the regex grader on its own would have reported scores 0–2 points higher than the real result.

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
- **Few runs.** v1 was run once; v2 and v3 three times per set. Totals still vary by up to 2 points between passes at temperature 0.
- **Same author for prompts, questions and grading.** I wrote the held-out set before v3 and didn't change v3 in response to it, but I knew the corpus when writing both. An independent question writer would be a stronger test.
- **No conversation memory.** Each question is sent on its own, so follow-ups like "who does she work for?" have no context. This came up in a manual demo.
- **The cross-check line is often filler.** The required `Cross-check:` line often just restates the source ("consistent with p. 4") or speculates about why figures differ.
- **The regex grader is lenient on reasoning.** It checks that the right numbers appear, not that they're labelled correctly. That's why manual review is required.
- **Small sample.** 20 questions can't support strong statistical claims. Read one failure as one failure, not as a rate.
- **No adversarial or multi-turn testing.** The bot is single-turn and the test set doesn't include prompt injection.
