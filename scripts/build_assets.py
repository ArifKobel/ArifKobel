#!/usr/bin/env python3
"""Erzeugt die SVG-Grafiken für das GitHub-Profil (Hell + Dunkel).

Benötigt fonttools + brotli:
    pipx install fonttools && pipx inject fonttools brotli
    ~/.local/share/pipx/venvs/fonttools/bin/python scripts/build_assets.py
"""
import base64
import io
import os
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "scripts", "fonts")
OUT = os.path.join(ROOT, "assets")

THEMES = {
    "light": dict(
        ink="#1d1d1f", ink2="#6e6e73", link="#0066cc", tile="#f5f5f7",
        surface="#ffffff", chrome="#ececf0", canvas="#e3e3e8", line="#d2d2d7",
        mute="#c7c7cc", shadow=0.10, accent="#0071e3",
        wall_a="#dfe8f7", wall_b="#bccdeb", taskbar="#f3f3f3", device="#1d1d1f",
    ),
    "dark": dict(
        ink="#f5f5f7", ink2="#86868b", link="#2997ff", tile="#161617",
        surface="#1d1d1f", chrome="#2a2a2d", canvas="#111112", line="#3a3a3c",
        mute="#48484a", shadow=0.55, accent="#0a84ff",
        wall_a="#1c2a44", wall_b="#0e1626", taskbar="#202020", device="#3a3a3c",
    ),
}

PAPER_INK = "#1d1d1f"
PAPER_LINE = "#e3e3e8"


# --------------------------------------------------------------------------
# Schrift: Inter, pro Gewicht auf die verwendeten Zeichen reduziert

class Font:
    def __init__(self, weight):
        self.weight = weight
        self.path = os.path.join(FONTS, f"inter-{weight}.woff2")
        f = TTFont(self.path)
        self.cmap = f.getBestCmap()
        self.hmtx = f["hmtx"]
        self.upm = f["head"].unitsPerEm
        self.chars = set()

    def width(self, s, size, ls=0.0):
        units = sum(self.hmtx[self.cmap[ord(c)]][0] for c in s)
        return units * size / self.upm + ls * len(s)

    def data_uri(self):
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern", "liga", "calt", "tnum"]
        font = TTFont(self.path)
        sub = subset.Subsetter(opts)
        sub.populate(text="".join(sorted(self.chars)) + " ")
        sub.subset(font)
        buf = io.BytesIO()
        font.flavor = "woff2"
        font.save(buf)
        return "data:font/woff2;base64," + base64.b64encode(buf.getvalue()).decode()


class Svg:
    """Sammelt Elemente, merkt sich verwendete Glyphen und bettet die Schrift ein."""

    def __init__(self, w, h, label, fonts):
        self.w, self.h, self.label, self.fonts = w, h, label, fonts
        self.defs, self.css, self.body = [], [], []
        self.used = set()

    def text(self, x, y, s, size, weight=400, fill="#000", anchor="start", ls=0.0, cls="", extra=""):
        f = self.fonts[weight]
        f.chars.update(s)
        self.used.add(weight)
        c = f' class="{cls}"' if cls else ""
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        l = f' letter-spacing="{ls}"' if ls else ""
        return (f'<text{c} x="{x:.1f}" y="{y:.1f}"{a} font-size="{size}" font-weight="{weight}"{l} '
                f'fill="{fill}"{extra}>{escape(s)}</text>')

    def width(self, s, size, weight, ls=0.0):
        return self.fonts[weight].width(s, size, ls)

    def render(self, fonts_ready):
        faces = "".join(
            f"@font-face{{font-family:I;font-weight:{w};src:url({fonts_ready[w]}) format('woff2')}}"
            for w in sorted(self.used)
        )
        css = faces + "text{font-family:I,-apple-system,'Segoe UI',sans-serif;font-kerning:normal}" + "".join(self.css)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.label)}">'
            f"<defs>{''.join(self.defs)}</defs><style>{css}</style>{''.join(self.body)}</svg>\n"
        )


def anim(attr, keys, dur, discrete=False, ease=True):
    """SMIL-Animation aus [(sekunde, wert), ...]."""
    times = ";".join(f"{t / dur:.4f}" for t, _ in keys)
    values = ";".join(str(v) for _, v in keys)
    if discrete:
        mode = 'calcMode="discrete"'
    elif ease:
        splines = ";".join(["0.25 0.1 0.25 1"] * (len(keys) - 1))
        mode = f'calcMode="spline" keySplines="{splines}"'
    else:
        mode = ""
    return (f'<animate attributeName="{attr}" dur="{dur}s" repeatCount="indefinite" '
            f'keyTimes="{times}" values="{values}" {mode}/>')


