"""Pistas para dibujar sobre pliegos de 70 x 100 cm (carro de 2 motores, ~20 cm).

    python docs/generar_pistas_pliegos.py
      -> docs/pistas/Pistas_en_Pliegos.pdf
      -> docs/pistas/pliegos_*.csv

Diseño: solo la línea guía (19 mm) sobre una franja de color de 16 cm; no hace falta una
carretera ancha porque el carro sigue la línea. Curvas de radio >= 20 cm (2 motores giran
cerrado), conos a >= 70 cm entre sí y a >= 12 cm de un cambio de color.

    Práctica : 1 pliego  (100 x 70)   óvalo, 3 colores, 1 cono
    Nivel 1  : 2 pliegos (140 x 100)  4 conos, 3 colores
    Nivel 2  : 4 pliegos (200 x 140)  6 conos, 4 colores
    Nivel 3  : 6 pliegos (210 x 200)  8 conos, 6 colores

Cada pista se valida en el gemelo digital (vuelta completa sin colisiones).
"""
from __future__ import annotations

import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generar_pistas as gp  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

gp.ROAD_W = 0.16
gp.MARGIN = 0.02
gp.MIN_OBST_GAP = 0.70
gp.MIN_BOUNDARY = 0.12
gp.ROAD_LABEL = "Franja de color"


def stadium(R, S, n=4000):
    """Óvalo de pista atlética: dos rectas de largo S y dos semicírculos de radio R."""
    L = 2 * math.pi * R + 2 * S
    pts = []
    for i in range(n):
        s = L * i / n
        if s < S:
            pts.append((-S / 2 + s, -R))
        elif s < S + math.pi * R:
            a = -math.pi / 2 + (s - S) / R
            pts.append((S / 2 + R * math.cos(a), R * math.sin(a)))
        elif s < 2 * S + math.pi * R:
            pts.append((S / 2 - (s - S - math.pi * R), R))
        else:
            a = math.pi / 2 + (s - 2 * S - math.pi * R) / R
            pts.append((-S / 2 + R * math.cos(a), R * math.sin(a)))
    return pts


def fit(pts, w, h):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    k = min(w / (max(xs) - min(xs)), h / (max(ys) - min(ys)))
    return [(x * k, y * k) for x, y in pts]


def stretch(pts, sx):
    return [(x * sx, y) for x, y in pts]


EDGE = gp.ROAD_W / 2 + gp.MARGIN       # distancia mínima de la línea al borde del papel

PISTAS = [
    dict(key="practica", nombre="Práctica · Óvalo", obstaculos=0, colores=["rojo", "verde", "azul"],
         grid=(1, 1, 1.00, 0.70), curva=stadium(0.20, 0.40)),
    dict(key="nivel1", nombre="Nivel 1 · Frijol", obstaculos=4, colores=["rojo", "verde", "azul"],
         grid=(2, 1, 0.70, 1.00),
         curva=fit(gp.raw_curve("frijol", (1.0, 0.66, 0.06)), 1.40 - 2 * EDGE, 1.00 - 2 * EDGE)),
    dict(key="nivel2", nombre="Nivel 2 · Estrella", obstaculos=6, colores=["rojo", "amarillo", "verde", "azul"],
         grid=(2, 2, 1.00, 0.70),
         curva=fit(stretch(gp.raw_curve("estrella", (1.0, 0.05)), 1.4), 2.00 - 2 * EDGE, 1.40 - 2 * EDGE)),
    dict(key="nivel3", nombre="Nivel 3 · Irregular", obstaculos=8,
         colores=["rojo", "amarillo", "verde", "azul", "blanco", "negro"],
         grid=(3, 2, 0.70, 1.00), gap=0.66, borde=0.10, salida=0.30,
         curva=fit(gp.raw_curve("irregular", (1.05, 1.0, 0.12, 0.06)), 2.10 - 2 * EDGE, 2.00 - 2 * EDGE)),
]


