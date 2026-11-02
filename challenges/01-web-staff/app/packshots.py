"""
Product drawings for the DécaFlop storefront: line drawings of each product,
like the ones in a product manual, shown on light-grey tiles. Inline SVG only
(the Pi has no internet, so there are no image files to load).

packshot(slug, crop=None, ink=..., paper=..., label="") returns an <svg>.
`crop` is an (x, y, w, h) viewBox used for the zoomed gallery thumbnails.
`ink`/`paper` swap the colours (the home banner draws white on blue).
ui(name, size) returns a small interface icon (header, services, footer).
"""
import math

INK = "#1b2266"
PAPER = "#ffffff"


def _band(d, ink, paper, w=10):
    """A strap drawn as an outlined band (dark stroke with a lighter core)."""
    return (f'<path d="{d}" fill="none" stroke="{ink}" stroke-width="{w}"/>'
            f'<path d="{d}" fill="none" stroke="{paper}" stroke-width="{w - 3.8}"/>')


def _text(x, y, s, ink, size=10, anchor="middle", extra=""):
    return (f'<text x="{x}" y="{y}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" font-weight="700" '
            f'fill="{ink}" stroke="none" text-anchor="{anchor}" letter-spacing=".6"{extra}>{s}</text>')


D = 'fill="none" stroke-width="1.3"'      # inner detail line


def _mirror(pts):
    right = [(400 - x, y) for x, y in reversed(pts)]
    return "M" + " L".join(f"{x} {y}" for x, y in pts + right) + " Z"


# ------------------------------------------------------------- natation
def goggles(ink, paper):
    lens = "M78 200 C78 174 100 162 130 162 C164 162 193 172 193 197 C193 222 170 238 138 238 C102 238 78 224 78 200 Z"
    mir = 'transform="translate(400 0) scale(-1 1)"'
    inset = lambda k: f'translate(135.5 200) scale({k}) translate(-135.5 -200)'
    return (_band("M64 196 C70 120 330 120 336 196", ink, paper) +
            _band("M66 208 C76 142 324 142 334 208", ink, paper) +
            _band("M58 202 C50 205 44 209 38 215", ink, paper, 9) +
            _band("M342 202 C350 205 356 209 362 215", ink, paper, 9) +
            '<rect x="52" y="184" width="28" height="34" rx="8"/><rect x="320" y="184" width="28" height="34" rx="8"/>'
            f'<path d="M58 193h16M58 199h16M58 205h16M326 193h16M326 199h16M326 205h16" {D}/>'
            f'<path d="{lens}"/><path d="{lens}" {mir}/>'
            f'<path d="{lens}" transform="{inset(.92)}" {D}/>'
            f'<path d="{lens}" transform="translate(400 0) scale(-1 1) {inset(.92)}" {D}/>'
            f'<path d="{lens}" transform="{inset(.84)}" fill="none" stroke-width="1.8"/>'
            f'<path d="{lens}" transform="translate(400 0) scale(-1 1) {inset(.84)}" fill="none" stroke-width="1.8"/>'
            f'<path d="M100 192 C110 180 132 176 156 178" {D}/><path d="M300 192 C290 180 268 176 244 178" {D}/>'
            '<path d="M189 194 C195 186 205 186 211 194 L211 207 C205 200 195 200 189 207 Z"/>' +
            _text(135, 252, "NAGEFLOP", ink, 7))


def cap(ink, paper):
    return ('<path d="M84 272 C78 104 322 104 316 272 C260 290 140 290 84 272 Z"/>'
            f'<path d="M92 256 C150 272 250 272 308 256" {D}/>'
            f'<path d="M200 150 C196 170 196 186 198 198" {D} stroke-dasharray="4 3"/>'
            f'<path d="M128 170 C146 156 168 148 188 146" {D}/>'
            f'<path d="M104 238 C104 214 110 194 120 180" {D}/>' +
            _text(200, 228, "NAGEFLOP", ink, 18, extra=' font-style="italic"') +
            _text(200, 246, "SILICONE", ink, 8))