def check_path(x, y, s, color, width=2.2):
    return (f'<path d="M{x} {y + s * .52} L{x + s * .38} {y + s * .88} L{x + s} {y + s * .12}" fill="none" '
            f'stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')


def tile_header(svg, t, name, tagline, link, cx=640):
    return "".join([
        svg.text(cx, 112, name, 56, 600, t["ink"], "middle", -1.4),
        svg.text(cx, 160, tagline, 25, 400, t["ink"], "middle", -0.2),
        svg.text(cx, 206, link, 20, 400, t["link"], "middle"),
    ])


def tile_frame(svg, t, w, h, inner, fade=True):
    """Transparenter Rahmen; angeschnittene Inhalte laufen unten weich aus."""
    svg.defs.append(
        f'<filter id="sh" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feDropShadow dx="0" dy="18" stdDeviation="28" flood-color="#000" flood-opacity="{t["shadow"]}"/></filter>'
    )
    if not fade:
        return inner
    svg.defs.append(
        f'<linearGradient id="fade" x1="0" y1="{h - 170}" x2="0" y2="{h}" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="{w}" height="{h}">'
        f'<rect width="{w}" height="{h}" fill="url(#fade)"/></mask>'
    )
    return f'<g mask="url(#m)">{inner}</g>'


def browser(svg, t, x, y, w, h, url):
    """Schlichtes Browserfenster; liefert (svg, inhalts_y)."""
    bar = 44
    parts = [
        f'<g filter="url(#sh)"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{t["surface"]}"/></g>',
        f'<path d="M{x} {y + bar} V{y + 14} a14 14 0 0 1 14 -14 H{x + w - 14} a14 14 0 0 1 14 14 V{y + bar} Z" fill="{t["chrome"]}"/>',
        f'<rect x="{x}" y="{y + bar}" width="{w}" height="1" fill="{t["line"]}"/>',
    ]
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        parts.append(f'<circle cx="{x + 22 + i * 20}" cy="{y + bar / 2}" r="6" fill="{c}"/>')
    if url:
        pw = 300
        parts.append(f'<rect x="{x + w / 2 - pw / 2}" y="{y + 10}" width="{pw}" height="24" rx="7" fill="{t["surface"]}" fill-opacity=".9"/>')
        parts.append(svg.text(x + w / 2, y + 27, url, 13, 500, t["ink2"], "middle"))
    return "".join(parts), y + bar + 1


# --------------------------------------------------------------------------
# App-Icons

ICONS = {
    # 48×48, Linien
    "doc": '<path d="M13 6h15l9 9v27H13z"/><path d="M28 6v9h9"/><path d="M19 25h12M19 32h8"/>',
    "bars": '<path d="M13 38V27M24 38V12M35 38V21" stroke-width="4.5"/>',
    "crop": '<path d="M8 17V8h9M31 8h9v9M40 31v9h-9M17 40H8v-9"/><circle cx="24" cy="24" r="2.5" fill="currentColor"/>',
    "key": '<circle cx="15" cy="24" r="8"/><path d="M23 24h19M37 24v7M31 24v5"/>',
    "leaf": '<path d="M10 38C10 20 22 10 40 9c1 18-9 30-27 30"/><path d="M10 38l16-16"/>',
    "folder": '<path d="M6 14a3 3 0 0 1 3-3h10l4 5h16a3 3 0 0 1 3 3v17a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3z"/><path d="M6 21h36"/>',
    "globe": '<circle cx="24" cy="24" r="16"/><path d="M8 24h32M24 8c-6 6-6 26 0 32M24 8c6 6 6 26 0 32"/>',
}

APPS = [
    # (Name, Icon, Farbe)
    ("Tintenfisch", "doc", "#5e5ce6"),
    ("Prezzy", "bars", "#ff9f0a"),
    ("NeatShot", "crop", "#0a84ff"),
    ("F*CK .SPASS", "key", "#ff375f"),
    ("EcoSchool", "leaf", "#30b350"),
    ("Bulkbox", "folder", "#12a7c4"),
    ("xTranslate", "globe", "#bf5af2"),
]


def lighten(hex_color, amount):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (round(c + (255 - c) * amount) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def app_icon(svg, x, y, size, icon, color):
    gid = f"ic-{icon}"
    if not any(f'id="{gid}"' in d for d in svg.defs):
        svg.defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
                        f'<stop offset="0" stop-color="{lighten(color, .22)}"/><stop offset="1" stop-color="{color}"/></linearGradient>')
    s = size / 48
    return (f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="{size * .225:.1f}" fill="url(#{gid})"/>'
            f'<g transform="translate({x + size * .2:.1f} {y + size * .2:.1f}) scale({s * .6:.4f})" fill="none" '
            f'stroke="#fff" color="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">{ICONS[icon]}</g>')


# --------------------------------------------------------------------------
# Hero

