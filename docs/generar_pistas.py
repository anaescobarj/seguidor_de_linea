"""Plantillas de las 3 pistas de la meta final (para construirlas en el piso).

    python docs/generar_pistas.py
      -> docs/pistas/Plantillas_Pistas.pdf      planos a escala 1:15 + tablas de trazado
      -> docs/pistas/pista_nivelN.csv           coordenadas de la línea guía cada 10 cm

Medidas de diseño (para un carro de ~20 x 19 cm):
  carretera 32 cm de ancho, línea guía de 19 mm, radio mínimo de curva >= 25 cm,
  secciones de color >= 30 cm, obstáculos a >= 80 cm entre sí y a >= 20 cm de un
  cambio de color, ubicados en los tramos más rectos.
Además, cada pista se valida en el gemelo digital (app/simulator.py): una vuelta
autónoma esquivando todos los obstáculos sin colisiones.
"""
from __future__ import annotations

import csv
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Polygon  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "pistas")
sys.path.insert(0, os.path.join(HERE, "..", "app"))

ROAD_W = 0.32          # m, ancho de la carretera
TAPE_W = 0.019         # m, cinta guía
MARGIN = 0.10          # m, borde libre alrededor de la carretera en el área total
OBST_R = 0.05          # m, radio del cono en la base (cono de entrenamiento ~10 cm)
MIN_OBST_GAP = 0.80    # m, separación mínima entre obstáculos
MIN_BOUNDARY = 0.20    # m, distancia mínima de un obstáculo a un cambio de color
SCALE = 15             # plano 1:15
PLIEGO = (0.70, 1.00)  # m, pliego de cartulina

HEX = {"negro": "#111111", "blanco": "#f2f2f2", "rojo": "#d62828", "amarillo": "#f6c90e",
       "verde": "#2a9d3f", "azul": "#1d4ed8"}
GUIDE = {c: ("blanca" if c == "negro" else "negra") for c in HEX}

LEVELS = {
    1: dict(nombre="Nivel 1 · Frijol", obstaculos=4, colores=["rojo", "verde", "azul"],
            forma=("frijol", (1.0, 0.60, 0.15))),
    2: dict(nombre="Nivel 2 · Estrella", obstaculos=6, colores=["rojo", "amarillo", "verde", "azul"],
            forma=("estrella", (1.0, 0.14))),
    3: dict(nombre="Nivel 3 · Irregular", obstaculos=8,
            colores=["rojo", "amarillo", "verde", "azul", "blanco", "negro"],
            forma=("irregular", (1.25, 1.0, 0.16, 0.08))),
}


# ------------------------------------------------------------------------------ geometría
def raw_curve(kind: str, p: tuple, n: int = 4000) -> list[tuple[float, float]]:
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        if kind == "frijol":
            a, b, k = p
            r = 1 + k * math.sin(2 * t)
            pts.append((a * r * math.cos(t), b * r * math.sin(t)))
        elif kind == "estrella":
            R, k = p
            r = R * (1 + k * math.cos(5 * t))
            pts.append((r * math.cos(t), r * math.sin(t)))
        else:
            a, b, k1, k2 = p
            r = 1 + k1 * math.sin(3 * t) + k2 * math.cos(5 * t + 0.7)
            pts.append((a * r * math.cos(t), b * r * math.sin(t)))
    return pts


def resample(pts, step=0.01):
    """Reparte puntos cada `step` metros de longitud de arco (curva cerrada)."""
    n = len(pts)
    cum = [0.0]
    for i in range(1, n + 1):
        cum.append(cum[-1] + math.dist(pts[i - 1], pts[i % n]))
    L = cum[-1]
    m = int(round(L / step))
    out, j = [], 0
    for k in range(m):
        s = k * L / m
        while cum[j + 1] < s:
            j += 1
        f = (s - cum[j]) / (cum[j + 1] - cum[j])
        a, b = pts[j], pts[(j + 1) % n]
        out.append((a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])))
    return out, L


def radius_at(pts, i, w=8):
    n = len(pts)
    a, b, c = pts[(i - w) % n], pts[i], pts[(i + w) % n]
    ab, bc, ca = math.dist(a, b), math.dist(b, c), math.dist(c, a)
    area = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2
    return 1e9 if area < 1e-12 else ab * bc * ca / (4 * area)


