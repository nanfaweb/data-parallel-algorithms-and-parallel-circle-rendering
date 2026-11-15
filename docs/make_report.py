"""Builds the combined report PDF from the saved benchmark outputs in docs/results.

Usage (from the repository root):  python docs/make_report.py
Needs: matplotlib, reportlab. Figures are written to tmp/figs (git ignored).
"""
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, Preformatted,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "docs", "results")
FIG = os.path.join(ROOT, "tmp", "figs")
OUT = os.path.join(ROOT, "docs", "RollNumber_Report.pdf")
os.makedirs(FIG, exist_ok=True)

# ---------------------------------------------------------------- fonts / styles
FONTS = "C:/Windows/Fonts"
if os.path.exists(os.path.join(FONTS, "arial.ttf")):
    pdfmetrics.registerFont(TTFont("Body", os.path.join(FONTS, "arial.ttf")))
    pdfmetrics.registerFont(TTFont("Body-Bold", os.path.join(FONTS, "arialbd.ttf")))
    pdfmetrics.registerFont(TTFont("Body-Italic", os.path.join(FONTS, "ariali.ttf")))
    pdfmetrics.registerFont(TTFont("Mono", os.path.join(FONTS, "consola.ttf")))
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic",
                       boldItalic="Body-Bold")
    BODY, BOLD, MONO = "Body", "Body-Bold", "Mono"
else:  # fallback without Greek glyphs
    BODY, BOLD, MONO = "Helvetica", "Helvetica-Bold", "Courier"

ss = getSampleStyleSheet()
P = ParagraphStyle("p", parent=ss["Normal"], fontName=BODY, fontSize=9.5, leading=13,
                   spaceAfter=5)
H1 = ParagraphStyle("h1", parent=P, fontName=BOLD, fontSize=15, leading=19, spaceBefore=8,
                    spaceAfter=6, textColor=colors.HexColor("#1f3a5f"))
H2 = ParagraphStyle("h2", parent=P, fontName=BOLD, fontSize=11.5, leading=15, spaceBefore=7,
                    spaceAfter=4, textColor=colors.HexColor("#1f3a5f"))
CAP = ParagraphStyle("cap", parent=P, fontSize=8.5, leading=11, textColor=colors.HexColor("#444444"),
                     alignment=TA_CENTER)
TITLE = ParagraphStyle("t", parent=H1, fontSize=20, leading=25, alignment=TA_CENTER)
CODE = ParagraphStyle("code", parent=P, fontName=MONO, fontSize=7.6, leading=9.6,
                      backColor=colors.HexColor("#f4f4f4"), borderPadding=4, spaceAfter=7)
BUL = ParagraphStyle("bul", parent=P, leftIndent=12, bulletIndent=2)

story = []


def para(t, st=P):
    story.append(Paragraph(t, st))


def bullets(items):
    for t in items:
        story.append(Paragraph(t, BUL, bulletText="•"))


def code(t):
    story.append(Preformatted(t.strip("\n"), CODE))


def table(rows, widths=None, header=True, size=8):
    data = [[Paragraph(str(c), ParagraphStyle("c", parent=P, fontSize=size, leading=size + 2,
                                              spaceAfter=0,
                                              fontName=BOLD if (header and i == 0) else BODY))
             for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde6f0")))
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 6))


def figure(path, caption, w=16):
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(path).getSize()
    story.append(KeepTogether([Image(path, width=w * cm, height=w * cm * ih / iw),
                               Paragraph(caption, CAP), Spacer(1, 6)]))


# ---------------------------------------------------------------- parse results
ROW = re.compile(r"^(\S+)\s+(\S+)\s+(serial|parallel)\s+(\d+)\s+([\d.]+)\s+(\S+)\s+(\S+)\s+([\d.]+)")


def load(name):
    rows = []
    with open(os.path.join(RES, name)) as f:
        for line in f:
            m = ROW.match(line)
            if m:
                inp, op, var, th, ms, sp, ef, vs = m.groups()
                rows.append(dict(input=inp, op=op, variant=var, threads=int(th), ms=float(ms),
                                 speedup=None if sp == "n/a" else float(sp),
                                 eff=None if ef == "n/a" else float(ef), vs=float(vs)))
    return rows


def header_lines(name):
    with open(os.path.join(RES, name)) as f:
        return [l.rstrip() for l in f if l.startswith("#")]


saxpy = load("saxpy_bench.txt")
scan = load("scan_bench.txt")
r_dyn1 = load("render_bench_dynamic1.txt")
r_stat = load("render_bench_static.txt")
r_dyn8 = load("render_bench_dynamic8.txt")
probe = open(os.path.join(RES, "analysis_probe.txt")).read()
correct = open(os.path.join(RES, "correctness.txt")).read()

kernel_bw = {int(m.group(1)): (float(m.group(2)), float(m.group(3)))
             for m in re.finditer(r"p=(\d+): ([\d.]+) ms \(([\d.]+) GB/s", probe)}
alloc_ms = float(re.search(r"alloc\+zero-fill 1e7 floats \(serial\): ([\d.]+)", probe).group(1))
img_ms = float(re.search(r"white fill \(serial\): ([\d.]+)", probe).group(1))
work = {}
for line in probe.splitlines():
    parts = line.split()
    if len(parts) == 8 and parts[0] in ("dense", "sparse", "overlap", "clustered"):
        work[parts[0]] = parts[1:]


def pick(rows, inp, op, var=None):
    return [r for r in rows if r["input"] == inp and r["op"] == op and (var is None or r["variant"] == var)]


def bench_table(rows, inputs, ops):
    out = [["input", "operation", "variant", "threads p", "median (ms)", "S<sub>p</sub> = T<sub>1</sub>/T<sub>p</sub>",
            "E<sub>p</sub> = S<sub>p</sub>/p", "serial / T<sub>p</sub>"]]
    for inp in inputs:
        for op in ops:
            for r in pick(rows, inp, op):
                out.append([inp, op, r["variant"], r["threads"], f"{r['ms']:.4f}",
                            "n/a" if r["speedup"] is None else f"{r['speedup']:.3f}",
                            "n/a" if r["eff"] is None else f"{r['eff']:.3f}", f"{r['vs']:.3f}"])
    return out


# ---------------------------------------------------------------- figures
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.3})
TH = [1, 2, 4, 8]

# Fig 1: SAXPY
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
for n in ["n=10000", "n=1000000", "n=10000000"]:
    rs = [r for r in pick(saxpy, n, "saxpy", "parallel")]
    ax[0].plot([r["threads"] for r in rs], [r["speedup"] for r in rs], "o-", label=n)
ax[0].plot(TH, TH, "k:", label="ideal")
ax[0].set(xlabel="threads p", ylabel="speedup T1/Tp", title="(a) saxpy_parallel speedup", xticks=TH)
ax[0].legend(fontsize=8)
ax[1].plot(TH, [kernel_bw[p][1] for p in TH], "s-", color="tab:red")
ax[1].set(xlabel="threads p", ylabel="achieved bandwidth (GB/s)", xticks=TH,
          title="(b) kernel only, n=1e7, 12 B/element", ylim=(0, 32))
fig.tight_layout()
fig.savefig(os.path.join(FIG, "saxpy.png"), dpi=170)
plt.close(fig)

