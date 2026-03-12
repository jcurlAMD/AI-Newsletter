"""
AMD Finance Newsletter Generator
==================================
Calls the AMD LLM Gateway to generate a weekly finance newsletter covering:
  - AMD financials & earnings
  - Global gaming market trends
  - Competitor analysis (Intel / Nvidia)

Outputs a professionally formatted PDF saved to the newsletters/ folder.

Requirements:
    pip install openai==1.101.0 reportlab

Configuration:
    Set the PROJECT_API_KEY environment variable to your AMD LLM Gateway
    subscription key. In GitHub Actions this is stored as a repository secret.
    For local use, set it in your terminal before running:
        Windows : set PROJECT_API_KEY=your-key-here
        Mac/Linux: export PROJECT_API_KEY=your-key-here
"""

import os
import re
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

import openai
import git
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# ---------------------------------------------------------------------------
# CONFIG — edit these values before running
# ---------------------------------------------------------------------------
API_KEY         = "PASTE_YOUR_AMD_GATEWAY_KEY_HERE"
REPO_PATH       = r"C:\Users\lucasb\AI-Newsletter"   # Local path to your cloned repo
OUTPUT_DIR      = Path(REPO_PATH) / "newsletters"
GIT_REMOTE      = "origin"
GIT_BRANCH      = "main"
MODEL           = "GPT-oss-20B"
MAX_TOKENS      = 3500
TEMPERATURE     = 0.5
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour palette — AMD red theme
# ---------------------------------------------------------------------------
AMD_RED    = colors.HexColor("#ED1C24")
AMD_DARK   = colors.HexColor("#1A1A1A")
AMD_GREY   = colors.HexColor("#4A4A4A")
AMD_LIGHT  = colors.HexColor("#F5F5F5")
AMD_BORDER = colors.HexColor("#DDDDDD")


def make_client():
    return openai.OpenAI(
        base_url="https://llm-api.amd.com/OnPrem",
        api_key="dummy",
        default_headers={
            "Ocp-Apim-Subscription-Key": API_KEY,
            "user": "github-actions",
        },
    )


def call_llm(client, section_prompt: str, section_name: str) -> str:
    """Call the AMD LLM Gateway for a single newsletter section."""
    log.info("Generating section: %s", section_name)

    system = (
        "You are a senior financial analyst and technology journalist specialising in "
        "the semiconductor industry. Write clear, insightful, data-driven newsletter "
        "content. Use a professional but engaging tone. Do not use markdown formatting — "
        "write in plain prose with clear paragraph breaks using blank lines. "
        "Do not use bullet points, asterisks, pound signs, or any other markdown symbols."
    )

    response = client.chat.completions.create(
        model=MODEL,
        max_completion_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": section_prompt},
        ],
    )

    choice = response.choices[0]
    log.info(
        "  %s — finish: %s | tokens: prompt=%s completion=%s",
        section_name,
        choice.finish_reason,
        response.usage.prompt_tokens,
        response.usage.completion_tokens,
    )

    content = choice.message.content
    if not content:
        log.warning("  Empty response for %s — using placeholder.", section_name)
        return f"Content for {section_name} could not be generated at this time."

    # Strip any markdown symbols the model sneaks in
    content = re.sub(r"[#*`]+", "", content)
    return content.strip()


def generate_content(client: openai.OpenAI, date_str: str) -> dict:
    """Generate all newsletter sections."""

    sections = {}

    # --- Editor's Note ---
    sections["editors_note"] = call_llm(client, f"""
Write a concise editor's note (2-3 short paragraphs) for the AMD Weekly Finance Newsletter
dated {date_str}. Briefly introduce this week's key themes: AMD's financial performance,
the global gaming market, and competitive dynamics with Intel and Nvidia.
Keep it under 150 words. Write in plain prose, no markdown.
""", "Editor's Note")

    # --- AMD Financials & Earnings ---
    sections["financials"] = call_llm(client, f"""
Write a detailed financial analysis section (4-5 paragraphs) for an AMD investor newsletter
dated {date_str}. Cover the following:
- AMD's most recent quarterly earnings performance (revenue, gross margin, EPS)
- Year-over-year and quarter-over-quarter growth trends across AMD's business segments
  (Data Center, Client, Gaming, Embedded)
- Key guidance and forward-looking statements from AMD management
- Stock performance context and analyst sentiment
- Any significant recent news such as acquisitions, partnerships, or product launches
  affecting AMD's financial outlook

Write in plain prose. No markdown, no bullet points, no asterisks.
Be specific with figures where possible, noting if estimates are used.
""", "AMD Financials & Earnings")

    # --- Global Gaming Market Trends ---
    sections["gaming"] = call_llm(client, f"""
Write a global gaming market analysis section (3-4 paragraphs) for an AMD investor newsletter
dated {date_str}. Cover the following:
- Current state of the global PC gaming hardware market and consumer spending trends
- Regional demand patterns for gaming CPUs — highlight key markets such as North America,
  Europe, and Asia-Pacific
- How gaming market trends are influencing AMD Ryzen CPU demand across product tiers
  (Ryzen 3, 5, 7, 9)
- Steam platform growth, active user trends, and what they signal for PC hardware demand
- Near-term outlook for gaming hardware demand through the remainder of 2025 and into 2026

Write in plain prose. No markdown, no bullet points, no asterisks.
""", "Global Gaming Market Trends")

    # --- Competitor Analysis ---
    sections["competitors"] = call_llm(client, f"""
Write a competitor analysis section (4-5 paragraphs) for an AMD investor newsletter
dated {date_str}. Cover the following:
- Intel's current CPU market position, recent product launches, financial health,
  and strategic challenges
- Nvidia's dominance in the GPU/AI accelerator market and any overlap or competition
  with AMD's data center and gaming GPU business
- AMD's competitive advantages and vulnerabilities vs both Intel (CPU) and Nvidia (GPU/AI)
- Market share trends in desktop, laptop, and data center CPU segments
- Key upcoming product launches or roadmap announcements from all three companies
  that investors should watch

Write in plain prose. No markdown, no bullet points, no asterisks.
""", "Competitor Analysis")

    # --- Key Takeaways ---
    sections["takeaways"] = call_llm(client, f"""
Write a brief "Key Takeaways" closing section (3-5 sentences) for an AMD investor newsletter
dated {date_str}. Summarise the most important investor-relevant insights from this week's
analysis of AMD financials, gaming market trends, and competitive positioning.
End with one forward-looking sentence about what to watch in the coming weeks.
Write in plain prose. No markdown.
""", "Key Takeaways")

    return sections