def build(p, idx):
    gp.MIN_OBST_GAP = p.get("gap", 0.70)
    gp.MIN_BOUNDARY = p.get("borde", 0.12)
    gp.START_FREE = p.get("salida", 0.40)
    gp.LEVELS[100 + idx] = dict(nombre=p["nombre"], obstaculos=p["obstaculos"], colores=p["colores"],
                                forma=("puntos", p["curva"]))
    d = gp.design(100 + idx)
    cols, rows, pw, ph = p["grid"]
    W, H = cols * pw, rows * ph
    # centrar la curva en el rectángulo formado por los pliegos
    xs, ys = [q[0] for q in d["pts"]], [q[1] for q in d["pts"]]
    dx = (W - (max(xs) + min(xs))) / 2
    dy = (H - (max(ys) + min(ys))) / 2
    d["pts"] = [(x + dx, y + dy) for x, y in d["pts"]]
    d["W"], d["H"] = W, H
    assert min(q[0] for q in d["pts"]) >= EDGE - 1e-6 and max(q[0] for q in d["pts"]) <= W - EDGE + 1e-6
    assert min(q[1] for q in d["pts"]) >= EDGE - 1e-6 and max(q[1] for q in d["pts"]) <= H - EDGE + 1e-6
    d["grid"] = p["grid"]
    d["key"] = p["key"]
    return d


def pliego_of(d):
    cols, rows, pw, ph = d["grid"]

    def f(x, y):
        c = min(int(x / pw), cols - 1)
        r = min(int((d["H"] - y) / ph), rows - 1)     # P1 = arriba a la izquierda
        return f"P{r * cols + c + 1}"
    return f


def seams(d):
    cols, rows, pw, ph = d["grid"]

    def draw(ax):
        for c in range(1, cols):
            ax.axvline(c * pw, color="#0f766e", lw=1.6, ls="--", zorder=8)
        for r in range(1, rows):
            ax.axhline(r * ph, color="#0f766e", lw=1.6, ls="--", zorder=8)
        for r in range(rows):
            for c in range(cols):
                ax.text(c * pw + 0.03, d["H"] - r * ph - 0.03, f"P{r * cols + c + 1}", ha="left", va="top",
                        fontsize=9, color="#0f766e", weight="bold", zorder=9,
                        bbox=dict(fc="white", ec="#0f766e", lw=0.6, pad=1.5))
    return draw


def scale_for(d):
    for s in (5, 8, 10, 12.5, 15, 20):
        if d["W"] * 100 / s <= 19.0 and d["H"] * 100 / s <= 18.0:
            return s
    return 20