def design(level: int) -> dict:
    cfg = LEVELS[level]
    pts, L = resample(raw_curve(*cfg["forma"]))
    n = len(pts)
    step = L / n
    radii = [radius_at(pts, i) for i in range(n)]
    # salida en el tramo más recto
    win = int(0.15 / step)
    straight = [min(radii[(i + k) % n] for k in range(-win, win + 1)) for i in range(n)]
    start = max(range(n), key=lambda i: straight[i])
    pts = pts[start:] + pts[:start]
    radii = radii[start:] + radii[:start]
    straight = straight[start:] + straight[:start]
    # para los conos: radio mínimo desde 30 cm antes hasta 90 cm después (zona de evasión y regreso)
    pre, post = int(0.30 / step), int(0.90 / step)
    evasion = [min(radii[(i + kk) % n] for kk in range(-pre, post + 1, 3)) for i in range(n)]
    # trasladar al primer cuadrante (origen = esquina inferior izquierda del área)
    off = ROAD_W / 2 + MARGIN
    minx, miny = min(p[0] for p in pts), min(p[1] for p in pts)
    pts = [(x - minx + off, y - miny + off) for x, y in pts]
    W = max(p[0] for p in pts) + off
    H = max(p[1] for p in pts) + off

    cols = cfg["colores"]
    seg = L / len(cols)
    bounds = [k * seg for k in range(len(cols))]

    def dist_to_bound(s):
        return min(min(abs(s - b), L - abs(s - b)) for b in bounds)

    def circ(a, b):
        d = abs(a - b) % L
        return min(d, L - d)

    # Ubicación de los conos: búsqueda aleatoria de conjuntos que cumplan separación >= 80 cm,
    # distancia a cambios de color >= MIN_BOUNDARY y salida libre; se elige el más recto y parejo.
    import random
    rng = random.Random(level)
    k = cfg["obstaculos"]
    allowed = [i * step for i in range(n)
               if dist_to_bound(i * step) >= MIN_BOUNDARY and 0.5 < i * step < L - 0.3]
    best, best_score = None, -1e9
    for _ in range(4000):
        s0 = rng.choice(allowed)
        chosen = [s0]
        for _ in range(k - 1):
            nxt = [c for c in allowed if c >= chosen[-1] + MIN_OBST_GAP]
            if not nxt:
                break
            target = chosen[-1] + max(MIN_OBST_GAP, (L - (chosen[-1] - s0)) / (k - len(chosen) + 1))
            nxt.sort(key=lambda c: abs(c - target) + rng.random() * 0.25)
            chosen.append(nxt[0])
        if len(chosen) < k or circ(chosen[-1], chosen[0]) < MIN_OBST_GAP:
            continue
        gaps = [((chosen[(j + 1) % k] - chosen[j]) % L) for j in range(k)]
        score = min(evasion[int(c / step) % n] for c in chosen) - 0.5 * (max(gaps) - min(gaps))
        if score > best_score:
            best, best_score = sorted(chosen), score
    if best is None:
        raise RuntimeError(f"Nivel {level}: no caben {k} obstáculos con las restricciones")
    obst = best

    return dict(level=level, cfg=cfg, pts=pts, L=L, step=step, W=W, H=H, colores=cols, seg=seg,
                obst=obst, rmin=min(radii))


def color_at(d, s):
    return d["colores"][min(int(s / d["seg"]), len(d["colores"]) - 1)]


def point_at(d, s):
    i = int(round(s / d["step"])) % len(d["pts"])
    return d["pts"][i]


def normals(pts):
    n = len(pts)
    out = []
    for i in range(n):
        a, b = pts[i - 1], pts[(i + 1) % n]
        tx, ty = b[0] - a[0], b[1] - a[1]
        m = math.hypot(tx, ty)
        out.append((-ty / m, tx / m))
    return out