# Fig 2: scan
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
for i, n in enumerate(["n=100000", "n=10000000"]):
    for op, c in (("scan", "tab:blue"), ("repeats", "tab:orange")):
        rs = pick(scan, n, op, "parallel")
        ser = pick(scan, n, op, "serial")[0]["ms"]
        ax[i].plot([r["threads"] for r in rs], [r["ms"] for r in rs], "o-", color=c, label=f"{op} parallel")
        ax[i].axhline(ser, color=c, ls="--", lw=1, label=f"{op} serial")
    ax[i].set(xlabel="threads p", ylabel="median time (ms)", title=f"({'ab'[i]}) {n}", xticks=TH)
    ax[i].set_yscale("log")
    ax[i].legend(fontsize=7)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "scan.png"), dpi=170)
plt.close(fig)

# Fig 3: renderer baseline vs optimized
SCENES = ["sparse", "overlap", "clustered", "dense"]
fig, axs = plt.subplots(1, 4, figsize=(11, 3.2))
for ax, s in zip(axs, SCENES):
    inp = f"{s}_512"
    for v, c in (("baseline", "tab:blue"), ("optimized", "tab:green")):
        rs = pick(r_dyn1, inp, v)
        ax.plot([r["threads"] for r in rs], [r["ms"] for r in rs], "o-", color=c, label=v)
    ax.axhline(pick(r_dyn1, inp, "reference")[0]["ms"], color="gray", ls="--", lw=1, label="serial ref")
    ax.set_yscale("log")
    ax.set(title=s, xlabel="threads p", xticks=TH)
axs[0].set_ylabel("median time (ms), log scale")
axs[0].legend(fontsize=7)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "render.png"), dpi=170)
plt.close(fig)

# Fig 4: schedules (efficiency at 8 threads)
fig, axs = plt.subplots(1, 2, figsize=(9, 3.3))
scheds = (("static", r_stat), ("dynamic,1", r_dyn1), ("dynamic,8", r_dyn8))
for ax, v in zip(axs, ("baseline", "optimized")):
    x = range(3)
    for j, (name, rows) in enumerate(scheds):
        vals = []
        for s in ("sparse", "overlap", "clustered"):
            r = [r for r in pick(rows, f"{s}_512", v) if r["threads"] == 8]
            vals.append(r[0]["ms"] if r else 0)
        ax.bar([i + (j - 1) * 0.27 for i in x], vals, width=0.27, label=name)
    ax.set_xticks(list(x))
    ax.set_xticklabels(["sparse", "overlap", "clustered"])
    ax.set(ylabel="median time at p=8 (ms)", title=f"{v} renderer, 8 threads")
    ax.legend(fontsize=7, title="OMP_SCHEDULE", title_fontsize=7)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "sched.png"), dpi=170)
plt.close(fig)


# Fig 5: MPI data flow
def box(ax, x, y, w, h, text, fc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", fc=fc, ec="#333333"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7.5)


def arrow(ax, a, b, text=None, c="#333333"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=9, color=c, lw=1))
    if text:
        ax.text((a[0] + b[0]) / 2 + 0.05, (a[1] + b[1]) / 2, text, fontsize=6.5, color=c)


fig, ax = plt.subplots(figsize=(10, 5.2))
ax.set_xlim(0, 10)
ax.set_ylim(0, 6.2)
ax.axis("off")
box(ax, 0.2, 2.6, 1.8, 1.0, "Rank 0 (root)\nreads scene,\nbuilds tile list", "#ffe9b3")
stages = [(5.75, "1. MPI_Bcast\nN_c, W, H, tile size,\ncircle array (28 B each)", "#cfe3ff"),
          (4.15, "2. MPI_Scatterv\ntile ids per rank\n(counts may differ)", "#d9f2d9"),
          (2.55, "3. local render\nof owned tiles\n(Part 4 code)", "#eeeeee"),
          (0.95, "4. MPI_Gatherv\ntile pixels to root\n(variable bytes)", "#f9d5d5")]
for y, t, c in stages:
    box(ax, 2.6, y - 0.45, 2.0, 0.9, t, c)
for i in range(8):
    x = 5.3 + i * 0.57
    box(ax, x, 2.75, 0.5, 0.7, f"P{i}", "#ffffff")
for y, _, c in stages:
    pass
arrow(ax, (2.0, 3.3), (2.6, 5.5))
arrow(ax, (2.0, 3.2), (2.6, 3.95))
arrow(ax, (4.6, 5.75), (6.1, 3.5), "broadcast: same bytes to all ranks", "#1f5fbf")
arrow(ax, (4.6, 4.15), (8.0, 3.5), "scatter: different tile ids per rank", "#2e8b57")
arrow(ax, (7.2, 2.75), (4.6, 0.95), "gather: tile pixels", "#b22222")
arrow(ax, (2.6, 0.95), (1.1, 2.6), "assemble image")
ax.text(5.3, 1.2, "Interconnect (binomial-tree collectives,\nlogical hypercube for p=8)", fontsize=7.5)
ax.text(5.3, 2.35, "each rank: circles (from Bcast) + its tile ids -> pixels", fontsize=7)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "mpi_flow.png"), dpi=170)
plt.close(fig)

# Fig 6: binomial tree p=8
fig, ax = plt.subplots(figsize=(7.5, 2.6))
ax.axis("off")
pos = {r: (r * 1.0, 0) for r in range(8)}
cols = {1: "#1f5fbf", 2: "#2e8b57", 3: "#b22222"}
sends = [(0, 4, 1), (0, 2, 2), (4, 6, 2), (0, 1, 3), (2, 3, 3), (4, 5, 3), (6, 7, 3)]
for a, b, st in sends:
    ya = 0.0
    ax.annotate("", xy=(pos[b][0], 0.15), xytext=(pos[a][0], 0.15),
                arrowprops=dict(arrowstyle="-|>", color=cols[st], lw=1.3,
                                connectionstyle=f"arc3,rad=-{0.15 + 0.1 * (3 - st)}"))
for r, (x, y) in pos.items():
    ax.add_patch(plt.Circle((x, y), 0.22, fc="#ffe9b3" if r == 0 else "white", ec="#333333"))
    ax.text(x, y, f"P{r}", ha="center", va="center", fontsize=8)
for st, c in cols.items():
    ax.plot([], [], color=c, label=f"step {st}")
ax.legend(loc="lower center", ncol=3, fontsize=7, bbox_to_anchor=(0.5, -0.45))
ax.set_xlim(-0.5, 7.5)
ax.set_ylim(-0.6, 2.0)
ax.set_aspect("equal")
fig.tight_layout()
fig.savefig(os.path.join(FIG, "binomial.png"), dpi=170)
plt.close(fig)

# ---------------------------------------------------------------- helpers for text numbers


def ms(rows, inp, op, th, var="parallel"):
    for r in rows:
        if r["input"] == inp and r["op"] == op and r["threads"] == th and r["variant"] == var:
            return r["ms"]
    return float("nan")


def r_ms(rows, scene, v, th):
    return ms(rows, f"{scene}_512", v, th)


def blelloch_trace(a):
    a = list(a)
    m = len(a)
    up, down = [], []
    d = 1
    while d < m:
        for i in range(0, m, 2 * d):
            a[i + 2 * d - 1] += a[i + d - 1]
        up.append((d, list(a)))
        d *= 2
    a[m - 1] = 0
    down.append(("clear", list(a)))
    d = m // 2
    while d >= 1:
        for i in range(0, m, 2 * d):
            t = a[i + d - 1]
            a[i + d - 1] = a[i + 2 * d - 1]
            a[i + 2 * d - 1] += t
        down.append((d, list(a)))
        d //= 2
    return up, down


