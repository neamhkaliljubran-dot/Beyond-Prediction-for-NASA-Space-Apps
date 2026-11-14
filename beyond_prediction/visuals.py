"""Static visual elements: conceptual schematic and pyramid.

The schematic is a simplified conceptual drawing of the equatorial Pacific
Walker circulation. It is NOT derived from data and carries no quantities.
"""

from __future__ import annotations

_ARROW = '<marker id="ah" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="currentColor"/></marker>'


def walker_schematic(state: str = "neutral") -> str:
    """Return inline SVG. state: 'neutral' (incl. La Niña-like) or 'elnino'."""
    el = state == "elnino"
    rise_x = 430 if el else 150           # main ascending branch
    sink_x = 150 if el else 610           # main descending branch
    warm_w = 520 if el else 300           # extent of warm pool
    thermo = "M60,250 C300,262 500,262 700,250" if el else "M60,275 C300,262 500,240 700,225"
    caption = ("El Niño (schematic): warm water and deep convection shift toward the central "
               "Pacific; air tends to sink over the Maritime Continent, a pattern often "
               "associated with drier conditions in parts of Indonesia, especially Jun–Nov.") if el else (
               "Neutral / La Niña-like (schematic): easterly trade winds pile warm water in the "
               "west; air rises over the Maritime Continent and sinks over the eastern Pacific.")
    return f"""
<svg viewBox="0 0 760 330" role="img" aria-label="Schematic of the Pacific Walker circulation"
     style="width:100%;max-width:760px;color:var(--bp-ink,#1f2937);font-family:sans-serif">
  <defs>{_ARROW}
    <linearGradient id="sea" x1="0" x2="1"><stop offset="0" stop-color="#e0533d"/>
      <stop offset="{warm_w/760:.2f}" stop-color="#f4a261"/><stop offset="1" stop-color="#4a90c2"/></linearGradient>
  </defs>
  <rect x="0" y="0" width="760" height="330" fill="none"/>
  <rect x="60" y="200" width="640" height="95" fill="url(#sea)" opacity="0.85"/>
  <path d="{thermo}" stroke="#123" stroke-dasharray="6 4" fill="none" stroke-width="2"/>
  <text x="600" y="{240 if el else 218}" font-size="11" fill="#123">thermocline</text>
  <rect x="20" y="185" width="70" height="20" fill="#6b8e4e"/><text x="22" y="180" font-size="12" fill="currentColor">Maritime Cont.</text>
  <rect x="690" y="185" width="60" height="20" fill="#8c7a5b"/><text x="688" y="180" font-size="12" fill="currentColor">S. America</text>
  <ellipse cx="{rise_x}" cy="70" rx="60" ry="22" fill="#cfd8e3" stroke="#8a99ab"/>
  <text x="{rise_x-44}" y="74" font-size="11" fill="#334">deep convection</text>
  <path d="M{rise_x},180 L{rise_x},100" stroke="currentColor" stroke-width="3" marker-end="url(#ah)" fill="none"/>
  <path d="M{rise_x+60},55 L{sink_x-20 if not el else sink_x+20},55" stroke="currentColor" stroke-width="2" marker-end="url(#ah)" fill="none" opacity="{1 if not el else 0.6}"/>
  <path d="M{sink_x},70 L{sink_x},170" stroke="currentColor" stroke-width="3" marker-end="url(#ah)" fill="none"/>
  <text x="{sink_x+8}" y="120" font-size="11" fill="currentColor">sinking, drier</text>
  <path d="M{sink_x-10 if not el else sink_x+10},190 L{rise_x+20 if not el else rise_x-20},190" stroke="currentColor" stroke-width="2" marker-end="url(#ah)" fill="none" opacity="0.8"/>
  <text x="{min(rise_x,sink_x)+120}" y="186" font-size="11" fill="currentColor">{'weakened / reversed trades' if el else 'easterly trade winds'}</text>
  <text x="70" y="315" font-size="11" fill="currentColor">Conceptual schematic only — not drawn from data, not to scale. Equatorial Pacific cross-section, west (left) to east (right).</text>
</svg>""", caption


PYRAMID_CSS = """
<style>
.bp-pyr{display:flex;flex-direction:column;align-items:center;gap:6px;margin:8px 0 4px}
.bp-layer{clip-path:polygon(var(--i) 0,calc(100% - var(--i)) 0,100% 100%,0 100%);
  color:#fff;text-align:center;padding:14px 12% 12px;width:100%;max-width:720px;box-sizing:border-box}
.bp-layer b{display:block;font-size:1.02rem;letter-spacing:.02em}
.bp-layer span{font-size:.82rem;opacity:.92}
.bp-l3{--i:38%;background:#b5542f;max-width:430px;padding-top:34px}
.bp-l2{--i:12%;background:#2f6f8f;max-width:580px}
.bp-l1{--i:6%;background:#26415e}
</style>"""

PYRAMID_HTML = PYRAMID_CSS + """
<div class="bp-pyr">
  <div class="bp-layer bp-l3"><b>Scientific Application</b><span>ENSO – Indonesia rainfall</span></div>
  <div class="bp-layer bp-l2"><b>G-NETS · Topological Interpretation</b>
    <span>Proposed investigational framework — not an established or validated theory</span></div>
  <div class="bp-layer bp-l1"><b>Scientific Discovery Engine</b>
    <span>Real observations → computed relationships → fitted equations → candidate hypotheses</span></div>
</div>"""
