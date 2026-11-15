"""Builds the combined report PDF from the saved benchmark outputs in docs/results.

Usage (from the repository root):
    python docs/make_report.py
Optional identity on the title block (never stored in the repository):
    REPORT_NAME="..." REPORT_ROLL="..." REPORT_SECTION="..." python docs/make_report.py
Needs matplotlib, numpy and reportlab. The rendered scene images are read from
tmp/render_<scene>_<variant>.ppm (produced by ./render_demo 512 <scene> <variant>
run inside tmp/). Figures are written to tmp/figs (git ignored).
"""
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, Image, KeepTogether, PageBreak, Paragraph, Preformatted,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "docs", "results")
TMP = os.path.join(ROOT, "tmp")
FIG = os.path.join(TMP, "figs")
OUT = os.path.join(ROOT, "docs", "RollNumber_Report.pdf")
os.makedirs(FIG, exist_ok=True)

# ------------------------------------------------------------------ fonts and styles
F = "C:/Windows/Fonts"
pdfmetrics.registerFont(TTFont("TNR", f"{F}/times.ttf"))
pdfmetrics.registerFont(TTFont("TNR-B", f"{F}/timesbd.ttf"))
pdfmetrics.registerFont(TTFont("TNR-I", f"{F}/timesi.ttf"))
pdfmetrics.registerFont(TTFont("TNR-BI", f"{F}/timesbi.ttf"))
pdfmetrics.registerFont(TTFont("CUR", f"{F}/cour.ttf"))
registerFontFamily("TNR", normal="TNR", bold="TNR-B", italic="TNR-I", boldItalic="TNR-BI")
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3})

ss = getSampleStyleSheet()
P = ParagraphStyle("p", parent=ss["Normal"], fontName="TNR", fontSize=11, leading=14.2,
                   alignment=TA_JUSTIFY, spaceAfter=6)
H1 = ParagraphStyle("h1", parent=P, fontName="TNR-B", fontSize=15, leading=19, spaceBefore=4,
                    spaceAfter=6, alignment=0, keepWithNext=1)
H2 = ParagraphStyle("h2", parent=P, fontName="TNR-B", fontSize=12, leading=15, spaceBefore=8,
                    spaceAfter=4, alignment=0, keepWithNext=1)
CAP = ParagraphStyle("cap", parent=P, fontSize=9.5, leading=12, alignment=TA_JUSTIFY)
TITLE = ParagraphStyle("t", parent=H1, fontSize=19, leading=24, alignment=TA_CENTER)
SUB = ParagraphStyle("s", parent=P, alignment=TA_CENTER)
CODE = ParagraphStyle("code", parent=P, fontName="CUR", fontSize=8.5, leading=10.5, alignment=0)
BUL = ParagraphStyle("bul", parent=P, leftIndent=14, bulletIndent=3, spaceAfter=3, bulletFontName="TNR")

story = []


def para(t, st=P):
    story.append(Paragraph(t, st))


def bullets(items):
    for t in items:
        story.append(Paragraph(t, BUL, bulletText="•"))
    story.append(Spacer(1, 3))


def code(t):
    story.append(Preformatted(t.strip("\n"), CODE))
    story.append(Spacer(1, 4))


def table(rows, widths=None, header=True, size=9):
    def cell(bold):
        return ParagraphStyle("c", parent=P, fontSize=size, leading=size + 2.2, spaceAfter=0,
                              alignment=0, fontName="TNR-B" if bold else "TNR")
    data = [[Paragraph(str(c), cell(header and i == 0)) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 2),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    story.append(t)
    story.append(Spacer(1, 7))


def figure(path, caption, w=16.5):
    iw, ih = ImageReader(path).getSize()
    story.append(KeepTogether([Image(path, width=w * cm, height=w * cm * ih / iw),
                               Paragraph(caption, CAP), Spacer(1, 6)]))


# ------------------------------------------------------------------ read the saved results
ROW = re.compile(r"^(\S+)\s+(\S+)\s+(serial|parallel)\s+(\d+)\s+([\d.]+)\s+(\S+)\s+(\S+)\s+([\d.]+)")


def load(name):
    rows = []
    for line in open(os.path.join(RES, name)):
        m = ROW.match(line)
        if m:
            inp, op, var, th, ms_, spd, ef, vs = m.groups()
            rows.append(dict(input=inp, op=op, variant=var, threads=int(th), ms=float(ms_),
                             speedup=None if spd == "n/a" else float(spd),
                             eff=None if ef == "n/a" else float(ef), vs=float(vs)))
    return rows


saxpy, scan = load("saxpy_bench.txt"), load("scan_bench.txt")
r_dyn1, r_stat, r_dyn8 = (load("render_bench_dynamic1.txt"), load("render_bench_static.txt"),
                          load("render_bench_dynamic8.txt"))
probe = open(os.path.join(RES, "analysis_probe.txt")).read()
correct = open(os.path.join(RES, "correctness.txt")).read()

kbw = {int(m.group(1)): float(m.group(2)) for m in re.finditer(r"p=(\d+): [\d.]+ ms \(([\d.]+) GB/s", probe)}
alloc_ms = float(re.search(r"alloc\+zero-fill 1e7 floats \(serial\): ([\d.]+)", probe).group(1))
img_ms = float(re.search(r"white fill \(serial\): ([\d.]+)", probe).group(1))
W = {}
for line in probe.splitlines():
    parts = line.split()
    if len(parts) == 8 and parts[0] in ("dense", "sparse", "overlap", "clustered"):
        W[parts[0]] = parts[1:]  # circles, base, tilebox, optcovers, reduction, max/mean, busiest share


def pick(rows, inp, op, var=None):
    return [r for r in rows if r["input"] == inp and r["op"] == op and (var is None or r["variant"] == var)]


def ms(rows, inp, op, th, var="parallel"):
    for r in rows:
        if (r["input"], r["op"], r["threads"], r["variant"]) == (inp, op, th, var):
            return r["ms"]
    return float("nan")


def rms(rows, scene, v, th):
    return ms(rows, f"{scene}_512", v, th)


def sp(rows, inp, op, th, var="parallel"):
    for r in rows:
        if (r["input"], r["op"], r["threads"], r["variant"]) == (inp, op, th, var):
            return r["speedup"]


def bench_table(rows, inputs, ops):
    out = [["input", "operation", "variant", "threads p", "median (ms)", "S<sub>p</sub> = T<sub>1</sub>/T<sub>p</sub>",
            "E<sub>p</sub> = S<sub>p</sub>/p", "serial time / T<sub>p</sub>"]]
    for inp in inputs:
        for op in ops:
            for r in pick(rows, inp, op):
                out.append([inp, op, r["variant"], r["threads"], f"{r['ms']:.4f}",
                            "n/a" if r["speedup"] is None else f"{r['speedup']:.3f}",
                            "n/a" if r["eff"] is None else f"{r['eff']:.3f}", f"{r['vs']:.3f}"])
    return out


BW = [2.3 * cm, 1.8 * cm, 1.6 * cm, 1.5 * cm, 2.0 * cm, 2.5 * cm, 2.3 * cm, 2.3 * cm]
TH = [1, 2, 4, 8]
SCENES = ["sparse", "overlap", "clustered", "dense"]

# ------------------------------------------------------------------ figures
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
for n in ["n=10000", "n=1000000", "n=10000000"]:
    rs = pick(saxpy, n, "saxpy", "parallel")
    ax[0].plot([r["threads"] for r in rs], [r["speedup"] for r in rs], "o-", label=n)
ax[0].plot(TH, TH, "k:", label="ideal")
ax[0].set(xlabel="threads p", ylabel="speedup S$_p$ = T$_1$/T$_p$", xticks=TH, title="(a) SAXPY speedup")
ax[0].legend(fontsize=8)
ax[1].plot(TH, [kbw[p] for p in TH], "s-", color="tab:red")
ax[1].set(xlabel="threads p", ylabel="bandwidth (GB/s)", xticks=TH, ylim=(0, 32),
          title="(b) loop only, n = 10$^7$, 12 B per element")
fig.tight_layout()
fig.savefig(os.path.join(FIG, "saxpy.png"), dpi=170)
plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
for i, n in enumerate(["n=100000", "n=10000000"]):
    for op, c in (("scan", "tab:blue"), ("repeats", "tab:orange")):
        rs = pick(scan, n, op, "parallel")
        ax[i].plot([r["threads"] for r in rs], [r["ms"] for r in rs], "o-", color=c, label=f"{op}, parallel")
        ax[i].axhline(pick(scan, n, op, "serial")[0]["ms"], color=c, ls="--", lw=1, label=f"{op}, serial")
    ax[i].set(xlabel="threads p", ylabel="median time (ms)", title=f"({'ab'[i]}) {n}", xticks=TH, yscale="log")
    ax[i].legend(fontsize=7)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "scan.png"), dpi=170)
