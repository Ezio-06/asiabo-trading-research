"""Builds the README charts (light + dark SVG) from numbers published in docs/.

Every value below is copied from a research note; the source is named next to it.
Run: python tools/make_readme_charts.py  (needs matplotlib; the lab itself does not)
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

OUT = Path(__file__).resolve().parent.parent / "assets" / "charts"
OUT.mkdir(parents=True, exist_ok=True)

FONT = "Inter" if any("Inter" in f.name for f in font_manager.fontManager.ttflist) else "DejaVu Sans"
plt.rcParams.update({"font.family": FONT, "svg.fonttype": "path", "axes.unicode_minus": False})

# Surfaces match GitHub's light / dark page backgrounds; palette validated against them.
THEMES = {
    "light": dict(bg="#ffffff", ink="#1f2328", ink2="#59636e", muted="#818b98",
                  grid="#e6e8eb", base="#c3c8cf",
                  s1="#2a78d6", s2="#eb6834", s3="#1baf7a", pos="#2a78d6", neg="#e34948"),
    "dark": dict(bg="#0d1117", ink="#f0f6fc", ink2="#c3c9d1", muted="#8b949e",
                 grid="#21262d", base="#3d444d",
                 s1="#3987e5", s2="#d95926", s3="#199e70", pos="#3987e5", neg="#e66767"),
}


def frame(t, title, subtitle, source, w=9.0, h=4.4):
    fig, ax = plt.subplots(figsize=(w, h), dpi=100)
    fig.patch.set_facecolor(t["bg"])
    ax.set_facecolor(t["bg"])
    fig.subplots_adjust(left=0.09, right=0.97, top=0.78, bottom=0.17)
    fig.text(0.02, 1 - 0.26 / h, title, fontsize=15, fontweight="bold", color=t["ink"], ha="left", va="top")
    fig.text(0.02, 1 - 0.6 / h, subtitle, fontsize=10.5, color=t["ink2"], ha="left", va="top")
    fig.text(0.02, 0.03, source, fontsize=8.5, color=t["muted"], ha="left", va="bottom")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(t["base"])
    ax.tick_params(colors=t["ink2"], labelsize=9.5, length=0)
    ax.grid(axis="y", color=t["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    return fig, ax


def zero_line(ax, t):
    ax.axhline(0, color=t["base"], linewidth=1.2, zorder=1)


def save(fig, name, theme):
    fig.savefig(OUT / f"{name}-{theme}.svg", facecolor=fig.get_facecolor())
    plt.close(fig)


def fmt(v, d=2):
    return f"{v:+.{d}f}"


# 1. Momentum dial ---------------------------------------------------------
# docs/engine_results.md, D1: edge per trade across five fake-market dial steps.
DIAL_X = ["Strong\nsnap-back", "Snap-back", "Neutral", "Momentum", "Strong\nmomentum"]
DIAL = {"Multi-day breakout": [-0.27, -0.14, 0.05, 0.17, 0.52],
        "Intraday breakout": [0.01, 0.05, 0.07, 0.12, 0.19],
        "Index dip-buy": [0.10, 0.27, 0.34, 0.42, 0.39]}


def momentum_dial(t, theme):
    fig, ax = frame(t, "Turn one dial on a fake market, watch the edge move",
                    "Edge per trade (in R) as fake markets shift from snap-back to momentum. Same code, only the dial changes.",
                    "Source: docs/engine_results.md · 23 synthetic worlds, 2 seeds · breakout slope t = +6.6")
    zero_line(ax, t)
    xs = range(len(DIAL_X))
    for (name, ys), c in zip(DIAL.items(), (t["s1"], t["s2"], t["s3"])):
        ax.plot(xs, ys, color=c, linewidth=2.2, solid_capstyle="round", zorder=3)
        ax.scatter(xs, ys, s=46, color=c, edgecolors=t["bg"], linewidths=2, zorder=4)
        ax.annotate(f"{name}  {fmt(ys[-1])}", (4, ys[-1]), xytext=(10, 0), textcoords="offset points",
                    va="center", fontsize=10, color=t["ink"], fontweight="medium")
    ax.annotate("loses money", (0, -0.27), xytext=(10, -2), textcoords="offset points",
                va="center", fontsize=9, color=t["ink2"])
    ax.set_xticks(list(xs), DIAL_X)
    ax.set_xlim(-0.25, 5.6)
    ax.set_ylim(-0.38, 0.62)
    ax.set_ylabel("Edge per trade (R)", color=t["ink2"], fontsize=9.5)
    save(fig, "momentum_dial", theme)


# 2. Shuffle test ----------------------------------------------------------
# docs/power_run_findings.md, synthetic batch 2: 2024+ money, $10k account, %/yr.
def shuffle_test(t, theme):
    fig, ax = frame(t, "The profit needs multi-month trends",
                    "Same strategies, 2024+ data. Cut history into blocks and shuffle them: short blocks break the trends, long blocks keep them.",
                    "Source: docs/power_run_findings.md · $10k account, %/yr · shuffled runs: 3 seeds each")
    labels = ["Real history", "Shuffled in\n8–26 week blocks", "Shuffled in\n2–6 week blocks"]
    vals = [18.6, 16.2, -0.7]
    cols = [t["pos"], t["pos"], t["neg"]]
    zero_line(ax, t)
    bars = ax.bar(labels, vals, width=0.5, color=cols, zorder=3)
    for b, v in zip(bars, vals):
        y = v + (0.8 if v >= 0 else -0.8)
        ax.text(b.get_x() + b.get_width() / 2, y, f"{v:+.1f}%/yr", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=11, fontweight="bold", color=t["ink"])
    ax.text(1, 9, "trends kept", ha="center", fontsize=9, color="#ffffff")
    ax.set_ylim(-5, 23)
    ax.set_ylabel("Return, % per year", color=t["ink2"], fontsize=9.5)
    save(fig, "shuffle_test", theme)


# 3. Training vs fresh data -------------------------------------------------
# docs/exam_us500_results.md and docs/dip_drift_results.md: dip net R per trade.
def train_vs_fresh(t, theme):
    fig, ax = frame(t, "Training numbers vs data the strategy has never seen",
                    "Index dip-buying, profit per trade after costs. Training data on the left, sealed fresh data on the right.",
                    "Source: docs/exam_us500_results.md, docs/dip_drift_results.md · n = trades")
    labels = ["US 500\n2020–21", "US 500\n2024+", "US 500\n2016–19", "US Tech 100\n2017–26"]
    vals = [0.757, 0.552, -0.106, 0.100]
    ns = [20, 28, 31, 110]
    cols = [t["muted"], t["muted"], t["pos"], t["pos"]]
    zero_line(ax, t)
    bars = ax.bar(labels, vals, width=0.55, color=cols, zorder=3)
    for b, v, n in zip(bars, vals, ns):
        up = v >= 0
        ax.text(b.get_x() + b.get_width() / 2, v + (0.03 if up else -0.03), f"{v:+.2f} R",
                ha="center", va="bottom" if up else "top", fontsize=11, fontweight="bold", color=t["ink"])
        ax.text(b.get_x() + b.get_width() / 2, (-0.03 if up else v - 0.12), f"n = {n}",
                ha="center", va="top", fontsize=8.5, color=t["ink2"])
    ax.axvline(1.5, color=t["base"], linewidth=1, linestyle=(0, (3, 3)))
    ax.text(0.5, 0.88, "TRAINING", ha="center", fontsize=9, fontweight="bold", color=t["ink2"])
    ax.text(2.5, 0.88, "FRESH (spent once)", ha="center", fontsize=9, fontweight="bold", color=t["ink2"])
    ax.set_ylim(-0.32, 0.95)
    ax.set_ylabel("Net profit per trade (R)", color=t["ink2"], fontsize=9.5)
    save(fig, "train_vs_fresh", theme)


# 4. Dip by year on fresh data ---------------------------------------------
# docs/dip_drift_results.md: variant A sized R by year, US Tech 100 (fresh).
def dip_by_year(t, theme):
    fig, ax = frame(t, "Real but small, and you can see where it bleeds",
                    "Index dip-buying on fresh US Tech 100 data, total result per year (R). Net +11 R over 110 trades.",
                    "Source: docs/dip_drift_results.md · variant A (dip as it is) · 2018 was also the worst year on the US 500 exam")
    years = list(range(2017, 2027))
    vals = [2.6, -9.0, -1.2, -3.8, 9.0, -2.8, -0.8, 11.9, -2.1, 7.2]
    zero_line(ax, t)
    cols = [t["pos"] if v >= 0 else t["neg"] for v in vals]
    bars = ax.bar([str(y) for y in years], vals, width=0.62, color=cols, zorder=3)
    for b, v in zip(bars, vals):
        up = v >= 0
        ax.text(b.get_x() + b.get_width() / 2, v + (0.4 if up else -0.4), f"{v:+.1f}",
                ha="center", va="bottom" if up else "top", fontsize=9.5, color=t["ink"])
    ax.text(1, -11.6, "Feb 2018\nvolatility spike", ha="center", va="top", fontsize=8.5, color=t["ink2"])
    ax.text(5, -5.2, "bear year", ha="center", va="top", fontsize=8.5, color=t["ink2"])
    ax.set_ylim(-15, 15)
    ax.set_ylabel("Result per year (R)", color=t["ink2"], fontsize=9.5)
    save(fig, "dip_by_year", theme)


# 5. Why the intraday breakout failed its exam -----------------------------
# docs/exam_us500_results.md, decomposition: net = -cost + path + EDGE.
# Training 2024+ orb30 path = net + cost - EDGE = 0.226 + 0.101 - 0.145 = 0.182.
def fast_autopsy(t, theme):
    fig, ax = frame(t, "Autopsy: why the intraday breakout failed its exam",
                    "US 500, profit per trade split into its parts. Training (2024+) vs the one-shot fresh exam (2016–19).",
                    "Source: docs/exam_us500_results.md · net = − costs + follow-through + direction call")
    cats = ["Costs", "Follow-through\n(either direction)", "Direction call\n(vs coin flip)", "Net result"]
    train = [-0.101, 0.182, 0.145, 0.226]
    exam = [-0.179, -0.105, -0.003, -0.287]
    x = range(len(cats))
    w = 0.34
    zero_line(ax, t)
    b1 = ax.bar([i - w / 2 - 0.01 for i in x], train, width=w, color=t["muted"], zorder=3, label="Training 2024+ (same setup)")
    b2 = ax.bar([i + w / 2 + 0.01 for i in x], exam, width=w, color=t["s2"], zorder=3, label="Fresh exam 2016–19")
    for bars, vals in ((b1, train), (b2, exam)):
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + (0.012 if v >= 0 else -0.012), f"{v:+.3f}",
                    ha="center", va="bottom" if v >= 0 else "top", fontsize=9.5, color=t["ink"])
    ax.set_xticks(list(x), cats)
    ax.set_ylim(-0.38, 0.32)
    ax.set_ylabel("R per trade", color=t["ink2"], fontsize=9.5)
    leg = ax.legend(loc="upper right", frameon=False, fontsize=9.5, ncol=2, bbox_to_anchor=(1.0, 1.1))
    for txt in leg.get_texts():
        txt.set_color(t["ink"])
    save(fig, "fast_autopsy", theme)


# 6. Coin-flip twin -------------------------------------------------------
# docs/dip_drift_results.md: variant A net +0.100, EDGE +0.226 -> twin = -0.126.
def coin_flip(t, theme):
    fig, ax = frame(t, "The coin-flip twin: what is the direction call worth?",
                    "Every trade gets a twin with the same entry time, stop, exit and costs, but a random direction.",
                    "Source: docs/dip_drift_results.md · index dip-buying, fresh US Tech 100, 110 trades · EDGE = real − twin",
                    h=3.6)
    fig.subplots_adjust(left=0.24, right=0.93, top=0.72, bottom=0.2)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=t["grid"], linewidth=0.8)
    labels = ["Coin-flip twin", "Real trade", "EDGE (the difference)"]
    vals = [-0.126, 0.100, 0.226]
    cols = [t["muted"], t["pos"], t["s3"]]
    ax.axvline(0, color=t["base"], linewidth=1.2)
    bars = ax.barh(labels, vals, height=0.52, color=cols, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(v + (0.008 if v >= 0 else -0.008), b.get_y() + b.get_height() / 2, f"{v:+.2f} R",
                ha="left" if v >= 0 else "right", va="center", fontsize=10.5, fontweight="bold", color=t["ink"])
    ax.set_xlim(-0.2, 0.3)
    ax.tick_params(axis="y", labelsize=10.5, colors=t["ink"])
    ax.invert_yaxis()
    save(fig, "coin_flip", theme)


if __name__ == "__main__":
    for theme, t in THEMES.items():
        for f in (momentum_dial, shuffle_test, train_vs_fresh, dip_by_year, fast_autopsy, coin_flip):
            f(t, theme)
    print("wrote", len(list(OUT.glob("*.svg"))), "files to", OUT)