def build_styles():
    """Build a custom style sheet."""
    base = getSampleStyleSheet()

    styles = {
        "masthead_title": ParagraphStyle(
            "masthead_title",
            fontSize=28,
            fontName="Helvetica-Bold",
            textColor=colors.white,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "masthead_sub": ParagraphStyle(
            "masthead_sub",
            fontSize=11,
            fontName="Helvetica",
            textColor=colors.HexColor("#FFCCCC"),
            alignment=TA_CENTER,
            spaceAfter=0,
        ),
        "section_heading": ParagraphStyle(
            "section_heading",
            fontSize=14,
            fontName="Helvetica-Bold",
            textColor=AMD_RED,
            spaceBefore=18,
            spaceAfter=6,
            borderPadding=(0, 0, 4, 0),
        ),
        "body": ParagraphStyle(
            "body",
            fontSize=10,
            fontName="Helvetica",
            textColor=AMD_DARK,
            leading=16,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
        ),
        "editors_note": ParagraphStyle(
            "editors_note",
            fontSize=10,
            fontName="Helvetica-Oblique",
            textColor=AMD_GREY,
            leading=15,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
        ),
        "takeaway_box": ParagraphStyle(
            "takeaway_box",
            fontSize=10,
            fontName="Helvetica",
            textColor=AMD_DARK,
            leading=15,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontSize=8,
            fontName="Helvetica",
            textColor=AMD_GREY,
            alignment=TA_CENTER,
        ),
        "disclaimer": ParagraphStyle(
            "disclaimer",
            fontSize=7,
            fontName="Helvetica-Oblique",
            textColor=AMD_GREY,
            alignment=TA_CENTER,
            leading=10,
        ),
    }
    return styles


def split_paragraphs(text: str) -> list:
    """Split plain text into paragraphs on blank lines."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paras


def build_pdf(sections: dict, output_path: Path, date_str: str) -> None:
    """Assemble the newsletter PDF using reportlab Platypus."""
    log.info("Building PDF: %s", output_path)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.75 * inch,
        title=f"AMD Finance Newsletter — {date_str}",
        author="AMD Finance Newsletter Bot",
        subject="AMD Weekly Finance & Market Intelligence",
    )

    styles = build_styles()
    story  = []
    W      = letter[0] - 1.5 * inch  # usable width

    # ---- Masthead banner ----
    masthead_data = [[
        Paragraph("AMD WEEKLY FINANCE NEWSLETTER", styles["masthead_title"]),
    ], [
        Paragraph(f"Market Intelligence &amp; Competitive Analysis  |  {date_str}", styles["masthead_sub"]),
    ]]
    masthead = Table(masthead_data, colWidths=[W])
    masthead.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AMD_RED),
        ("TOPPADDING",    (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ("LEFTPADDING",   (0, 0), (-1, -1), 20),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
    ]))
    story.append(masthead)
    story.append(Spacer(1, 12))

    # ---- Coverage tags row ----
    tags = ["AMD FINANCIALS & EARNINGS", "GLOBAL GAMING TRENDS", "INTEL & NVIDIA ANALYSIS"]
    tag_cells = [[Paragraph(t, ParagraphStyle(
        "tag", fontSize=8, fontName="Helvetica-Bold",
        textColor=AMD_RED, alignment=TA_CENTER
    )) for t in tags]]
    tag_table = Table(tag_cells, colWidths=[W / 3] * 3)
    tag_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), AMD_LIGHT),
        ("BOX",           (0, 0), (-1, -1), 0.5, AMD_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, AMD_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tag_table)
    story.append(Spacer(1, 16))

    # ---- Editor's Note ----
    story.append(Paragraph("EDITOR'S NOTE", styles["section_heading"]))
    story.append(HRFlowable(width=W, thickness=1, color=AMD_RED, spaceAfter=8))
    for para in split_paragraphs(sections["editors_note"]):
        story.append(Paragraph(para, styles["editors_note"]))
    story.append(Spacer(1, 8))

    # ---- AMD Financials ----
    story.append(Paragraph("AMD FINANCIALS &amp; EARNINGS", styles["section_heading"]))
    story.append(HRFlowable(width=W, thickness=1, color=AMD_RED, spaceAfter=8))
    for para in split_paragraphs(sections["financials"]):
        story.append(Paragraph(para, styles["body"]))
    story.append(Spacer(1, 8))

    # ---- Gaming Market ----
    story.append(PageBreak())
    story.append(Paragraph("GLOBAL GAMING MARKET TRENDS", styles["section_heading"]))
    story.append(HRFlowable(width=W, thickness=1, color=AMD_RED, spaceAfter=8))
    for para in split_paragraphs(sections["gaming"]):
        story.append(Paragraph(para, styles["body"]))
    story.append(Spacer(1, 8))

    # ---- Competitor Analysis ----
    story.append(Paragraph("COMPETITOR ANALYSIS: INTEL &amp; NVIDIA", styles["section_heading"]))
    story.append(HRFlowable(width=W, thickness=1, color=AMD_RED, spaceAfter=8))
    for para in split_paragraphs(sections["competitors"]):
        story.append(Paragraph(para, styles["body"]))
    story.append(Spacer(1, 12))

    # ---- Key Takeaways box ----
    story.append(PageBreak())
    story.append(Paragraph("KEY TAKEAWAYS", styles["section_heading"]))
    story.append(HRFlowable(width=W, thickness=1, color=AMD_RED, spaceAfter=8))
    takeaway_paras = [[Paragraph(p, styles["takeaway_box"])]
                      for p in split_paragraphs(sections["takeaways"])]
    if takeaway_paras:
        kt_table = Table(takeaway_paras, colWidths=[W])
        kt_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), AMD_LIGHT),
            ("BOX",           (0, 0), (-1, -1), 1, AMD_RED),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 14),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ]))
        story.append(kt_table)

    story.append(Spacer(1, 24))

    # ---- Footer ----
    story.append(HRFlowable(width=W, thickness=0.5, color=AMD_BORDER, spaceAfter=8))
    story.append(Paragraph(
        f"AMD Weekly Finance Newsletter  |  Generated {date_str}  |  Powered by AMD LLM Gateway",
        styles["footer"]
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "This newsletter is generated automatically for informational purposes only and does not "
        "constitute financial advice. All figures and projections are based on publicly available "
        "information and AI-generated analysis. Past performance is not indicative of future results.",
        styles["disclaimer"]
    ))

    doc.build(story)
    log.info("PDF saved: %s (%.1f KB)", output_path, output_path.stat().st_size / 1024)


def commit_and_push(output_path: Path, file_date: str) -> None:
    """Commit the newsletter PDF and push to GitHub."""
    repo = git.Repo(REPO_PATH)

    abs_path = str(output_path)
    repo.index.add([abs_path])
    log.info("Staged: %s", abs_path)

    try:
        staged_diff = repo.index.diff("HEAD")
        has_changes = len(staged_diff) > 0
    except Exception:
        has_changes = True

    if not has_changes:
        untracked = repo.untracked_files
        has_changes = any(f"newsletters" in f for f in untracked)

    if not has_changes:
        log.info("No changes detected — newsletter already up to date.")
        return

    origin = repo.remote(name=GIT_REMOTE)
    log.info("Pulling latest changes...")
    origin.pull(rebase=True)

    timestamp  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    commit_msg = f"chore(newsletter): publish AMD finance newsletter [{timestamp}]"
    repo.index.commit(commit_msg)
    log.info("Committed: %s", commit_msg)

    push_result = origin.push(refspec=f"HEAD:{GIT_BRANCH}")
    for info in push_result:
        if info.flags & info.ERROR:
            raise RuntimeError(f"Git push failed: {info.summary}")

    log.info("Pushed to %s/%s", GIT_REMOTE, GIT_BRANCH)


def main() -> None:
    if API_KEY == "PASTE_YOUR_AMD_GATEWAY_KEY_HERE":
        log.error("API_KEY is not set. Edit the CONFIG block at the top of this script.")
        sys.exit(1)

    if not Path(REPO_PATH).is_dir():
        log.error("REPO_PATH does not exist: %s", REPO_PATH)
        sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)

    date_str    = datetime.now(timezone.utc).strftime("%B %d, %Y")
    file_date   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_path = OUTPUT_DIR / f"amd_finance_newsletter_{file_date}.pdf"

    try:
        client   = make_client()
        sections = generate_content(client, date_str)
        build_pdf(sections, output_path, date_str)
        commit_and_push(output_path, file_date)
        log.info("Done. Newsletter published to %s", output_path)
    except Exception as exc:
        log.exception("Newsletter generation failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