def wetsuit(ink, paper):
    pts = [(177, 56), (152, 64), (132, 72), (116, 84), (100, 108), (86, 150), (74, 200), (62, 248), (56, 270),
           (82, 277), (94, 228), (106, 178), (118, 140), (125, 126), (129, 168), (132, 212), (134, 238),
           (131, 262), (132, 300), (137, 338), (141, 358), (181, 358), (184, 322), (191, 288), (200, 274)]
    return (f'<path d="{_mirror(pts)}"/>'
            f'<path d="M125 124 C140 112 160 104 182 100 L218 100 C240 104 260 112 275 124 L274 160 '
            f'C246 180 154 180 126 160" fill="none" stroke-width="1.8"/>'
            f'<path d="M128 166 C156 186 244 186 272 166" {D}/>'
            f'<path d="M132 72 L177 56 L182 90 L140 104 L116 84 M268 72 L223 56 L218 90 L260 104 L284 84" {D}/>'
            f'<path d="M140 172 L144 250 M260 172 L256 250" {D} stroke-dasharray="4 3"/>'
            f'<path d="M134 296 L182 296 L180 322 L136 322 Z M266 296 L218 296 L220 322 L264 322 Z" {D}/>'
            f'<path d="M140 300 L176 318 M140 310 L162 320 M154 298 L180 310 M260 300 L224 318 M260 310 L238 320 M246 298 L220 310" {D}/>'
            '<path d="M177 56 C186 66 214 66 223 56 L222 68 C212 78 188 78 178 68 Z"/>'
            f'<path d="M59 261 L84 268 M341 261 L316 268 M140 348 L182 348 M260 348 L218 348" {D}/>' +
            _text(200, 146, "NAGEFLOP", ink, 13, extra=' font-style="italic"') +
            '<text x="0" y="0" transform="translate(150 286) rotate(-90)" font-family="Arial,sans-serif" font-weight="700" '
            f'font-size="8" fill="{ink}" stroke="none" letter-spacing=".8">TRI 500</text>')


def pullbuoy(ink, paper):
    def lobe(cy):
        return (f'<path d="M95 {cy} L95 {cy + 26} A105 44 0 0 0 305 {cy + 26} L305 {cy} Z"/>'
                f'<ellipse cx="200" cy="{cy}" rx="105" ry="44"/>'
                f'<ellipse cx="200" cy="{cy}" rx="92" ry="36" {D} stroke-dasharray="4 3"/>')
    return (lobe(252) +
            f'<path d="M150 170 L150 238 M250 170 L250 238" stroke-width="2.2"/>'
            '<path d="M150 168 L250 168 L250 236 L150 236 Z" stroke="none"/>'
            f'<path d="M150 168 L150 236 M250 168 L250 236" />' +
            lobe(140) + _text(200, 145, "NAGEFLOP", ink, 15, extra=' font-style="italic"') +
            _text(200, 258, "EVA", ink, 10))


def drybag(ink, paper):
    return (_band("M276 150 C330 176 334 262 290 292", ink, paper, 12) +
            '<path d="M128 132 L272 132 L280 318 C280 338 120 338 120 318 Z"/>'
            f'<path d="M121 318 C150 330 250 330 279 318" {D}/>'
            f'<path d="M150 140 L144 316 M250 140 L256 316" {D} stroke-dasharray="4 3"/>'
            '<rect x="116" y="100" width="168" height="34" rx="10"/>'
            f'<path d="M122 112 H278 M122 122 H278" {D}/>'
            f'<path d="M122 106 C140 76 168 80 186 86 M278 106 C260 76 232 80 214 86" stroke-width="2.2" fill="none"/>'
            '<rect x="186" y="76" width="28" height="22" rx="4"/>'
            f'<path d="M192 82 H208 M192 87 H208 M192 92 H208" {D}/>'
            '<rect x="268" y="142" width="14" height="18" rx="4"/>' +
            _text(200, 214, "NAGEFLOP", ink, 17, extra=' font-style="italic"') +
            _text(200, 236, "SAC ÉTANCHE 30 L", ink, 9))