# ------------------------------------------------------------------------------ validación
def simulate(d, seconds=150):
    from simulator import SimRobot
    r = SimRobot(1)
    w = r.world
    w.track = list(d["pts"])
    w.cum = [0.0]
    for i in range(1, len(w.track) + 1):
        w.cum.append(w.cum[-1] + math.dist(w.track[i - 1], w.track[i % len(w.track)]))
    w.length = w.cum[-1]
    w.section_colors = d["colores"]
    w.obstacles = [(*point_at(d, s), OBST_R) for s in d["obst"]]
    (x0, y0), (x1, y1) = w.track[0], w.track[5]
    r.x, r.y, r.theta = x0, y0, math.atan2(y1 - y0, x1 - x0)
    r.trail = []
    r.handle("/api/mode", {"m": ["auto"]})
    n = len(w.track)
    last, prog, maxoff = 0, 0, 0.0
    for _ in range(int(seconds / 0.05)):
        r.step()
        i, off = w.nearest(r.x, r.y)
        maxoff = max(maxoff, off)
        prog += (i - last + n // 2) % n - n // 2
        last = i
        if prog >= n:
            break
    return dict(vuelta=prog >= n, t=r.t, esquivados=r.obstacles_avoided, colisiones=r.collisions,
                desvio_max=maxoff, trail=list(r.trail))


# ------------------------------------------------------------------------------ dibujo
A4L = (11.69, 8.27)


def page_plano(pdf, d, sim):
    fig = plt.figure(figsize=A4L)
    W, H = d["W"], d["H"]
    # ejes con tamaño físico exacto para que la escala 1:15 sea real al imprimir al 100 %
    aw, ah = W * 100 / SCALE / 2.54, H * 100 / SCALE / 2.54
    left = 0.55
    bottom = (A4L[1] - ah) / 2 - 0.15
    ax = fig.add_axes([left / A4L[0], bottom / A4L[1], aw / A4L[0], ah / A4L[1]])
    ax.set_xlim(0, W); ax.set_ylim(0, H)
    ax.set_aspect("equal")
    # cuadrícula 10 cm / 50 cm
    for v in [i / 10 for i in range(int(W * 10) + 1)]:
        ax.axvline(v, color="#cbd5e1" if (round(v * 10) % 5) else "#64748b", lw=0.3 if (round(v * 10) % 5) else 0.7,
                   zorder=0)
    for v in [i / 10 for i in range(int(H * 10) + 1)]:
        ax.axhline(v, color="#cbd5e1" if (round(v * 10) % 5) else "#64748b", lw=0.3 if (round(v * 10) % 5) else 0.7,
                   zorder=0)
    ax.set_xticks([i / 2 for i in range(int(W * 2) + 1)])
    ax.set_xticklabels([f"{int(i * 50)}" for i in range(int(W * 2) + 1)], fontsize=6)
    ax.set_yticks([i / 2 for i in range(int(H * 2) + 1)])
    ax.set_yticklabels([f"{int(i * 50)}" for i in range(int(H * 2) + 1)], fontsize=6)
    ax.tick_params(length=2, pad=1)
    for sp in ax.spines.values():
        sp.set_linewidth(1.2)
    # carretera por secciones
    pts, nrm = d["pts"], normals(d["pts"])
    n = len(pts)
    hw = ROAD_W / 2
    for k, c in enumerate(d["colores"]):
        i0, i1 = int(k * d["seg"] / d["step"]), int((k + 1) * d["seg"] / d["step"])
        idx = [i % n for i in range(i0, i1 + 1)]
        outer = [(pts[i][0] + hw * nrm[i][0], pts[i][1] + hw * nrm[i][1]) for i in idx]
        inner = [(pts[i][0] - hw * nrm[i][0], pts[i][1] - hw * nrm[i][1]) for i in idx]
        ax.add_patch(Polygon(outer + inner[::-1], closed=True, fc=HEX[c], ec="#334155", lw=0.4, zorder=2))
        mid = pts[(i0 + i1) // 2 % n]
        ax.text(mid[0], mid[1] + 0.0, "", zorder=6)
    # línea guía (negra; blanca en la sección negra)
    for k, c in enumerate(d["colores"]):
        i0, i1 = int(k * d["seg"] / d["step"]), int((k + 1) * d["seg"] / d["step"])
        idx = [i % n for i in range(i0, i1 + 1)]
        ax.plot([pts[i][0] for i in idx], [pts[i][1] for i in idx],
                color="white" if c == "negro" else "black", lw=1.0, zorder=3)
    # cambios de color
    for k in range(len(d["colores"])):
        i = int(k * d["seg"] / d["step"]) % n
        p, q = pts[i], nrm[i]
        ax.plot([p[0] + (hw + 0.04) * q[0], p[0] - (hw + 0.04) * q[0]],
                [p[1] + (hw + 0.04) * q[1], p[1] - (hw + 0.04) * q[1]], color="#7c3aed", lw=1.2, zorder=4)
    # obstáculos
    for j, s in enumerate(d["obst"]):
        x, y = point_at(d, s)
        ax.add_patch(Circle((x, y), OBST_R, fc="#ea580c", ec="k", lw=0.6, zorder=5))
        ax.text(x, y, str(j + 1), ha="center", va="center", fontsize=6, color="white", weight="bold", zorder=6)
    # salida y sentido
    p0, p1 = pts[0], pts[int(0.30 / d["step"])]
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=12, color="#16a34a", lw=2, zorder=6))
    ax.text(p0[0], p0[1] - 0.05, "SALIDA", fontsize=6.5, color="#16a34a", weight="bold", ha="center", va="top",
            zorder=7, bbox=dict(fc="white", ec="none", pad=0.5))
    # trayectoria simulada (tenue)
    if sim["trail"]:
        ax.plot([t[0] for t in sim["trail"]], [t[1] for t in sim["trail"]], color="#a855f7", lw=0.6, ls=":",
                zorder=4)
    # barra de escala
    fig.text(0.5, 0.965, f"PISTA {d['cfg']['nombre'].upper()}  ·  área {W * 100:.0f} × {H * 100:.0f} cm  ·  "
             f"línea guía {d['L']:.2f} m", ha="center", fontsize=12, weight="bold")
    x0 = (left + aw + 0.3) / A4L[0]
    info = [
        f"Escala 1:{SCALE}  (imprimir al 100 %)",
        "Cuadrícula: 10 cm (fina), 50 cm (gruesa)",
        "Coordenadas en cm desde la esquina",
        "inferior izquierda del área.",
        "",
        f"Carretera: {ROAD_W * 100:.0f} cm de ancho",
        "Línea guía: cinta de 19 mm por el centro",
        "(blanca en la sección negra)",
        f"Radio mínimo de curva: {d['rmin'] * 100:.0f} cm",
        f"Sección de color: {d['seg'] * 100:.0f} cm c/u",
        "",
        "Secciones (desde la salida):",
    ]
    info += [f"  {k + 1}. {c:<9} {k * d['seg'] * 100:5.0f}–{(k + 1) * d['seg'] * 100:4.0f} cm"
             for k, c in enumerate(d["colores"])]
    info += ["", "Obstáculos (conos ≥ 18 cm de alto):"]
    for j, s in enumerate(d["obst"]):
        x, y = point_at(d, s)
        info.append(f"  {j + 1}. a {s * 100:5.0f} cm  (x={x * 100:4.0f}, y={y * 100:4.0f})")
    info += ["", "Validación en el gemelo digital:",
             f"  vuelta completa: {'sí' if sim['vuelta'] else 'NO'} ({sim['t']:.0f} s)",
             f"  esquivados {sim['esquivados']}/{len(d['obst'])} · colisiones {sim['colisiones']}",
             f"  máx. separación de la línea: {sim['desvio_max'] * 100:.0f} cm",
             "  (punteado morado = trayectoria)",
             "", "Dejar ≥ 50 cm libres a cada lado",
             "de la carretera junto a los obstáculos."]
    fig.text(x0, 0.90, "\n".join(info), va="top", ha="left", fontsize=7.2, family="DejaVu Sans Mono")
    # barra de 50 cm a escala
    bar_in = 50 / SCALE / 2.54
    bx, by = x0, 0.06
    fig.add_artist(plt.Line2D([bx, bx + bar_in / A4L[0]], [by, by], color="k", lw=3))
    fig.text(bx, by + 0.012, "50 cm (a escala)", fontsize=7)
    pdf.savefig(fig)
    plt.close(fig)


