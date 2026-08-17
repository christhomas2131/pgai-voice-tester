"""Render the project's Markdown deliverables as .docx for sharing.

The repo keeps Markdown because that's what GitHub renders. This produces a
Word copy of the same content to send to people who want a document.

    python tools/make_docx.py                    # all deliverables
    python tools/make_docx.py BUGS.md            # just one
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = ["README.md", "ARCHITECTURE.md", "BUGS.md"]

MONO = "Menlo"
CODE_GREY = RGBColor(0x33, 0x33, 0x33)
LINK_BLUE = RGBColor(0x1A, 0x5F, 0xB4)

# **bold** | `code` | [text](url) — order matters, code wins over everything
# inside it so backticked asterisks aren't treated as emphasis.
INLINE = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))")


def add_inline(paragraph, text: str) -> None:
    """Write text into a paragraph, honouring bold, inline code and links."""
    for piece in INLINE.split(text):
        if not piece:
            continue
        if piece.startswith("`") and piece.endswith("`"):
            run = paragraph.add_run(piece[1:-1])
            run.font.name = MONO
            run.font.size = Pt(9.5)
            run.font.color.rgb = CODE_GREY
        elif piece.startswith("**") and piece.endswith("**"):
            paragraph.add_run(piece[2:-2]).bold = True
        elif link := re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", piece):
            # fullmatch, not match: a checklist item's "[ ] " also starts with a
            # bracket and is not a link.
            label, url = link.groups()
            run = paragraph.add_run(label)
            run.font.color.rgb = LINK_BLUE
            run.underline = True
            if not url.startswith("#") and "://" in url:
                paragraph.add_run(f" ({url})").font.size = Pt(8.5)
        else:
            paragraph.add_run(piece)


def add_code_block(doc: Document, lines: list[str]) -> None:
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Pt(18)
    para.paragraph_format.space_before = Pt(6)
    para.paragraph_format.space_after = Pt(6)
    run = para.add_run("\n".join(lines))
    run.font.name = MONO
    run.font.size = Pt(9)
    run.font.color.rgb = CODE_GREY


def add_table(doc: Document, rows: list[list[str]]) -> None:
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            para = table.cell(r, c).paragraphs[0]
            add_inline(para, cell)
            if r == 0:
                for run in para.runs:
                    run.bold = True


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_divider(line: str) -> bool:
    return bool(re.fullmatch(r"\|?[\s:|-]+\|?", line.strip())) and "-" in line


def convert(md_path: Path, compact: bool = False) -> Path:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(9.5 if compact else 11)

    if compact:
        # Squeeze onto one page: narrow margins, tight leading, no space between
        # bullets, and headings that don't claim a third of the page.
        for section in doc.sections:
            section.top_margin = section.bottom_margin = Inches(0.5)
            section.left_margin = section.right_margin = Inches(0.6)
        style.paragraph_format.space_after = Pt(1)
        style.paragraph_format.line_spacing = 1.0
        for name, size in (("Heading 1", 14), ("Heading 2", 11), ("Heading 3", 10)):
            heading = doc.styles[name]
            heading.font.size = Pt(size)
            heading.paragraph_format.space_before = Pt(5)
            heading.paragraph_format.space_after = Pt(2)
        bullet = doc.styles["List Bullet"].paragraph_format
        bullet.space_after = Pt(1)
        bullet.line_spacing = 1.0

    lines = md_path.read_text().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            block: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            add_code_block(doc, block)
            i += 1
            continue

        # A table is a pipe row followed by a --- divider row.
        if stripped.startswith("|") and i + 1 < len(lines) and is_divider(lines[i + 1]):
            rows = [split_row(stripped)]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            add_table(doc, rows)
            doc.add_paragraph()
            continue

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            doc.add_heading(stripped[level:].strip(), level=min(level, 4))
        elif stripped in ("---", "***", "___"):
            rule = doc.add_paragraph()
            rule.alignment = WD_ALIGN_PARAGRAPH.CENTER
            rule.add_run("* * *").font.size = Pt(9)
        elif re.match(r"^[-*] ", stripped):
            add_inline(doc.add_paragraph(style="List Bullet"), stripped[2:])
        elif re.match(r"^\d+\. ", stripped):
            add_inline(
                doc.add_paragraph(style="List Number"),
                re.sub(r"^\d+\.\s*", "", stripped),
            )
        elif stripped:
            add_inline(doc.add_paragraph(), stripped)
        i += 1

    out = md_path.with_suffix(".docx")
    doc.save(out)
    return out


def main() -> None:
    args = sys.argv[1:]
    compact = "--compact" in args
    targets = [a for a in args if not a.startswith("--")] or DEFAULTS
    for name in targets:
        path = Path(name)
        if not path.is_absolute():
            path = ROOT / name
        if not path.exists():
            print(f"skipped {path.name} (not found)")
            continue
        out = convert(path, compact=compact)
        print(f"{path.name} -> {out.name} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
