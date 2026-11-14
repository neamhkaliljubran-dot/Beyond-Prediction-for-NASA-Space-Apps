"""Landing-page visuals: CSS starfield and a conceptual topological network.

Both are decorative and generated deterministically (fixed seeds). The conceptual
network is NOT data: the real, computed network is drawn by beyond_prediction.network.
Performance notes: stars move by translating whole layers (GPU-composited), and the
network's large static layers rotate/breathe as whole elements; only a small sparkle
layer animates opacity.
"""

from __future__ import annotations

import numpy as np

STAR_COLORS = ["#E9F2FF", "#E9F2FF", "#E9F2FF", "#CFE6FF", "#57B9F5", "#B9B0F0"]


def _shadows(n: int, seed: int, w: int = 1700, h: int = 1100) -> str:
    rng = np.random.default_rng(seed)
    xs, ys = rng.integers(0, w, n), rng.integers(0, h, n)
    cols = rng.choice(STAR_COLORS, size=n)
    return ", ".join(f"{x}px {y}px {c}" for x, y, c in zip(xs, ys, cols))


def starfield_html() -> str:
    """Fixed, full-viewport starfield.

    Drifting layers and twinkling layers are separate elements (animating one property per
    layer keeps compositing cheap); stars tile a 1700 x 1100 px field that repeats seamlessly.
    """
    H = 1100
    layers = [  # (class, star px, count, seed, kind, seconds)
        ("d1", 1, 170, 11, "drift", 150),
        ("d2", 2, 70, 12, "drift", 95),
        ("t1", 2, 45, 13, "twinkle", 3.6),
        ("t2", 3, 18, 14, "twinkle", 5.1),
    ]
    css, divs = [], []
    for name, px, n, seed, kind, sec in layers:
        sh = _shadows(n, seed)
        anim = (f"bp-drift {sec}s linear infinite" if kind == "drift"
                else f"bp-twinkle {sec}s ease-in-out infinite alternate")
        css.append(f"""
.bp-stars .{name}{{position:absolute;top:0;left:0;width:{px}px;height:{px}px;border-radius:50%;
  box-shadow:{sh};animation:{anim};will-change:{'transform' if kind == 'drift' else 'opacity'};}}""")
        if kind == "drift":
            css.append(f"""
.bp-stars .{name}::after{{content:"";position:absolute;top:{H}px;left:0;width:{px}px;height:{px}px;
  border-radius:50%;box-shadow:{sh};}}""")
        divs.append(f'<div class="{name}"></div>')
    return f"""<style>
.bp-stars{{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden;}}
@keyframes bp-drift{{from{{transform:translate3d(0,0,0)}}to{{transform:translate3d(0,-{H}px,0)}}}}
@keyframes bp-twinkle{{0%{{opacity:.25}}55%{{opacity:1}}100%{{opacity:.5}}}}
{''.join(css)}
@media (prefers-reduced-motion: reduce){{.bp-stars div{{animation:none !important}}}}
</style><div class="bp-stars">{''.join(divs)}</div>"""


def _sphere(n: int, rot: float, tilt: float):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5 ** 0.5) * i
    p = np.c_[np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)]
    cr, sr = np.cos(rot), np.sin(rot)
    p = p @ np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]]).T
    ct, stt = np.cos(tilt), np.sin(tilt)
    return p @ np.array([[1, 0, 0], [0, ct, -stt], [0, stt, ct]]).T


def _knn_edges(p: np.ndarray, k: int) -> set[tuple[int, int]]:
    d = ((p[:, None, :] - p[None, :, :]) ** 2).sum(-1)
    np.fill_diagonal(d, np.inf)
    edges = set()
    for a, row in enumerate(np.argsort(d, axis=1)[:, :k]):
        for b in row:
            edges.add((min(a, int(b)), max(a, int(b))))
    return edges