plt.close(fig)

fig, axs = plt.subplots(1, 4, figsize=(11, 3.2))
for ax, s in zip(axs, SCENES):
    for v, c in (("baseline", "tab:blue"), ("optimized", "tab:green")):
        rs = pick(r_dyn1, f"{s}_512", v)
        ax.plot([r["threads"] for r in rs], [r["ms"] for r in rs], "o-", color=c, label=v)
    ax.axhline(pick(r_dyn1, f"{s}_512", "reference")[0]["ms"], color="gray", ls="--", lw=1, label="serial reference")
    ax.set(title=s, xlabel="threads p", xticks=TH, yscale="log")
axs[0].set_ylabel("median time (ms), log scale")
axs[0].legend(fontsize=7)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "render.png"), dpi=170)
plt.close(fig)

fig, axs = plt.subplots(1, 2, figsize=(9, 3.3))
scheds = (("static", r_stat), ("dynamic,1", r_dyn1), ("dynamic,8", r_dyn8))
for ax, v in zip(axs, ("baseline", "optimized")):
    for j, (name, rows) in enumerate(scheds):
        vals = [rms(rows, s, v, 8) for s in ("sparse", "overlap", "clustered")]
        ax.bar([i + (j - 1) * 0.27 for i in range(3)], vals, width=0.27, label=name)
    ax.set_xticks(range(3))
    ax.set_xticklabels(["sparse", "overlap", "clustered"])
    ax.set(ylabel="median time (ms)", title=f"{v} renderer, p = 8")
    ax.legend(fontsize=7, title="OMP_SCHEDULE", title_fontsize=7)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "sched.png"), dpi=170)
plt.close(fig)


def read_ppm(path):
    tok = open(path).read().split()
    w, h = int(tok[1]), int(tok[2])
    return np.array(tok[4:4 + 3 * w * h], dtype=np.uint8).reshape(h, w, 3)


fig, axs = plt.subplots(3, 4, figsize=(9, 7))
for j, s in enumerate(["dense", "sparse", "overlap", "clustered"]):
    for i, v in enumerate(["reference", "parallel", "optimized"]):
        axs[i, j].imshow(read_ppm(os.path.join(TMP, f"render_{s}_{v}.ppm")))
        axs[i, j].set_xticks([])
        axs[i, j].set_yticks([])
        axs[i, j].grid(False)
        if i == 0:
            axs[i, j].set_title(s)
        if j == 0:
            axs[i, j].set_ylabel({"reference": "serial reference", "parallel": "render_parallel",
                                  "optimized": "render_optimized"}[v])
fig.tight_layout()
fig.savefig(os.path.join(FIG, "images.png"), dpi=140)
plt.close(fig)


def box(ax, x, y, w, h, text, fc="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", fc=fc, ec="black"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8)


def arrow(ax, a, b, text=None):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=10, color="black", lw=1))
    if text:
        ax.text((a[0] + b[0]) / 2 + 0.08, (a[1] + b[1]) / 2 + 0.08, text, fontsize=7.5)


fig, ax = plt.subplots(figsize=(10, 4.6))
ax.set_xlim(0, 10)
ax.set_ylim(0, 5.2)
ax.axis("off")
box(ax, 0.2, 2.0, 1.9, 1.1, "Rank 0 (root)\nreads scene,\nsplits it into tiles")
box(ax, 2.8, 4.0, 2.4, 0.9, "1. MPI_Bcast\nW, H, tile size, N$_c$,\ncircle array (28 B each)")
box(ax, 2.8, 2.7, 2.4, 0.9, "2. MPI_Scatterv\ntile ids per rank\n(counts may differ)")
box(ax, 2.8, 1.4, 2.4, 0.9, "3. each rank renders\nits own tiles\n(Part 4 code)")
box(ax, 2.8, 0.1, 2.4, 0.9, "4. MPI_Gatherv\ntile pixels back to root\n(sizes may differ)")
for i in range(8):
    box(ax, 5.9 + i * 0.5, 2.2, 0.45, 0.7, f"P{i}")
