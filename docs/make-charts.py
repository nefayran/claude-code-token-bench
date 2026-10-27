#!/usr/bin/env python3
# Draws the charts in docs/images/ and the dev.to cover. Run from anywhere: python3 docs/make-charts.py
# Needs matplotlib (pip install matplotlib pillow).
#
# Where the numbers come from:
# - The benchmark charts (results-priced-tokens, tool-definitions-deferred-vs-loaded) are computed from
#   results/*.json, and the script stops if a computed median or count differs from the published one.
# - CAP, BASH, HITS and REBUILD come from an earlier round on private repositories (billed input tokens, every
#   input token counted the same); they are not in results/.
# - COPILOT is the graph/grep ratio of priced tokens on structural questions of the large repositories in the
#   Copilot CLI benchmark, with "graph cheaper on", from results/v2/stats.md.
import json, statistics
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"
BG, PRIMARY, SECONDARY, GRID = "#02030a", "#EDEEF3", "#A3A7B7", "#1D2030"
BLUE, ORANGE, GREEN, GRAY = "#4C8DF6", "#F2713C", "#2BB673", "#7B8194"
plt.rcParams["font.family"] = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]
DPI, W, M = 200, 10.0, 0.5          # charts: 10 in at 200 dpi = 2000 px; side margin in inches

CAP = (267_000, 7, 708_000, 18)            # one answer: no cap (tokens, turns), 12,000-character cap (tokens, turns)
BASH = (1_800_000, 252_000)                # grep-only setup: Bash and subagents allowed, both denied
HITS = (1342, 251, 115)                    # bytes of one search hit: graph server, wrapper, grep line
REBUILD = (3_460_000, 83, 1_620_000, 36)   # one round of questions: first wrapper, rebuilt wrapper
COPILOT = ((0.29, "graph cheaper on 15 of 16 questions"), (0.74, "graph cheaper on 12 of 16 questions"),
           (0.97, "graph cheaper on 7 of 12 questions"))

EXPECTED = {  # published medians (priced tokens), correct answers, runs that called the graph
    ("haiku-4.5-main.json", "graph"): (30321, "28/36", 22),
    ("haiku-4.5-main.json", "rawgraph"): (43846, "32/36"),
    ("haiku-4.5-main.json", "nograph"): (31159, "33/36"),
    ("haiku-4.5-large.json", "graph"): (18791, "22/24"),
    ("haiku-4.5-large.json", "rawgraph"): (20687, "22/24"),
    ("haiku-4.5-large.json", "nograph"): (14955, "20/24"),
    ("sonnet-5-large.json", "graph"): (17227, "22/24"),
    ("sonnet-5-large.json", "rawgraph"): (23085, "22/24"),
    ("sonnet-5-large.json", "nograph"): (13348, "22/24"),
    ("haiku-4.5-toolsearch-default.json", "graph"): (41008, "11/12", 2),
    ("haiku-4.5-unguided.json", "graph-unguided"): (62008, "9/12", 4),
}


def stats(file, arm):
    runs = [r for r in json.loads((ROOT / "results" / file).read_text())["runs"] if r["arm"] == arm and r["valid"]]
    got = (int(statistics.median(r["tokenEquiv"] for r in runs)),
           f"{sum(r['correct'] for r in runs)}/{len(runs)}",
           sum(any(k.startswith("mcp__cbm__") for k in r["toolCalls"]) for r in runs))
    want = EXPECTED[(file, arm)]
    if got[:len(want)] != want:
        raise SystemExit(f"{file} {arm}: computed {got}, published {want}")
    return got


# Text is measured on a scratch canvas so every line can be wrapped to the width it really takes.
_scratch = plt.figure(figsize=(W, 2), dpi=DPI)
_renderer = _scratch.canvas.get_renderer()


def width_in(s, size, bold=False):
    t = _scratch.text(0, 0, s, fontsize=size, fontweight="bold" if bold else "normal")
    w = t.get_window_extent(_renderer).width / DPI
    t.remove()
    return w


def wrap(s, size, max_w, bold=False):
    lines, line = [], ""
    for word in s.split():
        trial = f"{line} {word}".strip()
        if line and width_in(trial, size, bold) > max_w:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line]


def line_h(size):
    return size * 1.3 / 72