# ---------------------------------------------------------------- report text
para("Data-Parallel Algorithms and Parallel Circle Rendering", TITLE)
para("Parallel and Distributed Computing — Assignment 3 — Combined Performance Report", CAP)
story.append(Spacer(1, 8))
# Identity comes from the environment so it is never stored in the repository:
#   REPORT_NAME, REPORT_ROLL, REPORT_SECTION
_who = [os.environ.get(k, "") for k in ("REPORT_NAME", "REPORT_ROLL", "REPORT_SECTION")]
if any(_who):
    table([["Name", _who[0], "Roll number", _who[1]],
           ["Section", _who[2], "Date", "15 November 2026"]],
          widths=[2.6 * cm, 6 * cm, 2.6 * cm, 5 * cm], header=False, size=9)
else:
    para("Date: 15 November 2026", CAP)

para("Machine and toolchain", H2)
table([["Item", "Value"],
       ["CPU", "AMD Ryzen 7 7435HS (laptop), 8 physical cores, 16 hardware threads (SMT)"],
       ["Operating system", "Windows 11 Home, version 10.0.26200 (64-bit)"],
       ["Compiler", "GCC 15.2.0, target x86_64-w64-mingw32 (MinGW-w64)"],
       ["OpenMP runtime", "GNU libgomp shipped with GCC 15.2.0; _OPENMP = 201511 (OpenMP 4.5)"],
       ["Flags", "-O2 -std=c++17 -Wall -Wextra -fopenmp (unchanged Makefile flags)"],
       ["Measurement rule", "median of 5 (renderer) or 7 (SAXPY, scan) timed runs after one warm-up run; "
        "T<sub>1</sub> = the parallel code on one thread; file output never timed; every timing row is "
        "preceded by a passing comparison against the serial reference"]],
      widths=[3.6 * cm, 12.6 * cm])
para("Thread counts 1, 2, 4 and 8 are all supported (16 logical processors), so no count was skipped. "
     "Because this is a laptop, the single-thread runs execute at a higher boost clock than all-core runs; "
     "this lowers every measured efficiency somewhat and is a measured-environment effect, not an algorithmic one. "
     "Raw benchmark output, including the program header lines, is in <font face='Mono'>docs/results/</font>.")

# ================================================================ PART 1
para("Part 1 — SAXPY and parallel work-sharing", H1)
para("Implementation", H2)
code("""
const long long n = static_cast<long long>(x.size());
#pragma omp parallel for schedule(static)
for (long long i = 0; i < n; ++i) op[i] = a * xp[i] + yp[i];
""")
para("A static work-sharing loop gives each thread one contiguous block of indices, so every "
     "<i>z<sub>i</sub></i> is written exactly once by exactly one thread and the output order is the index order; "
     "no element is shared between threads. A signed index makes the loop canonical for OpenMP and an empty "
     "input simply executes zero iterations. The size check (throwing <font face='Mono'>std::invalid_argument</font>) "
     "is kept from the reference contract.")
para("Correctness evidence", H2)
bullets(["Supplied demo: <font face='Mono'>SAXPY N=1000000 ... correctness=PASS</font>; also PASS for n = 0, 1, 7, 1000 "
         "and n = 10 000 001 with 3 threads (not divisible by the thread count).",
         "Added test (<font face='Mono'>tests/edge_tests.cpp</font>): n in {0, 1, 2, 3, 7, 13, 1001, 65537} at "
         "p in {1, 2, 3, 4, 7, 8} compared <i>bitwise</i> with <font face='Mono'>saxpy_serial</font>; "
         "sizes smaller than p and not divisible by p are included; mismatched sizes must throw. All pass.",
         "<font face='Mono'>saxpy_bench</font> compares every thread count with the reference before timing (all PASS)."])
para("Timing table (saxpy_bench 7 1,2,4,8 10000,1000000,10000000)", H2)
table(bench_table(saxpy, ["n=10000", "n=1000000", "n=10000000"], ["saxpy"]),
      widths=[2.3 * cm, 1.6 * cm, 1.6 * cm, 1.5 * cm, 2.1 * cm, 2.4 * cm, 2.3 * cm, 2.3 * cm])
figure(os.path.join(FIG, "saxpy.png"),
       "Figure 1. (a) Measured speedup of saxpy_parallel (median of 7) for three sizes; the dotted line is ideal "
       "linear speedup. (b) Bandwidth achieved by the loop alone (output pre-allocated, n = 10<sup>7</sup>, "
       "tests/analysis_probe.cpp). The figure shows that the loop stops scaling once memory bandwidth "
       "saturates at about 4 threads, and that the full function scales even less because of a serial phase.")
para("Analysis", H2)
para(f"<b>Minimum traffic per element.</b> Under an ideal single-pass model each element needs one 4-byte read of "
     f"<i>x<sub>i</sub></i>, one 4-byte read of <i>y<sub>i</sub></i> and one 4-byte write of <i>z<sub>i</sub></i>: "
     f"<b>12 bytes per element</b> for only 2 floating-point operations (arithmetic intensity 2/12 ≈ 0.17 flop/byte). "
     f"With a write-allocate cache the store first reads the line, so real traffic is ≈ 16 B/element. For "
     f"n = 10<sup>7</sup> the minimum is 120 MB per call. The starter's output constructor also zero-fills the vector "
     f"(another 4–8 B/element) on one thread before the parallel loop runs.")
para(f"<b>Why SAXPY is bandwidth-limited.</b> A core can issue far more than 0.17 flop per byte it can load, so each "
     f"thread spends most of its time waiting for DRAM. Adding threads only helps until the memory controller "
     f"is saturated. The measured kernel-only bandwidth (Figure 1b) is {kernel_bw[1][1]:.1f} GB/s at p = 1, "
     f"{kernel_bw[2][1]:.1f} GB/s at p = 2, {kernel_bw[4][1]:.1f} GB/s at p = 4 and {kernel_bw[8][1]:.1f} GB/s at p = 8: "
     f"going from 4 to 8 threads adds almost nothing even though 8 idle cores are available. "
     f"For the full function at n = 10<sup>7</sup>, a separate measurement shows that allocating and zero-filling the "
     f"output takes {alloc_ms:.1f} ms on one thread (first-touch page faults on Windows plus the 40 MB fill), which is about half of "
     f"T<sub>1</sub> = {ms(saxpy, 'n=10000000', 'saxpy', 1):.1f} ms. With serial fraction f ≈ 0.5, Amdahl's law limits speedup "
     f"to below 1/f ≈ 2, and with the bandwidth ceiling the measured S<sub>8</sub> is only "
     f"{pick(saxpy, 'n=10000000', 'saxpy', 'parallel')[-1]['speedup']:.2f}.")
s2 = [r for r in pick(saxpy, "n=10000", "saxpy", "parallel")]
para(f"<b>Case where more threads reduce efficiency.</b> For n = 10<sup>4</sup> the time <i>rises</i> from "
     f"{s2[0]['ms']*1000:.0f} µs (p = 1) to {s2[1]['ms']*1000:.0f} µs (p = 2) and {s2[3]['ms']*1000:.0f} µs (p = 8), "
     f"so E<sub>2</sub> = {s2[1]['eff']:.3f} and E<sub>8</sub> = {s2[3]['eff']:.3f}. The whole computation (40 KB per "
     f"array, in L2 cache) takes about 5 µs, while waking the libgomp worker threads and the barrier at the end of the "
     f"parallel loop cost tens of microseconds, and that cost grows with p. For n = 10<sup>6</sup> the efficiency also falls from "
     f"{pick(saxpy, 'n=1000000', 'saxpy', 'parallel')[1]['eff']:.3f} (p = 2) to "
     f"{pick(saxpy, 'n=1000000', 'saxpy', 'parallel')[3]['eff']:.3f} (p = 8), because bandwidth saturation and the "
     f"serial allocation leave nothing for the extra threads to speed up.")

