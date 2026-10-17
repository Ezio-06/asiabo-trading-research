"""Builds the README diagrams and banner (light + dark SVG). Plain string templates, no dependencies.
Run: python tools/make_readme_diagrams.py
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"

T = {
    "light": dict(bg="#ffffff", card="#f6f8fa", line="#d1d9e0", ink="#1f2328", ink2="#59636e",
                  accent="#2a78d6", accent_bg="#eaf2fc", red="#d1242f", red_bg="#fdeeee",
                  green="#1a7f37", green_bg="#e9f6ec", arrow="#818b98"),
    "dark": dict(bg="#0d1117", card="#151b23", line="#3d444d", ink="#f0f6fc", ink2="#9198a1",
                 accent="#4493f8", accent_bg="#13233a", red="#f85149", red_bg="#2a1517",
                 green="#3fb950", green_bg="#12261a", arrow="#656c76"),
}


def svg(w, h, body, t):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'font-family="{FONT}">\n<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
            f'fill="{t["arrow"]}"/></marker></defs>\n<rect width="{w}" height="{h}" rx="12" fill="{t["bg"]}"/>\n'
            f'{body}\n</svg>\n')


def text_lines(x, y, lines, size, color, weight=400, anchor="start", lh=1.35, family=None):
    fam = f' font-family="{family}"' if family else ""
    out = []
    for i, ln in enumerate(lines):
        ln = ln.replace("&", "&amp;").replace("<", "&lt;")
        out.append(f'<text x="{x}" y="{y + i * size * lh:.1f}" font-size="{size}" fill="{color}" '
                   f'font-weight="{weight}" text-anchor="{anchor}"{fam}>{ln}</text>')
    return "\n".join(out)


def box(x, y, w, h, t, fill=None, stroke=None, rx=10):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill or t["card"]}" '
            f'stroke="{stroke or t["line"]}" stroke-width="1.2"/>')


def arrow(x1, y1, x2, y2, t, dash=False):
    d = ' stroke-dasharray="4 4"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{t["arrow"]}" stroke-width="1.6"'
            f'{d} marker-end="url(#ah)"/>')


# ---------------------------------------------------------------- pipeline
STEPS = [
    ("1", "Idea", ["A theory that names", "who pays: who loses", "money to you, and why?"]),
    ("2", "Prediction", ["Expected result written", "down BEFORE the run,", "scored afterwards."]),
    ("3", "Noise bar", ["Same test on fake", "random markets. Pass", "bar sits above noise."]),
    ("4", "Real data", ["Training years only.", "Every trade vs its", "coin-flip twin."]),
    ("5", "Shuffle tests", ["Shuffled copies of real", "history: which part", "needs the real order?"]),
    ("6", "Sealed exam", ["Fresh data, spent", "once. The script locks", "itself afterwards."]),
]


def pipeline(t):
    W, H = 960, 330
    bw, gap, x0, y0, bh = 140, 18, 21, 64, 104
    b = [text_lines(24, 34, ["How every idea was tested"], 17, t["ink"], 700)]
    for i, (n, title, cap) in enumerate(STEPS):
        x = x0 + i * (bw + gap)
        is_test = i >= 2
        b.append(box(x, y0, bw, bh, t, t["accent_bg"] if is_test else t["card"],
                     t["accent"] if is_test else t["line"]))
        b.append(f'<circle cx="{x + 18}" cy="{y0 + 20}" r="10" fill="{t["accent"] if is_test else t["arrow"]}"/>')
        b.append(text_lines(x + 18, y0 + 24, [n], 11, "#ffffff", 700, "middle"))
        b.append(text_lines(x + 34, y0 + 25, [title], 13.5, t["ink"], 700))
        b.append(text_lines(x + 12, y0 + 52, cap, 11, t["ink2"]))
        if i < len(STEPS) - 1:
            b.append(arrow(x + bw + 2, y0 + bh / 2, x + bw + gap - 2, y0 + bh / 2, t))
        if is_test and i < 5:
            b.append(arrow(x + bw / 2, y0 + bh + 2, x + bw / 2, 226, t, dash=True))
    # graveyard spans steps 3-5, survivor under step 6
    gx = x0 + 2 * (bw + gap)
    gw = 3 * bw + 2 * gap
    b.append(box(gx, 230, gw, 72, t, t["red_bg"], t["red"]))
    b.append(text_lines(gx + 16, 256, ["✕  Fail any test → killed, with a cause of death on record"], 13, t["red"], 700))
    b.append(text_lines(gx + 16, 280, ["Most ideas end here, several of mine included. Full list in RETIREMENT.md."],
                        11, t["ink2"]))
    sx = x0 + 5 * (bw + gap)
    b.append(arrow(sx + bw / 2, y0 + bh + 2, sx + bw / 2, 226, t))
    b.append(box(sx, 230, bw, 72, t, t["green_bg"], t["green"]))
    b.append(text_lines(sx + 12, 256, ["✓  Survivor"], 13, t["green"], 700))
    b.append(text_lines(sx + 12, 280, ["2 real but small,", "0 deployable"], 11, t["ink2"]))
    b.append(text_lines(x0, 252, ["Steps 1–2 keep", "you honest.", "Steps 3–6 try to", "kill the idea."], 11, t["ink2"], lh=1.4))
    return svg(W, H, "\n".join(b), t)


# ------------------------------------------------------------ architecture
def architecture(t):
    W, H = 960, 470
    b = [text_lines(24, 34, ["How the lab is built"], 17, t["ink"], 700),
         text_lines(24, 56, ["Python standard library + SQLite only. ~20k lines across 20 scripts."], 12, t["ink2"])]

    def node(x, y, w, h, title, lines, accent=False, mono_title=True):
        out = [box(x, y, w, h, t, t["accent_bg"] if accent else t["card"], t["accent"] if accent else t["line"])]
        out.append(text_lines(x + 14, y + 24, [title], 13, t["ink"], 700, family=MONO if mono_title else None))
        out.append(text_lines(x + 14, y + 46, lines, 11, t["ink2"]))
        return "\n".join(out)

    # column 1: data
    b.append(text_lines(24, 92, ["DATA"], 11, t["ink2"], 700))
    b.append(node(24, 102, 270, 70, "BarExtract (C# cBot)", ["Custom cTrader bot that exports", "13 years of 1-minute bars"], mono_title=False))
    b.append(arrow(159, 174, 159, 196, t))
    b.append(node(24, 198, 270, 86, "build_bars_db.py", ["Builds the database, logs every gap", "and checks it against US/UK/DE/JP", "holiday calendars"]))
    b.append(arrow(159, 286, 159, 308, t))
    b.append(node(24, 310, 270, 118, "bars.db  (SQLite, 2.5 GB)", ["8 markets: gold, US 500, Germany 40,", "EURUSD, USDJPY, WTI oil,", "Japan 225, US Tech 100",
                                                                      "🔒 exam years locked out in code"], accent=True))
    # column 2: engine
    b.append(text_lines(345, 92, ["ENGINE"], 11, t["ink2"], 700))
    b.append(node(345, 102, 270, 136, "asiabo_offline.py / _lab.py", ["Replays history minute by minute:", "real broker costs, spreads, swaps,",
                                                                      "money management, and a", "coin-flip twin for every trade.", "Imported by every study."], accent=True))
    b.append(node(345, 266, 270, 118, "make_synth.py", ["Fake-market generator: shuffles,", "cousin histories, momentum and", "regime dials. A realism gate (8 stats)", "fails any world that looks unreal."]))
    b.append(arrow(296, 369, 343, 300, t))
    b.append(arrow(296, 360, 343, 200, t))
    b.append(arrow(480, 264, 480, 240, t))
    # column 3: studies + output
    b.append(text_lines(666, 92, ["STUDIES & OUTPUT"], 11, t["ink2"], 700))
    b.append(node(666, 102, 270, 118, "15 study scripts", ["why · engine · hunt · regime · switch", "ladder · probe · young · explore", "exam · dipdrift: one-shot, refuse", "to run twice (DONE markers)"], mono_title=False))
    b.append(arrow(617, 170, 664, 162, t))
    b.append(arrow(801, 222, 801, 264, t))
    b.append(node(666, 266, 270, 118, "reports/ + docs/", ["One dated folder per run (92 kept).", "37 research notes: plans written", "before runs, results after, and a", "ledger of 34 market theories."], mono_title=False))
    # launcher bar
    b.append(box(345, 410, 591, 40, t))
    b.append(text_lines(361, 435, ["run.bat → asiabo.py menu · modules.json registry · runs.csv logs every run, its time and RAM"], 11.5, t["ink2"], family=None))
    b.append(text_lines(361, 435, [""], 11, t["ink2"]))
    return svg(W, H, "\n".join(b), t)


# ------------------------------------------------------------------ banner
def banner(t):
    W, H = 960, 250
    # faint price-like path as texture (deterministic random walk)
    import random
    r = random.Random(7)
    y, pts = 150.0, []
    for i in range(97):
        y += r.gauss(0, 7)
        y = min(max(y, 60), 220)
        pts.append(f"{i * 10},{y:.1f}")
    b = [f'<polyline points="{" ".join(pts)}" fill="none" stroke="{t["accent"]}" stroke-width="2" opacity="0.18"/>']
    b.append(text_lines(40, 82, ["asiabo"], 46, t["ink"], 800, family=MONO))
    b.append(text_lines(42, 116, ["A trading-strategy research lab built to prove its own ideas wrong."], 18, t["ink2"], 500))
    stats = [("13 yrs", "of 1-minute bars"), ("8", "markets"), ("~30", "ideas tested"), ("0", "deployable edges")]
    x = 42
    for big, small in stats:
        b.append(text_lines(x, 182, [big], 28, t["accent"], 800))
        b.append(text_lines(x, 206, [small], 12.5, t["ink2"]))
        x += 210
    return svg(W, H, "\n".join(b), t)


if __name__ == "__main__":
    for theme, t in T.items():
        for name, f in (("pipeline", pipeline), ("architecture", architecture), ("banner", banner)):
            (OUT / f"{name}-{theme}.svg").write_text(f(t), encoding="utf-8")
    print("wrote", len(list(OUT.glob("*.svg"))), "files to", OUT)