ax.text(7.6, 1.75, "ranks P0 ... P7\n(P0 is the root)", fontsize=8)
arrow(ax, (2.1, 2.9), (2.8, 4.3))
arrow(ax, (2.1, 2.6), (2.8, 3.1))
arrow(ax, (5.2, 4.4), (6.3, 2.95), "same data to all")
arrow(ax, (5.2, 3.15), (7.0, 2.95), "different tile ids")
arrow(ax, (7.2, 2.15), (5.2, 0.7), "rendered tiles")
arrow(ax, (2.8, 0.6), (1.4, 2.0), "final image")
fig.tight_layout()
fig.savefig(os.path.join(FIG, "mpi_flow.png"), dpi=170)
plt.close(fig)

fig, ax = plt.subplots(figsize=(7.5, 2.6))
ax.axis("off")
sends = [(0, 4, 1), (0, 2, 2), (4, 6, 2), (0, 1, 3), (2, 3, 3), (4, 5, 3), (6, 7, 3)]
styles = {1: "-", 2: "--", 3: ":"}
for a, b, st in sends:
    ax.annotate("", xy=(b, 0.2), xytext=(a, 0.2),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.2, ls=styles[st],
                                connectionstyle=f"arc3,rad=-{0.15 + 0.1 * (3 - st)}"))
for r in range(8):
    ax.add_patch(plt.Circle((r, 0), 0.22, fc="white", ec="black"))
    ax.text(r, 0, f"P{r}", ha="center", va="center", fontsize=8)
for st, ls in styles.items():
    ax.plot([], [], color="black", ls=ls, label=f"step {st}")
ax.legend(loc="lower center", ncol=3, fontsize=8, bbox_to_anchor=(0.5, -0.4))
ax.set(xlim=(-0.5, 7.5), ylim=(-0.6, 2.0))
ax.set_aspect("equal")
fig.tight_layout()
fig.savefig(os.path.join(FIG, "binomial.png"), dpi=170)
plt.close(fig)


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
    down.append(("root", list(a)))
    d = m // 2
    while d >= 1:
        for i in range(0, m, 2 * d):
            t = a[i + d - 1]
            a[i + d - 1] = a[i + 2 * d - 1]
            a[i + 2 * d - 1] += t
        down.append((d, list(a)))
        d //= 2
    return up, down


# ================================================================== title and setup
para("Data-Parallel Algorithms and Parallel Circle Rendering", TITLE)
para("Parallel and Distributed Computing, Assignment 3: Combined Performance Report", SUB)
who = [os.environ.get(k, "") for k in ("REPORT_NAME", "REPORT_ROLL", "REPORT_SECTION")]
if any(who):
    table([["Name", who[0], "Roll number", who[1]], ["Section", who[2], "Date", "15 November 2026"]],
          widths=[2.6 * cm, 6 * cm, 2.8 * cm, 5 * cm], header=False, size=10)

para("Machine and measurement setup", H2)
table([["Item", "Value"],
       ["CPU", "AMD Ryzen 7 7435HS laptop processor, 8 cores, 16 hardware threads"],
       ["Operating system", "Windows 11 Home 10.0.26200"],
       ["Compiler", "GCC 15.2.0 (MinGW-w64), flags -O2 -std=c++17 -Wall -Wextra -fopenmp"],
       ["OpenMP runtime", "GNU libgomp from GCC 15.2.0, OpenMP 4.5 (_OPENMP = 201511)"],
       ["Statistic", "median of 7 timed runs (SAXPY, scan) or 5 runs (renderer), after 1 warm-up run"],
       ["Definitions", "T<sub>1</sub> = the parallel code run on 1 thread; S<sub>p</sub> = T<sub>1</sub>/T<sub>p</sub>; "
        "E<sub>p</sub> = S<sub>p</sub>/p. Output files are never included in timings. Every timing was preceded "
        "by a passing comparison with the serial reference."]],
      widths=[3.3 * cm, 13.7 * cm])
para("Thread counts 1, 2, 4 and 8 are all supported (16 logical processors), so none were skipped. This is a laptop, "
     "so a single thread probably runs at a higher clock than eight threads. This lowers all measured efficiencies "
     "somewhat. Raw program output is in the <font face='CUR'>results</font> folder of the submission.")

# ================================================================== PART 1
para("Part 1: SAXPY", H1)
para("Implementation", H2)
code("""#pragma omp parallel for schedule(static)
for (long long i = 0; i < n; ++i) op[i] = a * xp[i] + yp[i];""")
para("Each thread receives one contiguous block of indices, so every output element is written once, by one thread, "
     "and the output order is the input order. An empty array runs zero iterations.")
para("Correctness evidence", H2)
bullets(["Supplied demo: <font face='CUR'>SAXPY N=1000000 correctness=PASS</font>. It also passes for n = 0, 1, 7, 1000 "
         "and for n = 10 000 001 with 3 threads (not divisible by the thread count).",
         "Extra test (<font face='CUR'>tests/edge_tests.cpp</font>): n = 0, 1, 2, 3, 7, 13, 1001, 65537 at 1, 2, 3, 4, 7 and "
         "8 threads, compared exactly with <font face='CUR'>saxpy_serial</font>. Different input sizes must throw an "
         "exception. All pass.",
         "<font face='CUR'>saxpy_bench</font> checks every thread count before timing. All pass."])
para("Timing (input sizes 10<super>4</super>, 10<super>6</super>, 10<super>7</super>; threads 1, 2, 4, 8; median of 7)", H2)
table(bench_table(saxpy, ["n=10000", "n=1000000", "n=10000000"], ["saxpy"]), widths=BW)
figure(os.path.join(FIG, "saxpy.png"),
       "<b>Figure 1.</b> (a) Speedup of SAXPY for three sizes; the dotted line is ideal speedup. (b) Memory bandwidth reached "
       "by the loop alone (output already allocated). Graph (a) shows that SAXPY barely speeds up. Graph (b) shows why: "
       "bandwidth stops growing after about 4 threads.")
para("Analysis", H2)
para("<b>Minimum bytes per element.</b> In an ideal single pass, each element reads x<sub>i</sub> (4 B), reads y<sub>i</sub> "
     "(4 B) and writes z<sub>i</sub> (4 B). That is <b>12 bytes per element</b> for only 2 floating-point operations. "
     "For n = 10<super>7</super> this is 120 MB per call.")