# ================================================================ PART 2
story.append(PageBreak())
para("Part 2 — Exclusive scan and repeated-index compaction", H1)
para("Implementation", H2)
para("<font face='Mono'>exclusive_scan_parallel</font> copies the input into a zero-padded buffer whose length is the next "
     "power of two and runs the work-efficient Blelloch scan in place. One <font face='Mono'>omp parallel</font> region "
     "contains every tree level; each level is an <font face='Mono'>omp for</font> whose implicit barrier is the "
     "synchronization between stages (level d+1 reads what level d wrote). The root is cleared inside an "
     "<font face='Mono'>omp single</font> (which also ends in a barrier). Within a level each iteration touches its own "
     "disjoint pair of slots, so a level is free of data races. Additions use unsigned arithmetic, so overflow wraps the same way as the "
     "serial loop does in practice, without signed-overflow undefined behaviour.")
code("""
for (d = 1; d < m; d *= 2)            // up-sweep
  #pragma omp for
  for (k = 0; k < m/(2d); ++k) a[k*2d + 2d-1] += a[k*2d + d-1];
#pragma omp single
a[m-1] = 0;
for (d = m/2; d >= 1; d /= 2)         // down-sweep
  #pragma omp for
  for (k ...) { t = a[i+d-1]; a[i+d-1] = a[i+2d-1]; a[i+2d-1] += t; }
""")
para("<font face='Mono'>find_repeats_parallel</font> follows the requested three phases: (1) a parallel loop sets "
     "flag[i] = 1 when A<sub>i</sub> = A<sub>i+1</sub> for i in [0, n−2]; (2) "
     "<font face='Mono'>exclusive_scan_parallel(flags)</font> gives each flagged index its output slot, and the output "
     "length is offset[n−2] + flag[n−2]; (3) a parallel scatter writes i to out[offset[i]]. Offsets strictly increase over "
     "flagged positions, so each slot has exactly one writer and the output is in ascending order. Inputs shorter than 2 "
     "return an empty vector.")
para("Correctness evidence", H2)
bullets(["Supplied demo at the required lengths: " + ", ".join(
    re.findall(r"SCAN N=(\d+) scan=PASS repeats=PASS", correct)) + " → all <i>scan=PASS repeats=PASS</i>.",
         "Added tests: handout examples [1,4,6,8,2] → [0,1,5,11,19] and [1,2,2,1,1,1,3,5,3,3] → [1,3,4,8]; random arrays "
         "of lengths 0, 1, 2, 3, 7, 8, 9, 31, 33, 1023, 1024, 1025, 4097, 100003; negative values; all-equal (every "
         "position repeats); strictly increasing (no repeats); each at p in {1,2,3,4,7,8}. All pass.",
         "<font face='Mono'>scan_bench</font> checks both operations against the serial versions at every thread count (all PASS)."])

para("Staged scan for n = 16, input = [1,2,3,4] repeated four times", H2)
up, down = blelloch_trace([1, 2, 3, 4] * 4)
rows = [["stage"] + [str(i) for i in range(16)], ["input"] + [str(v) for v in [1, 2, 3, 4] * 4]]
for d, arr in up:
    rows.append([f"up d={d}"] + [str(v) for v in arr])
for d, arr in down:
    rows.append([("root := 0" if d == "clear" else f"down d={d}")] + [str(v) for v in arr])
table(rows, widths=[2.1 * cm] + [0.88 * cm] * 16, size=7.5)
para("In the up-sweep, level d adds a[i+d−1] into a[i+2d−1] for every block of width 2d. After the last up-sweep level, "
     "slot 15 holds the total, 40. The down-sweep sets the root to 0. Then at each level the left child takes the "
     "parent's value and the right child takes parent + old left. The last row, "
     "[0,1,3,6,10,11,13,16,20,21,23,26,30,31,33,36], is the exclusive scan (it matches the serial result).")

para("Work and span of the tree scan", H2)
para("For m = 2<sup>k</sup> elements the up-sweep performs m/2 + m/4 + … + 1 = m − 1 additions and the down-sweep performs "
     "another m − 1 additions (plus m − 1 swaps). Total work is <b>W(m) = 2(m − 1) = O(m)</b>, the same order as the "
     "serial scan (m − 1 additions), but with roughly twice the operations and memory traffic. "
     "Each sweep has log<sub>2</sub> m dependent levels and every operation inside a level is independent, so the span "
     "(depth) is <b>D(m) = 2 log<sub>2</sub> m = O(log m)</b>. By Brent's bound "
     "T<sub>p</sub> ≤ W/p + D. Every level needs a barrier, so a more realistic model is "
     "T<sub>p</sub> ≈ 2m·c/p + 2 log<sub>2</sub>m · t<sub>barrier</sub>(p). Here c is the per-element cost, which grows "
     "when the stride exceeds a cache line. t<sub>barrier</sub> is a few microseconds and grows with p. Synchronization "
     "therefore adds a term proportional to the depth. That term dominates for small n. The top levels "
     "also have fewer than p active nodes (at level d only m/2d pairs exist), so threads sit idle at those barriers.")

para("Padding for n = 1025", H2)
para("Safe strategy: copy the 1025 values into a buffer of length 2<sup>ceil(log2 1025)</sup> = <b>2048</b> and fill slots "
     "1025…2047 with <b>0</b>, the identity of addition. Padding is only appended after the real data, and zeros add nothing, "
     "so prefix sums for indices 0…1024 are unchanged. The tail is discarded when the result is copied back. "
     "Overhead: 2048 − 1025 = <b>1023 extra elements</b> (99.8 % more storage and up to about 2× more tree work). This is the worst case, "
     "just past a power of two. A blocked scan (per-thread partial sums, then a scan of the p sums) needs no padding at all.")

para("Serial vs parallel timing (scan_bench 7 1,2,4,8 100000,10000000)", H2)
table(bench_table(scan, ["n=100000", "n=10000000"], ["scan", "repeats"]),
      widths=[2.3 * cm, 1.6 * cm, 1.6 * cm, 1.5 * cm, 2.1 * cm, 2.4 * cm, 2.3 * cm, 2.3 * cm], size=7.5)
figure(os.path.join(FIG, "scan.png"),
       "Figure 2. Median time (log scale) of the parallel scan and repeat compaction against thread count, with the "
       "serial reference as dashed lines. The figure shows that at 10<sup>5</sup> elements the parallel code slows "
       "down as threads are added, while at 10<sup>7</sup> it scales up to 4 threads but never reaches the serial time.")
