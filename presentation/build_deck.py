"""Builds the presentation deck: ContextAI_Evaluation.pptx.

Run make_diagrams.py and make_charts.py first (or via `python3 build_deck.py`,
which does it automatically) to (re)generate the image assets this script
places on slides.
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
              align=PP_ALIGN.LEFT, italic=False, font=FONT, line_spacing=1.15,
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


def _add_bullets(slide, x, y, w, h, items, size=19, color=DARK_TEXT, bold_first=False,
                  bullet_color=GREEN, spacing_after=10, font=FONT):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(spacing_after)
        p.line_spacing = 1.12
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


def _accent_bar(slide, color=GREEN, y=Inches(1.28), height=Pt(4)):
    bar = slide.shapes.add_shape(1, Inches(0.55), y, Inches(2.2), height)  # MSO_SHAPE.RECTANGLE = 1
    bar.fill.solid()
    bar.fill.fore_color.rgb = color
    bar.line.fill.background()
    bar.shadow.inherit = False
    return bar


def add_title_bar(slide, title, subtitle=None, title_color=NAVY, accent=GREEN):
    _add_text(slide, Inches(0.55), Inches(0.42), Inches(12.2), Inches(0.9), title,
              size=32, bold=True, color=title_color)
    _accent_bar(slide, color=accent)
    if subtitle:
        _add_text(slide, Inches(0.55), Inches(1.42), Inches(12.2), Inches(0.5), subtitle,
                   size=15.5, color=RGBColor(0x66, 0x66, 0x66), italic=True)


def add_content_slide(prs, title, subtitle=None, bg=WHITE, accent=GREEN):
    slide = _blank_slide(prs)
    _fill_bg(slide, bg)
    add_title_bar(slide, title, subtitle, accent=accent)
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


def add_footer(slide, text, page_no=None):
    _add_text(slide, Inches(0.55), Inches(7.08), Inches(9), Inches(0.35), text,
              size=10.5, color=RGBColor(0xAA, 0xAA, 0xAA))
    if page_no is not None:
        _add_text(slide, Inches(12.5), Inches(7.08), Inches(0.6), Inches(0.35), str(page_no),
                   size=10.5, color=RGBColor(0xAA, 0xAA, 0xAA), align=PP_ALIGN.RIGHT)


# --------------------------------------------------------------------------
# Slide builders
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
              "Putting ContextAI's code-graph tool to the test with a real AI coding agent",
              size=19, color=GRAY, align=PP_ALIGN.CENTER, italic=True)
    _add_text(slide, Inches(1.5), Inches(6.5), Inches(10.3), Inches(0.5),
              "A hands-on evaluation \u2014 48 real questions, 4 real codebases, 288 AI runs",
              size=14, color=RGBColor(0x88, 0x88, 0x99), align=PP_ALIGN.CENTER)
    return slide


def slide_section(prs, number, title, subtitle):
    slide = _blank_slide(prs)
    _fill_bg(slide, NAVY)
    _add_text(slide, Inches(1.0), Inches(2.4), Inches(2.0), Inches(1.4), number,
              size=90, bold=True, color=GREEN, align=PP_ALIGN.LEFT)
    _add_text(slide, Inches(3.3), Inches(2.75), Inches(9.0), Inches(1.0), title,
              size=34, bold=True, color=WHITE)
    _add_text(slide, Inches(3.3), Inches(3.75), Inches(9.0), Inches(1.0), subtitle,
              size=17, color=GRAY, italic=True)
    return slide


def slide_problem(prs):
    slide = add_content_slide(prs, "The everyday problem", "Why understanding a big codebase is hard")
    _add_bullets(slide, Inches(0.7), Inches(2.0), Inches(6.4), Inches(4.5), [
        "Real software projects are huge \u2014 tens of thousands of lines, spread across hundreds of files.",
        "When you ask an AI assistant a question like \u201cwho calls this function?\u201d, it usually has to search for text and open files one at a time \u2014 like a very fast game of Ctrl+F.",
        "That works, but it's slow, and it's easy to miss something hiding in a file that never got opened.",
    ], size=18.5)
    add_picture_fit(slide, ASSETS / "search_vs_map.png", Inches(7.15), Inches(1.9), Inches(5.6), Inches(4.9))
    add_footer(slide, "Part 1 \u2014 The Idea")
    return slide


def slide_idea(prs):
    slide = add_content_slide(prs, "The idea: give the AI a map first", accent=GREEN)
    _add_text(slide, Inches(0.7), Inches(2.0), Inches(11.8), Inches(1.3),
              "What if, instead of re-reading the whole codebase every time, the AI could look up a "
              "pre-built \u201cmap\u201d that already shows which functions connect to which?",
              size=24, color=NAVY, bold=True)
    _add_text(slide, Inches(0.7), Inches(4.1), Inches(11.5), Inches(2.2),
              "That's what ContextAI's code-graph tool promises to do.\n\n"
              "This is exactly the kind of tool people believed, a few months ago, that AI coding "
              "assistants would badly need \u2014 codebases are big, and AI \u201cattention\u201d was limited. "
              "We built a rigorous, real-world test to find out if it actually helps.",
              size=18.5, color=DARK_TEXT)
    add_footer(slide, "Part 1 \u2014 The Idea")
    return slide


def slide_what_is_graph(prs):
    slide = add_content_slide(prs, "What is a \u201ccode graph,\u201d really?")
    _add_text(slide, Inches(0.7), Inches(1.85), Inches(11.9), Inches(1.5),
              "Think of it like a subway map for your code. Instead of a list of station names, it "
              "shows every station (function) and every line connecting them (which function calls "
              "which) \u2014 so you can trace a route instantly.",
              size=19, color=NAVY, italic=True)
    add_picture_fit(slide, ASSETS / "graph_capabilities.png", Inches(0.6), Inches(3.15), Inches(12.1), Inches(3.9))
    add_footer(slide, "Part 1 \u2014 The Idea")
    return slide


def slide_research_question(prs):
    slide = add_content_slide(prs, "The question we set out to answer")
    _callout_box(
        slide, Inches(1.3), Inches(2.5), Inches(10.7), Inches(2.6),
        "\u201cDoes a real AI coding assistant answer code questions better when it also has "
        "ContextAI's map \u2014 compared to using only its normal tools?\u201d",
        fill=LIGHT_BG, border=GREEN, size=25,
    )
    _add_text(slide, Inches(1.3), Inches(5.5), Inches(10.7), Inches(1.0),
              "We answered this with real runs of a real AI agent \u2014 not a guess.",
              size=17, color=RGBColor(0x66, 0x66, 0x66), italic=True, align=PP_ALIGN.CENTER)
    add_footer(slide, "Part 1 \u2014 The Idea")
    return slide


def slide_what_we_built(prs):
    slide = add_content_slide(prs, "What we actually built & reproduced")
    _add_bullets(slide, Inches(0.7), Inches(2.0), Inches(12.0), Inches(4.5), [
        "4 real, well-known open-source projects (Flask, Click, HTTPX, Rich) \u2014 the same code real developers use every day, 9,000 to 26,000 lines each.",
        "48 hand-written, realistic questions about that code (\u201cwho calls this,\u201d \u201cwhat breaks if I change this,\u201d \u201ctrace this request end-to-end,\u201d and more).",
        "A real AI coding agent (OpenAI's Codex) to answer them \u2014 not a toy stand-in.",
        "The actual ContextAI code-map tool, connected the same way a real developer would connect it \u2014 as a plug-in tool for the AI, not hard-wired into our test scripts.",
        "An automatic scoring system, so results are measured, not eyeballed.",
    ], size=19.5, spacing_after=14)
    add_footer(slide, "Part 2 \u2014 What We Built")
    return slide


def slide_two_modes(prs):
    slide = add_content_slide(prs, "Two modes, one fair comparison")
    add_picture_fit(slide, ASSETS / "two_modes.png", Inches(0.6), Inches(1.85), Inches(12.1), Inches(5.2))
    add_footer(slide, "Part 2 \u2014 What We Built")
    return slide


def slide_mcp(prs):
    slide = add_content_slide(prs, "How we connected the map to the AI")
    add_picture_fit(slide, ASSETS / "mcp_connection.png", Inches(0.6), Inches(1.85), Inches(12.1), Inches(5.2))
    add_footer(slide, "Part 2 \u2014 What We Built")
    return slide


def slide_hiccups(prs):
    slide = add_content_slide(prs, "Two real hiccups along the way", accent=AMBER)
    _add_text(slide, Inches(0.7), Inches(1.9), Inches(5.7), Inches(0.5), "\U0001F41B  A hidden naming clash",
              size=20, bold=True, color=AMBER)
    _add_text(slide, Inches(0.7), Inches(2.5), Inches(5.7), Inches(3.8),
              "One of the test projects (Flask) happens to have a file named the same as a core Python building block.\n\n"
              "That silently confused the map-building tool and crashed it \u2014 a subtle bug that only shows up on that one project.\n\n"
              "We tracked it down and fixed it by keeping the map-builder in its own safe folder, away from the project it's mapping.",
              size=16, color=DARK_TEXT)

    _add_text(slide, Inches(6.9), Inches(1.9), Inches(5.7), Inches(0.5), "\u23F1\uFE0F  A permissions limitation",
              size=20, bold=True, color=AMBER)
    _add_text(slide, Inches(6.9), Inches(2.5), Inches(5.7), Inches(3.8),
              "When run unattended (no human watching), the AI tool we used wouldn't let the map get used at all \u2014 it kept waiting for a permission click that could never come.\n\n"
              "We found the setting to safely allow it to run unattended, and applied the exact same setting to both modes \u2014 so the comparison stayed fair.",
              size=16, color=DARK_TEXT)
    add_footer(slide, "Part 2 \u2014 What We Built")
    return slide


def slide_pipeline(prs):
    slide = add_content_slide(prs, "How the test was run, end to end")
    add_picture_fit(slide, ASSETS / "pipeline.png", Inches(0.5), Inches(1.85), Inches(12.3), Inches(5.2))
    add_footer(slide, "Part 3 \u2014 Testing")
    return slide


def slide_grading(prs):
    slide = add_content_slide(prs, "How we graded the answers")
    add_picture_fit(slide, ASSETS / "grading.png", Inches(0.5), Inches(1.85), Inches(12.3), Inches(5.2))
    add_footer(slide, "Part 3 \u2014 Testing")
    return slide


def slide_results_headline(prs):
    slide = add_content_slide(prs, "The headline result", accent=GREEN)
    add_picture_fit(slide, ASSETS / "chart_headline.png", Inches(0.6), Inches(1.7), Inches(7.6), Inches(5.3))
    _add_text(slide, Inches(8.5), Inches(2.3), Inches(4.3), Inches(1.0), "Roughly a coin flip.",
              size=24, bold=True, color=NAVY)
    _add_bullets(slide, Inches(8.5), Inches(3.2), Inches(4.3), Inches(3.5), [
        "No clear overall winner.",
        "The map-assisted answers were preferred slightly less often than the plain answers.",
        "288 total AI runs. Zero crashes.",
    ], size=15.5)
    add_footer(slide, "Part 4 \u2014 Results")
    return slide


def slide_results_by_project(prs):
    slide = add_content_slide(prs, "Not one project favored the map")
    add_picture_fit(slide, ASSETS / "chart_by_project.png", Inches(0.6), Inches(1.75), Inches(12.1), Inches(5.1))
    add_footer(slide, "Part 4 \u2014 Results")
    return slide


def slide_results_cost(prs):
    slide = add_content_slide(prs, "The map wasn't free", accent=AMBER)
    add_picture_fit(slide, ASSETS / "chart_cost.png", Inches(0.9), Inches(1.75), Inches(11.5), Inches(4.6))
    _add_text(slide, Inches(0.9), Inches(6.5), Inches(11.5), Inches(0.7),
              "Same number of steps, but the AI had to \u201cread\u201d about 70% more material per question when the map was available.",
              size=15.5, color=RGBColor(0x66, 0x66, 0x66), italic=True, align=PP_ALIGN.CENTER)
    add_footer(slide, "Part 4 \u2014 Results")
    return slide


def slide_why_1(prs):
    slide = add_content_slide(prs, "Why didn't it help more? Reason #1", accent=BLUE)
    _add_text(slide, Inches(0.7), Inches(1.9), Inches(11.8), Inches(0.6),
              "Sometimes, the referee itself got it wrong.", size=21, bold=True, color=BLUE)
    _add_text(slide, Inches(0.7), Inches(2.7), Inches(11.8), Inches(3.6),
              "We double-checked one \u201closs\u201d by hand: the map-assisted answer said a certain "
              "piece of memory was \u201cshared per-thread\u201d \u2014 and the AI judge marked this wrong.\n\n"
              "We went and read the actual source code ourselves. The map-assisted answer was "
              "correct. The judge made the mistake, not the AI being tested.\n\n"
              "This tells us the true gap between the two modes is probably even smaller than "
              "our headline number suggests \u2014 some of the \u201closses\u201d aren't real losses.",
              size=18, color=DARK_TEXT)
    add_footer(slide, "Part 5 \u2014 Why the Results Look This Way")
    return slide


def slide_why_2(prs):
    slide = add_content_slide(prs, "Why didn't it help more? Reason #2", accent=AMBER)
    add_picture_fit(slide, ASSETS / "chart_recall_gap.png", Inches(0.6), Inches(1.75), Inches(7.4), Inches(4.9))
    _add_text(slide, Inches(8.3), Inches(2.1), Inches(4.5), Inches(1.0),
              "Trusting the map\ntoo much.", size=23, bold=True, color=AMBER)
    _add_text(slide, Inches(8.3), Inches(3.2), Inches(4.5), Inches(3.6),
              "The map is honest about gaps in itself \u2014 it even flags things it "
              "couldn't fully resolve.\n\n"
              "But when the AI trusted the map's answer as \u201ccomplete\u201d instead of double-"
              "checking, it sometimes missed real connections that a plain text search "
              "would have caught.",
              size=15.5, color=DARK_TEXT)
    add_footer(slide, "Part 5 \u2014 Why the Results Look This Way")
    return slide


def _callout_box(slide, x, y, w, h, text, fill=RGBColor(0xEE, 0xF6, 0xEE), border=GREEN, size=24):
    box = slide.shapes.add_shape(1, x, y, w, h)
    box.fill.solid()
    box.fill.fore_color.rgb = fill
    box.line.color.rgb = border
    box.line.width = Pt(2.5)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = True
    run.font.color.rgb = NAVY
    run.font.name = FONT
    return box


def slide_takeaway_box(prs):
    slide = add_content_slide(prs, "Bottom line, in one sentence", accent=GREEN)
    _callout_box(
        slide, Inches(0.9), Inches(2.5), Inches(11.5), Inches(2.7),
        "Giving today's AI coding agent an extra \u201ccode map\u201d tool didn't clearly make it better "
        "at understanding code \u2014 it used the tool eagerly, but that didn't translate into better answers.",
        size=24,
    )
    add_footer(slide, "Part 5 \u2014 Why the Results Look This Way")
    return slide


def slide_reflection(prs):
    slide = _blank_slide(prs)
    _fill_bg(slide, NAVY)
    _add_text(slide, Inches(0.9), Inches(0.55), Inches(11.5), Inches(0.9),
              "A personal note, 4 months later", size=30, bold=True, color=WHITE)
    _accent_bar(slide, color=AMBER, y=Inches(1.4))

    _add_text(slide, Inches(0.9), Inches(1.85), Inches(11.5), Inches(1.6),
              "When this problem first came up about 4 months ago, it felt urgent: AI models "
              "couldn't hold a big codebase \u201cin their head,\u201d so a pre-built map felt essential.",
              size=19, color=RGBColor(0xDD, 0xDD, 0xE5))

    _add_text(slide, Inches(0.9), Inches(3.55), Inches(11.5), Inches(1.9),
              "In just those few months, AI models have gotten dramatically better at holding "
              "and reasoning over much more code at once, and simply gotten smarter overall. "
              "That original problem \u2014 the one this tool was built to solve \u2014 has largely "
              "shrunk on its own, just from the base AI models improving.",
              size=19, color=RGBColor(0xDD, 0xDD, 0xE5))

    _add_text(slide, Inches(0.9), Inches(5.75), Inches(11.5), Inches(1.2),
              "Our results fit that story: a modern, capable AI agent with just its ordinary tools "
              "already does a solid job \u2014 the extra map no longer clears as high a bar as it once would have.",
              size=18, bold=True, color=GREEN)
    add_footer(slide, "Part 6 \u2014 Reflection")
    return slide


def slide_final_takeaways(prs):
    slide = add_content_slide(prs, "What this means going forward")
    _add_bullets(slide, Inches(0.7), Inches(2.0), Inches(12.0), Inches(4.6), [
        "Tools like this still have a place \u2014 but the bar for \u201cworth adding\u201d keeps rising as base AI models improve.",
        "If a tool like this is used, the AI should be encouraged to double-check the map's answer, not just trust it outright \u2014 especially for \u201clist everything\u201d style questions.",
        "The token/reading cost of using extra tools is real and should be weighed against the (currently unclear) benefit.",
        "This kind of test is worth re-running periodically \u2014 as models keep improving, the answer to \u201cdoes this tool help\u201d can keep changing.",
    ], size=19.5, spacing_after=16)
    add_footer(slide, "Part 6 \u2014 Reflection")
    return slide


def slide_thankyou(prs):
    slide = _blank_slide(prs)
    _fill_bg(slide, NAVY)
    _add_text(slide, Inches(1.0), Inches(3.0), Inches(11.3), Inches(1.0), "Thank you",
              size=44, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    _add_text(slide, Inches(1.0), Inches(4.0), Inches(11.3), Inches(0.6),
              "Full write-up, charts, and raw data: eval/report/REPORT.md",
              size=16, color=GRAY, align=PP_ALIGN.CENTER, italic=True)
    band = slide.shapes.add_shape(1, Inches(5.5), Inches(2.6), Inches(2.3), Inches(0.06))
    band.fill.solid()
    band.fill.fore_color.rgb = GREEN
    band.line.fill.background()
    return slide


def main():
    subprocess.run([sys.executable, str(HERE / "make_diagrams.py")], check=True)
    subprocess.run([sys.executable, str(HERE / "make_charts.py")], check=True)

    prs = new_presentation()

    slide_title(prs)
    slide_section(prs, "1", "The Idea", "What problem were we trying to solve?")
    slide_problem(prs)
    slide_idea(prs)
    slide_what_is_graph(prs)
    slide_research_question(prs)

    slide_section(prs, "2", "What We Built", "Reproducing a real, fair test")
    slide_what_we_built(prs)
    slide_two_modes(prs)
    slide_mcp(prs)
    slide_hiccups(prs)

    slide_section(prs, "3", "Testing", "How we ran and graded it")
    slide_pipeline(prs)
    slide_grading(prs)

    slide_section(prs, "4", "Results", "What actually happened")
    slide_results_headline(prs)
    slide_results_by_project(prs)
    slide_results_cost(prs)

    slide_section(prs, "5", "Why", "Why the results look this way")
    slide_why_1(prs)
    slide_why_2(prs)
    slide_takeaway_box(prs)

    slide_section(prs, "6", "Reflection", "Four months later")
    slide_reflection(prs)
    slide_final_takeaways(prs)

    slide_thankyou(prs)

    prs.save(OUT_PATH)
    print(f"Saved {OUT_PATH} ({len(prs.slides._sldIdLst)} slides)")


if __name__ == "__main__":
    main()
