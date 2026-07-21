"""Builds the presentation deck: ContextAI_Evaluation.pptx.

Run make_diagrams.py and make_charts.py first (or via `python3 build_deck.py`,
which does it automatically) to (re)generate the image assets this script
places on slides.

Covers all three connected projects, not just this evaluation repo:
  - ContextAI      - the graph-extraction engine
  - ConnectContext - the MCP server (published as `contextai-mcp`) that
                     exposes ContextAI's graph as tools an AI agent can call
  - Test_context   - this repo: the evaluation of whether that combination
                     actually helps a real coding agent (Codex)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt, Emu

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
OUT_PATH = HERE / "ContextAI_Evaluation.pptx"

# ---- theme ----
NAVY = RGBColor(0x1A, 0x1A, 0x2E)
GREEN = RGBColor(0x2C, 0xA0, 0x2C)
GRAY = RGBColor(0x94, 0xA3, 0xB8)
LIGHT_BG = RGBColor(0xF7, 0xF8, 0xFA)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DARK_TEXT = RGBColor(0x33, 0x33, 0x33)
AMBER = RGBColor(0xD9, 0x77, 0x06)
BLUE = RGBColor(0x25, 0x63, 0xEB)
PURPLE = RGBColor(0x93, 0x33, 0xEA)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

FONT = "Calibri"


def new_presentation() -> Presentation:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def _blank_slide(prs):
    layout = prs.slide_layouts[6]  # blank
    return prs.slides.add_slide(layout)


def _fill_bg(slide, color=WHITE):
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = color


def _add_text(slide, x, y, w, h, text, size=18, bold=False, color=DARK_TEXT,
              align=PP_ALIGN.LEFT, italic=False, font=FONT, line_spacing=1.12,
              anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.alignment = align
        p.line_spacing = line_spacing
        for run in p.runs:
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.italic = italic
            run.font.name = font
            run.font.color.rgb = color
    return box


def _add_bullets(slide, x, y, w, h, items, size=17, color=DARK_TEXT,
                  bullet_color=GREEN, spacing_after=8, font=FONT):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(spacing_after)
        p.line_spacing = 1.08
        run_bullet = p.add_run()
        run_bullet.text = "\u25B8  "
        run_bullet.font.size = Pt(size)
        run_bullet.font.color.rgb = bullet_color
        run_bullet.font.bold = True
        run_bullet.font.name = font
        run_text = p.add_run()
        run_text.text = item
        run_text.font.size = Pt(size)
        run_text.font.color.rgb = color
        run_text.font.name = font
    return box


def _accent_bar(slide, color=GREEN, y=Inches(1.1), height=Pt(4), x=Inches(0.55), w=Inches(2.2)):
    bar = slide.shapes.add_shape(1, x, y, w, height)  # MSO_SHAPE.RECTANGLE = 1
    bar.fill.solid()
    bar.fill.fore_color.rgb = color
    bar.line.fill.background()
    bar.shadow.inherit = False
    return bar


def add_title_bar(slide, title, subtitle=None, title_color=NAVY, accent=GREEN, size=28):
    _add_text(slide, Inches(0.55), Inches(0.3), Inches(10.8), Inches(0.7), title,
              size=size, bold=True, color=title_color)
    _accent_bar(slide, color=accent, y=Inches(0.98))
    if subtitle:
        _add_text(slide, Inches(0.55), Inches(1.08), Inches(11.0), Inches(0.4), subtitle,
                   size=13.5, color=RGBColor(0x66, 0x66, 0x66), italic=True)


def add_part_badge(slide, label, color=GREEN):
    """Small top-right badge replacing full-page section dividers, to keep the deck dense."""
    w = Inches(0.145 * len(label) + 0.5)
    badge = slide.shapes.add_shape(1, SLIDE_W - w - Inches(0.5), Inches(0.42), w, Inches(0.4))
    badge.fill.solid()
    badge.fill.fore_color.rgb = color
    badge.line.fill.background()
    badge.shadow.inherit = False
    tf = badge.text_frame
    tf.word_wrap = False
    tf.margin_left = Emu(0)
    tf.margin_right = Emu(0)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = label
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.color.rgb = WHITE
    run.font.name = FONT


def add_content_slide(prs, title, subtitle=None, bg=WHITE, accent=GREEN, part=None, title_size=28):
    slide = _blank_slide(prs)
    _fill_bg(slide, bg)
    add_title_bar(slide, title, subtitle, accent=accent, size=title_size)
    if part:
        add_part_badge(slide, part, color=accent)
    return slide


def add_picture_fit(slide, img_path, x, y, max_w, max_h):
    from PIL import Image

    with Image.open(img_path) as im:
        iw, ih = im.size
    ratio = min(max_w / iw, max_h / ih)
    w, h = int(iw * ratio), int(ih * ratio)
    px = x + (max_w - w) // 2
    py = y + (max_h - h) // 2
    slide.shapes.add_picture(str(img_path), px, py, width=w, height=h)


def _callout_box(slide, x, y, w, h, text, fill=RGBColor(0xEE, 0xF6, 0xEE), border=GREEN, size=22,
                  text_color=NAVY):
    box = slide.shapes.add_shape(1, x, y, w, h)
    box.fill.solid()
    box.fill.fore_color.rgb = fill
    box.line.color.rgb = border
    box.line.width = Pt(2.25)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = True
    run.font.color.rgb = text_color
    run.font.name = FONT
    return box


# --------------------------------------------------------------------------
# Slides
# --------------------------------------------------------------------------

def slide_title(prs):
    slide = _blank_slide(prs)
    _fill_bg(slide, NAVY)

    _add_text(slide, Inches(1.0), Inches(1.9), Inches(11.3), Inches(1.9),
              "Does Giving an AI a \u201cMap\u201d of Your Code\nActually Help?",
              size=40, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    band = slide.shapes.add_shape(1, Inches(0), Inches(4.15), SLIDE_W, Inches(0.06))
    band.fill.solid()
    band.fill.fore_color.rgb = GREEN
    band.line.fill.background()

    _add_text(slide, Inches(1.5), Inches(4.4), Inches(10.3), Inches(0.6),
              "ContextAI + ConnectContext, put to the test with a real AI coding agent",
              size=19, color=GRAY, align=PP_ALIGN.CENTER, italic=True)
    _add_text(slide, Inches(1.5), Inches(6.5), Inches(10.3), Inches(0.5),
              "A hands-on evaluation across 3 connected projects \u2014 48 real questions, 288 AI runs",
              size=14, color=RGBColor(0x88, 0x88, 0x99), align=PP_ALIGN.CENTER)
    return slide


def slide_problem_and_idea(prs):
    slide = add_content_slide(prs, "The everyday problem \u2014 and the idea",
                               "Why understanding a big codebase is hard, and what if the AI had a map first?",
                               part="1 \u00b7 THE IDEA")
    add_picture_fit(slide, ASSETS / "search_vs_map.png", Inches(0.5), Inches(1.75), Inches(12.3), Inches(3.55))
    _callout_box(
        slide, Inches(1.0), Inches(5.55), Inches(11.3), Inches(1.55),
        "\u201cDoes a real AI coding assistant answer code questions better with a "
        "pre-built map of the code \u2014 compared to using only its normal tools?\u201d",
        fill=LIGHT_BG, border=GREEN, size=19,
    )
    return slide


def slide_three_repos(prs):
    slide = add_content_slide(prs, "Three connected projects, one pipeline",
                               "This isn't one repo \u2014 it's a small stack, and this deck covers all of it",
                               part="1 \u00b7 THE IDEA")
    add_picture_fit(slide, ASSETS / "three_repos.png", Inches(0.4), Inches(1.7), Inches(12.5), Inches(5.4))
    return slide


def slide_contextai(prs):
    slide = add_content_slide(prs, "Project 1: ContextAI \u2014 the engine", accent=GREEN,
                               part="2 \u00b7 THE THREE PROJECTS")
    add_picture_fit(slide, ASSETS / "graph_pipeline.png", Inches(0.4), Inches(1.55), Inches(8.0), Inches(5.5))
    _add_bullets(slide, Inches(8.6), Inches(1.85), Inches(4.4), Inches(5.0), [
        "Each function/class becomes a rich node: its code, inputs/outputs, error handling, complexity, even test coverage & git history.",
        "Each connection becomes a typed edge (calls, imports, reads/writes data, and more), with how critical and how likely-to-fail it is.",
        "Alpha stage, but backed by 150+ automated tests.",
    ], size=14.5, spacing_after=10)
    return slide


def slide_connectcontext(prs):
    slide = add_content_slide(prs, "Project 2: ConnectContext \u2014 the bridge", accent=BLUE,
                               part="2 \u00b7 THE THREE PROJECTS")
    add_picture_fit(slide, ASSETS / "tool_tiers.png", Inches(0.4), Inches(1.55), Inches(12.5), Inches(5.5))
    return slide


def slide_what_we_built(prs):
    slide = add_content_slide(prs, "Project 3: this evaluation \u2014 what we built",
                               accent=AMBER, part="2 \u00b7 THE THREE PROJECTS", title_size=26)
    add_picture_fit(slide, ASSETS / "two_modes.png", Inches(0.4), Inches(1.55), Inches(7.3), Inches(4.0))
    _add_bullets(slide, Inches(8.0), Inches(1.75), Inches(5.0), Inches(4.8), [
        "4 real open-source projects (Flask, Click, HTTPX, Rich), 9k\u201326k lines each.",
        "48 realistic questions (\u201cwho calls this,\u201d \u201cwhat breaks if I change this,\u201d and more).",
        "A real AI coding agent (OpenAI's Codex) \u2014 not a toy stand-in.",
        "ConnectContext plugged in exactly the way a real developer would.",
    ], size=15, spacing_after=9)
    _add_text(slide, Inches(0.4), Inches(5.75), Inches(7.3), Inches(0.7),
              "Same questions. Same AI. Same rules. The map is the only thing that's different.",
              size=13, color=RGBColor(0x66, 0x66, 0x66), italic=True, align=PP_ALIGN.CENTER)
    return slide


def slide_mcp_and_hiccups(prs):
    slide = add_content_slide(prs, "Wiring it up \u2014 and two real hiccups", accent=BLUE,
                               part="3 \u00b7 TESTING")
    add_picture_fit(slide, ASSETS / "mcp_connection.png", Inches(0.4), Inches(1.5), Inches(7.5), Inches(4.4))
    _add_text(slide, Inches(8.1), Inches(1.65), Inches(4.9), Inches(0.4), "\U0001F41B Hidden naming clash",
              size=15, bold=True, color=AMBER)
    _add_text(slide, Inches(8.1), Inches(2.1), Inches(4.9), Inches(1.5),
              "Flask ships a file with the same name as a core Python module, which silently broke the "
              "map-builder when run inside it. Fixed by keeping it in its own safe folder.",
              size=13, color=DARK_TEXT)
    _add_text(slide, Inches(8.1), Inches(3.75), Inches(4.9), Inches(0.4), "\u23F1\uFE0F Permissions limitation",
              size=15, bold=True, color=AMBER)
    _add_text(slide, Inches(8.1), Inches(4.2), Inches(4.9), Inches(1.5),
              "Run unattended, the AI tool wouldn't let the map get used at all \u2014 it waited for a permission "
              "click that could never come. Fixed with a setting, applied identically to both modes.",
              size=13, color=DARK_TEXT)
    return slide


def slide_pipeline_and_grading(prs):
    slide = add_content_slide(prs, "How we ran it, and how we graded it", part="3 \u00b7 TESTING")
    add_picture_fit(slide, ASSETS / "pipeline.png", Inches(0.4), Inches(1.5), Inches(12.5), Inches(2.85))
    add_picture_fit(slide, ASSETS / "grading.png", Inches(0.4), Inches(4.35), Inches(12.5), Inches(2.85))
    return slide


def slide_results_headline_and_project(prs):
    slide = add_content_slide(prs, "The results: roughly a coin flip", accent=GREEN, part="4 \u00b7 RESULTS")
    add_picture_fit(slide, ASSETS / "chart_headline.png", Inches(0.3), Inches(1.55), Inches(6.4), Inches(5.4))
    add_picture_fit(slide, ASSETS / "chart_by_project.png", Inches(6.75), Inches(1.55), Inches(6.3), Inches(5.4))
    return slide


def slide_results_cost(prs):
    slide = add_content_slide(prs, "The map wasn't free", accent=AMBER, part="4 \u00b7 RESULTS")
    add_picture_fit(slide, ASSETS / "chart_cost.png", Inches(1.1), Inches(1.6), Inches(11.1), Inches(4.5))
    _add_text(slide, Inches(1.1), Inches(6.35), Inches(11.1), Inches(0.7),
              "Same number of steps, but ~70% more material \u201cread\u201d per question when the map was available.",
              size=15, color=RGBColor(0x66, 0x66, 0x66), italic=True, align=PP_ALIGN.CENTER)
    return slide


def slide_why(prs):
    slide = add_content_slide(prs, "Why didn't it help more? Two real reasons", accent=PURPLE,
                               part="5 \u00b7 WHY", title_size=26)
    _add_text(slide, Inches(0.55), Inches(1.6), Inches(6.0), Inches(0.4),
              "1. The referee itself was sometimes wrong", size=16, bold=True, color=BLUE)
    _add_text(slide, Inches(0.55), Inches(2.05), Inches(6.0), Inches(1.9),
              "We hand-checked one \u201closs\u201d: the map-assisted answer was actually correct (verified against "
              "the real source code) \u2014 the AI judge simply made a mistake. The true gap is probably smaller "
              "than the headline number suggests.",
              size=13.5, color=DARK_TEXT)

    _add_text(slide, Inches(6.85), Inches(1.6), Inches(6.0), Inches(0.4),
              "2. Trusting the map too much", size=16, bold=True, color=AMBER)
    add_picture_fit(slide, ASSETS / "chart_recall_gap.png", Inches(6.85), Inches(2.05), Inches(6.0), Inches(3.15))

    _callout_box(
        slide, Inches(0.55), Inches(5.5), Inches(12.3), Inches(1.55),
        "Bottom line: the extra map didn't clearly make the AI better at understanding code \u2014 it used "
        "the tool eagerly, but that didn't translate into better answers.",
        fill=RGBColor(0xF3, 0xEC, 0xFB), border=PURPLE, size=17,
    )
    return slide


def slide_reflection(prs):
    slide = _blank_slide(prs)
    _fill_bg(slide, NAVY)
    _add_text(slide, Inches(0.9), Inches(0.5), Inches(11.5), Inches(0.8),
              "A personal note, 4 months later", size=28, bold=True, color=WHITE)
    _accent_bar(slide, color=AMBER, y=Inches(1.28), x=Inches(0.9))

    _add_text(slide, Inches(0.9), Inches(1.7), Inches(11.5), Inches(1.5),
              "When this problem first came up about 4 months ago, it felt urgent: AI models couldn't hold "
              "a big codebase \u201cin their head,\u201d so a pre-built map felt essential.",
              size=18, color=RGBColor(0xDD, 0xDD, 0xE5))

    _add_text(slide, Inches(0.9), Inches(3.3), Inches(11.5), Inches(1.9),
              "In just those few months, AI models have gotten dramatically better at holding and "
              "reasoning over much more code at once, and simply gotten smarter overall. That original "
              "problem \u2014 the one this tool was built to solve \u2014 has largely shrunk on its own, just from "
              "the base AI models improving.",
              size=18, color=RGBColor(0xDD, 0xDD, 0xE5))

    _callout_box(
        slide, Inches(0.9), Inches(5.35), Inches(11.5), Inches(1.5),
        "Our results fit that story: a modern, capable AI agent with just its ordinary tools already does "
        "a solid job \u2014 the extra map no longer clears as high a bar as it once would have.",
        fill=RGBColor(0x22, 0x33, 0x2A), border=GREEN, size=18, text_color=GREEN,
    )
    return slide


def slide_takeaways_and_thanks(prs):
    slide = add_content_slide(prs, "What this means going forward", part="6 \u00b7 REFLECTION")
    _add_bullets(slide, Inches(0.55), Inches(1.7), Inches(12.3), Inches(3.7), [
        "Tools like this still have a place \u2014 but the bar for \u201cworth adding\u201d keeps rising as base AI models improve.",
        "The AI should be encouraged to double-check the map's answer, not just trust it outright \u2014 especially for \u201clist everything\u201d style questions.",
        "The token/reading cost of extra tools is real and should be weighed against the (currently unclear) benefit.",
        "Worth re-running periodically \u2014 as models keep improving, the answer to \u201cdoes this tool help\u201d can keep changing.",
    ], size=17, spacing_after=12)
    band = slide.shapes.add_shape(1, Inches(0.55), Inches(6.05), Inches(12.3), Inches(0.02))
    band.fill.solid()
    band.fill.fore_color.rgb = RGBColor(0xE5, 0xE7, 0xEB)
    band.line.fill.background()
    _add_text(slide, Inches(0.55), Inches(6.3), Inches(12.3), Inches(0.7),
              "Thank you \u2014 full write-up, charts & raw data: eval/report/REPORT.md",
              size=16, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
    return slide


def main():
    subprocess.run([sys.executable, str(HERE / "make_diagrams.py")], check=True)
    subprocess.run([sys.executable, str(HERE / "make_charts.py")], check=True)

    prs = new_presentation()

    slide_title(prs)
    slide_problem_and_idea(prs)
    slide_three_repos(prs)
    slide_contextai(prs)
    slide_connectcontext(prs)
    slide_what_we_built(prs)
    slide_mcp_and_hiccups(prs)
    slide_pipeline_and_grading(prs)
    slide_results_headline_and_project(prs)
    slide_results_cost(prs)
    slide_why(prs)
    slide_reflection(prs)
    slide_takeaways_and_thanks(prs)

    prs.save(OUT_PATH)
    print(f"Saved {OUT_PATH} ({len(prs.slides._sldIdLst)} slides)")


if __name__ == "__main__":
    main()