# ----------------------------------------------------------------- vélo
def bike(ink, paper):
    spokes = "".join(
        f'<line x1="304" y1="262" x2="{304 + 50 * math.cos(a * math.pi / 9):.1f}" '
        f'y2="{262 + 50 * math.sin(a * math.pi / 9):.1f}"/>' for a in range(18))
    return ('<circle cx="100" cy="262" r="72"/><circle cx="100" cy="262" r="64"/>'
            f'<circle cx="100" cy="262" r="40" {D}/><circle cx="100" cy="262" r="9"/>' +
            _text(100, 214, "DISC 1.0", ink, 8) +
            '<circle cx="304" cy="262" r="72"/><circle cx="304" cy="262" r="64"/>'
            f'<circle cx="304" cy="262" r="50" fill="none"/>'
            f'<g stroke-width=".9">{spokes}</g><circle cx="304" cy="262" r="7"/>'
            f'<circle cx="100" cy="262" r="12" {D}/>'
            f'<path d="M186 248 L100 250 M186 296 L106 288" {D}/>'
            '<path d="M98 272 L110 292 L102 298 L92 282 Z"/>'
            '<path d="M186 266 L190 279 L104 269 L98 257 Z"/>'
            '<path d="M176 200 L183 212 L105 267 L96 258 Z"/>'
            '<path d="M160 162 L173 162 Q176 222 197 275 L181 281 Q160 224 160 162 Z"/>'
            '<path d="M266 152 L273 165 L173 173 L166 162 Z"/>'
            '<path d="M268 165 L285 188 L199 283 Q186 290 177 271 Z"/>'
            '<path d="M263 151 L278 149 L287 192 L272 196 Z"/>'
            '<path d="M274 192 L287 189 L308 258 L299 264 Z"/>' +
            '<text x="0" y="0" transform="translate(206 254) rotate(-48.5)" font-family="Arial,sans-serif" '
            f'font-weight="700" font-style="italic" font-size="15" fill="{ink}" stroke="none" letter-spacing=".5">PÉDALO</text>'
            '<text x="0" y="0" transform="translate(196 169) rotate(-4)" font-family="Arial,sans-serif" font-weight="700" '
            f'font-size="7" fill="{ink}" stroke="none" letter-spacing="1">RACE 900</text>'
            '<circle cx="186" cy="272" r="26" stroke-dasharray="2 1.6"/><circle cx="186" cy="272" r="21"/>'
            '<circle cx="186" cy="272" r="7"/>'
            '<path d="M182 274 L200 308 L210 304 L192 270 Z"/><rect x="196" y="304" width="22" height="7" rx="2"/>'
            '<path d="M161 162 L172 162 L170 138 L160 138 Z"/>'
            '<path d="M134 136 C150 127 186 127 197 133 L195 141 C176 138 150 140 136 144 Z"/>'
            '<path d="M270 154 L286 150" stroke-width="7"/><path d="M270 154 L286 150" stroke="' + paper + '" stroke-width="3.2"/>'
            + _band("M284 152 C298 152 306 160 308 176", ink, paper, 8)
            + _band("M276 144 L340 134 C344 133 346 130 346 122", ink, paper, 8) +
            '<rect x="268" y="134" width="30" height="9" rx="4"/>')


def helmet(ink, paper):
    return ('<path d="M68 226 C66 150 150 104 226 116 C290 126 336 168 352 206 C330 216 290 230 256 238 '
            'C196 252 120 258 84 248 C74 244 68 236 68 226 Z"/>'
            '<path d="M70 228 C78 262 124 276 172 268 L160 236 C130 240 96 238 70 228 Z"/>'
            f'<path d="M84 240 C104 256 132 262 162 258" {D}/>'
            f'<path d="M100 172 C160 140 250 142 330 192" {D}/>'
            f'<path d="M120 196 C180 176 250 180 318 210" {D} stroke-dasharray="4 3"/>'
            '<rect x="112" y="132" width="34" height="9" rx="4.5" transform="rotate(-18 129 136)"/>'
            '<rect x="158" y="120" width="34" height="9" rx="4.5" transform="rotate(-6 175 124)"/>'
            f'<circle cx="214" cy="226" r="14" {D}/>'
            f'<path d="M206 240 L196 300 M222 238 L236 296" {D}/>'
            '<rect x="200" y="294" width="34" height="12" rx="3"/>' +
            _text(250, 178, "PÉDALO", ink, 12, extra=' font-style="italic" transform="rotate(14 250 178)"'))