para(f"<b>Why SAXPY is limited by memory bandwidth.</b> A core can do far more arithmetic than memory can feed it, so each "
     f"thread mostly waits for data. Extra cores only help until the memory system is saturated. The loop alone reaches "
     f"{kbw[1]:.1f}, {kbw[2]:.1f}, {kbw[4]:.1f} and {kbw[8]:.1f} GB/s at 1, 2, 4 and 8 threads (Figure 1b). Going from 4 to 8 "
     f"threads adds almost nothing. In addition, the output vector is allocated and zero-filled by one thread "
     f"before the parallel loop. This took {alloc_ms:.1f} ms in a separate measurement, about half of T<sub>1</sub> = "
     f"{ms(saxpy, 'n=10000000', 'saxpy', 1):.1f} ms. With half of the time serial, Amdahl's law limits the speedup "
     f"to about 2. The measured S<sub>8</sub> at n = 10<super>7</super> is "
     f"{sp(saxpy, 'n=10000000', 'saxpy', 8):.2f}.")
r4 = pick(saxpy, "n=10000", "saxpy", "parallel")
para(f"<b>A case where more threads reduce efficiency.</b> For n = 10<super>4</super>, the time increases from "
     f"{r4[0]['ms']*1000:.0f} µs on 1 thread to {r4[1]['ms']*1000:.0f} µs on 2 threads and {r4[3]['ms']*1000:.0f} µs on 8 threads. "
     f"Efficiency falls from 1.00 to {r4[1]['eff']:.2f} and then {r4[3]['eff']:.3f}. The arithmetic takes only a few "
     f"microseconds, while starting the threads and the barrier at the end of the loop cost more than that and grow with p.")

# ================================================================== PART 2
para("Part 2: Exclusive scan and repeated-index compaction", H1)
para("Implementation", H2)
para("<font face='CUR'>exclusive_scan_parallel</font> copies the input into a buffer padded with zeros to the next power of two, "
     "then runs the Blelloch scan in place. A single parallel region contains all levels of the tree. Each level is an "
     "<font face='CUR'>omp for</font> loop, and its implicit barrier makes sure that level d+1 starts only after level d is "
     "finished. Inside one level, each iteration touches its own pair of elements, so there are no data races.")
code("""for (d = 1; d < m; d *= 2)            // up-sweep
    #pragma omp for
    for (k = 0; k < m/(2*d); ++k) a[k*2*d + 2*d-1] += a[k*2*d + d-1];
#pragma omp single
a[m-1] = 0;                           // clear the root
for (d = m/2; d >= 1; d /= 2)         // down-sweep
    #pragma omp for
    for (k = 0; k < m/(2*d); ++k) { t = a[i+d-1]; a[i+d-1] = a[i+2*d-1]; a[i+2*d-1] += t; }""")
para("<font face='CUR'>find_repeats_parallel</font> has three steps. (1) A parallel loop sets flag[i] = 1 when "
     "A<sub>i</sub> = A<sub>i+1</sub>. (2) An exclusive scan of the flags gives every matching position its slot in the output. "
     "(3) A parallel loop writes i to out[offset[i]] for each flagged i. Every slot has exactly one writer and the "
     "offsets increase with i, so the result is in ascending order. Inputs shorter than 2 return an empty vector.")
para("Correctness evidence", H2)
lens = re.findall(r"SCAN N=(\d+) scan=PASS repeats=PASS", correct)
bullets([f"Supplied demo for lengths {', '.join(lens)}: scan=PASS and repeats=PASS for all.",
         "Extra tests: the two handout examples ([1,4,6,8,2] and [1,2,2,1,1,1,3,5,3,3]); random arrays of 14 different "
         "lengths from 0 to 100003 (including 7, 8, 9, 1023, 1024, 1025); negative values; an array with all values equal; "
         "an array with no repeats. Each is run at 1, 2, 3, 4, 7 and 8 threads. All pass.",
         "<font face='CUR'>scan_bench</font> checks both operations at every thread count before timing. All pass."])

para("Up-sweep and down-sweep for n = 16, input [1,2,3,4] repeated four times", H2)
up, down = blelloch_trace([1, 2, 3, 4] * 4)
rows = [["step"] + [str(i) for i in range(16)], ["input"] + [str(v) for v in [1, 2, 3, 4] * 4]]
rows += [[f"up-sweep d={d}"] + [str(v) for v in arr] for d, arr in up]
rows += [[("root set to 0" if d == "root" else f"down-sweep d={d}")] + [str(v) for v in arr] for d, arr in down]
table(rows, widths=[2.6 * cm] + [0.9 * cm] * 16, size=8)
para("In the up-sweep, level d adds the left element of each pair of blocks into the right one, so after the last level "
     "slot 15 holds the total, 40. The root is then set to 0. In the down-sweep, at each level the left child takes the "
     "parent's value and the right child takes the parent's value plus the old left value. The last row is the exclusive "
     "scan and matches the serial result.")

para("Work and span of a tree-based scan", H2)
para("For m = 2<super>k</super> elements, the up-sweep does m/2 + m/4 + ... + 1 = m − 1 additions and the down-sweep does "
     "another m − 1. So the total <b>work is 2(m − 1) = O(m)</b>, the same order as the serial scan (m − 1 additions) but about "
     "twice as many operations. Each sweep has log<sub>2</sub> m levels that depend on each other, while all operations inside "
     "a level are independent. So the <b>span (depth) is 2 log<sub>2</sub> m = O(log m)</b>. Brent's bound gives "
     "T<sub>p</sub> ≤ W/p + D.")
para("<b>Effect of synchronization.</b> Each level ends with a barrier, so the runtime is roughly "
     "T<sub>p</sub> ≈ (2m·c)/p + 2 log<sub>2</sub>m · t<sub>barrier</sub>(p), where c is the cost per element and "
     "t<sub>barrier</sub> grows with p. The barrier term is small for large m but dominates for small m. The top levels "
     "also have fewer than p pairs, so some threads wait idle there.")

para("Padding for n = 1025", H2)
para("<b>Strategy:</b> copy the 1025 values into a buffer of size 2048 (the next power of two) and set elements 1025 to 2047 to "
     "0. Zero is the identity for addition, and the padding is only after the real data, so the prefix sums for indices 0 to "
     "1024 are unchanged. The padded tail is discarded afterwards. <b>Overhead: 2048 − 1025 = 1023 extra elements</b>, "
     "almost doubling the storage and tree work. This is the worst case, just above a power of two.")

para("Serial and parallel timing at two sizes (n = 10<super>5</super> and 10<super>7</super>; median of 7)", H2)
table(bench_table(scan, ["n=100000", "n=10000000"], ["scan", "repeats"]), widths=BW, size=8.5)
figure(os.path.join(FIG, "scan.png"),
       "<b>Figure 2.</b> Median time (log scale) of the parallel scan and repeat compaction against thread count. Dashed lines "
       "are the serial times. The graph shows that for n = 10<super>5</super> the parallel code gets slower as threads are "
       "added, and that for n = 10<super>7</super> it speeds up until 4 threads but never reaches the serial time.")