def hero(fonts, t):
    W, H = 1280, 570
    svg = Svg(W, H, "Moin, ich bin Arif. Software Engineer aus Hamburg.", fonts)
    svg.css.append(
        ".a{animation:up .9s cubic-bezier(.2,.8,.2,1) both}"
        "@keyframes up{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}"
    )
    inner = [
        svg.text(640, 132, "Moin, ich bin Arif.", 60, 600, t["ink"], "middle", -1.6, cls="a"),
        svg.text(640, 186, "Ich baue Websites und Web-Apps in Hamburg.", 25, 400, t["ink"], "middle", -0.2,
                 cls="a", extra=' style="animation-delay:.08s"'),
        svg.text(640, 220, "Und die Tools, die mir selbst gefehlt haben.", 25, 400, t["ink"], "middle", -0.2,
                 cls="a", extra=' style="animation-delay:.08s"'),
    ]
    l1, l2 = "arifkobel.com ›", "hallo@arifkobel.com ›"
    w1, w2, gap = svg.width(l1, 20, 400), svg.width(l2, 20, 400), 44
    lx = 640 - (w1 + gap + w2) / 2
    inner.append(f'<g class="a" style="animation-delay:.16s">'
                 + svg.text(lx, 276, l1, 20, 400, t["link"])
                 + svg.text(lx + w1 + gap, 276, l2, 20, 400, t["link"]) + "</g>")

    size, gap = 92, 34
    x0 = 640 - (len(APPS) * size + (len(APPS) - 1) * gap) / 2
    for i, (name, icon, color) in enumerate(APPS):
        x = x0 + i * (size + gap)
        inner.append(f'<g class="a" style="animation-delay:{.3 + i * .06:.2f}s">'
                     + app_icon(svg, x, 360, size, icon, color)
                     + svg.text(x + size / 2, 486, name, 14, 500, t["ink2"], "middle") + "</g>")

    svg.body.append("".join(inner))
    return svg


# --------------------------------------------------------------------------
# Werkzeuge + Werdegang, als Datenblatt

def specs(fonts, t):
    W, H = 1280, 430
    svg = Svg(W, H, "Werkzeuge und Werdegang", fonts)
    inner = [svg.text(80, 118, "Werkzeuge", 36, 600, t["ink"], ls=-0.9)]
    cols = [
        ("Sprachen", ["TypeScript", "PHP", "Rust", "Go", "WebAssembly"]),
        ("Frameworks", ["React", "Next.js", "Laravel", "TYPO3"]),
        ("Tools", ["Git", "Docker", "n8n", "Claude Code"]),
    ]
    for c, (label, items) in enumerate(cols):
        x = 80 + c * 180
        inner.append(f'<rect x="{x}" y="152" width="150" height="1" fill="{t["line"]}"/>')
        inner.append(svg.text(x, 184, label, 14, 600, t["ink2"]))
        for i, item in enumerate(items):
            inner.append(svg.text(x, 222 + i * 34, item, 19, 400, t["ink"]))

    rx = 720
    inner.append(svg.text(rx, 118, "Bisher", 36, 600, t["ink"], ls=-0.9))
    entries = [
        ("Seit 2026", "Web Engineer", "Websites und Web-Apps für Kunden."),
        ("2023 – 2026", "Ausbildung", "Fachinformatiker."),
    ]
    for i, (when, role, desc) in enumerate(entries):
        y = 152 + i * 124
        inner.append(f'<rect x="{rx}" y="{y}" width="480" height="1" fill="{t["line"]}"/>')
        inner.append(svg.text(rx, y + 32, when, 14, 600, t["ink2"]))
        inner.append(svg.text(rx, y + 66, role, 22, 600, t["ink"], ls=-0.3))
        inner.append(svg.text(rx, y + 96, desc, 17, 400, t["ink2"]))

    svg.body.append("".join(inner))
    return svg


# --------------------------------------------------------------------------
# Tintenfisch: Text im PDF wird direkt ersetzt