def page_tabla(pdf, d):
    # puntos cada 20 cm + filas exactas en cada cambio de color y en cada cono
    marks = [(k * d["seg"], f"▶ inicia {c}") for k, c in enumerate(d["colores"])]
    marks += [(so, f"◆ CONO {j + 1}") for j, so in enumerate(d["obst"])]
    items = {}
    s = 0.0
    while s < d["L"] - 1e-6:
        items[round(s, 3)] = ""
        s += 0.20
    for sm, note in marks:
        key = min(items, key=lambda k: abs(k - sm))
        if abs(key - sm) < 0.015:            # coincide con un punto de la malla
            items[key] = (items[key] + " " if items[key] else "") + note
        else:
            items[round(sm, 3)] = (items.get(round(sm, 3), "") + " " if items.get(round(sm, 3)) else "") + note
    rows = []
    for sk in sorted(items):
        x, y = point_at(d, sk)
        col = color_at(d, sk + 1e-6)
        for c in d["colores"]:
            if f"inicia {c}" in items[sk]:
                col = c
        rows.append([f"{sk * 100:.0f}", f"{x * 100:.0f}", f"{y * 100:.0f}", col, items[sk]])
    per_col = 46
    chunks = [rows[i:i + per_col] for i in range(0, len(rows), per_col)]
    for c0 in range(0, len(chunks), 2):
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.text(0.5, 0.965, f"TABLA DE TRAZADO · {d['cfg']['nombre']}", ha="center", fontsize=12, weight="bold")
        fig.text(0.5, 0.945, "Puntos de la línea guía cada 20 cm, medidos desde la esquina inferior izquierda "
                 "del área (x hacia la derecha, y hacia arriba).", ha="center", fontsize=8)
        for k, ch in enumerate(chunks[c0:c0 + 2]):
            ax = fig.add_axes([0.04 + k * 0.48, 0.04, 0.44, 0.88])
            ax.axis("off")
            t = ax.table(cellText=ch, colLabels=["s (cm)", "x (cm)", "y (cm)", "color", "nota"],
                         colWidths=[0.14, 0.13, 0.13, 0.2, 0.4], loc="upper center", cellLoc="center")
            t.auto_set_font_size(False)
            t.set_fontsize(7)
            t.scale(1, 1.18)
            for (r, cidx), cell in t.get_celld().items():
                cell.set_linewidth(0.3)
                if r == 0:
                    cell.set_facecolor("#0f3d6e"); cell.get_text().set_color("white")
                elif cidx == 3:
                    col = ch[r - 1][3]
                    cell.set_facecolor(HEX[col])
                    cell.get_text().set_color("white" if col in ("negro", "azul", "rojo", "verde") else "black")
        pdf.savefig(fig)
        plt.close(fig)