def bottle(ink, paper):
    return ('<path d="M186 90 L186 74 C186 64 214 64 214 74 L214 90 Z"/>'
            '<rect x="162" y="88" width="76" height="30" rx="6"/>'
            f'<path d="M174 92 V114 M186 92 V114 M198 92 V114 M210 92 V114 M222 92 V114" {D}/>'
            '<path d="M150 130 C150 122 156 118 164 118 L236 118 C244 118 250 122 250 130 L250 200 C240 214 240 232 250 246 '
            'L250 318 C250 332 238 340 226 340 L174 340 C162 340 150 332 150 318 L150 246 C160 232 160 214 150 200 Z"/>'
            f'<path d="M150 252 H250 M150 304 H250" {D}/>'
            f'<path d="M168 140 V190 M168 262 V296" {D}/>'
            f'<path d="M154 206 C162 216 162 230 154 240 M246 206 C238 216 238 230 246 240" {D}/>' +
            _text(200, 276, "BOFBOF", ink, 15, extra=' font-style="italic"') +
            _text(200, 294, "750 ML", ink, 9))


def repairkit(ink, paper):
    return ('<rect x="92" y="150" width="216" height="130" rx="26"/>'
            f'<path d="M110 172 H290" {D} stroke-dasharray="3 2"/>'
            '<path d="M286 166 L302 160 L306 172 L290 178 Z"/>' +
            _text(200, 228, "PÉDALO", ink, 16, extra=' font-style="italic"') +
            _text(200, 246, "KIT CREVAISON", ink, 8) +
            '<g transform="rotate(-16 170 300)"><path d="M90 292 H236 C246 292 250 300 246 306 L226 312 H90 '
            'C82 312 82 292 90 292 Z"/><path d="M96 302 H200" fill="none" stroke-width="1.3"/></g>'
            '<g transform="rotate(-8 190 320)"><path d="M110 312 H256 C266 312 270 320 266 326 L246 332 H110 '
            'C102 332 102 312 110 312 Z"/><path d="M116 322 H220" fill="none" stroke-width="1.3"/></g>'
            '<rect x="262" y="290" width="36" height="36" rx="8"/><rect x="292" y="276" width="30" height="30" rx="15"/>'
            f'<circle cx="307" cy="291" r="8" {D}/><path d="M270 300 H290 M270 308 H290 M270 316 H284" {D}/>')


def gloves(ink, paper):
    fingers = "".join(f'<rect x="{x}" y="{y}" width="28" height="70" rx="13"/>'
                      for x, y in ((150, 122), (182, 108), (214, 112), (246, 128)))
    return (fingers +
            f'<path d="M150 162 H178 M182 150 H210 M214 152 H242 M246 168 H274" {D}/>'
            '<path d="M140 232 L104 196 C96 188 104 174 116 180 L150 206 Z"/>'
            f'<path d="M112 186 L124 194" {D}/>'
            '<path d="M144 300 L138 214 C136 190 142 170 156 160 L262 158 C278 166 284 186 280 212 L262 300 Z"/>'
            f'<path d="M156 184 C190 176 232 176 266 186 L258 272 C224 280 184 280 150 272 Z" {D} stroke-dasharray="4 3"/>'
            '<rect x="146" y="292" width="114" height="44" rx="10"/>'
            '<rect x="178" y="300" width="70" height="28" rx="6"/>' +
            _text(213, 318, "PÉDALO", ink, 10, extra=' font-style="italic"') +
            f'<g {D}>' + "".join(f'<circle cx="{x}" cy="{y}" r="2"/>' for x in range(172, 252, 14)
                                 for y in range(198, 262, 14)) + '</g>')


# ------------------------------------------------------- course à pied
def shoe(ink, paper):
    return ('<path d="M56 296 C54 316 68 330 92 332 L322 332 C350 330 362 316 358 298 Z"/>'
            f'<path d="M60 312 C120 316 260 316 356 310" {D}/>'
            f'<path d="M80 332 V324 M110 332 V324 M140 332 V324 M170 332 V324 M200 332 V324 M230 332 V324 '
            f'M260 332 V324 M290 332 V324 M320 332 V324" {D}/>'
            '<path d="M62 298 C60 260 66 230 80 214 C96 206 116 204 132 206 C150 222 168 228 184 222 '
            'L214 190 C246 206 286 236 316 258 C340 272 356 284 358 298 Z"/>'
            '<path d="M80 214 L72 192 L92 188 L98 210" />'
            f'<path d="M184 222 C204 236 220 252 228 274" {D}/>'
            f'<path d="M214 190 C230 214 250 236 270 252" {D}/>'
            f'<path d="M204 222 L232 212 M214 234 L244 224 M226 246 L256 236 M238 258 L266 248" stroke-width="2.6" fill="none"/>'
            '<rect x="252" y="206" width="14" height="22" rx="4" transform="rotate(-24 259 217)"/>'
            f'<path d="M88 244 C120 262 170 268 224 268" {D}/>'
            f'<path d="M300 262 C310 270 318 278 322 290" {D} stroke-dasharray="3 2"/>' +
            _text(140, 290, "RUNFLOP", ink, 12, extra=' font-style="italic"'))


