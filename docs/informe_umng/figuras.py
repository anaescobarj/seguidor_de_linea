"""Figuras y datos de simulación para el informe en formato UMNG.

    python docs/informe_umng/figuras.py   -> docs/informe_umng/fig/*.png y resultados.txt
"""
import math
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.dirname(HERE)
ROOT = os.path.dirname(DOCS)
sys.path.insert(0, DOCS)
sys.path.insert(0, os.path.join(ROOT, "app"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import generar_pistas as gp  # noqa: E402
import generar_pistas_pliegos as gpp  # noqa: E402
from simulator import SimRobot  # noqa: E402

FIG = os.path.join(HERE, "fig")
os.makedirs(FIG, exist_ok=True)


def run(d, seconds):
    r = SimRobot(1)
    w = r.world
    w.track = list(d["pts"])
    w.cum = [0.0]
    for i in range(1, len(w.track) + 1):
        w.cum.append(w.cum[-1] + math.dist(w.track[i - 1], w.track[i % len(w.track)]))
    w.length = w.cum[-1]
    w.section_colors = d["colores"]
    w.obstacles = [(*gp.point_at(d, s), gp.OBST_R) for s in d["obst"]]
    (x0, y0), (x1, y1) = w.track[0], w.track[5]
    r.x, r.y, r.theta = x0, y0, math.atan2(y1 - y0, x1 - x0)
    r.trail = []
    r.handle("/api/mode", {"m": ["auto"]})
    n = len(w.track)
    last, prog, maxoff, t_lap, trail = 0, 0, 0.0, None, []
    while r.t < seconds:
        r.step()
        i, off = w.nearest(r.x, r.y)
        maxoff = max(maxoff, off)
        prog += (i - last + n // 2) % n - n // 2
        last = i
        if t_lap is None:
            trail.append((r.x, r.y))
            if prog >= n:
                t_lap = r.t
    return dict(t_lap=t_lap, laps=prog / n, avoided=r.obstacles_avoided, coll=r.collisions,
                maxoff=maxoff, changes=r.color_changes, trail=trail, dist=r.distance_m)


def main():
    designs = [gpp.build(p, i) for i, p in enumerate(gpp.PISTAS)]
    res = [run(d, 300) for d in designs]
    fig, axs = plt.subplots(2, 2, figsize=(7.2, 6.2))
    for ax, d, r in zip(axs.flat, designs, res):
        pts, n = d["pts"], len(d["pts"])
        for k, c in enumerate(d["colores"]):
            i0, i1 = int(k * d["seg"] / d["step"]), int((k + 1) * d["seg"] / d["step"])
            idx = [i % n for i in range(i0, i1 + 1)]
            ax.plot([pts[i][0] * 100 for i in idx], [pts[i][1] * 100 for i in idx], color=gp.HEX[c], lw=6,
                    solid_capstyle="butt")
        ax.plot([p[0] * 100 for p in pts], [p[1] * 100 for p in pts], color="k", lw=0.5)
        for s in d["obst"]:
            x, y = gp.point_at(d, s)
            ax.plot(x * 100, y * 100, "^", color="#ea580c", ms=7, mec="k", mew=0.5)
        ax.plot([p[0] * 100 for p in r["trail"]], [p[1] * 100 for p in r["trail"]], color="#7c3aed", lw=0.9,
                ls="--")
        cols, rows, pw, ph = d["grid"]
        for c in range(1, cols):
            ax.axvline(c * pw * 100, color="#0f766e", lw=0.6, ls=":")
        for rr in range(1, rows):
            ax.axhline(rr * ph * 100, color="#0f766e", lw=0.6, ls=":")
        ax.set_xlim(-45, d["W"] * 100 + 45); ax.set_ylim(-45, d["H"] * 100 + 45)
        ax.add_patch(plt.Rectangle((0, 0), d["W"] * 100, d["H"] * 100, fill=False, ec="0.4", lw=0.8))
        ax.set_aspect("equal")
        ax.tick_params(labelsize=6)
        ax.set_title(f"{d['cfg']['nombre']} ({cols * rows} pliego{'s' if cols * rows > 1 else ''})", fontsize=8)
        ax.set_xlabel("x [cm]", fontsize=7); ax.set_ylabel("y [cm]", fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "simulacion_pliegos.png"), dpi=220)
    plt.close(fig)
    with open(os.path.join(HERE, "resultados.txt"), "w") as f:
        for d, r in zip(designs, res):
            line = (f"{d['cfg']['nombre']}|{d['W'] * 100:.0f}x{d['H'] * 100:.0f}|{d['L']:.2f}|"
                    f"{d['rmin'] * 100:.0f}|{len(d['obst'])}|{r['t_lap']:.0f}|{r['laps']:.1f}|"
                    f"{r['avoided']}|{r['coll']}|{r['maxoff'] * 100:.0f}|{r['changes']}")
            print(line)
            f.write(line + "\n")
    # figuras existentes del proyecto
    for src in ["img/arquitectura_general.png", "img/maquina_estados.png", "img/esquematico.png",
                "img/esquematico_esp32.png", "img/plano_lateral.png", "img/app_dashboard.png",
                "img/bloque_termico.png", "img/bloque_obstaculos.png", "img/bloque_color.png"]:
        shutil.copy(os.path.join(DOCS, src), FIG)
    shutil.copy(os.path.join(ROOT, "hardware/cad/render_iso.png"), FIG)
    # copia del firmware para el anexo: se acortan las líneas decorativas de comentarios
    import re
    src = open(os.path.join(ROOT, "firmware/robot_esp32/robot_esp32.ino"), encoding="utf-8").read()
    src = re.sub(r"(//\s*)[-=]{20,}", lambda m: m.group(1) + "-" * 40, src)
    open(os.path.join(FIG, "anexo_robot_esp32.ino"), "w", encoding="utf-8").write(src)


if __name__ == "__main__":
    main()