class Page:
    """Lays a chart out top to bottom in inches, then draws it on one full-figure axes (y grows downward)."""

    def __init__(self, width=W, margin=M):
        self.w, self.m, self.y, self.ops = width, margin, margin, []

    def text(self, s, size, color, bold=False, x=None, gap_after=0.0):
        for line in wrap(s, size, self.w - 2 * self.m, bold):
            self.ops.append(("text", (self.m if x is None else x), self.y, line, size, color, bold, "left"))
            self.y += line_h(size)
        self.y += gap_after

    def gap(self, h):
        self.y += h

    def save(self, name, height=None):
        h = height or self.y + self.m
        fig = plt.figure(figsize=(self.w, h), dpi=DPI, facecolor=BG)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, self.w)
        ax.set_ylim(h, 0)
        ax.axis("off")
        for op in self.ops:
            if op[0] == "text":
                _, x, y, s, size, color, bold, ha, *boxed = op
                ax.text(x, y, s, fontsize=size, color=color, fontweight="bold" if bold else "normal",
                        ha=ha, va="top", zorder=3,
                        bbox=dict(facecolor=BG, edgecolor="none", pad=3) if boxed else None)
            elif op[0] == "rect":
                _, x, y, w, hh, color = op
                ax.add_patch(Rectangle((x, y), w, hh, color=color, lw=0, zorder=1))
            elif op[0] == "line":
                _, x0, y0, x1, y1, color, style = op
                ax.plot([x0, x1], [y0, y1], color=color, lw=1.4, ls=style, zorder=0.5 if style == "-" else 2)
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / name
        fig.savefig(path, dpi=DPI, facecolor=BG)
        plt.close(fig)
        px = (round(self.w * DPI), round(h * DPI))
        print(f"{path.relative_to(ROOT)}: {px[0]} x {px[1]}")


LABEL, VALUE, DETAIL, TICK = 20, 21, 17, 18
BAR_H, ROW_GAP = 0.36, 0.30


def bars(page, rows, maximum, ticks, fmt, groups=None, refline=None, label_left=False):
    """rows: dicts with label, value, color, end, optional detail, optional blocks, optional label_color.
    One value axis at the bottom. The plot width shrinks until every end label fits on the canvas.
    label_left puts each row label in a column left of its bar instead of on a line above it."""
    x0, avail = page.m, page.w - 2 * page.m
    if label_left:
        col = max(width_in(r["label"], LABEL) for r in rows) + 0.25
        x0, avail = x0 + col, avail - col
    pad = 0.12
    plot_w = min([avail] + [(avail - pad - width_in(r["end"], VALUE)) / (r["value"] / maximum) for r in rows])
    top = page.y
    for i, r in enumerate(rows):
        if groups and i in groups:
            page.gap(0.10 if i else 0)
            page.text(groups[i], 22, PRIMARY, bold=True, gap_after=0.06)
        if label_left:
            page.ops.append(("text", page.m, page.y + (BAR_H - line_h(LABEL) * 0.8) / 2, r["label"], LABEL,
                             r.get("label_color", PRIMARY), False, "left"))
        else:
            page.text(r["label"], LABEL, r.get("label_color", PRIMARY), gap_after=0.06)
        w = plot_w * r["value"] / maximum
        n = r.get("blocks", 1)
        gap = 0.035 if n > 1 else 0
        for b in range(n):
            page.ops.append(("rect", x0 + b * w / n, page.y, w / n - gap, BAR_H, r["color"]))
        page.ops.append(("text", x0 + w + pad, page.y + (BAR_H - line_h(VALUE) * 0.8) / 2, r["end"], VALUE,
                         PRIMARY, False, "left", True))
        page.y += BAR_H
        if r.get("detail"):
            page.gap(0.06)
            page.text(r["detail"], DETAIL, SECONDARY, x=x0)
        page.gap(0.16 if label_left else ROW_GAP)
    bottom = page.y - (0.16 if label_left else ROW_GAP) + 0.15
    for t in ticks:  # the one axis: faint gridlines behind the bars, tick labels under them
        x = x0 + plot_w * t / maximum
        page.ops.insert(0, ("line", x, top, x, bottom, GRID, "-"))
        label = fmt(t)
        page.ops.append(("text", x - width_in(label, TICK) / 2 if t else x, bottom + 0.08, label, TICK,
                         SECONDARY, False, "left"))
    if refline:
        value, label = refline
        x = x0 + plot_w * value / maximum
        page.ops.append(("line", x, top - 0.1, x, bottom, SECONDARY, "--"))
        page.ops.append(("text", x + 0.08, top - 0.12, label, TICK, SECONDARY, False, "left", True))
    page.y = bottom + 0.08 + line_h(TICK)