sc1 = ms(scan, "n=100000", "scan", 1)
scs = ms(scan, "n=100000", "scan", 1, "serial")
para(f"<b>Does the measurement agree with the work–depth analysis?</b> Partly, and the disagreement is explained by "
     f"constants the asymptotic model ignores. "
     f"At n = 10<sup>5</sup> the serial scan takes {scs*1000:.0f} µs, while the parallel scan takes {sc1*1000:.0f} µs on one thread "
     f"and {ms(scan,'n=100000','scan',8)*1000:.0f} µs on eight. The work is tiny, so the "
     f"2 log<sub>2</sub>(131072) = 34 barriers, each costing more as p grows, dominate. This is the depth/synchronization term "
     f"of the model, and it is why time <i>increases</i> with p. At n = 10<sup>7</sup> the "
     f"work term dominates: the parallel scan improves from {ms(scan,'n=10000000','scan',1):.0f} ms (p = 1) to "
     f"{ms(scan,'n=10000000','scan',4):.0f} ms (p = 4), S<sub>4</sub> = "
     f"{[r for r in pick(scan,'n=10000000','scan','parallel') if r['threads']==4][0]['speedup']:.2f}. That matches the W/p "
     f"prediction until p = 4, where it flattens at the memory-bandwidth limit already measured in Part 1. "
     f"It still never beats the serial scan ({ms(scan,'n=10000000','scan',1,'serial'):.0f} ms) for three reasons. (i) It does "
     f"about 2× the additions. (ii) Padding 10<sup>7</sup> → 2<sup>24</sup> = 16.8 M adds 68 % more elements. (iii) Above stride 16 "
     f"every access touches a different 64-byte cache line, so the tree passes cost one cache miss per operation, while "
     f"the serial scan streams sequentially. In short, the O(n) work bound holds, but the constant factor is about "
     f"7× the serial one on this memory-bound machine, so the O(log n) depth cannot pay for it at p ≤ 8. "
     f"The repeat compaction shows the same pattern because it is two parallel passes plus one scan.")

# ================================================================ PART 3
story.append(PageBreak())
para("Part 3 — Correct parallel circle rendering", H1)
para("Implementation", H2)
code("""
#pragma omp parallel for schedule(runtime)
for (int y = 0; y < height; ++y)
  for (int x = 0; x < width; ++x) {
    Pixel p = px[y*width + x];
    for (int k = 0; k < nc; ++k)               // circles in input order
      if (covers(cs[k], x, y, width, height)) blend(p, cs[k]);
    px[y*width + x] = p;
  }
""")
para("This is a pixel-parallel decomposition by rows. Each row, and so each pixel, belongs to exactly one thread, so no "
     "two workers ever write the same pixel and no synchronization is needed. For every pixel the circles are applied "
     "in their original order with the unchanged <font face='Mono'>covers()</font> and <font face='Mono'>blend()</font>. "
     "The reference only has the loops nested the other way round (circle outermost), so each pixel receives the same "
     "sequence of floating-point operations, and the output is bit-identical to the reference, not just within the 10<sup>−4</sup> "
     "tolerance. <font face='Mono'>schedule(runtime)</font> lets OMP_SCHEDULE select the schedule in Part 4.")
para("Correctness evidence", H2)
demo_lines = [l for l in correct.splitlines() if l.startswith("RENDER")]
table([["scene", "variant", "circles", "result (512×512, 16 threads)"]] +
      [[re.search(r"scene=(\w+)", l).group(1), re.search(r"variant=(\w+)", l).group(1),
        re.search(r"circles=(\d+)", l).group(1), "PASS" if "PASS" in l else "FAIL"] for l in demo_lines],
      widths=[3 * cm, 3 * cm, 2 * cm, 5 * cm])
para("Added tests (all pass at p in {1,2,3,4,7,8}, for both render_parallel and render_optimized): an empty scene (image must stay "
     "white), a 1×1 image, a non-square 37×113 image, circles partly or completely outside the image, a zero-radius "
     "circle, circles whose edges pass exactly through pixel centres on an 8×8 image, every named scene at 200×200 (not a "
     "multiple of the tile size), and the hand-computed A/B order example below, checked for exact values. Overlapping "
     "circles are covered by <i>overlap</i> and <i>dense</i>. Scenes where most pixels are empty are covered by <i>sparse</i>.")
para("Order of blending: A = (1,0,0,0.5) and B = (0,0,1,0.5) over white (1,1,1)", H2)
table([["order", "after first circle", "after second circle (final RGB)"],
       ["A then B", "A: 0.5·(1,0,0) + 0.5·(1,1,1) = (1, 0.5, 0.5)",
        "B: 0.5·(0,0,1) + 0.5·(1,0.5,0.5) = <b>(0.5, 0.25, 0.75)</b>"],
       ["B then A", "B: 0.5·(0,0,1) + 0.5·(1,1,1) = (0.5, 0.5, 1)",
        "A: 0.5·(1,0,0) + 0.5·(0.5,0.5,1) = <b>(0.75, 0.25, 0.5)</b>"]],
      widths=[2.2 * cm, 6.3 * cm, 7.7 * cm])
para("The results differ because P<sub>new</sub> = αC + (1−α)P<sub>old</sub> is not commutative. The last circle "
     "contributes weight α = 0.5 and an earlier circle only α(1−α) = 0.25, because the later blend scales it down. Changing "
     "the order swaps those weights between red and blue. Green, which neither circle contains, is 0.25 in both: the "
     "white background survives only through (1−α)<sup>2</sup> = 0.25. A parallel renderer must therefore preserve the "
     "per-pixel order, not just apply the right set of circles.")
para("A race when two threads blend different circles into one pixel", H2)
table([["time", "thread T1 (blending A)", "thread T2 (blending B)", "pixel in memory"],
       ["t1", "load P = (1,1,1)", "", "(1,1,1)"],
       ["t2", "", "load P = (1,1,1)", "(1,1,1)"],
       ["t3", "compute A over P → (1,0.5,0.5)", "compute B over P → (0.5,0.5,1)", "(1,1,1)"],
       ["t4", "store (1,0.5,0.5)", "", "(1,0.5,0.5)"],
       ["t5", "", "store (0.5,0.5,1)", "<b>(0.5,0.5,1)</b>"]],
      widths=[1.2 * cm, 5 * cm, 5 * cm, 5 * cm])
para("Both threads read the old value before either writes. This is a lost update, and A's contribution disappears. The final "
     "(0.5,0.5,1) matches neither legal answer, (0.5,0.25,0.75) or (0.75,0.25,0.5). If the stores of the three components "
     "interleave, the pixel can even mix channels from both results, for example (1,0.5,1).")
para("Circle-parallel vs pixel-parallel decomposition", H2)
bullets(["<b>Circle-parallel</b> (threads take different circles): two constraints must hold. Each per-pixel update must be "
         "atomic, and for every pixel, circle i must be blended before circle j whenever i &lt; j. A critical section or lock "
         "provides only the first: it makes updates mutually exclusive, but the order of entry is whatever the scheduler "
         "produces, so the image would still be nondeterministic. Enforcing order needs per-pixel tickets or "
         "waiting, which serializes the work.",
         "<b>Why a critical section per pixel update performs poorly:</b> a blend is about 10 floating-point operations, "
         "while an <font face='Mono'>omp critical</font> is one global lock. Every covered pixel would take that lock, "
         "so all threads queue on it and the lock cache line moves between cores at roughly 100 cycles per transfer. Throughput "
         "would fall below serial. Fine-grained per-pixel locks reduce contention but add lock memory and atomic "
         "operations to every blend, and they still do not fix the order.",
         "<b>Pixel-parallel</b> (used here): each pixel has a single owner, which visits circles in input order. The only "
         "constraint is that ownership is disjoint, which a work-sharing loop over rows or tiles guarantees. The circle "
         "array is shared read-only, so it needs no synchronization and is cached by every core. The cost is that every "
         "thread scans the whole circle list for its pixels; Part 4 removes most of that cost."])