def concept_network_svg(seed: int = 7) -> str:
    """Original animated topological network inspired by a node-sphere and a web-like graph."""
    rng = np.random.default_rng(seed)
    W, H, cx, cy, R = 640, 520, 320, 260, 175
    sph = _sphere(230, 0.6, 0.45)
    sph *= (1 + rng.normal(0, 0.035, size=(len(sph), 1)))          # slightly irregular surface
    sx, sy, sz = cx + R * sph[:, 0], cy + R * sph[:, 1], sph[:, 2]
    edges = _knn_edges(sph, 5)
    back, front = [], []
    for a, b in edges:
        z = (sz[a] + sz[b]) / 2
        op = 0.16 + 0.62 * (z + 1) / 2
        line = (f'<line x1="{sx[a]:.1f}" y1="{sy[a]:.1f}" x2="{sx[b]:.1f}" y2="{sy[b]:.1f}" '
                f'stroke-opacity="{op:.2f}"/>')
        (front if z > 0 else back).append(line)
    nodes = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{1.0 + 1.6 * (z + 1) / 2:.2f}" '
                    f'fill-opacity="{0.45 + 0.55 * (z + 1) / 2:.2f}"/>' for x, y, z in zip(sx, sy, sz))
    # outer web: noisy ring of points joined to neighbours, plus long curved strands
    m = 150
    ang = np.sort(rng.uniform(0, 2 * np.pi, m))
    rad = R * (1.18 + 0.28 * rng.random(m) + 0.10 * np.sin(3 * ang + 1.3))
    wx, wy = cx + rad * np.cos(ang) * 1.12, cy + rad * np.sin(ang) * 0.92
    wp = np.c_[wx, wy, np.zeros(m)]
    web = []
    for a, b in _knn_edges(wp, 3):
        web.append(f'<line x1="{wx[a]:.1f}" y1="{wy[a]:.1f}" x2="{wx[b]:.1f}" y2="{wy[b]:.1f}"/>')
    strands = []
    for _ in range(46):
        a, b = rng.integers(0, m, 2)
        if abs(int(a) - int(b)) < 12:
            continue
        mx = (wx[a] + wx[b]) / 2 + rng.normal(0, 40)
        my = (wy[a] + wy[b]) / 2 + rng.normal(0, 40)
        strands.append(f'<path d="M{wx[a]:.1f},{wy[a]:.1f} Q{mx:.1f},{my:.1f} {wx[b]:.1f},{wy[b]:.1f}"/>')
    # sphere-to-web ties
    for _ in range(36):
        a = int(rng.integers(0, len(sph)))
        if sz[a] < 0.2:
            continue
        b = int(np.argmin((wx - sx[a]) ** 2 + (wy - sy[a]) ** 2))
        web.append(f'<line x1="{sx[a]:.1f}" y1="{sy[a]:.1f}" x2="{wx[b]:.1f}" y2="{wy[b]:.1f}" '
                   f'stroke-opacity=".22"/>')
    webdots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.3"/>' for x, y in zip(wx, wy))
    # sparkles: brightest front nodes twinkle
    idx = np.argsort(-sz)[:34]
    sparks = "".join(
        f'<circle class="bp-spark" cx="{sx[i]:.1f}" cy="{sy[i]:.1f}" r="2.6" '
        f'style="animation-delay:{rng.uniform(0, 4):.2f}s;animation-duration:{rng.uniform(2.4, 4.8):.2f}s"/>'
        for i in idx)
    svg_open = f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
    return f"""<style>
.bp-net{{position:relative;width:min(560px,92vw);aspect-ratio:{W}/{H};margin:0 auto;}}
.bp-net .layer{{position:absolute;inset:0;will-change:transform;}}
.bp-net::before{{content:'';position:absolute;inset:8% 14%;border-radius:50%;background:radial-gradient(closest-side,rgba(87,185,245,.20),rgba(130,117,218,.08) 55%,transparent 75%);}}
.bp-net svg{{width:100%;height:100%;overflow:visible;}}
.bp-net .web{{animation:bp-breathe 14s ease-in-out infinite;}}
.bp-net .sphere,.bp-net .sparks{{animation:bp-spin 140s linear infinite;}}
.bp-net .web line,.bp-net .web path{{stroke:#57B9F5;stroke-width:.65;stroke-opacity:.40;fill:none;}}
.bp-net .web circle{{fill:#8FD3FF;fill-opacity:.55;}}
.bp-net .sphere line{{stroke:#8AD4FF;stroke-width:.8;}}
.bp-net .sphere circle{{fill:#CFE6FF;}}
.bp-net .glow{{}}
.bp-spark{{fill:#F3F8FF;animation:bp-spark 3s ease-in-out infinite;}}
@keyframes bp-spin{{from{{transform:rotate(0deg)}}to{{transform:rotate(360deg)}}}}
@keyframes bp-breathe{{0%,100%{{transform:scale(1) rotate(0deg)}}50%{{transform:scale(1.025) rotate(-2deg)}}}}
@keyframes bp-spark{{0%,100%{{opacity:.15}}50%{{opacity:1}}}}
@media (prefers-reduced-motion: reduce){{.bp-net .layer,.bp-spark{{animation:none !important}}}}
</style>
<div class="bp-net">
 <div class="layer web">{svg_open}{''.join(web)}{''.join(strands)}{webdots}</svg></div>
 <div class="layer sphere glow">{svg_open}<g>{''.join(back)}</g><g>{''.join(front)}</g><g>{nodes}</g></svg></div>
 <div class="layer sparks">{svg_open}{sparks}</svg></div>
</div>"""