def tintenfisch(fonts, t):
    W, H, D = 1280, 760, 8.0
    svg = Svg(W, H, "Tintenfisch. PDFs bearbeiten. Ganz im Browser.", fonts)
    inner = [tile_header(svg, t, "Tintenfisch", "PDFs bearbeiten. Ganz im Browser.", "tintenfisch.app ›")]

    bx, by, bw, bh = 190, 270, 900, 560
    chrome, cy = browser(svg, t, bx, by, bw, bh, "tintenfisch.app")
    inner.append(chrome)

    # Werkzeugleiste
    ty = cy + 12
    for i in range(5):
        active = i == 0
        fill = t["accent"] if active else t["chrome"]
        inner.append(f'<rect x="{bx + 20 + i * 42}" y="{ty}" width="32" height="32" rx="8" fill="{fill}"/>')
    inner.append(svg.text(bx + 36, ty + 22, "T", 16, 600, "#fff", "middle"))
    for i in range(4):
        gx = bx + 20 + (i + 1) * 42
        inner.append(f'<rect x="{gx + 10}" y="{ty + 14}" width="12" height="4" rx="2" fill="{t["ink2"]}"/>')
    ex = svg.width("Exportieren", 14, 600) + 28
    inner.append(f'<rect x="{bx + bw - 20 - ex}" y="{ty}" width="{ex}" height="32" rx="8" fill="{t["accent"]}"/>')
    inner.append(svg.text(bx + bw - 20 - ex / 2, ty + 21, "Exportieren", 14, 600, "#fff", "middle"))

    # Arbeitsfläche + Seite
    ay = ty + 44
    inner.append(f'<rect x="{bx}" y="{ay}" width="{bw}" height="{by + bh - ay}" fill="{t["canvas"]}"/>')
    px, py, pw = 380, ay + 30, 520
    inner.append(f'<rect x="{px}" y="{py}" width="{pw}" height="600" rx="4" fill="#fff" filter="url(#sh)"/>')
    lx = px + 48
    inner.append(f'<rect x="{lx}" y="{py + 44}" width="56" height="8" rx="4" fill="{t["accent"]}"/>')
    inner.append(svg.text(lx, py + 100, "Projektangebot", 28, 700, PAPER_INK, ls=-0.6))

    # Die bearbeitete Zeile
    ly, fs = py + 140, 17
    prefix, old, new = "Gültig bis ", "31. Oktober", "30. November"
    inner.append(svg.text(lx, ly, prefix, fs, 400, PAPER_INK))
    sx = lx + svg.width(prefix, fs, 400)
    w_old = svg.width(old, fs, 400)

    # Markierung
    inner.append(
        f'<rect x="{sx - 2}" y="{ly - 17}" height="23" rx="3" fill="{t["accent"]}" fill-opacity=".22" width="0">'
        + anim("width", [(0, 0), (1.0, 0), (1.6, w_old + 4), (2.0, w_old + 4), (2.01, 0), (D, 0)], D)
        + "</rect>"
    )
    inner.append(svg.text(sx, ly, old, fs, 400, PAPER_INK).replace(
        "</text>", anim("opacity", [(0, 1), (2.0, 1), (2.01, 0), (7.6, 0), (7.61, 1), (D, 1)], D, discrete=True) + "</text>"))

    # Neuer Text, Buchstabe für Buchstabe
    steps = [(0, 0), (2.0, 0)]
    caret = [(0, sx), (2.0, sx)]
    t0, dt = 2.15, 0.085
    for i in range(1, len(new) + 1):
        wi = svg.width(new[:i], fs, 400)
        steps.append((t0 + i * dt, wi))
        caret.append((t0 + i * dt, sx + wi))
    end_w = svg.width(new, fs, 400)
    steps += [(7.6, end_w), (7.61, 0), (D, 0)]
    caret += [(7.6, sx + end_w), (D, sx + end_w)]
    svg.defs.append(f'<clipPath id="typed"><rect x="{sx}" y="{ly - 24}" height="34" width="0">'
                    + anim("width", steps, D, discrete=True) + "</rect></clipPath>")
    inner.append(f'<g clip-path="url(#typed)">{svg.text(sx, ly, new, fs, 400, PAPER_INK)}</g>')
    blink = [(0, 0), (1.95, 0), (1.96, 1)]
    k = t0 + len(new) * dt + 0.5
    on = True
    while k < 7.3:
        on = not on
        blink.append((k, 1 if on else 0))
        k += 0.5
    blink += [(7.3, 0), (D, 0)]
    inner.append(
        f'<rect x="0" y="{ly - 16}" width="1.6" height="21" fill="{t["accent"]}">'
        + anim("x", caret, D, discrete=True) + anim("opacity", blink, D, discrete=True) + "</rect>"
    )

    # Fließtext als ruhige Linien
    for i, lw in enumerate((420, 400, 410, 260)):
        inner.append(f'<rect x="{lx}" y="{ly + 40 + i * 22}" width="{lw}" height="7" rx="3.5" fill="{PAPER_LINE}"/>')
    ty2 = ly + 160
    inner.append(f'<rect x="{lx}" y="{ty2}" width="{pw - 96}" height="1" fill="{PAPER_LINE}"/>')
    for i in range(3):
        yy = ty2 + 30 + i * 30
        inner.append(f'<rect x="{lx}" y="{yy}" width="{180 - i * 30}" height="7" rx="3.5" fill="{PAPER_LINE}"/>')
        inner.append(f'<rect x="{px + pw - 48 - 70}" y="{yy}" width="70" height="7" rx="3.5" fill="{PAPER_LINE}"/>')

    # Hinweis: lokal gespeichert
    label = "Lokal gespeichert"
    lw = svg.width(label, 14, 500) + 52
    inner.append(
        f'<g opacity="0">'
        + anim("opacity", [(0, 0), (3.4, 0), (3.7, 1), (6.9, 1), (7.2, 0), (D, 0)], D)
        + f'<rect x="{px + pw + 24}" y="{ly - 30}" width="{lw}" height="34" rx="17" fill="{t["surface"]}" stroke="{t["line"]}"/>'
        + check_path(px + pw + 42, ly - 19, 12, "#30a14e")
        + svg.text(px + pw + 62, ly - 8, label, 14, 500, t["ink"])
        + "</g>"
    )

    svg.body.append(tile_frame(svg, t, W, H, "".join(inner)))
    return svg