para("Static allocation for a 1024×1024 image with p = 8", H2)
para("1024 × 1024 = 1 048 576 pixels, and 1 048 576 / 8 = <b>131 072 pixels per worker</b> (128 rows of 1024 pixels). The pixel count "
     "is even, but the work is not. A pixel's cost is N<sub>c</sub> coverage tests plus one blend per covering circle, and "
     "coverage is spatially concentrated: in <i>clustered</i>, most circles lie in two hot spots, so the 128-row bands "
     "through them do many more blends than empty bands. In the optimized renderer the cost is proportional to the "
     "circles that reach each tile, and our counts show the busiest 32×32 tile has 26.7× the mean work in <i>clustered</i>. "
     "Other sources of unevenness are SMT siblings sharing a core, uneven turbo frequencies, and OS interrupts on "
     "individual cores.")

# ================================================================ PART 4
story.append(PageBreak())
para("Part 4 — Renderer optimization and performance investigation", H1)
para("Chosen optimization: bounding-box culling inside ordered per-tile passes", H2)
para("The image is cut into 32×32 tiles, and each tile is owned by one thread "
     "(<font face='Mono'>#pragma omp parallel for schedule(runtime)</font> over tiles). Before that, each circle's pixel "
     "bounding box is computed once (in parallel). The box is derived from the pixel-centre condition and padded by one "
     "pixel on every side, so rounding can never exclude a covered pixel. The tile owner walks the circles in "
     "<b>original input order</b>, skips any circle whose box misses the tile (4 integer comparisons), and runs "
     "<font face='Mono'>covers()</font> + <font face='Mono'>blend()</font> only on the box-tile intersection rectangle. "
     "Coverage is still decided by <font face='Mono'>covers()</font>, and the box is only a filter.")
para("<b>Why this choice.</b> Plain bounding-box culling with circles as the outer loop would put the parallelism over "
     "circles and bring back the race and order problem from Part 3. Tiles keep the race-free single-owner property, "
     "and walking circles in order inside a tile keeps every pixel's blend order without any sorting. Within a tile the "
     "circle loop is outermost and runs in order, so each pixel still sees its circles in input order. The candidate list for a "
     "tile is produced on the fly from that ordered walk rather than stored, so there is no list-building pass and no extra memory. "
     "The tile size 32 gives 256 tiles at 512×512 (32 per thread at p = 8), which is enough for dynamic balancing, "
     "and keeps the tile×circle box tests small (at most 128 000 per frame, against 131 million coverage tests for the "
     "baseline on <i>clustered</i>). A 32×32 tile of pixels is 12 KB, which fits in L1/L2 while all its circles are applied.")
para("Correctness: render_bench compares every renderer against the reference at every thread count before timing, and "
     "all comparisons passed for all schedules (the PASS rows in the table above and in docs/results). The edge tests listed in "
     "Part 3 also run render_optimized.")
para("Reproducible commands", H2)
code("""
cd PDC_Assignment_3_Starter && make            # or: sh build.sh
make test                                       # edge tests, all parts
for s in dense sparse overlap clustered; do ./render_demo 512 $s parallel; ./render_demo 512 $s optimized; done
OMP_SCHEDULE="static"    ./render_bench 512 5 1,2,4,8 sparse,overlap,clustered,dense
OMP_SCHEDULE="dynamic,1" ./render_bench 512 5 1,2,4,8 sparse,overlap,clustered,dense
OMP_SCHEDULE="dynamic,8" ./render_bench 512 5 1,2,4,8 sparse,overlap,clustered
./analysis_probe                                # work-model counts + serial overhead probe
""")
para("Results: baseline vs optimized (512×512, OMP_SCHEDULE=dynamic,1, median of 5 runs)", H2)
table(bench_table(r_dyn1, [f"{s}_512" for s in SCENES], ["reference", "baseline", "optimized"]),
      widths=[2.3 * cm, 1.7 * cm, 1.6 * cm, 1.4 * cm, 2.1 * cm, 2.4 * cm, 2.3 * cm, 2.3 * cm], size=7.2)
para("The <i>sparse</i> scene has 300 small circles over a mostly empty image. <i>overlap</i> has 150 large, low-alpha "
     "circles that heavily overlap in the centre. <i>clustered</i> has 500 circles concentrated in two hot spots, which "
     "makes the work very uneven. <i>dense</i> is the default demo scene. T<sub>1</sub> is "
     "each renderer's own one-thread time, and the last column compares against the serial reference.")
figure(os.path.join(FIG, "render.png"),
       "Figure 3. Median render time (log scale) against thread count for the baseline and optimized renderers, with the "
       "serial reference dashed. The optimization changes run time by one to two orders of magnitude on sparse and "
       "clustered scenes but only about 1.7× on overlap, where nearly every circle really does cover most of the image. Thread scaling of "
       "the optimized renderer flattens early because only a small amount of parallel work is left.")

para("Static vs dynamic schedules", H2)
srows = [["scene / renderer", "p", "static (ms)", "dynamic,1 (ms)", "dynamic,8 (ms)", "best"]]
for s in ("sparse", "overlap", "clustered"):
    for v in ("baseline", "optimized"):
        for p in (4, 8):
            vals = [r_ms(rows_, s, v, p) for rows_ in (r_stat, r_dyn1, r_dyn8)]
            best = ["static", "dynamic,1", "dynamic,8"][vals.index(min(vals))]
            srows.append([f"{s} / {v}", p] + [f"{x:.3f}" for x in vals] + [best])
table(srows, widths=[4 * cm, 1 * cm, 2.5 * cm, 2.7 * cm, 2.7 * cm, 2.5 * cm])
figure(os.path.join(FIG, "sched.png"),
       "Figure 4. Median time at 8 threads under the three OpenMP schedules. The figure shows that the schedule matters "
       "most where the per-chunk work is most uneven: the optimized renderer on the clustered scene.")
w = work
para(f"<b>Trade-off.</b> <i>static</i> splits the iterations into p equal contiguous blocks at no scheduling cost, but a block "
     f"that contains a hot spot finishes last. For the optimized renderer on <i>clustered</i>, our tile counts show that the "
     f"busiest of the 8 static blocks holds {float(w['clustered'][6])*100:.0f} % of all coverage work (an ideal share is 12.5 %), "
     f"which caps static speedup near 1/{float(w['clustered'][6]):.2f} ≈ {1/float(w['clustered'][6]):.1f}. The measured time at "
     f"p = 8 is {r_ms(r_stat,'clustered','optimized',8):.2f} ms static against {r_ms(r_dyn1,'clustered','optimized',8):.2f} ms "
     f"dynamic,1. <i>dynamic,1</i> hands out one tile (or one row for the baseline) at a time from a shared counter. "
     f"That costs one atomic operation per chunk, but threads that finish cheap tiles keep taking more. <i>dynamic,8</i> halves the "
     f"balancing granularity (32 chunks of 8 tiles) and lands in between ({r_ms(r_dyn8,'clustered','optimized',8):.2f} ms): fewer "
     f"atomics, but a chunk of 8 tiles can contain a whole hot spot. For the baseline, every row does the same "
     f"N<sub>c</sub> coverage tests, so work per row is nearly uniform and the schedules differ by noise-level amounts, "
     f"except on clustered at p = 8 ({r_ms(r_stat,'clustered','baseline',8):.1f} ms static against "
     f"{r_ms(r_dyn1,'clustered','baseline',8):.1f} ms dynamic,1), where the hot-spot rows also do many more blends. Smaller tiles "
     f"improve balance but add box tests (N<sub>tiles</sub>·N<sub>c</sub>) and more scheduling operations. Larger tiles do the reverse. On "
     f"<i>sparse</i> nothing changes, because the parallel loop is no longer the bottleneck (see below).")