def watch(ink, paper):
    holes = "".join(f'<circle cx="200" cy="{y}" r="3.5" fill="none"/>' for y in (300, 318, 336))
    return ('<path d="M160 136 L166 42 C166 34 234 34 234 42 L240 136 Z"/>'
            f'<path d="M172 60 H228 M172 80 H228 M172 100 H228" {D}/>'
            '<path d="M160 264 L166 358 C166 366 234 366 234 358 L240 264 Z"/>' + holes +
            '<rect x="102" y="170" width="10" height="22" rx="3"/><rect x="102" y="208" width="10" height="22" rx="3"/>'
            '<rect x="288" y="188" width="10" height="24" rx="3"/>'
            '<circle cx="200" cy="200" r="88"/><circle cx="200" cy="200" r="76"/>'
            f'<circle cx="200" cy="200" r="66" {D}/>' +
            f'<g {D}>' + "".join(
                f'<line x1="{200 + 82 * math.cos(a * math.pi / 30):.1f}" y1="{200 + 82 * math.sin(a * math.pi / 30):.1f}" '
                f'x2="{200 + 86 * math.cos(a * math.pi / 30):.1f}" y2="{200 + 86 * math.sin(a * math.pi / 30):.1f}"/>'
                for a in range(0, 60, 5)) + '</g>' +
            _text(200, 182, "TRI", ink, 9) +
            _text(200, 214, "1:42:18", ink, 24, extra=' font-family="Arial,sans-serif"') +
            _text(200, 236, "38,4 KM", ink, 10) +
            f'<path d="M160 246 H240" {D}/>' + _text(200, 260, "RUNFLOP", ink, 7))


def racebelt(ink, paper):
    return (_band("M70 250 C70 208 330 208 330 250", ink, paper, 18) +
            '<rect x="128" y="150" width="144" height="112" rx="4"/>'
            f'<path d="M128 176 H272" {D}/>' + _text(200, 170, "DÉCAFLOP", ink, 11, extra=' font-style="italic"') +
            _text(200, 238, "357", ink, 52) +
            '<circle cx="142" cy="164" r="4"/><circle cx="258" cy="164" r="4"/>'
            '<rect x="134" y="206" width="12" height="22" rx="3"/><rect x="254" y="206" width="12" height="22" rx="3"/>' +
            _band("M70 250 C70 292 330 292 330 250", ink, paper, 18) +
            '<rect x="88" y="266" width="22" height="26" rx="5"/><rect x="290" y="266" width="22" height="26" rx="5"/>'
            '<rect x="184" y="280" width="32" height="18" rx="4"/>')


def runcap(ink, paper):
    return ('<path d="M310 238 C350 230 380 242 382 256 C352 268 300 268 262 254 Z"/>'
            f'<path d="M300 246 C330 244 356 248 372 256" {D}/>'
            '<path d="M96 248 C92 168 168 120 250 132 C302 142 326 190 322 248 Z"/>'
            f'<path d="M224 128 C200 168 186 210 184 248" {D}/>'
            f'<path d="M226 128 C258 166 274 206 278 248" {D}/>'
            f'<path d="M222 128 C170 146 130 190 118 248" {D}/>'
            f'<path d="M130 214 C120 230 118 240 118 248 M142 196 C128 220 126 236 126 248 M156 180 C140 210 136 232 136 248" '
            f'{D} stroke-dasharray="3 3"/>'
            '<ellipse cx="224" cy="128" rx="10" ry="5"/>'
            f'<path d="M96 248 C150 258 260 258 322 248" {D}/>' +
            _text(236, 210, "RUNFLOP", ink, 11, extra=' font-style="italic"'))