# --------------------------------------------------------------------------
# Prezzy: Abstimmung am Handy, Ergebnis live auf der Folie

def prezzy(fonts, t):
    W, H, D = 1280, 760, 8.0
    svg = Svg(W, H, "Prezzy. Präsentationen, die zurückreden.", fonts)
    inner = [tile_header(svg, t, "Prezzy", "Präsentationen, die zurückreden.", "Zur Case Study ›")]

    bx, by, bw, bh = 150, 270, 820, 560
    chrome, cy = browser(svg, t, bx, by, bw, bh, None)
    inner.append(chrome)
    inner.append(svg.text(bx + bw / 2, by + 27, "Prezzy", 13, 600, t["ink2"], "middle"))

    sx = bx + 56
    inner.append(svg.text(sx, cy + 74, "Was nutzt ihr am liebsten?", 32, 600, t["ink"], ls=-0.6))

    options = [("React", .41), ("Laravel", .27), ("Next.js", .22), ("TYPO3", .10)]
    full = 540
    for i, (name, share) in enumerate(options):
        y = cy + 120 + i * 66
        inner.append(f'<rect x="{sx}" y="{y}" width="{full}" height="46" rx="10" fill="{t["chrome"]}"/>')
        fw = full * share / .41 * .86
        mid = fw * (.55 if i else .45)
        inner.append(
            f'<rect x="{sx}" y="{y}" height="46" rx="10" fill="{t["accent"]}" fill-opacity="{1 if i == 0 else .55}" width="0">'
            + anim("width", [(0, 0), (0.4, 0), (1.3, mid), (1.9, mid + (fw - mid) * (0.2 if i else 0)),
                             (2.9, fw), (7.2, fw), (7.7, 0), (D, 0)], D)
            + "</rect>"
        )
        inner.append(svg.text(sx + 18, y + 29, name, 17, 600, "#fff" if i == 0 else t["ink"]))
        inner.append(
            svg.text(sx + full + 64, y + 29, f"{round(share * 100)} %", 17, 500, t["ink2"], "end").replace(
                "</text>", anim("opacity", [(0, 0), (2.6, 0), (3.0, 1), (7.2, 1), (7.6, 0), (D, 0)], D, ease=False) + "</text>")
        )

    # Hinweis zum Mitmachen
    qy = cy + 410
    q = 22
    qx = sx
    inner.append(f'<rect x="{qx}" y="{qy}" width="{q}" height="{q}" rx="4" fill="none" stroke="{t["ink2"]}" stroke-width="2"/>')
    inner.append(f'<rect x="{qx + 6}" y="{qy + 6}" width="{q - 12}" height="{q - 12}" rx="1.5" fill="{t["ink2"]}"/>')
    inner.append(svg.text(qx + 34, qy + 17, "QR-Code scannen und mitmachen", 15, 500, t["ink2"]))

    # Handy
    phx, phy, phw, phh = 900, 330, 250, 520
    inner.append(f'<g filter="url(#sh)"><rect x="{phx}" y="{phy}" width="{phw}" height="{phh}" rx="40" fill="{t["device"]}"/></g>')
    inner.append(f'<rect x="{phx + 10}" y="{phy + 10}" width="{phw - 20}" height="{phh - 20}" rx="31" fill="{t["surface"]}"/>')
    inner.append(f'<rect x="{phx + phw / 2 - 36}" y="{phy + 22}" width="72" height="20" rx="10" fill="#000"/>')
    mx = phx + 28
    inner.append(svg.text(mx, phy + 82, "Prezzy", 13, 600, t["ink2"]))
    inner.append(svg.text(mx, phy + 112, "Was nutzt ihr", 19, 600, t["ink"], ls=-0.3))
    inner.append(svg.text(mx, phy + 136, "am liebsten?", 19, 600, t["ink"], ls=-0.3))
    for i, (name, _) in enumerate(options):
        y = phy + 160 + i * 54
        bwid = phw - 56
        if i == 0:
            inner.append(
                f'<rect x="{mx}" y="{y}" width="{bwid}" height="42" rx="10" fill="{t["chrome"]}">'
                + anim("fill", [(0, t["chrome"]), (1.2, t["chrome"]), (1.25, t["accent"]), (7.4, t["accent"]), (7.45, t["chrome"]), (D, t["chrome"])], D, discrete=True)
                + "</rect>"
            )
            inner.append(
                svg.text(mx + 16, y + 27, name, 15, 600, t["ink"]).replace(
                    "</text>", anim("fill", [(0, t["ink"]), (1.25, "#fff"), (7.45, t["ink"]), (D, t["ink"])], D, discrete=True) + "</text>")
            )
            inner.append(
                f'<g opacity="0">' + anim("opacity", [(0, 0), (1.3, 0), (1.5, 1), (7.3, 1), (7.4, 0), (D, 0)], D)
                + check_path(mx + bwid - 30, y + 15, 13, "#fff") + "</g>"
            )
        else:
            inner.append(f'<rect x="{mx}" y="{y}" width="{bwid}" height="42" rx="10" fill="{t["chrome"]}"/>')
            inner.append(svg.text(mx + 16, y + 27, name, 15, 600, t["ink"]))

    # Finger-Tipp
    tapx, tapy = mx + 150, phy + 181
    inner.append(
        f'<circle cx="{tapx}" cy="{tapy}" r="18" fill="{t["ink"]}" fill-opacity=".18" opacity="0">'
        + anim("opacity", [(0, 0), (0.9, 0), (1.1, 1), (1.4, 0), (D, 0)], D)
        + anim("r", [(0, 26), (0.9, 26), (1.25, 16), (1.4, 22), (D, 22)], D)
        + "</circle>"
    )

    svg.body.append(tile_frame(svg, t, W, H, "".join(inner)))
    return svg