para(f"<b>Does the measurement agree with the work and depth analysis?</b> Partly. At n = 10<super>5</super> the serial scan "
     f"takes {ms(scan,'n=100000','scan',1,'serial')*1000:.0f} µs, but the parallel scan takes "
     f"{ms(scan,'n=100000','scan',1)*1000:.0f} µs with 1 thread and {ms(scan,'n=100000','scan',8)*1000:.0f} µs with 8. There "
     f"is little work and 2 log<sub>2</sub>(131072) = 34 barriers, so the depth and synchronization term dominates, as the model "
     f"predicts. At n = 10<super>7</super> the work term dominates, and the time falls from "
     f"{ms(scan,'n=10000000','scan',1):.0f} ms (p = 1) to {ms(scan,'n=10000000','scan',4):.0f} ms (p = 4), then stops "
     f"improving. This agrees with W/p until memory bandwidth becomes the limit, as in Part 1. The parallel scan still never beats the serial "
     f"scan ({ms(scan,'n=10000000','scan',1,'serial'):.0f} ms), because (i) it does about twice the additions, (ii) padding "
     f"10<super>7</super> to 2<super>24</super> adds 68% more elements, and (iii) the tree passes access memory with large "
     f"strides, so they miss the cache, while the serial scan reads sequentially. Even the one-thread parallel scan is about "
     f"{ms(scan,'n=10000000','scan',1)/ms(scan,'n=10000000','scan',1,'serial'):.0f} times slower than the serial scan. "
     f"So the O(log n) depth cannot pay for the extra constant work with p ≤ 8. This is a measured result for this machine "
     f"and these sizes.")

# ================================================================== PART 3
para("Part 3: Correct parallel circle rendering", H1)
para("Implementation", H2)
code("""#pragma omp parallel for schedule(runtime)
for (int y = 0; y < height; ++y)
    for (int x = 0; x < width; ++x) {
        Pixel p = px[y*width + x];
        for (int k = 0; k < nc; ++k)          // circles in input order
            if (covers(cs[k], x, y, width, height)) blend(p, cs[k]);
        px[y*width + x] = p;
    }""")
para("The image rows are shared between threads, so every pixel has exactly one owner and no pixel is written by two threads. "
     "For each pixel, circles are applied in their original order with the unchanged <font face='CUR'>covers()</font> and "
     "<font face='CUR'>blend()</font>. The reference only nests the loops the other way round, so each pixel gets the same "
     "operations in the same order. <font face='CUR'>schedule(runtime)</font> lets the schedule be chosen with "
     "<font face='CUR'>OMP_SCHEDULE</font> in Part 4.")
para("Correctness evidence", H2)
demo = [l for l in correct.splitlines() if l.startswith("RENDER")]
table([["scene (512×512)", "variant", "circles", "comparison with reference"]] +
      [[re.search(r"scene=(\w+)", l).group(1), re.search(r"variant=(\w+)", l).group(1),
        re.search(r"circles=(\d+)", l).group(1), "PASS" if "PASS" in l else "FAIL"] for l in demo],
      widths=[3.5 * cm, 3 * cm, 2.5 * cm, 5 * cm])
para("Extra tests (1, 2, 3, 4, 7 and 8 threads, for both renderers, all pass): an empty scene (image stays white), a 1×1 image, "
     "a 37×113 image, circles partly or fully outside the image, a circle of radius 0, circle edges exactly on pixel "
     "centres, every scene at 200×200, and the A/B order example below. Overlapping circles are covered by the "
     "<i>overlap</i> and <i>dense</i> scenes. A scene where most pixels are empty is covered by <i>sparse</i>.")
figure(os.path.join(FIG, "images.png"),
       "<b>Figure 3.</b> Output images (512×512, shown for four scenes). Rows: serial reference, <font face='CUR'>render_parallel</font>, "
       "<font face='CUR'>render_optimized</font>. The three rows look identical, which matches the PASS results in the table above.",
       w=14)

para("Order of blending: A = (1,0,0,0.5) and B = (0,0,1,0.5) over a white pixel", H2)
table([["order", "after the first circle", "after the second circle (final RGB)"],
       ["A then B", "0.5·(1,0,0) + 0.5·(1,1,1) = (1, 0.5, 0.5)",
        "0.5·(0,0,1) + 0.5·(1,0.5,0.5) = <b>(0.5, 0.25, 0.75)</b>"],
       ["B then A", "0.5·(0,0,1) + 0.5·(1,1,1) = (0.5, 0.5, 1)",
        "0.5·(1,0,0) + 0.5·(0.5,0.5,1) = <b>(0.75, 0.25, 0.5)</b>"]],
      widths=[2.3 * cm, 6.5 * cm, 8.2 * cm])
para("The results differ because P<sub>new</sub> = αC + (1−α)P<sub>old</sub> is not commutative. The circle blended last has "
     "weight α = 0.5, but the circle blended first is scaled down again by the second blend and only has weight "
     "α(1−α) = 0.25. So the order decides whether red or blue is stronger. Green is 0.25 in both cases because only the "
     "white background contributes, twice scaled by (1−α) = 0.5. A parallel renderer must therefore keep the blending order of every pixel.")

para("A race when two threads blend different circles into the same pixel", H2)
table([["time", "thread 1 (circle A)", "thread 2 (circle B)", "pixel in memory"],
       ["1", "reads pixel (1,1,1)", "", "(1,1,1)"],
       ["2", "", "reads pixel (1,1,1)", "(1,1,1)"],
       ["3", "computes (1, 0.5, 0.5)", "computes (0.5, 0.5, 1)", "(1,1,1)"],
       ["4", "writes (1, 0.5, 0.5)", "", "(1, 0.5, 0.5)"],
       ["5", "", "writes (0.5, 0.5, 1)", "<b>(0.5, 0.5, 1)</b>"]],
      widths=[1.5 * cm, 5.3 * cm, 5.3 * cm, 4.9 * cm])
para("Both threads read the old pixel before either one writes, so the update of thread 1 is lost. The final value "
     "(0.5, 0.5, 1) is neither of the two correct answers, (0.5, 0.25, 0.75) or (0.75, 0.25, 0.5).")