def tokens(x):
    if x >= 1_000_000:
        return f"{x / 1_000_000:g}M"
    return f"{x / 1000:g}k" if x else "0"


def chart(name, title, subtitle, rows, maximum, ticks, fmt=tokens, footer=None, groups=None, refline=None,
          label_left=False):
    page = Page()
    page.text(title, 30, PRIMARY, bold=True, gap_after=0.14)
    page.text(subtitle, 20, SECONDARY, gap_after=0.45 if refline else 0.35)
    bars(page, rows, maximum, ticks, fmt, groups, refline, label_left)
    if footer:
        page.gap(0.30)
        page.text(footer, 17, SECONDARY)
    page.save(name)


def results_chart():
    settings = [("3 small repositories · Haiku 4.5", "haiku-4.5-main.json"),
                ("dub, 25k graph nodes · Haiku 4.5", "haiku-4.5-large.json"),
                ("dub, 25k graph nodes · Sonnet 5", "sonnet-5-large.json")]
    setups = [("graph", "Graph through my wrapper", BLUE), ("rawgraph", "Graph server directly", ORANGE),
              ("nograph", "Read and Grep only", GREEN)]
    rows, groups = [], {}
    for heading, file in settings:
        groups[len(rows)] = heading
        for arm, label, color in setups:
            med, correct, _ = stats(file, arm)
            rows.append(dict(label=label, label_color=SECONDARY, value=med, color=color,
                             end=f"{med:,} · {correct} correct"))
    chart("results-priced-tokens.png", "The code graph did not make Claude Code cheaper",
          "Median priced tokens per run over 252 headless Claude Code runs. Lower is cheaper. "
          "Labels give correct answers.",
          rows, 50_000, [0, 10_000, 20_000, 30_000, 40_000, 50_000], groups=groups, label_left=True,
          footer="Priced tokens = fresh input + 1.25 × cache writes + 0.1 × cache reads, Anthropic's price "
                 "multipliers. Claude Code 2.1.283, codebase-memory-mcp 0.9.0.")


def tool_definitions_chart():
    rows = []
    for file, arm, label, color, of in [
            ("haiku-4.5-toolsearch-default.json", "graph", "Tool definitions deferred (the default), routing rule",
             GRAY, 12),
            ("haiku-4.5-unguided.json", "graph-unguided", "All definitions loaded, no routing rule", ORANGE, 12),
            ("haiku-4.5-main.json", "graph", "All definitions loaded, with the routing rule", BLUE, 36)]:
        med, correct, called = stats(file, arm)
        rows.append(dict(label=label, value=med, color=color, end=f"{med:,}",
                         detail=f"graph called in {called} of {of} runs · {correct} correct"))
    chart("tool-definitions-deferred-vs-loaded.png", "The most expensive setup was a graph the agent mostly ignored",
          "Haiku 4.5 on the twelve small-repository questions. Median priced tokens per run.",
          rows, 70_000, [0, 20_000, 40_000, 60_000],
          footer="Deferred: Claude Code lists an MCP server's tools by name and loads a definition only when the "
                 "model asks for it. ENABLE_TOOL_SEARCH=false loads every definition up front.")