# --------------------------------------------------------------------------
# NeatShot: Bereich aufziehen, Vorschau erscheint

def neatshot(fonts, t):
    W, H, D = 1280, 760, 7.0
    svg = Svg(W, H, "NeatShot. Screenshots unter Windows. Endlich schön.", fonts)
    inner = [tile_header(svg, t, "NeatShot", "Screenshots unter Windows. Endlich schön.", "neatshot.kobel.click ›")]

    sx, sy, sw, sh = 190, 262, 900, 450
    svg.defs.append(f'<clipPath id="scr"><rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="14"/></clipPath>')
    svg.defs.append(f'<linearGradient id="wall" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["wall_a"]}"/><stop offset="1" stop-color="{t["wall_b"]}"/></linearGradient>')
    scr = [f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="url(#wall)"/>']

    # Ein Fenster auf dem Desktop
    wx, wy, ww, wh = sx + 150, sy + 46, 600, 320
    scr.append(f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="8" fill="{t["surface"]}" filter="url(#sh)"/>')
    scr.append(f'<rect x="{wx}" y="{wy + 36}" width="{ww}" height="1" fill="{t["line"]}"/>')
    for i in range(3):
        cx = wx + ww - 22 - i * 40
        scr.append(f'<rect x="{cx - 5}" y="{wy + 17}" width="10" height="1.5" fill="{t["ink2"]}"/>' if i == 2 else
                   f'<rect x="{cx - 5}" y="{wy + 13}" width="10" height="10" fill="none" stroke="{t["ink2"]}" stroke-width="1.3"/>' if i == 1 else
                   f'<path d="M{cx - 5} {wy + 13} l10 10 M{cx + 5} {wy + 13} l-10 10" stroke="{t["ink2"]}" stroke-width="1.3"/>')
    scr.append(svg.text(wx + 16, wy + 23, "Entwurf.pdf", 12, 500, t["ink2"]))
    scr.append(f'<rect x="{wx + 32}" y="{wy + 64}" width="200" height="14" rx="7" fill="{t["ink"]}" fill-opacity=".85"/>')
    for i, lw in enumerate((520, 480, 500)):
        scr.append(f'<rect x="{wx + 32}" y="{wy + 98 + i * 20}" width="{lw}" height="7" rx="3.5" fill="{t["mute"]}"/>')
    scr.append(f'<rect x="{wx + 32}" y="{wy + 172}" width="250" height="118" rx="8" fill="{t["accent"]}" fill-opacity=".85"/>')
    scr.append(f'<rect x="{wx + 300}" y="{wy + 172}" width="268" height="118" rx="8" fill="{t["ink2"]}" fill-opacity=".35"/>')

    # Taskleiste
    tb = 44
    scr.append(f'<rect x="{sx}" y="{sy + sh - tb}" width="{sw}" height="{tb}" fill="{t["taskbar"]}" fill-opacity=".92"/>')
    for i in range(5):
        ix = sx + sw / 2 - 2.5 * 34 + i * 34 + 5
        fill = t["accent"] if i == 0 else t["mute"]
        scr.append(f'<rect x="{ix}" y="{sy + sh - tb + 11}" width="22" height="22" rx="5" fill="{fill}"/>')

    # Auswahl
    x0, y0 = wx - 20, wy - 16
    x1, y1 = wx + ww + 20, wy + wh + 16
    a0, a1, hold, shot = 0.9, 2.4, 3.1, 3.2
    dim = [(0, 0), (0.6, 0), (0.8, 1), (hold, 1), (shot, 0), (D, 0)]
    scr.append(f'<g opacity="0">{anim("opacity", dim, D)}'
               f'<path fill-rule="evenodd" fill="#000" fill-opacity=".38" d="M{sx} {sy}h{sw}v{sh}h{-sw}Z M{x0} {y0}h0v0h0Z">'
               + f'<animate attributeName="d" dur="{D}s" repeatCount="indefinite" calcMode="spline" '
                 f'keyTimes="0;{a0 / D:.4f};{a1 / D:.4f};1" keySplines="0.4 0 0.2 1;0.4 0 0.2 1;0 0 1 1" values="'
               + ";".join(
                   f"M{sx} {sy}h{sw}v{sh}h{-sw}Z M{x0} {y0}h{w}v{h}h{-w}Z"
                   for w, h in ((0, 0), (0, 0), (x1 - x0, y1 - y0), (x1 - x0, y1 - y0)))
               + '"/></path>'
               + f'<rect x="{x0}" y="{y0}" fill="none" stroke="#fff" stroke-width="1.5" width="0" height="0">'
               + anim("width", [(0, 0), (a0, 0), (a1, x1 - x0), (D, x1 - x0)], D)
               + anim("height", [(0, 0), (a0, 0), (a1, y1 - y0), (D, y1 - y0)], D)
               + "</rect>")
    # Fadenkreuz folgt der Ecke
    def cross(cx, cy):
        return f'M{cx - 11} {cy}h22 M{cx} {cy - 11}v22'
    scr.append(
        f'<path stroke="#fff" stroke-width="1.5" d="{cross(x0, y0)}">'
        + f'<animate attributeName="d" dur="{D}s" repeatCount="indefinite" calcMode="spline" '
          f'keyTimes="0;{a0 / D:.4f};{a1 / D:.4f};1" keySplines="0.4 0 0.2 1;0.4 0 0.2 1;0 0 1 1" '
          f'values="{cross(x0 - 60, y0 - 30)};{cross(x0, y0)};{cross(x1, y1)};{cross(x1, y1)}"/></path>'
    )
    label = f"{(x1 - x0) * 2} × {(y1 - y0) * 2}"
    lw = svg.width(label, 13, 600) + 20
    scr.append(f'<g opacity="0">{anim("opacity", [(0, 0), (a1 - 0.1, 0), (a1 + 0.1, 1), (hold, 1), (shot, 0), (D, 0)], D)}'
               f'<rect x="{x1 - lw - 10}" y="{y1 - 34}" width="{lw}" height="24" rx="6" fill="#000" fill-opacity=".72"/>'
               + svg.text(x1 - lw / 2 - 10, y1 - 17, label, 13, 600, "#fff", "middle") + "</g>")
    scr.append("</g>")

    # Blitz
    scr.append(f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="#fff" opacity="0">'
               + anim("opacity", [(0, 0), (shot, 0), (shot + 0.06, .7), (shot + 0.45, 0), (D, 0)], D, ease=False) + "</rect>")

    # Vorschau unten links
    th_w = 220
    img_w = th_w - 16
    img_h = img_w * (y1 - y0) / (x1 - x0)
    th_h = 8 + img_h + 10 + 26 + 10
    tx, ty = sx + 20, sy + sh - tb - th_h - 18
    svg.defs.append(f'<clipPath id="thumbimg"><rect x="{tx + 8}" y="{ty + 8}" width="{img_w}" height="{img_h:.1f}" rx="5"/></clipPath>')
    thumb = [f'<rect x="{tx}" y="{ty}" width="{th_w}" height="{th_h:.1f}" rx="12" fill="{t["surface"]}" stroke="{t["line"]}"/>']
    thumb.append(f'<g clip-path="url(#thumbimg)"><g transform="translate({tx + 8} {ty + 8}) scale({img_w / (x1 - x0):.4f}) translate({-x0} {-y0})">'
                 f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="url(#wall)"/>'
                 f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="8" fill="{t["surface"]}"/>'
                 f'<rect x="{wx + 32}" y="{wy + 64}" width="200" height="14" rx="7" fill="{t["ink"]}" fill-opacity=".85"/>'
                 f'<rect x="{wx + 32}" y="{wy + 172}" width="250" height="118" rx="8" fill="{t["accent"]}" fill-opacity=".85"/>'
                 f'<rect x="{wx + 300}" y="{wy + 172}" width="268" height="118" rx="8" fill="{t["ink2"]}" fill-opacity=".35"/>'
                 "</g></g>")
    by_ = ty + 8 + img_h + 10
    bwid = (img_w - 8) / 2
    for j, (lbl, primary) in enumerate((("Kopieren", True), ("Speichern", False))):
        bx_ = tx + 8 + j * (bwid + 8)
        thumb.append(f'<rect x="{bx_:.1f}" y="{by_:.1f}" width="{bwid:.1f}" height="26" rx="13" fill="{t["accent"] if primary else t["chrome"]}"/>')
        thumb.append(svg.text(bx_ + bwid / 2, by_ + 17, lbl, 12, 600, "#fff" if primary else t["ink"], "middle"))
    scr.append(f'<g opacity="0">'
               + anim("opacity", [(0, 0), (shot + 0.25, 0), (shot + 0.6, 1), (D - 0.6, 1), (D - 0.2, 0), (D, 0)], D)
               + f'<animateTransform attributeName="transform" type="translate" dur="{D}s" repeatCount="indefinite" calcMode="spline" '
                 f'keyTimes="0;{(shot + 0.25) / D:.4f};{(shot + 0.7) / D:.4f};1" keySplines="0 0 1 1;0.2 0.8 0.2 1;0 0 1 1" values="-40 0;-40 0;0 0;0 0"/>'
               + "".join(thumb) + "</g>")

    inner.append(f'<g filter="url(#sh)"><rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="14" fill="{t["surface"]}"/></g>')
    inner.append(f'<g clip-path="url(#scr)">{"".join(scr)}</g>')
    svg.body.append(tile_frame(svg, t, W, H, "".join(inner), fade=False))
    return svg


# --------------------------------------------------------------------------
# Kleine Kacheln

def small(fonts, t, name, lines, link):
    W, H = 620, 380
    svg = Svg(W, H, name, fonts)
    _, icon, color = next(a for a in APPS if a[0] == name)
    inner = [
        app_icon(svg, W / 2 - 32, 50, 64, icon, color),
        svg.text(W / 2, 168, name, 36, 600, t["ink"], "middle", -0.9),
        svg.text(W / 2, 214, lines[0], 19, 400, t["ink2"], "middle"),
        svg.text(W / 2, 242, lines[1], 19, 400, t["ink2"], "middle"),
        svg.text(W / 2, 306, link, 18, 400, t["link"], "middle"),
    ]
    svg.defs.append(f'<clipPath id="tile"><rect width="{W}" height="{H}" rx="28"/></clipPath>')
    svg.body.append(f'<g clip-path="url(#tile)"><rect width="{W}" height="{H}" fill="{t["tile"]}"/>{"".join(inner)}</g>')
    return svg


def footer(fonts, t):
    svg = Svg(1280, 260, "Sag Moin. hallo@arifkobel.com", fonts)
    svg.body.append(svg.text(640, 120, "Sag Moin.", 88, 700, t["ink"], "middle", -3))
    svg.body.append(svg.text(640, 185, "hallo@arifkobel.com ›", 24, 400, t["link"], "middle"))
    return svg


# --------------------------------------------------------------------------

def main():
    fonts = {w: Font(w) for w in (400, 500, 600, 700)}
    builds = []
    for theme, t in THEMES.items():
        builds += [(name, theme, svg) for name, svg in [
            ("hero", hero(fonts, t)),
            ("tintenfisch", tintenfisch(fonts, t)),
            ("prezzy", prezzy(fonts, t)),
            ("neatshot", neatshot(fonts, t)),
            ("fckspass", small(fonts, t, "F*CK .SPASS", ("Holt Passwörter aus Samsung Pass", "und macht sie wieder frei."), "Ansehen ›")),
            ("ecoschool", small(fonts, t, "EcoSchool", ("Umwelt-Quiz und Schulverwaltung.", "In einem."), "Ansehen ›")),
            ("bulkbox", small(fonts, t, "Bulkbox", ("Findet Dropbox-Links in langen Texten", "und sortiert sie in Ordner."), "Ansehen ›")),
            ("xtranslate", small(fonts, t, "xTranslate", ("Übersetzt XLIFF-Dateien.", "Automatisch."), "Auf GitHub ›")),
            ("specs", specs(fonts, t)),
            ("footer", footer(fonts, t)),
        ]]
    ready = {w: f.data_uri() for w, f in fonts.items()}
    os.makedirs(OUT, exist_ok=True)
    for name, theme, svg in builds:
        path = os.path.join(OUT, f"{name}-{theme}.svg")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg.render(ready))
        print(f"{os.path.relpath(path, ROOT):32s} {os.path.getsize(path) / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