para("Circle-parallel and pixel-parallel decomposition", H2)
bullets(["<b>Circle-parallel</b> (threads take different circles): two things must hold for every pixel. The update must be "
         "atomic, and circle i must be blended before circle j when i &lt; j. A critical section gives only the first "
         "property. It makes updates exclusive, but the order of entering is decided by timing, so the image is "
         "still wrong or changes from run to run. Forcing the order would make threads wait for each other.",
         "<b>Why a critical section around each pixel update performs poorly:</b> one blend is only a few arithmetic operations, "
         "while an <font face='CUR'>omp critical</font> is a single lock shared by all threads. Every covered pixel would "
         "need the lock, so the threads queue up behind it and the work becomes almost serial, with extra locking cost on "
         "top. Per-pixel locks reduce the waiting but add memory and atomic operations to every blend, and they still do "
         "not fix the order.",
         "<b>Pixel-parallel</b> (used here): each pixel has one owner who applies the circles in input order. The only "
         "requirement is that owners do not overlap, which a loop over rows or tiles guarantees. The circle list is shared "
         "read-only, so it needs no synchronization. The cost is that each thread tests every circle for its pixels, "
         "which Part 4 reduces."])
para("Pixels per worker for a 1024×1024 image with p = 8", H2)
para("1024 × 1024 = 1 048 576 pixels, and 1 048 576 / 8 = <b>131 072 pixels per worker</b> (128 rows). The work is still uneven "
     "because the cost of a pixel depends on how many circles cover it, and circles are often concentrated in some regions. "
     "In the <i>clustered</i> scene, rows through the two hot spots do many more blends than empty rows. Other causes are "
     "two threads sharing one core (SMT), different clock speeds across cores, and interruptions by the operating system.")

# ================================================================== PART 4
para("Part 4: Renderer optimization and performance investigation", H1)
para("Chosen optimization: tiles with bounding-box culling", H2)
para("<font face='CUR'>render_optimized</font> first computes the pixel bounding box of every circle once. The box is made one pixel "
     "larger on every side, so rounding can never exclude a covered pixel, and it is only a filter: "
     "<font face='CUR'>covers()</font> still decides coverage. The image is then cut into 32×32 tiles and each tile "
     "is owned by one thread (<font face='CUR'>schedule(runtime)</font> over the tiles). The owner goes through the circles in "
     "<b>original input order</b>, skips every circle whose box does not touch the tile, and blends the others only inside the "
     "overlap of the box and the tile. Circles are never sorted.")
para("<b>Why this choice.</b> Culling alone would not give a parallel decomposition. Tiles give one owner per pixel (no "
     "race, no locks), and going through the circles in order inside a tile keeps the blending order of every pixel. "
     "The candidate list is produced while looping, so no lists need to be built or stored. A 32×32 tile gives 256 tiles at "
     "512×512 (32 per thread at p = 8), which is enough for load balancing, and the 128 000 box tests per frame are few "
     "compared with the 131 million tests of the baseline on <i>clustered</i>.")
para("Reproducible commands", H2)
code("""make
for s in dense sparse overlap clustered; do
    ./render_demo 512 $s parallel; ./render_demo 512 $s optimized; done
OMP_SCHEDULE="static"    ./render_bench 512 5 1,2,4,8 sparse,overlap,clustered,dense
OMP_SCHEDULE="dynamic,1" ./render_bench 512 5 1,2,4,8 sparse,overlap,clustered,dense
OMP_SCHEDULE="dynamic,8" ./render_bench 512 5 1,2,4,8 sparse,overlap,clustered
./analysis_probe""")
para("Correctness: all images match the reference (Part 3 table and Figure 3). <font face='CUR'>render_bench</font> compares every "
     "image with the reference before it records a time, and no comparison failed.")
para("Performance: baseline and optimized (512×512, OMP_SCHEDULE = dynamic,1, median of 5 runs)", H2)
table(bench_table(r_dyn1, [f"{s}_512" for s in SCENES], ["reference", "baseline", "optimized"]),
      widths=[2.4 * cm, 1.9 * cm, 1.6 * cm, 1.4 * cm, 2.0 * cm, 2.4 * cm, 2.2 * cm, 2.1 * cm], size=8)
para("<i>sparse</i>: 300 small circles, most pixels empty. <i>overlap</i>: 150 large low-opacity circles that overlap heavily in "
     "the middle. <i>clustered</i>: 500 small circles, most of them in two hot spots (uneven work). <i>dense</i>: 40 circles on a "
     "grid. T<sub>1</sub> is the one-thread time of the same renderer, so speedup compares each renderer with itself. The "
     "last column compares with the serial reference.")
figure(os.path.join(FIG, "render.png"),
       "<b>Figure 4.</b> Median render time (log scale) against thread count, for the baseline and the optimized renderer; the dashed "
       "line is the serial reference. The graph shows that culling saves one to two orders of magnitude on <i>sparse</i> and "
       "<i>clustered</i> but much less on <i>overlap</i>, and that the optimized renderer scales worse because little parallel work is left.")

para("Static and dynamic schedules", H2)
srows = [["scene / renderer", "p", "static (ms)", "dynamic,1 (ms)", "dynamic,8 (ms)", "fastest"]]
for s in ("sparse", "overlap", "clustered"):
    for v in ("baseline", "optimized"):
        for p in (4, 8):
            vals = [rms(rows_, s, v, p) for rows_ in (r_stat, r_dyn1, r_dyn8)]
            srows.append([f"{s} / {v}", p] + [f"{x:.3f}" for x in vals] +
                         [["static", "dynamic,1", "dynamic,8"][vals.index(min(vals))]])
table(srows, widths=[4.3 * cm, 1 * cm, 2.6 * cm, 2.8 * cm, 2.8 * cm, 2.5 * cm])
figure(os.path.join(FIG, "sched.png"),
       "<b>Figure 5.</b> Median time at p = 8 for the three schedules. The graph shows that the schedule matters most for the "
       "optimized renderer on <i>clustered</i>, where work per tile is very uneven.", w=14)