def cover():
    w, h = 5.0, 2.1  # 1000 x 420 px
    page = Page(width=w, margin=0.22)
    page.y = 0.34
    left = 2.8
    for s, size, color, bold, after in [("Capped my agent's tool output to save tokens.", 13, PRIMARY, True, 0.08),
                                        ("It used 2.65× as many.", 17, PRIMARY, True, 0.12),
                                        ("Claude Code, measured", 11, SECONDARY, False, 0)]:
        for line in wrap(s, size, left - page.m, bold):
            page.ops.append(("text", page.m, page.y, line, size, color, bold, "left"))
            page.y += line_h(size)
        page.y += after
    x0, x1 = 2.95, w - 0.22
    scale = (x1 - x0) / CAP[2]
    for y, total, n, color, label in [(0.55, CAP[0], CAP[1], GRAY, "7 turns · 267k"),
                                      (1.25, CAP[2], CAP[3], ORANGE, "18 turns · 708k")]:
        page.ops.append(("text", x0, y, label, 11, PRIMARY, False, "left"))
        bw = total * scale / n
        for b in range(n):
            page.ops.append(("rect", x0 + b * bw, y + 0.27, bw - 0.018, 0.2, color))
    page.save("devto-cover.png", height=h)


def main():
    chart("output-cap-turns.png", "A 12,000-character cap on tool output: 18 turns instead of 7",
          "Billed input tokens for one answer. Each block is one turn, and every turn re-sends the whole "
          "conversation.",
          [dict(label="No cap", value=CAP[0], blocks=CAP[1], color=GRAY, end="267k · 7 turns"),
           dict(label="12,000-character cap", value=CAP[2], blocks=CAP[3], color=ORANGE,
                end="708k · 18 turns · 2.65×")],
          800_000, [0, 200_000, 400_000, 600_000, 800_000],
          footer="Earlier round on private repositories. Every input token counted the same, cache reads "
                 "included. A block is the average turn: about 38k tokens without the cap, 39k with it.")
    results_chart()
    tool_definitions_chart()
    chart("bash-subagents.png", "Grep-only with Bash and subagents allowed: 1.8M tokens. Without them: 252k.",
          "Billed input tokens for the grep-only setup on the same questions. With Bash allowed the model ran "
          "grep | head loop after loop, much of it inside subagents.",
          [dict(label="Bash and subagents allowed", value=BASH[0], color=ORANGE, end="1.8M"),
           dict(label="Bash and Agent denied", value=BASH[1], color=GREEN, end="252k")],
          2_000_000, [0, 500_000, 1_000_000, 1_500_000, 2_000_000],
          footer="Earlier round on private repositories. A subagent's turns are billed but left out of the main "
                 "run's turn count.")
    chart("search-hit-size.png", "One search hit: 1,342 bytes from the graph server, 251 through my wrapper",
          "Size of one hit as the model receives it. The raw hit is mostly hash vectors, complexity metrics and "
          "a list of every identifier in the function body.",
          [dict(label="Graph server, raw JSON", value=HITS[0], color=ORANGE, end="1,342 bytes"),
           dict(label="Through my wrapper", value=HITS[1], color=BLUE, end="251 bytes"),
           dict(label="The same hit as a grep line", value=HITS[2], color=GREEN, end="115 bytes")],
          1500, [0, 500, 1000, 1500], fmt=lambda x: f"{x:,}")
    chart("rebuild-turns.png", "Rebuilt around turns: 83 turns down to 36",
          "Billed input tokens for one round of questions.",
          [dict(label="First wrapper, 12,000-character cap", value=REBUILD[0], color=ORANGE, end="3.46M · 83 turns"),
           dict(label="Rebuilt: one-call answers, a layout file, 60,000-character cap", value=REBUILD[2],
                color=BLUE, end="1.62M · 36 turns")],
          4_000_000, [0, 1_000_000, 2_000_000, 3_000_000, 4_000_000],
          footer="Earlier round on private repositories. Listing a project's HTTP routes alone went from 23 turns "
                 "to 8.")
    chart("large-repos-copilot.png", "On kubernetes and vscode the graph paid off for Haiku",
          "GitHub Copilot CLI, structural questions on repositories of 146k and 219k graph nodes. Priced tokens "
          "with the graph as a share of grep's, median of per-question ratios.",
          [dict(label=m, value=v, color=BLUE, end=f"{v:.2f}", detail=note)
           for m, (v, note) in zip(("Haiku 4.5", "Sonnet 5", "Opus 5.5"), COPILOT)],
          1.2, [0, 0.25, 0.5, 0.75, 1.0], fmt=lambda x: f"{x:g}", refline=(1.0, "same as grep"),
          footer="A separate benchmark, not comparable with the Claude Code runs.")
    cover()


if __name__ == "__main__":
    main()
