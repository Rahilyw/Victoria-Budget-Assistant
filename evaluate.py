"""Run the 20-question test set and auto-grade the answers.

Usage:
    python evaluate.py               # run against the Azure deployment (prompt v2)
    python evaluate.py --prompt v1   # run with the original prompt
    python evaluate.py --regrade FILE  # re-grade a saved results JSON (no API calls)

Auto-grading is a first pass. Every row should be read by a person; put overrides
in the "manual" field of the results JSON and re-run with --regrade.
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"

REFUSAL = re.compile(
    r"do(es)? not (contain|include|provide|state|cover|specify)|not (in|included in|provided in|stated in|covered by) the"
    r"|no information|isn't (stated|included|provided)|aren't (stated|included|provided)|cannot (calculate|provide|determine|answer)"
    r"|can't (calculate|provide|determine|answer)|not able to|outside (my|the|these) (sources|documents|scope)|only cover",
    re.I,
)
# Tolerates stray characters inside the brackets, e.g. "[$Financial Plan p. 4]".
CITATION = re.compile(r"\[[^\]a-z]*(financial plan|vicpd|tax notice)[^\]]*\d[^\]]*\]", re.I)


def normalize(text: str) -> str:
    t = text.lower()
    t = re.sub(r"(?<=\d),(?=\d{3})", "", t)        # 1,234,567 -> 1234567
    t = re.sub(r"(\d)\s*million\b", r"\1m", t)       # 78.05 million -> 78.05m
    t = t.replace("−", "-").replace(" ", " ")
    return t


def grade(item: dict, answer: str) -> dict:
    norm = normalize(answer)
    reasons = []
    for group in item.get("must_include", []):
        if not any(re.search(p, norm) for p in group):
            reasons.append(f"missing one of {group}")
    for p in item.get("must_not_include", []):
        if re.search(p, norm):
            reasons.append(f"contains forbidden /{p}/")
    if item["category"] == "unanswerable" and not REFUSAL.search(answer):
        reasons.append("no refusal language")
    cited = bool(CITATION.search(answer))
    # Pure refusals don't need a citation; everything else does.
    needs_citation = item["category"] != "unanswerable" and item["id"] != "C4"
    if answer.startswith("[BLOCKED"):
        reasons.append("blocked by content filter")
    return {
        "auto_pass": not reasons,
        "cited": cited,
        "citation_ok": cited or not needs_citation,
        "reasons": reasons,
    }


def summarize(rows: list) -> str:
    def final(r):
        return r["manual"] if r.get("manual") in ("pass", "fail") else ("pass" if r["auto_pass"] else "fail")

    groups = {
        "Answerable (8)": [r for r in rows if r["category"] == "answerable"],
        "Not answerable (6)": [r for r in rows if r["category"] == "unanswerable"],
        "Ambiguous / conflicting (6)": [r for r in rows if r["category"] in ("ambiguous", "conflict")],
    }
    lines = ["| Group | Correct | Cited (where required) |", "|---|---|---|"]
    for name, rs in groups.items():
        ok = sum(final(r) == "pass" for r in rs)
        cit = sum(r["citation_ok"] for r in rs)
        lines.append(f"| {name} | {ok}/{len(rs)} ({ok / len(rs):.0%}) | {cit}/{len(rs)} |")
    total = sum(final(r) == "pass" for r in rows)
    lines.append(f"| **All (20)** | **{total}/{len(rows)} ({total / len(rows):.0%})** | {sum(r['citation_ok'] for r in rows)}/{len(rows)} |")
    lines += ["", "| ID | Category | Result | Cited | Notes |", "|---|---|---|---|---|"]
    for r in rows:
        src = "manual" if r.get("manual") in ("pass", "fail") else "auto"
        notes = "; ".join(r["reasons"]).replace("|", "\\|") or ""
        if r.get("manual_note"):
            notes = (notes + "; " if notes else "") + r["manual_note"]
        lines.append(f"| {r['id']} | {r['category']} | {final(r)} ({src}) | {'yes' if r['cited'] else 'no'} | {notes} |")
    lines += ["", "## Answers", ""]
    for r in rows:
        lines += [f"### {r['id']}: {r['question']}", "", f"**Expected:** {r['expected']}", "", "**Answer:**", "",
                  "> " + r["answer"].replace("\n", "\n> "), ""]
    return "\n".join(lines)


def run(prompt_version: str):
    from assistant import Assistant

    items = json.loads((ROOT / "test_set.json").read_text(encoding="utf-8"))
    bot = Assistant(prompt_version)
    rows = []
    for item in items:
        print(f"{item['id']}: {item['question']}", flush=True)
        answer = bot.ask(item["question"])
        rows.append({**{k: item[k] for k in ("id", "category", "question", "expected")},
                     "answer": answer, "manual": "", "manual_note": "", **grade(item, answer)})
    return rows, bot.deployment


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regrade", type=Path, help="re-grade a saved results JSON")
    ap.add_argument("--prompt", default="v2", choices=["v1", "v2"], help="system prompt version")
    args = ap.parse_args()
    RESULTS.mkdir(exist_ok=True)

    if args.regrade:
        data = json.loads(args.regrade.read_text(encoding="utf-8"))
        items = {i["id"]: i for i in json.loads((ROOT / "test_set.json").read_text(encoding="utf-8"))}
        for r in data["rows"]:
            r.update(grade(items[r["id"]], r["answer"]))
        out_json = args.regrade
    else:
        rows, deployment = run(args.prompt)
        data = {"run_at": datetime.now().isoformat(timespec="seconds"), "deployment": deployment,
                "prompt": args.prompt, "rows": rows}
        out_json = RESULTS / f"results_{args.prompt}_{datetime.now():%Y%m%d_%H%M%S}.json"

    out_json.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    md = f"# Results: {data['deployment']}, prompt {data.get('prompt', 'v1')}, {data['run_at']}\n\n" + summarize(data["rows"])
    out_md = out_json.with_suffix(".md")
    out_md.write_text(md, encoding="utf-8")
    print("\n" + md.split("\n## Answers")[0])
    print(f"\nSaved {out_json.name} and {out_md.name} in {RESULTS}")


if __name__ == "__main__":
    sys.exit(main())