share = float(W["clustered"][6])
para(f"<b>Trade-off.</b> <i>static</i> has no scheduling cost, but it gives each thread one fixed block, so the thread whose block "
     f"contains a hot spot finishes last. For the optimized renderer on <i>clustered</i>, the busiest of 8 static blocks holds "
     f"{share*100:.0f}% of all work (a perfect share is 12.5%). At p = 8 it takes {rms(r_stat,'clustered','optimized',8):.2f} ms "
     f"with static and {rms(r_dyn1,'clustered','optimized',8):.2f} ms with dynamic,1. <i>dynamic,1</i> hands out one tile at a "
     f"time, which costs one shared-counter update per tile but lets idle threads take more work. <i>dynamic,8</i> has less "
     f"scheduling cost but coarser balance, and lands in between ({rms(r_dyn8,'clustered','optimized',8):.2f} ms). Smaller tiles "
     f"balance better but increase the number of box tests and scheduling operations; larger tiles do the opposite. For the "
     f"baseline, every row costs about the same, so the schedules differ little, apart from "
     f"<i>clustered</i> at p = 8 ({rms(r_stat,'clustered','baseline',8):.1f} ms static, {rms(r_dyn1,'clustered','baseline',8):.1f} ms "
     f"dynamic,1), where hot-spot rows do more blending. For <i>sparse</i> the schedule hardly matters, because the loop is not "
     f"the bottleneck (see below).")

para("Work model", H2)
para("Let N<sub>c</sub> = number of circles, W×H = image size, t<sub>c</sub> = cost of one <font face='CUR'>covers()</font> test, "
     "t<sub>b</sub> = cost of one blend, B = number of blends (fixed by the scene), A<sub>k</sub> = clipped box area of circle k, "
     "and t<sub>init</sub> = cost per pixel of creating the white image (done by one thread).")
bullets(["<b>Baseline:</b> T ≈ (N<sub>c</sub>·W·H·t<sub>c</sub> + B·t<sub>b</sub>)/p + W·H·t<sub>init</sub>, which is O(N<sub>c</sub>WH).",
         "<b>Optimized:</b> T ≈ (N<sub>c</sub>·t<sub>box</sub> + N<sub>tiles</sub>·N<sub>c</sub>·t<sub>test</sub> + "
         "Σ<sub>k</sub> A<sub>k</sub>·t<sub>c</sub> + B·t<sub>b</sub>)/p<sub>eff</sub> + W·H·t<sub>init</sub>. Here p<sub>eff</sub> ≤ p "
         "because of uneven tiles, and t<sub>box</sub>, t<sub>test</sub> are the costs of computing a box and of one tile-box test."])
table([["scene", "N<sub>c</sub>", "baseline tests N<sub>c</sub>WH", "tile-box tests", "optimized covers tests ΣA<sub>k</sub>",
        "test reduction", "busiest tile / mean tile", "measured T<sub>1</sub> baseline / optimized"]] +
      [[s, W[s][0], f"{int(W[s][1]):,}", f"{int(W[s][2]):,}", f"{int(W[s][3]):,}", W[s][4], W[s][5],
        f"{rms(r_dyn1, s, 'baseline', 1) / rms(r_dyn1, s, 'optimized', 1):.1f}×"] for s in SCENES],
      widths=[1.8 * cm, 1.1 * cm, 2.6 * cm, 2.0 * cm, 2.6 * cm, 1.9 * cm, 2.2 * cm, 2.8 * cm], size=8)
para(f"The counts come from <font face='CUR'>analysis_probe</font> (512×512, 32×32 tiles). On <i>sparse</i> the tests fall by "
     f"{W['sparse'][4]}, but the measured one-thread gain is only "
     f"{rms(r_dyn1,'sparse','baseline',1)/rms(r_dyn1,'sparse','optimized',1):.0f}×, because the rest of the time is the serial creation "
     f"of the white image ({img_ms:.2f} ms measured). On <i>overlap</i> the tests fall by only {W['overlap'][4]}, and blends cannot be "
     f"skipped, so the gain is {rms(r_dyn1,'overlap','baseline',1)/rms(r_dyn1,'overlap','optimized',1):.1f}×.")
para("<b>When the optimization can lose.</b> It loses when preprocessing costs more than the tests it removes, that is, when "
     "N<sub>c</sub>·t<sub>box</sub> + N<sub>tiles</sub>·N<sub>c</sub>·t<sub>test</sub> is larger than "
     "(N<sub>c</sub>·W·H − ΣA<sub>k</sub>)·t<sub>c</sub>. This happens when almost every circle covers the whole image (so "
     "A<sub>k</sub> ≈ WH and nothing is saved), or when there are very many tiny circles on a small image. Also, in a tile the "
     "pixels are loaded and stored once per circle, while the baseline keeps a pixel in a register, so an image covered by "
     "all circles could be slightly slower. This is a prediction from the model. None of the provided scenes shows it, and it was "
     "not measured.")

para("Strongest bottleneck in each scene", H2)
bullets([f"<b>sparse:</b> the serial creation of the 512×512 white image ({img_ms:.2f} ms) is about "
         f"{img_ms / rms(r_dyn1,'sparse','optimized',8)*100:.0f}% of the {rms(r_dyn1,'sparse','optimized',8):.2f} ms 8-thread "
         f"time of the optimized renderer (Amdahl's law, not scheduling). For the baseline it is the 78.6 million "
         f"<font face='CUR'>covers()</font> tests, which scale to {sp(r_dyn1,'sparse_512','baseline',8):.1f}× at p = 8.",
         f"<b>overlap:</b> blending itself. About 10 million tests remain after culling and most of them blend. Of the four scenes, "
         f"the optimized renderer scales best here ({sp(r_dyn1,'overlap_512','optimized',8):.1f}× at p = 8). The remaining loss comes from the "
         f"central tiles having {W['overlap'][5]} times the mean work, and probably from the lower all-core clock speed.",
         f"<b>clustered:</b> load imbalance. The busiest tile has {W['clustered'][5]} times the mean work, and with static scheduling "
         f"one block holds {share*100:.0f}% of the work. Dynamic scheduling fixes most of this; after that the serial "
         f"image creation limits the speedup (S<sub>8</sub> = {sp(r_dyn1,'clustered_512','optimized',8):.2f}).",
         f"<b>dense:</b> little work remains (about 0.6 million tests), so at p = 8 the serial image creation ({img_ms:.2f} ms) and "
         f"the thread start and barrier take most of the {rms(r_dyn1,'dense','optimized',8):.2f} ms."])

# ================================================================== PART 5
story.append(CondPageBreak(9 * cm))
para("Part 5: MPI collectives and communication-cost reasoning", H1)
para("Data-flow design", H2)
figure(os.path.join(FIG, "mpi_flow.png"),
       "<b>Figure 6.</b> Network and data-flow diagram for p = 8 processes: broadcast the scene, scatter the tile ownership, "
       "render locally, gather the tile pixels at the root.", w=15)