def materiales(d):
    """Pliegos de 70x100 por color: por área (60 % de desperdicio en curvas) y por número de
    tiras de 32 cm x ~90 cm útiles (2 tiras por pliego); se toma el mayor."""
    out = {}
    for c in d["colores"]:
        by_area = math.ceil(d["seg"] * ROAD_W * 1.6 / (PLIEGO[0] * PLIEGO[1]))
        by_strips = math.ceil(math.ceil(d["seg"] / 0.90) / 2)
        out[c] = max(by_area, by_strips)
    return out


def page_portada(pdf, designs, sims):
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.text(0.5, 0.95, "PLANTILLAS DE LAS PISTAS", ha="center", fontsize=18, weight="bold", color="#0f3d6e")
    fig.text(0.5, 0.925, "Meta final · 3 niveles de dificultad · Robot móvil ESP32", ha="center", fontsize=10)
    txt = [
        "CÓMO CONSTRUIRLAS",
        "1. Marque en el piso un rectángulo del tamaño del área (ver tabla) con cinta de enmascarar:",
        "   la esquina inferior izquierda es el origen (0, 0).",
        "2. Con un metro, marque los puntos de la TABLA DE TRAZADO (x, y en cm) y únalos a mano alzada",
        "   o con una manguera/cordón flexible: esa es la línea central.",
        f"3. Marque los bordes de la carretera a {ROAD_W * 50:.0f} cm a cada lado de la línea central (use un",
        f"   listón de {ROAD_W * 50:.0f} cm perpendicular a la línea cada 10 cm).",
        "4. Pegue la cartulina MATE de cada color en su sección: póngala encima, marque los bordes,",
        "   recorte y pegue con doble faz en toda la superficie. Uniones a tope, sin montar.",
        "5. Pegue la cinta guía de 19 mm por el centro, en tramos cortos en las curvas, sin arrugas.",
        "   En la sección NEGRA use cinta BLANCA.",
        "6. Ponga los conos en los puntos marcados (◆ en la tabla) y la salida con la flecha verde.",
        "",
        "ANTES DE HACER LA PISTA COMPLETA: haga un tramo recto de 1 m con todos los colores y la cinta,",
        "y pruebe el carro con las pruebas 3 (línea) y 5 (color) de firmware/pruebas_modulos.",
        "",
        "IMPRESIÓN: los planos están a escala 1:15 en A4 horizontal. Imprima al 100 % (sin «ajustar a",
        "página») y verifique la barra de 50 cm con una regla (debe medir 3,3 cm).",
    ]
    fig.text(0.07, 0.885, "\n".join(txt), va="top", fontsize=8.6, family="DejaVu Sans Mono")

    ax = fig.add_axes([0.07, 0.27, 0.86, 0.27])
    ax.axis("off")
    rows = []
    for d, s in zip(designs, sims):
        m = materiales(d)
        rows.append([d["cfg"]["nombre"], f"{d['W'] * 100:.0f} × {d['H'] * 100:.0f}", f"{d['L']:.2f}",
                     f"{d['rmin'] * 100:.0f}", str(len(d["obst"])),
                     "\n".join(", ".join(f"{c} {v}" for c, v in list(m.items())[i:i + 3])
                               for i in range(0, len(m), 3)),
                     f"{math.ceil(d['L'] * 1.1)}",
                     f"{'✓' if s['vuelta'] and s['colisiones'] == 0 else '✗'} {s['t']:.0f} s"])
    t = ax.table(cellText=rows, colLabels=["Pista", "Área (cm)", "Línea (m)", "R mín (cm)", "Conos",
                                           "Pliegos cartulina 70×100", "Cinta (m)", "Simulación"],
                 colWidths=[0.15, 0.1, 0.08, 0.08, 0.06, 0.33, 0.07, 0.11], loc="upper center", cellLoc="center")
    t.auto_set_font_size(False)
    t.set_fontsize(7.4)
    t.scale(1, 2.4)
    for (r, c), cell in t.get_celld().items():
        cell.set_linewidth(0.4)
        if r == 0:
            cell.set_facecolor("#0f3d6e"); cell.get_text().set_color("white")
    fig.text(0.07, 0.30, "Pliegos por color e incluyen desperdicio por recortes en curva; compre 1 de repuesto por "
             "color.\nLos conos deben medir ≥ 18 cm de alto (el ultrasonido va a ~11 cm del piso). "
             "Deje ≥ 50 cm libres junto a la carretera donde hay conos.", fontsize=7.5)

    # miniaturas
    for k, d in enumerate(designs):
        ax = fig.add_axes([0.05 + k * 0.31, 0.05, 0.28, 0.2])
        pts, n = d["pts"], len(d["pts"])
        for kk, c in enumerate(d["colores"]):
            i0, i1 = int(kk * d["seg"] / d["step"]), int((kk + 1) * d["seg"] / d["step"])
            idx = [i % n for i in range(i0, i1 + 1)]
            ax.plot([pts[i][0] for i in idx], [pts[i][1] for i in idx], color=HEX[c], lw=5,
                    solid_capstyle="butt")
        for s in d["obst"]:
            x, y = point_at(d, s)
            ax.plot(x, y, "^", color="#ea580c", ms=5)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        ax.set_facecolor("#e5e7eb")
        ax.set_title(d["cfg"]["nombre"], fontsize=8)
    pdf.savefig(fig)
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    designs, sims = [], []
    for lvl in (1, 2, 3):
        d = design(lvl)
        s = simulate(d)
        designs.append(d); sims.append(s)
        print(f"{d['cfg']['nombre']}: área {d['W'] * 100:.0f}x{d['H'] * 100:.0f} cm, línea {d['L']:.2f} m, "
              f"R mín {d['rmin'] * 100:.0f} cm | sim: vuelta={s['vuelta']} t={s['t']:.0f}s "
              f"esquivados={s['esquivados']} colisiones={s['colisiones']} desvío máx={s['desvio_max'] * 100:.0f} cm")
        with open(os.path.join(OUT, f"pista_nivel{lvl}.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["s_cm", "x_cm", "y_cm", "color"])
            for i in range(0, len(d["pts"]), max(1, int(round(0.10 / d["step"])))):
                sx = i * d["step"]
                w.writerow([f"{sx * 100:.0f}", f"{d['pts'][i][0] * 100:.1f}", f"{d['pts'][i][1] * 100:.1f}",
                            color_at(d, sx)])
    path = os.path.join(OUT, "Plantillas_Pistas.pdf")
    with PdfPages(path) as pdf:
        page_portada(pdf, designs, sims)
        for d, s in zip(designs, sims):
            page_plano(pdf, d, s)
            page_tabla(pdf, d)
    print("PDF:", path)


if __name__ == "__main__":
    main()