def portada(pdf, designs, sims):
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.text(0.5, 0.95, "PISTAS SOBRE PLIEGOS", ha="center", fontsize=18, weight="bold", color="#0f3d6e")
    fig.text(0.5, 0.925, "Pliegos de 70 × 100 cm · carro de 2 motores (~20 cm)", ha="center", fontsize=10)
    txt = [
        "CÓMO DIBUJARLAS",
        "1. Una los pliegos por DETRÁS con cinta, en la posición del plano (P1 arriba a la",
        "   izquierda) y numérelos. La esquina inferior izquierda es el origen (0, 0).",
        "2. Con un metro, marque los puntos de la TABLA DE TRAZADO (x, y en cm) y únalos con",
        "   lápiz a mano alzada (o apoyando un cordón/manguera): esa es la línea central.",
        "3. Franja de color de 16 cm: marque 8 cm a cada lado de la línea y coloree con",
        "   témpera/vinilo MATE o pegue tiras de cartulina mate. Uniones de color rectas.",
        "   · Sección BLANCA: deje el papel blanco.  · Sección NEGRA: franja negra.",
        "4. Pegue la cinta aislante de 19 mm sobre la línea central (o repásela con marcador",
        "   negro permanente de punta gruesa, 2 pasadas). En la sección NEGRA, cinta BLANCA.",
        "5. Ponga los conos en los puntos ◆ y la salida en la flecha verde.",
        "",
        "IMPORTANTE",
        "· Al esquivar, el carro se sale del papel hasta ~45 cm: deje el piso libre alrededor",
        "  y péguelo al piso con cinta para que no se mueva ni se arrugue.",
        "· Los conos deben ser más altos que el ultrasonido (≥ 18 cm).",
        "· Empiece por la pista de PRÁCTICA (1 pliego): sirve para calibrar línea y color.",
        "  No lleva cono (no cabe la evasión): pruebe la evasión en una recta de cinta de",
        "  1,5 m en el piso con un cono a la mitad.",
        "",
        "IMPRESIÓN: imprima al 100 % (sin «ajustar a página») y verifique la barra de 50 cm.",
    ]
    fig.text(0.07, 0.885, "\n".join(txt), va="top", fontsize=8.6, family="DejaVu Sans Mono")
    ax = fig.add_axes([0.07, 0.25, 0.86, 0.2])
    ax.axis("off")
    rows = []
    for d, s in zip(designs, sims):
        cols, rws, pw, ph = d["grid"]
        rows.append([d["cfg"]["nombre"], f"{cols * rws}", f"{d['W'] * 100:.0f} × {d['H'] * 100:.0f}",
                     f"{d['L']:.2f}", f"{d['rmin'] * 100:.0f}", str(len(d["obst"])),
                     f"{math.ceil(d['L'] * 1.1)}",
                     f"{'✓' if s['vuelta'] and s['colisiones'] == 0 else '✗'} {s['t']:.0f} s"])
    t = ax.table(cellText=rows, colLabels=["Pista", "Pliegos", "Tamaño (cm)", "Línea (m)", "R mín (cm)",
                                           "Conos", "Cinta (m)", "Simulación"],
                 colWidths=[0.2, 0.08, 0.14, 0.1, 0.11, 0.08, 0.1, 0.13], loc="upper center", cellLoc="center")
    t.auto_set_font_size(False)
    t.set_fontsize(8)
    t.scale(1, 2.2)
    for (r, c), cell in t.get_celld().items():
        cell.set_linewidth(0.4)
        if r == 0:
            cell.set_facecolor("#0f3d6e"); cell.get_text().set_color("white")
    fig.text(0.07, 0.235, f"Total: {sum(d['grid'][0] * d['grid'][1] for d in designs)} pliegos "
             "(blancos o claros). Simulación = vuelta autónoma en el gemelo digital esquivando todos los conos.",
             fontsize=7.5)
    for k, d in enumerate(designs):
        ax = fig.add_axes([0.04 + k * 0.24, 0.04, 0.21, 0.17])
        pts, n = d["pts"], len(d["pts"])
        for kk, c in enumerate(d["colores"]):
            i0, i1 = int(kk * d["seg"] / d["step"]), int((kk + 1) * d["seg"] / d["step"])
            idx = [i % n for i in range(i0, i1 + 1)]
            ax.plot([pts[i][0] for i in idx], [pts[i][1] for i in idx], color=gp.HEX[c], lw=4,
                    solid_capstyle="butt")
        for s in d["obst"]:
            x, y = gp.point_at(d, s)
            ax.plot(x, y, "^", color="#ea580c", ms=4)
        cols, rws, pw, ph = d["grid"]
        for c in range(1, cols):
            ax.axvline(c * pw, color="#0f766e", lw=0.6, ls="--")
        for r in range(1, rws):
            ax.axhline(r * ph, color="#0f766e", lw=0.6, ls="--")
        ax.set_xlim(0, d["W"]); ax.set_ylim(0, d["H"])
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(d["cfg"]["nombre"], fontsize=7.5)
    pdf.savefig(fig)
    plt.close(fig)


def main():
    os.makedirs(gp.OUT, exist_ok=True)
    designs, sims = [], []
    for i, p in enumerate(PISTAS):
        d = build(p, i)
        s = gp.simulate(d, seconds=120)
        designs.append(d); sims.append(s)
        print(f"{p['nombre']}: {d['W'] * 100:.0f}x{d['H'] * 100:.0f} cm, línea {d['L']:.2f} m, "
              f"R mín {d['rmin'] * 100:.0f} cm, conos {[round(x, 2) for x in d['obst']]} | "
              f"sim vuelta={s['vuelta']} t={s['t']:.0f}s esquivados={s['esquivados']} "
              f"colisiones={s['colisiones']} desvío={s['desvio_max'] * 100:.0f} cm")
        with open(os.path.join(gp.OUT, f"pliegos_{p['key']}.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["s_cm", "x_cm", "y_cm", "color", "pliego"])
            po = pliego_of(d)
            for j in range(0, len(d["pts"]), max(1, int(round(0.10 / d["step"])))):
                x, y = d["pts"][j]
                w.writerow([f"{j * d['step'] * 100:.0f}", f"{x * 100:.1f}", f"{y * 100:.1f}",
                            gp.color_at(d, j * d["step"]), po(x, y)])
    path = os.path.join(gp.OUT, "Pistas_en_Pliegos.pdf")
    with PdfPages(path) as pdf:
        portada(pdf, designs, sims)
        for d, s in zip(designs, sims):
            gp.SCALE = scale_for(d)
            gp.page_plano(pdf, d, s, extra=seams(d))
            gp.page_tabla(pdf, d, pliego_of=pliego_of(d))
    print("PDF:", path)


if __name__ == "__main__":
    main()
