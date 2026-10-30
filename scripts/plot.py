"""Charts for the write-up. matplotlib is a dev-only dependency: nothing in ate/ imports it.

  python scripts/plot.py results/<sweep>.jsonl [more.jsonl ...] [--out docs/figures]

Writes three PNGs: pass_vs_usage.png, per_task_grid.png, tokens_by_stage.png.
Usage (tokens) is the primary axis; API-equivalent dollars are not drawn. Retryable runs
(rate_limited / auth_error / harness_error) are left out, exactly as `ate report` does.
Colours follow the dataviz palette checks (validated with its validate_palette.py): one fixed
colour per config, text always in ink colours, never in a series colour.
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e7eaee"
CONFIG_COLORS = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a"}   # categorical slots 1-3, fixed per config
EXTRA_COLORS = ["#eda100", "#e87ba4", "#6250d6", "#e34948"]         # any further config, in slot order
CONFIG_NAMES = {"A": "A single agent", "B": "B builder + reviewer", "C": "C planner + builder + reviewer"}
STAGE_ORDER = ["plan", "build", "review", "fix"]
STAGE_COLORS = {"plan": "#e87ba4", "build": "#6250d6", "review": "#008300", "fix": "#eda100"}
HEAT = ("#cde2fb", "#184f95")   # one-hue ramp, light to dark, for pass fraction


def load_pyplot():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return matplotlib, plt
    except ImportError:
        print("matplotlib is needed for charts: pip install matplotlib  (dev-only; ate/ itself never imports it)")
        raise SystemExit(1)


def color_for(cid, seen):
    if cid in CONFIG_COLORS:
        return CONFIG_COLORS[cid]
    others = [c for c in seen if c not in CONFIG_COLORS]
    return EXTRA_COLORS[others.index(cid) % len(EXTRA_COLORS)]


def label_for(cid):
    return CONFIG_NAMES.get(cid, f"config {cid}")


def total_tokens(r):
    t = r["tokens"]
    return t["input"] + t["output"] + t["cache_read"] + t["cache_creation"]


def stage_group(name):
    base = name.split("_")[0]
    return "build" if base == "solve" else base


def prepare(records):
    from ate import report
    done = report.counted(records)
    configs = sorted({r["config_id"] for r in done})
    return done, configs, report.wilson


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c9d1")
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def finish(fig, plt, path, dry, note):
    if dry:
        fig.text(0.5, 0.5, "DRY RUN, fake agents", ha="center", va="center", fontsize=34, color="#8892a0",
                 alpha=0.28, rotation=20, weight="bold")
    fig.text(0.01, 0.01, note, fontsize=7.5, color=MUTED, ha="left", va="bottom")
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)


def pass_vs_usage(records, out, plt):
    done, configs, wilson = prepare(records)
    dry = bool(records) and all(r["dry_run"] for r in records)
    fig, ax = plt.subplots(figsize=(7.2, 4.4), facecolor=SURFACE)
    style_axes(ax)
    xmax = 0
    for cid in configs:
        rs = [r for r in done if r["config_id"] == cid]
        k = sum(r["passed"] for r in rs)
        n = len(rs)
        x = sum(total_tokens(r) for r in rs) / n / 1000
        y = k / n
        lo, hi = wilson(k, n)
        c = color_for(cid, configs)
        ax.errorbar([x], [y * 100], yerr=[[(y - lo) * 100], [(hi - y) * 100]], fmt="o", color=c, markersize=10,
                    markeredgecolor=SURFACE, markeredgewidth=2, elinewidth=2, capsize=4, zorder=3,
                    label=label_for(cid))
        first = cid == configs[0]
        ax.annotate(f"{cid}  {k}/{n}", (x, y * 100), textcoords="offset points",
                    xytext=(-12 if first else 12, 0), ha="right" if first else "left", fontsize=10, color=INK,
                    va="center", weight="bold")
        xmax = max(xmax, x)
    ax.set_xlim(0, xmax * 1.3 if xmax else 1)
    ax.set_ylim(0, 104)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend([h[0] for h in handles], labels, frameon=False, fontsize=9, labelcolor=INK, loc="lower right")
    fig.subplots_adjust(bottom=0.2, left=0.1, right=0.97)
    ax.set_xlabel("tokens per run, thousands (input + output + cache), mean over runs", color=MUTED, fontsize=9)
    ax.set_ylabel("pass rate on hidden tests, %", color=MUTED, fontsize=9)
    ax.set_title("Pass rate vs usage per run", loc="left", color=INK, fontsize=12, weight="bold")
    n_runs = sorted({sum(1 for r in done if r["config_id"] == c) for c in configs})
    finish(fig, plt, out, dry,
           f"Bars: Wilson 95% interval. {'/'.join(map(str, n_runs))} runs per config, "
           f"{len({r['task_id'] for r in done})} tasks. Usage = plan tokens; no dollars shown.")


def per_task_grid(records, out, plt, matplotlib):
    done, configs, _ = prepare(records)
    dry = bool(records) and all(r["dry_run"] for r in records)
    tasks = sorted({r["task_id"] for r in done})
    cell = defaultdict(lambda: [0, 0])
    for r in done:
        c = cell[(r["task_id"], r["config_id"])]
        c[0] += r["passed"]
        c[1] += 1
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("passfrac", HEAT)
    fig, ax = plt.subplots(figsize=(max(5.2, 1.7 * len(configs) + 3.2), 0.55 * len(tasks) + 1.9), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for i, t in enumerate(tasks):
        for j, c in enumerate(configs):
            k, n = cell[(t, c)]
            frac = k / n if n else None
            face = cmap(frac) if frac is not None else SURFACE
            ax.add_patch(plt.Rectangle((j, len(tasks) - 1 - i), 1, 1, facecolor=face, edgecolor=SURFACE, linewidth=3))
            if n:
                dark = frac is not None and frac > 0.55
                ax.text(j + 0.5, len(tasks) - 1 - i + 0.5, f"{k}/{n}", ha="center", va="center", fontsize=10,
                        color="#ffffff" if dark else INK, weight="bold" if frac < 1 else "normal")
    ax.set_xlim(0, len(configs))
    ax.set_ylim(0, len(tasks))
    ax.set_xticks([j + 0.5 for j in range(len(configs))], [label_for(c).replace(" + ", "\n+ ", 1) for c in configs],
                  color=INK, fontsize=8.5)
    ax.set_yticks([len(tasks) - 1 - i + 0.5 for i in range(len(tasks))], tasks, color=INK, fontsize=9)
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    fig.subplots_adjust(left=0.27, right=0.97, top=0.78, bottom=0.12)
    fig.suptitle("Passes / runs per task and config", x=0.02, ha="left", y=0.985, color=INK, fontsize=12,
                 weight="bold")
    finish(fig, plt, out, dry, "Darker = higher pass fraction. A cell shows passed runs / counted runs.")


def tokens_by_stage(records, out, plt):
    done, configs, _ = prepare(records)
    dry = bool(records) and all(r["dry_run"] for r in records)
    per = defaultdict(lambda: defaultdict(float))
    runs = defaultdict(int)
    for r in done:
        runs[r["config_id"]] += 1
        for s in r["stages"]:
            t = s["tokens"]
            per[r["config_id"]][stage_group(s["name"])] += t["input"] + t["output"] + t["cache_read"] + t["cache_creation"]
    fig, ax = plt.subplots(figsize=(7.2, 4.4), facecolor=SURFACE)
    style_axes(ax)
    stages = [s for s in STAGE_ORDER if any(per[c][s] for c in configs)] + sorted(
        {s for c in configs for s in per[c]} - set(STAGE_ORDER))
    bottoms = [0.0] * len(configs)
    for s in stages:
        vals = [per[c][s] / runs[c] / 1000 if runs[c] else 0 for c in configs]
        ax.bar(range(len(configs)), vals, bottom=bottoms, width=0.55, label=s,
               color=STAGE_COLORS.get(s, "#8892a0"), edgecolor=SURFACE, linewidth=2)
        for j, v in enumerate(vals):
            if v > max(bottoms[j] + v, 1) * 0.07 and v >= 8:
                ax.text(j, bottoms[j] + v / 2, f"{v:,.0f}k", ha="center", va="center", fontsize=8.5,
                        color="#ffffff" if s in ("build", "review") else INK)
        bottoms = [b + v for b, v in zip(bottoms, vals)]
    for j, total in enumerate(bottoms):
        ax.text(j, total + max(bottoms) * 0.015, f"{total:,.0f}k", ha="center", va="bottom", fontsize=9.5,
                color=INK, weight="bold")
    ax.set_xticks(range(len(configs)), [label_for(c).replace(" + ", "\n+ ", 1) for c in configs], color=INK, fontsize=9)
    ax.set_ylim(0, max(bottoms) * 1.12 if bottoms else 1)
    ax.set_ylabel("tokens per run, thousands (input + output + cache)", color=MUTED, fontsize=9)
    ax.set_title("Where the tokens go, by stage", loc="left", color=INK, fontsize=12, weight="bold")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], title="stage", frameon=False, fontsize=9, title_fontsize=9,
              labelcolor=INK, loc="upper left")
    fig.subplots_adjust(bottom=0.2, left=0.1, right=0.97)
    finish(fig, plt, out, dry, "Mean over counted runs. Single agent = one build stage. Fix = the one allowed fix round.")


def make_figures(records, out_dir):
    """Write the three charts into out_dir; returns their paths."""
    matplotlib, plt = load_pyplot()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / "pass_vs_usage.png", out_dir / "per_task_grid.png", out_dir / "tokens_by_stage.png"]
    pass_vs_usage(records, paths[0], plt)
    per_task_grid(records, paths[1], plt, matplotlib)
    tokens_by_stage(records, paths[2], plt)
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="results/*.jsonl")
    ap.add_argument("--out", default=str(ROOT / "docs" / "figures"))
    args = ap.parse_args(argv)
    from ate import report
    records = report.load(args.files)
    if not report.counted(records):
        print("no countable records to plot")
        return 1
    for p in make_figures(records, args.out):
        print(f"wrote {p} ({p.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