def gels(ink, paper):
    def sachet(rot, label, front=True):
        return (f'<g transform="rotate({rot} 200 340)">'
                '<path d="M156 160 L236 160 L244 168 L244 318 C244 326 238 330 232 330 L168 330 C162 330 156 326 156 318 Z"/>'
                f'<path d="M156 184 H244" {D}/><path d="M236 160 L232 172 L244 168" {D}/>'
                f'<path d="M166 168 H220" {D} stroke-dasharray="2 2"/>' +
                ((_text(200, 236, "GEL", ink, 22) + _text(200, 256, label, ink, 9) +
                  _text(200, 306, "32 G", ink, 9) + _text(200, 206, "BOFBOF", ink, 9, extra=' font-style="italic"'))
                 if front else "") + '</g>')
    return sachet(-16, "", False) + sachet(14, "", False) + sachet(0, "CITRON")


# ---------------------------------------------------------- other art
def pricetag(ink, paper):
    return ('<path d="M112 128 L232 128 L302 200 L232 272 L112 272 C102 272 96 266 96 256 L96 144 C96 134 102 128 112 128 Z" '
            'transform="rotate(-12 200 200)"/>'
            '<g transform="rotate(-12 200 200)">'
            '<circle cx="124" cy="200" r="10"/>' +
            _text(200, 214, "-30 %", ink, 34) + '</g>'
            f'<path d="M112 186 C84 160 70 120 86 92" {D} stroke-width="2"/>')


DRAW = {
    "lunettes-natation": goggles, "bonnet-silicone": cap, "combinaison-tri-500": wetsuit,
    "pull-buoy": pullbuoy, "sac-etanche-30l": drybag,
    "velo-chrono-race-900": bike, "casque-aero": helmet, "bidon-750": bottle,
    "kit-reparation": repairkit, "gants-velo": gloves,
    "chaussures-lacage-rapide": shoe, "montre-gps": watch, "ceinture-dossard": racebelt,
    "casquette-running": runcap, "gels-energetiques": gels,
    "etiquette": pricetag,
}


def packshot(slug, crop=None, ink=INK, paper=PAPER, label=""):
    vb = " ".join(str(v) for v in (crop or (0, 0, 400, 400)))
    aria = f' role="img" aria-label="{label}"' if label else ' aria-hidden="true" focusable="false"'
    return (f'<svg viewBox="{vb}" xmlns="http://www.w3.org/2000/svg"{aria}>'
            f'<g fill="{paper}" stroke="{ink}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round">'
            + DRAW[slug](ink, paper) + '</g></svg>')


# ------------------------------------------------------------- UI icons
_UI = {
    "menu": '<path d="M3 6h18M3 12h18M3 18h18"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20.5 20.5 16 16"/>',
    "pin": '<path d="M12 21s7-6.4 7-12a7 7 0 0 0-14 0c0 5.6 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4.3 4.2-6.5 8-6.5s7 2.2 8 6.5"/>',
    "bag": '<path d="M5 8h14l-1 13H6z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
    "store": '<path d="M3 9l2-5h14l2 5"/><path d="M4 9v11h16V9"/><path d="M3 9h18"/><path d="M10 20v-6h4v6"/>',
    "truck": '<path d="M2 6h12v10H2z"/><path d="M14 9h4l3 3v4h-7"/><circle cx="6" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
    "return": '<path d="M9 14 4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    "card": '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/>',
    "wrench": '<path d="M14.5 6.5a4 4 0 0 0 5 5L12 19a2.1 2.1 0 0 1-3-3l7.5-7.5a4 4 0 0 1-2-2z"/>',
    "bike": '<circle cx="6" cy="16" r="4"/><circle cx="18" cy="16" r="4"/><path d="M6 16l4-8h5l3 8M10 8l3 8M9 6h3"/>',
    "tag": '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "phone": '<path d="M5 3h4l2 5-2.5 1.5a11 11 0 0 0 6 6L16 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 5a2 2 0 0 1 2-2z"/>',
    "wave": '<path d="M2 9c2-2 4-2 6 0s4 2 6 0 4-2 6 0M2 15c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/>',
    "run": '<circle cx="14" cy="4.5" r="2"/><path d="M8 21l3-6 3 2 1 4M6 12l3-4h5l2 4 3 1M11 15l1-5"/>',
}


def ui(name, size=24):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
            f'{_UI[name]}</svg>')