bullets(["<b>MPI_Bcast (scene metadata).</b> The root broadcasts the image size, the tile size, N<sub>c</sub> and the circle array "
         "(7 floats = 28 bytes per circle, in input order). All ranks need the same read-only data.",
         "<b>MPI_Scatter or MPI_Scatterv (tile ownership).</b> The root sends each rank the list of tile ids it owns. "
         "<b>MPI_Scatterv</b> is needed when ranks receive different counts: when the number of tiles is not divisible by p "
         "(e.g. 256 tiles on 6 ranks gives 43 or 42), or when tiles are assigned by cost so that some ranks get fewer tiles.",
         "<b>MPI_Gather or MPI_Gatherv (final image).</b> Each rank sends back the pixels of its tiles. "
         "<b>MPI_Gatherv</b> is needed when the byte counts differ: edge tiles are smaller when the image size is not a "
         "multiple of the tile size, and ranks may own different numbers of tiles. The root uses a displacement array to place "
         "each block. Fixed-count MPI_Gather works only when every rank sends the same amount."])
para("Broadcast time under T(m) = α + βm", H2)
para("<b>Assumptions:</b> a process sends or receives one message at a time; links are full-duplex and different pairs do not "
     "disturb each other; a process forwards a message only after receiving all m bytes (no pipelining); α and β are the "
     "same for all pairs.")
bullets(["<b>(i) Linear:</b> the root sends to the other p − 1 processes one after another, so "
         "<b>T<sub>linear</sub> = (p − 1)(α + βm)</b>.",
         "<b>(ii) Binomial tree:</b> in every step each process that has the data sends it to one that does not, so the number of "
         "holders doubles (1, 2, 4, 8 in Figure 7). Then <b>T<sub>binomial</sub> = log<sub>2</sub>p · (α + βm)</b>, which is "
         "3(α + βm) for p = 8."])
figure(os.path.join(FIG, "binomial.png"),
       "<b>Figure 7.</b> Binomial-tree broadcast for p = 8. Step 1: P0 to P4. Step 2: P0 to P2 and P4 to P6. Step 3: P0 to P1, "
       "P2 to P3, P4 to P5, P6 to P7.", w=13)
para("Numbers for p = 8, m = 2<super>20</super> bytes, α = 10 µs, β = 1 ns/byte", H2)
table([["quantity", "calculation", "result"],
       ["βm", "2<super>20</super> B × 1 ns/B = 1 048 576 ns", "1048.576 µs"],
       ["α + βm", "10 µs + 1048.576 µs", "1058.576 µs"],
       ["T<sub>linear</sub>", "(8 − 1) × 1058.576 µs", "<b>7410.032 µs ≈ 7.41 ms</b>"],
       ["T<sub>binomial</sub>", "log<sub>2</sub>8 = 3, so 3 × 1058.576 µs", "<b>3175.728 µs ≈ 3.18 ms</b>"]],
      widths=[3.4 * cm, 8 * cm, 5.6 * cm])
para("The binomial tree is 7410.032 / 3175.728 = 2.33 times faster. For this large m, βm is about 100 times larger than α, so "
     "the transfer time dominates both schemes.")
para("Broadcast steps for p = 16", H2)
table([["topology", "routing assumption", "steps"],
       ["ring (bidirectional)", "neighbour-only store-and-forward; data goes both ways round the ring", "(p − 1)/2 rounded up = <b>8</b> (15 if one-way)"],
       ["2D mesh 4×4", "root in a corner; first along its row, then down every column; neighbour-only links", "3 + 3 = <b>6</b> (4 from a central root)"],
       ["hypercube (d = 4)", "in step i, send across dimension i; every send uses a direct link", "log<sub>2</sub>16 = <b>4</b>"]],
      widths=[3.4 * cm, 9 * cm, 4.6 * cm])
para("Step count alone does not predict time, because: (1) each step costs α + βm, so for large m the transfer size matters "
     "more than the number of steps, and a pipelined ring can beat a 4-step hypercube broadcast; (2) with cut-through routing "
     "a message over several hops costs little more than over one hop; (3) links can be shared, which causes contention; "
     "(4) injection bandwidth and software cost (part of α) differ between machines; (5) a step cannot start until its sender "
     "has arrived.")
para("Load balance for tile times [2, 2, 3, 3, 3, 4, 5, 18] ms on 8 processes", H2)
table([["quantity", "calculation", "result"],
       ["total work", "2+2+3+3+3+4+5+18", "40 ms"],
       ["ideal balanced makespan (lower bound)", "40 / 8", "<b>5 ms</b>"],
       ["actual makespan, one tile per process", "largest tile", "<b>18 ms</b>"],
       ["efficiency, ignoring communication", "40 / (8 × 18)", "<b>0.278 (27.8%)</b>"]],
      widths=[6 * cm, 5 * cm, 6 * cm])
para("<b>Recommended change:</b> split the 18 ms tile into 4 pieces of 4.5 ms (pixels are independent, so this is safe) and "
     "give the largest pieces out first. The 11 pieces are 5, 4.5, 4.5, 4.5, 4.5, 4, 3, 3, 3, 2, 2. The first eight go one per "
     "rank. The remaining 3, 2 and 2 go to the least loaded ranks: a 3 ms rank gets the 3 (total 6), the other 3 ms rank gets "
     "a 2 (total 5), and the 4 ms rank gets the last 2 (total 6). The makespan falls from 18 ms to <b>6 ms</b> and the "
     "efficiency rises to 40 / (8 × 6) = <b>0.83</b>.")
para("<b>Communication cost of this change.</b> The scene broadcast does not change. The scatter must use MPI_Scatterv because the "
     "counts differ (or, with a work queue, one request and one reply of about 2α = 20 µs per work item). The gather has 11 "
     "blocks instead of 8, which adds about 3α = 30 µs of latency, and the root must reassemble the split tile. The total pixel "
     "data is unchanged. A few tens of microseconds is small compared with the 12 ms saved.")

para("Summary", H2)
para("All parallel functions pass the supplied comparisons and the extra tests. SAXPY is limited by memory bandwidth and a serial "
     "allocation. The tree scan has O(n) work and O(log n) depth, but on this machine it is slower than the serial scan. "
     "Pixel-parallel rendering is correct without any locks. Tiled culling makes the renderer much faster on sparse and "
     "clustered scenes, and afterwards the speedup is limited by load imbalance (clustered) and by the serial image creation "
     "(sparse, dense).")


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("TNR", 9)
    canvas.drawCentredString(A4[0] / 2, 1.1 * cm, f"{doc.page}")
    canvas.restoreState()


SimpleDocTemplate(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                  bottomMargin=1.8 * cm, title="PDC Assignment 3 Report", author="").build(
    story, onFirstPage=footer, onLaterPages=footer)
print("wrote", OUT)
