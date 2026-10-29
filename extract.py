"""Extract the runtime corpus from the source PDFs into corpus/*.txt with page markers.

Run once: python extract.py
"""
import re
from pathlib import Path

import pypdf

ROOT = Path(__file__).parent
OUT = ROOT / "corpus"

PLAN = ROOT / "2026-2030 Financial Plan.pdf"
PRES = ROOT / "Presentation_Victoria Police 2026 Budget.pdf"
TAX = ROOT / "Property Tax Insert_2026 DIGITAL_1.pdf"

# Financial Plan PDF page index == printed page number.
# p.3 revenues, p.4 expenditures, pp.5-6 Council, pp.123-124 Police capital.
PLAN_PAGES = [3, 4, 5, 6, 123, 124]


def extract_plan() -> str:
    reader = pypdf.PdfReader(PLAN)
    parts = []
    for n in PLAN_PAGES:
        text = reader.pages[n - 1].extract_text()
        parts.append(f"[Financial Plan 2026-2030, p. {n}]\n{text.strip()}\n")
    return "\n".join(parts)


def extract_presentation() -> str:
    """Each PDF page holds two slides. Layout mode prints the slide number on its
    own line under each slide, so we split on those lines."""
    reader = pypdf.PdfReader(PRES)
    parts = []
    for i, page in enumerate(reader.pages):
        first, second = 2 * i + 1, 2 * i + 2
        text = page.extract_text(extraction_mode="layout")
        text = re.sub(r"^\s*2025-11-21\s*$", "", text, flags=re.M)
        # Slide 10's table fuses the % column into the next number ("9.51%68,153,143$").
        text = re.sub(r"(\d%)(\d)", lambda m: m[1] + "  " + m[2], text)
        text = text.replace("BaseOne-TimeTotal", "Base  One-Time  Total")
        text = re.sub(rf"^\s*{i + 1}\s*$\Z", "", text.rstrip(), flags=re.M)  # PDF page footer
        m = re.search(rf"^\s*{first}\s*$", text, flags=re.M)
        if m:
            slides = [(first, text[: m.start()]), (second, re.sub(rf"^\s*{second}\s*$", "", text[m.end():], flags=re.M))]
        else:
            slides = [(f"{first}-{second}", text)]
        for num, body in slides:
            body = re.sub(r"\n\s*\n+", "\n", body).strip()
            if not body:
                body = "(no text layer on this slide; content is an image or chart)"
            parts.append(f"[VicPD 2026 Budget Presentation, slide {num}]\n{body}\n")
    return "\n".join(parts)


def extract_tax_insert() -> str:
    reader = pypdf.PdfReader(TAX)
    parts = []
    for n, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if n == 1:
            # Default extraction emits the right column before the left one.
            # Put the letter back in reading order.
            right, left = text.split("Dear Victorians,", 1)
            header = "2026 CITY OF VICTORIA PROPERTY TAXES\nMessage from the Mayor\n"
            left = left.replace("2026 CITY OF VICTORIA PROPERTY TAXES\nMessage from the Mayor\n", "")
            left = left.replace("TAXES DUE:\nJULY\n2\nTHURSDAY", "").strip()
            text = header + "Dear Victorians,\n" + left.lstrip() + "\n" + right.strip()
        parts.append(f"[2026 Property Tax Notice insert (incl. Mayor's message), p. {n}]\n{text.strip()}\n")
    return "\n".join(parts)


def main():
    OUT.mkdir(exist_ok=True)
    files = {
        "financial_plan.txt": extract_plan(),
        "vicpd_presentation.txt": extract_presentation(),
        "property_tax_notice.txt": extract_tax_insert(),
    }
    for name, text in files.items():
        (OUT / name).write_text(text, encoding="utf-8")
        print(f"{name}: {len(text):,} chars")


if __name__ == "__main__":
    main()