para("Work model", H2)
para("Let t<sub>c</sub> be the cost of one covers() test, t<sub>b</sub> of one blend, t<sub>box</sub> of one tile–box "
     "test, B the number of blends (fixed by the scene, the same for every correct renderer), A<sub>k</sub> the clipped "
     "box area of circle k, and t<sub>init</sub> the per-pixel cost of creating the white image.")
para("<b>Baseline:</b> T<sub>base</sub> ≈ (N<sub>c</sub>·W·H·t<sub>c</sub> + B·t<sub>b</sub>)/p + W·H·t<sub>init</sub>. "
     "<b>Optimized:</b> T<sub>opt</sub> ≈ (N<sub>c</sub>·t<sub>bbox</sub> + N<sub>tiles</sub>·N<sub>c</sub>·t<sub>box</sub> + "
     "Σ<sub>k</sub>A<sub>k</sub>·t<sub>c</sub> + B·t<sub>b</sub>)/p<sub>eff</sub> + W·H·t<sub>init</sub>. Here p<sub>eff</sub> ≤ p "
     "reflects tile imbalance, and the W·H·t<sub>init</sub> term is serial because the Image constructor fills the image on one thread.")
table([["scene", "N<sub>c</sub>", "baseline covers tests N<sub>c</sub>WH", "tile–box tests N<sub>tiles</sub>N<sub>c</sub>",
        "optimized covers tests ΣA<sub>k</sub>", "test reduction", "max/mean tile work", "measured T<sub>1</sub> ratio base/opt"]] +
      [[s, w[s][0], f"{int(w[s][1]):,}", f"{int(w[s][2]):,}", f"{int(w[s][3]):,}", w[s][4], w[s][5],
        f"{r_ms(r_dyn1, s, 'baseline', 1) / r_ms(r_dyn1, s, 'optimized', 1):.1f}×"] for s in SCENES],
      widths=[1.8 * cm, 1 * cm, 2.6 * cm, 2.3 * cm, 2.5 * cm, 1.8 * cm, 1.9 * cm, 2.3 * cm], size=7.5)
para(f"The model explains the gap between the predicted and measured gains. On <i>sparse</i> coverage tests fall "
     f"{w['sparse'][4]}, but the measured one-thread gain is only "
     f"{r_ms(r_dyn1,'sparse','baseline',1)/r_ms(r_dyn1,'sparse','optimized',1):.0f}× because the remaining time is mostly the serial "
     f"image allocation and fill, measured at {img_ms:.2f} ms for 512×512 (tests/analysis_probe.cpp). On <i>overlap</i>, tests fall only "
     f"{w['overlap'][4]} and B is large (many blends per pixel). Blends cannot be removed, so the gain is "
     f"{r_ms(r_dyn1,'overlap','baseline',1)/r_ms(r_dyn1,'overlap','optimized',1):.1f}×.")
para("<b>When the optimization loses.</b> It is worse when the culling cannot remove work: "
     "N<sub>c</sub>·t<sub>bbox</sub> + N<sub>tiles</sub>·N<sub>c</sub>·t<sub>box</sub> &gt; (N<sub>c</sub>·W·H − ΣA<sub>k</sub>)·t<sub>c</sub>. "
     "That happens when every circle covers (nearly) the whole image, so A<sub>k</sub> ≈ W·H and nothing is saved, or with "
     "a very large number of tiny circles on a small image, where N<sub>tiles</sub>·N<sub>c</sub> box tests are comparable to the "
     "pixels themselves. There is also a cost the model does not count: with the circle loop outermost inside a tile, a pixel "
     "covered by every circle is loaded and stored once per circle, while the baseline keeps it in registers. On a scene "
     "where all circles cover the whole image, the optimized version can therefore be slightly slower than the baseline. This is a prediction "
     "from the model and was not measured; none of the provided scenes is like that.")

para("Strongest observed bottleneck per scene", H2)
bullets([f"<b>sparse</b> — optimized: the <i>serial</i> image construction. The white fill of 262 144 pixels "
         f"({img_ms:.2f} ms measured) is about {img_ms / r_ms(r_dyn1,'sparse','optimized',8)*100:.0f} % of the "
         f"{r_ms(r_dyn1,'sparse','optimized',8):.2f} ms 8-thread time, plus thread wake-up at the parallel loop. This is "
         f"Amdahl's serial fraction, not loop scheduling, which is why speedup stalls near 1.3. Baseline: covers() arithmetic, "
         f"78.6 M tests, compute-bound and scaling to {pick(r_dyn1,'sparse_512','baseline')[-1]['speedup']:.1f}× at p = 8.",
         f"<b>overlap</b> — blend arithmetic and per-pixel read–modify–write. Nearly 10 M tests survive culling, and most "
         f"of them blend. The work is real and divisible, so this scene scales best "
         f"({pick(r_dyn1,'overlap_512','optimized')[-1]['speedup']:.1f}× at p = 8). The remaining loss comes from centre tiles "
         f"carrying {w['overlap'][5]}× the mean tile work and from the lower all-core clock.",
         f"<b>clustered</b> — load imbalance. The busiest tile has {w['clustered'][5]}× the mean work and, under static "
         f"scheduling, one thread's block holds {float(w['clustered'][6])*100:.0f} % of the work. Dynamic scheduling removes "
         f"most of this, after which the same serial image fill as in <i>sparse</i> limits it "
         f"(S<sub>8</sub> = {pick(r_dyn1,'clustered_512','optimized')[-1]['speedup']:.2f}).",
         f"<b>dense</b> — the work is small (≈0.6 M tests after culling), so at p = 8 the serial fill ({img_ms:.2f} ms) and "
         f"the fork/join barrier make up most of the {r_ms(r_dyn1,'dense','optimized',8):.2f} ms."])

# ================================================================ PART 5
story.append(PageBreak())
para("Part 5 — MPI collectives and communication-cost reasoning", H1)
para("Data-flow design", H2)
figure(os.path.join(FIG, "mpi_flow.png"),
       "Figure 5. Data flow for distributing renderer tiles to p = 8 processes: broadcast of the scene, scatter of tile "
       "ownership, local rendering, and gather of tile pixels to the root.", w=15.5)
bullets(["<b>MPI_Bcast (scene metadata):</b> the root broadcasts W, H, the tile size, N<sub>c</sub> and the circle array "
         "(7 floats = 28 B per circle, keeping input order). Every rank needs the same read-only data, which is exactly a "
         "broadcast. Sending only per-tile candidate lists is an alternative when the scene is very large.",
         "<b>MPI_Scatter / MPI_Scatterv (tile ownership):</b> the root sends each rank the list of tile ids it owns. "
         "<b>MPI_Scatterv</b> is needed when the counts differ: when the number of tiles is not divisible by p (for example 256 tiles on "
         "6 ranks gives 43/42), when tiles are assigned by cost so heavy ranks get fewer tiles, or when each rank is also sent "
         "its variable-length candidate circle lists.",
         "<b>MPI_Gather / MPI_Gatherv (results):</b> each rank returns its rendered pixels (12 B per pixel as 3 floats, or 3 B as "
         "8-bit RGB). <b>MPI_Gatherv</b> is needed when ranks return different byte counts: edge tiles are smaller when W or H "
         "is not a multiple of the tile size, and ranks own different numbers of tiles. The root uses the displacement array to "
         "place each block. A fixed-count MPI_Gather only works with equal blocks, such as p equal horizontal bands of a "
         "divisible image."])
