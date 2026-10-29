# Victoria Budget Assistant

A question-answering assistant for the City of Victoria, BC's 2026 budget.
It answers from the Financial Plan 2026–2030, the VicPD 2026 budget
presentation, and the 2026 property tax notice. Every answer cites its
source. When the documents disagree, it reports both figures. When they
don't contain the answer, it says so.

## Why this exists

The 2026 budget is spread across several documents, and they don't always
use the same totals. The police net budget, for example, appears as
$78.05M in one place and $77.99M in another. This tool makes lookups fast,
and the evaluation shows where it can be trusted and where it can't.

## Scope

- Covers: the City of Victoria 2026 Financial Plan (operating summary
  pp. 3–4, Council pp. 5–6, Victoria Police capital pp. 123–124), the
  VicPD 2026 budget presentation (18 slides), and the 2026 property tax
  notice including the Mayor's message.
- Does not cover: the rest of the Financial Plan, other years, other
  municipalities, tax advice, or forecasts beyond what the plan states.
- A Newfoundland municipality also called Victoria is excluded. The test
  set checks that the assistant doesn't confuse the two.

## How it works

1. `extract.py` pulls text from each PDF with page or slide markers into
   `corpus/`. It splits the presentation's two-slides-per-page layout into
   separate slides and restores the column order of the Mayor's letter.
2. `assistant.py` puts the whole corpus (about 30K characters) in the
   system prompt. The model answers only from that text and cites
   `[Financial Plan p. N]`, `[VicPD slide N]` or `[Tax Notice p. N]`.
3. Where sources conflict, both figures are reported with their sources.
4. Where the answer isn't in the documents, the model says so.

There is no vector store or retrieval step. The runtime corpus fits in one
prompt, which keeps failures easy to attribute to the model rather than
to retrieval.

Built with Azure AI Foundry (serverless chat deployment, Azure OpenAI v1
SDK with content filtering enabled).

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in endpoint, key, deployment name
python extract.py           # builds corpus/ (already committed; rerun if PDFs change)
python assistant.py "What is the Victoria Police net budget for 2026?"
python assistant.py         # interactive mode
python evaluate.py          # runs the 20-question test set, writes results/
```

## Evaluation

The test set (`test_set.json`) has 20 questions in three groups:
answerable (8), not answerable (6), and ambiguous or conflicting (6).
`evaluate.py` auto-grades each answer with regex checks on the required
figures, refusal language, and citations. A person then reviews each row,
and those overrides are recorded in the results file.

Results on `gpt-4.1-mini`, after manual review:

| Prompt | Answerable | Refusals | Conflict / ambiguity | Total |
|---|---|---|---|---|
| v1 | 8/8 | 5/6 | 1/6 | 14/20 |
| v2 (2 passes) | 7/8, 7/8 | 5/6, 6/6 | 4/6, 5/6 | 16/20, 18/20 |

v2 fixed the tax-calculation failure and most missed conflicts. It also
introduced a false conflict, and its two passes differ on 2 questions.
v2 was tuned on this same test set, so these numbers are optimistic.
Details are in [EVALUATION.md](EVALUATION.md).