para("Broadcast cost under T(m) = α + βm", H2)
para("Assumptions: one-port model (a process sends or receives at most one message at a time), full-duplex links with no "
     "contention between distinct pairs, store-and-forward (a process forwards only after it has received the whole "
     "m-byte message; no pipelining or segmentation), and the same α and β for every pair.")
bullets(["<b>(i) Linear:</b> the root sends the message to the p − 1 others one after another, so "
         "<b>T<sub>lin</sub> = (p − 1)(α + βm)</b>.",
         "<b>(ii) Binomial tree:</b> in step s every process that already has the data sends it to one that does not, so the "
         "number of holders doubles each step (1 → 2 → 4 → 8, Figure 6). After ceil(log<sub>2</sub> p) steps all hold it: "
         "<b>T<sub>bin</sub> = ceil(log<sub>2</sub> p)·(α + βm)</b>, which is 3(α + βm) for p = 8."])
figure(os.path.join(FIG, "binomial.png"),
       "Figure 6. Binomial-tree broadcast for p = 8 from P0: step 1 P0→P4; step 2 P0→P2, P4→P6; step 3 P0→P1, P2→P3, "
       "P4→P5, P6→P7.", w=12)
para("Numbers for p = 8, m = 2<sup>20</sup> B, α = 10 µs, β = 1 ns/B", H2)
table([["quantity", "calculation", "value"],
       ["βm", "2<sup>20</sup> B × 1 ns/B = 1 048 576 ns", "1048.576 µs"],
       ["α + βm (one message)", "10 µs + 1048.576 µs", "1058.576 µs"],
       ["T<sub>lin</sub>", "(8 − 1) × 1058.576 µs", "<b>7410.032 µs ≈ 7.41 ms</b>"],
       ["T<sub>bin</sub>", "log<sub>2</sub>8 = 3;  3 × 1058.576 µs", "<b>3175.728 µs ≈ 3.18 ms</b>"],
       ["ratio", "7410.032 / 3175.728", "2.33× faster with the tree"]],
      widths=[3.8 * cm, 8 * cm, 4.4 * cm])
para("With m this large, βm (1.05 ms) is about 100 times α, so both schemes are bandwidth-dominated. Long messages are "
     "usually broadcast with scatter + allgather or a pipelined chain, which costs about 2βm + O(log p)α ≈ 2.1 ms here. That "
     "beats the binomial tree, whose bandwidth term grows with log p.")
para("Broadcast steps for p = 16 on different topologies", H2)
table([["topology (p = 16)", "routing assumption", "steps"],
       ["ring, bidirectional", "store-and-forward to neighbours only; data travels both ways round the ring",
        "ceil((p−1)/2) = <b>8</b> (15 if unidirectional)"],
       ["2D mesh 4×4, no wrap-around", "root at a corner; first along its row, then every row node down its column "
        "(dimension-ordered); neighbour-only sends", "3 + 3 = <b>6</b> (4 with the root at a centre node; 4 on a 4×4 torus)"],
       ["hypercube, d = 4", "in step i send across dimension i (binomial tree mapped onto the cube); every send uses a "
        "direct link", "log<sub>2</sub>16 = <b>4</b>"]],
      widths=[3.6 * cm, 8.8 * cm, 3.8 * cm])
para("Step count alone may not predict time, for several reasons. (1) Each step costs α + βm, and for large m the βm term "
     "dominates, so a pipelined ring broadcast (cost about (p−1+k)·(α + βm/k) with k segments) can beat a 4-step hypercube "
     "broadcast. (2) With cut-through or wormhole routing, multi-hop messages cost little more than one-hop ones, so the "
     "logical tree matters more than the physical diameter. (3) Link contention appears when the logical algorithm maps onto "
     "a physical network that does not have every link it uses, or when other jobs share the network. (4) Per-node injection "
     "bandwidth, NIC queues and software overhead (part of α) differ between machines. (5) Process skew: a step cannot start "
     "until its sender has arrived.")
para("Load balance for tile times [2, 2, 3, 3, 3, 4, 5, 18] ms on 8 processes", H2)
table([["quantity", "calculation", "value"],
       ["total work", "2+2+3+3+3+4+5+18", "40 ms"],
       ["ideal balanced makespan (lower bound)", "total / p = 40 / 8", "<b>5 ms</b>"],
       ["bound if tiles are indivisible", "max(40/8, largest tile 18)", "18 ms"],
       ["actual makespan, one tile per process", "max of the eight times", "<b>18 ms</b>"],
       ["efficiency (ignoring communication)", "total / (p × makespan) = 40 / (8 × 18)", "<b>0.278 (27.8 %)</b>"],
       ["speedup", "40 / 18", "2.22 on 8 processes"]],
      widths=[5.5 * cm, 6.7 * cm, 4 * cm])
para("<b>Recommendation:</b> split the expensive 18 ms tile into 4 sub-tiles of about 4.5 ms (it is a hot spot; the pixels are "
     "independent, so splitting does not affect correctness) and assign the 11 work items with longest-processing-time "
     "first: 5, 4.5, 4.5, 4.5, 4.5, 4, 3, 3 go one per process, then 3 → the 3 ms rank (6), 2 → the other 3 ms rank (5), 2 → the "
     "4 ms rank (6). Makespan falls from 18 ms to <b>6 ms</b>, and efficiency rises to 40/(8 × 6) = <b>0.83</b>. A dynamic "
     "master–worker queue of small tiles would give a similar result without knowing the costs in advance.")
para("<b>Communication cost of the change:</b> the broadcast of circle data is unchanged. The assignment becomes an "
     "MPI_Scatterv with unequal counts, or under dynamic scheduling one request and one reply per work item, about 2α ≈ 20 µs "
     "each. The result gather becomes an MPI_Gatherv with 11 blocks instead of 8. The total pixel bytes are unchanged; only "
     "3 extra blocks are added, about 3α ≈ 30 µs of latency, plus the bookkeeping to reassemble the split tile. "
     "That costs tens of microseconds in exchange for a 12 ms shorter makespan.")

para("Summary", H2)
para("All parallel functions pass the supplied comparisons and the added edge tests. SAXPY is limited by memory bandwidth "
     "and a serial allocation. The Blelloch scan shows the O(n)-work / O(log n)-depth trade-off but loses to the serial scan "
     "on this memory-bound machine. Pixel-parallel rendering is correct without synchronization. Tiled bounding-box culling "
     "gives 1.7–73× single-thread gains, and after it, scaling is limited by load imbalance (clustered, fixed by "
     "dynamic scheduling) and the serial image fill (sparse, dense).")


# ---------------------------------------------------------------- build
def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(BODY, 8)
    canvas.drawRightString(A4[0] - 1.8 * cm, 1.1 * cm, f"PDC Assignment 3 report — page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                        topMargin=1.6 * cm, bottomMargin=1.7 * cm,
                        title="PDC Assignment 3 Report", author="")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("wrote", OUT)
