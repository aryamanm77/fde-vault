#!/usr/bin/env python3
"""FDE-VAULT startup motion identity.

A ~1.2s, time-based (not frame-count-based) terminal animation:

  Stage 1  0.00-0.45s  Geometric vault-dial mark materializes along a diagonal
                       light front, then locks in with a single crisp flash.
  Stage 2  0.45-0.85s  A slanted specular band sweeps left-to-right across the
                       F D E wordmark, revealing it and interpolating
                       warm-ivory -> burnished-amber as it passes.
  Stage 3  0.85-1.20s  One status line settles:
                       "Initializing vault session..." -> "Ready."

Pure Python 3 stdlib. Never emits anything when stdout is not a TTY.

Public API
    play_startup_animation(skip=False)   # bypasses with zero delay if skipped
    consume_no_anim_flag(argv=None)      # strips --no-anim from argv, returns bool

Bypassed when: skip=True, --no-anim in argv, FDE_NO_ANIM=1, TERM=dumb,
or stdout is not a TTY. NO_COLOR keeps the motion but drops all color.
"""

import math
import os
import shutil
import sys
import time

__all__ = ["play_startup_animation", "consume_no_anim_flag", "should_skip"]

# --------------------------------------------------------------------------- #
# Timing
# --------------------------------------------------------------------------- #
DURATION = 1.20
FPS = 60
T_MARK = (0.00, 0.45)
T_WORD = (0.45, 0.85)
T_STATUS = (0.85, 1.20)
T_STATUS_SWAP = 1.03  # "Initializing..." -> "Ready."

# --------------------------------------------------------------------------- #
# Palette (warm ivory -> burnished amber)
# --------------------------------------------------------------------------- #
AMBER_DEEP = (150, 92, 30)
AMBER = (206, 138, 46)
GOLD = (234, 182, 92)
IVORY = (248, 240, 222)
SPEC = (255, 251, 240)
MUTED = (150, 140, 124)
SUB = (170, 128, 68)

HIDE, SHOW, RESET = "\033[?25l", "\033[?25h", "\033[0m"


# --------------------------------------------------------------------------- #
# Math / easing
# --------------------------------------------------------------------------- #
def _clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def _out_cubic(x):
    return 1.0 - (1.0 - _clamp(x)) ** 3


def _out_quad(x):
    x = _clamp(x)
    return 1.0 - (1.0 - x) * (1.0 - x)


def _smooth(x):
    x = _clamp(x)
    return x * x * (3.0 - 2.0 * x)


def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def _grad(stops, t):
    t = _clamp(t) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    return _lerp(stops[i], stops[i + 1], t - i)


def _span(t, window):
    return _clamp((t - window[0]) / (window[1] - window[0]))


# --------------------------------------------------------------------------- #
# Color output (24-bit -> 256 -> none)
# --------------------------------------------------------------------------- #
def _color_mode():
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        return "none"
    return "truecolor"


def _to256(c):
    r, g, b = (int(round(v)) for v in c)
    if max(r, g, b) - min(r, g, b) < 10:  # near-grey -> grey ramp
        v = int(round((r + g + b) / 3 / 255 * 23))
        return 232 + v
    q = lambda v: int(round(v / 255 * 5))
    return 16 + 36 * q(r) + 6 * q(g) + q(b)


class _Ink:
    def __init__(self, mode):
        self.mode = mode

    def fg(self, c):
        if self.mode == "truecolor":
            return "\033[38;2;%d;%d;%dm" % tuple(int(round(v)) for v in c)
        if self.mode == "256":
            return "\033[38;5;%dm" % _to256(c)
        return ""

    def bg(self, c):
        if self.mode == "truecolor":
            return "\033[48;2;%d;%d;%dm" % tuple(int(round(v)) for v in c)
        if self.mode == "256":
            return "\033[48;5;%dm" % _to256(c)
        return ""

    def key(self, c):
        return tuple(int(round(v)) for v in c) if self.mode == "truecolor" else _to256(c) if self.mode == "256" else 0

    def text(self, s, c):
        return (self.fg(c) + s + RESET) if self.mode != "none" else s


def _cells(pix, w, h, ink):
    """Rasterize a w x h pixel grid (None | rgb) into half-block cell rows."""
    rows = []
    for cy in range(0, h, 2):
        out, cur_fg, cur_bg = [], None, False
        for x in range(w):
            top = pix[cy][x]
            bot = pix[cy + 1][x] if cy + 1 < h else None
            if top is None and bot is None:
                if cur_bg:
                    out.append("\033[49m"); cur_bg = False
                out.append(" ")
                continue
            if ink.mode == "none":
                out.append("█" if top is not None and bot is not None else "▀" if top is not None else "▄")
                continue
            if top is not None and bot is not None and ink.key(top) != ink.key(bot):
                want_fg, want_bg, ch = top, bot, "▀"
            elif top is not None and bot is not None:
                want_fg, want_bg, ch = top, None, "█"
            elif top is not None:
                want_fg, want_bg, ch = top, None, "▀"
            else:
                want_fg, want_bg, ch = bot, None, "▄"
            if want_bg is None and cur_bg:
                out.append("\033[49m"); cur_bg = False
            if want_bg is not None:
                out.append(ink.bg(want_bg)); cur_bg = True
            k = ink.key(want_fg)
            if k != cur_fg:
                out.append(ink.fg(want_fg)); cur_fg = k
            out.append(ch)
        if ink.mode != "none":
            out.append(RESET)
        rows.append("".join(out))
    return rows


# --------------------------------------------------------------------------- #
# Geometry: the mark (vault dial) and the F D E wordmark
# --------------------------------------------------------------------------- #
_N = 16  # mark is 16x16 half-block pixels -> 16 cols x 8 rows (square pixels)


def _build_mark():
    """Chamfered octagonal ring + diamond core + four cardinal dial ticks."""
    c, cells = (_N - 1) / 2.0, []
    for y in range(_N):
        for x in range(_N):
            dx, dy = abs(x - c), abs(y - c)
            d = max(dx, dy, (dx + dy) / 1.5)
            if 5.9 <= d <= 7.6:
                cells.append((x, y, "ring"))
            elif dx + dy <= 4.0:
                cells.append((x, y, "core"))
            elif (dx <= 0.5 and 4.0 < dy < 6.0) or (dy <= 0.5 and 4.0 < dx < 6.0):
                cells.append((x, y, "tick"))
    return cells


_MARK = _build_mark()
_DELAY = {"ring": 0.0, "core": 0.10, "tick": 0.20}

_FONT = {  # 6 x 8 px glyphs, 2px strokes
    "F": ["######", "######", "##....", "####..", "####..", "##....", "##....", "##...."],
    "D": ["#####.", "######", "##..##", "##..##", "##..##", "##..##", "######", "#####."],
    "E": ["######", "######", "##....", "####..", "####..", "##....", "######", "######"],
}
_GAP = 3
_WORD = [[] for _ in range(8)]
for _i, _ch in enumerate("FDE"):
    for _r in range(8):
        _WORD[_r].append(_FONT[_ch][_r])
        if _i < 2:
            _WORD[_r].append("." * _GAP)
_WORD = ["".join(r) for r in _WORD]
_WW, _WH = len(_WORD[0]), 8  # 24 x 8

_MARK_COLS, _SEP = _N, 5
_COMP_W = _MARK_COLS + _SEP + _WW  # 45
_SUBTITLE = "V A U L T"
_TINY = "◆ F D E   V A U L T"


# --------------------------------------------------------------------------- #
# Frame composition
# --------------------------------------------------------------------------- #
def _mark_pixels(t):
    p1 = _out_quad(_span(t, T_MARK))
    front = p1 * 1.32  # overshoots 1.0 so the glow fully clears the mark
    flash = math.exp(-(t - T_MARK[1]) * 9.0) * 0.40 if t > T_MARK[1] else 0.0
    pix = [[None] * _N for _ in range(_N)]
    for x, y, reg in _MARK:
        u = (x + y) / (2.0 * (_N - 1))
        thr = front - _DELAY[reg]
        if u > thr:
            continue
        if reg == "ring":
            base = _grad([AMBER_DEEP, AMBER, GOLD], u)
        elif reg == "core":
            base = _lerp(GOLD, IVORY, u)
        else:
            base = AMBER
        glow = _clamp(1.0 - (thr - u) / 0.28) ** 1.5
        c = _lerp(base, SPEC, 0.9 * glow)
        pix[y][x] = _lerp(c, SPEC, flash) if flash > 0.002 else c
    return pix


def _band_color(xp, s, ypos):
    """Wordmark/tiny-text color at slanted coordinate xp for band center s."""
    settled = _lerp(IVORY, AMBER, 0.15 + 0.70 * ypos)
    base = _lerp(AMBER_DEEP, settled, _smooth((s - xp) / 8.0))
    g = math.exp(-((xp - s) ** 2) / (2 * 2.6 ** 2))
    return _lerp(base, SPEC, 0.9 * g)


def _word_pixels(t):
    p2 = _out_quad(_span(t, T_WORD))
    s = -4.0 + p2 * 40.0
    pix = [[None] * _WW for _ in range(_WH)]
    if t <= T_WORD[0]:
        return pix
    for y in range(_WH):
        for x in range(_WW):
            if _WORD[y][x] != "#":
                continue
            xp = x + 0.6 * y
            if xp <= s + 4.0:
                pix[y][x] = _band_color(xp, s, y / 7.0)
    return pix


def _typed(text, frac):
    return text[: int(round(len(text) * _clamp(frac)))]


def _subtitle(t, ink):
    n = int(round(len(_SUBTITLE) * _out_cubic(_clamp((t - 0.65) / 0.25))))
    out = "".join(ink.text(ch, SUB) if ch != " " else " " for ch in _SUBTITLE[:n])
    return out + " " * (_WW - n)


_STATUS_W = 32


def _status(t, ink):
    if t < T_STATUS[0]:
        return " " * _STATUS_W
    if t < T_STATUS_SWAP:
        msg = _typed("Initializing vault session...", _out_cubic((t - T_STATUS[0]) / 0.12))
        vis = 2 + len(msg)
        return ink.text("●", AMBER) + " " + ink.text(msg, MUTED) + " " * (_STATUS_W - vis)
    k = _out_cubic((t - T_STATUS_SWAP) / (DURATION - T_STATUS_SWAP))
    dot = _lerp(SPEC, AMBER, k)
    return ink.text("●", dot) + " " + ink.text("Ready.", IVORY) + " " * (_STATUS_W - 8)


def _frame_full(t, ink, left):
    pad = " " * left
    mark = _cells(_mark_pixels(t), _N, _N, ink)
    word = _cells(_word_pixels(t), _WW, _WH, ink)
    lines = []
    for r in range(8):
        right = word[r - 1] if 1 <= r <= 4 else _subtitle(t, ink) if r == 6 else ""
        lines.append(pad + mark[r] + " " * _SEP + right)
    lines.append("")
    lines.append(pad + " " * ((_COMP_W - _STATUS_W) // 2) + _status(t, ink))
    return lines


def _frame_tiny(t, ink, left):
    s = -4.0 + _out_quad(_span(t, (0.0, 0.85))) * (len(_TINY) + 10)
    out = []
    for i, ch in enumerate(_TINY):
        if ch == " " or i > s + 2:
            out.append(" ")
        else:
            out.append(ink.text(ch, _band_color(float(i), s, 0.3)))
    pad = " " * left
    st = _status(t, ink)
    return [pad + "".join(out), "", pad + st]


# --------------------------------------------------------------------------- #
# Skip logic / entrypoints
# --------------------------------------------------------------------------- #
def consume_no_anim_flag(argv=None):
    """Remove --no-anim from argv (default sys.argv) and report whether it was present."""
    argv = sys.argv if argv is None else argv
    found = False
    while "--no-anim" in argv:
        argv.remove("--no-anim")
        found = True
    return found


def should_skip(skip=False):
    if skip or "--no-anim" in sys.argv:
        return True
    if os.environ.get("FDE_NO_ANIM", "").strip().lower() in ("1", "true", "yes", "on"):
        return True
    try:
        if not sys.stdout.isatty():
            return True
    except Exception:
        return True
    return os.environ.get("TERM") == "dumb"


def _layout():
    cols = shutil.get_terminal_size((80, 24)).columns
    if cols >= _COMP_W + 4:
        return _frame_full, (cols - _COMP_W) // 2, 10
    if cols >= len(_TINY) + 2:
        return _frame_tiny, (cols - len(_TINY)) // 2, 3
    return None, 0, 0


def play_startup_animation(skip: bool = False) -> None:
    """Play the ~1.2s FDE-VAULT intro. No-op (zero delay) when skipped or non-TTY."""
    if should_skip(skip):
        return
    frame_fn, left, n = _layout()
    if frame_fn is None:
        return
    if os.name == "nt":
        os.system("")  # enable VT processing on modern Windows consoles

    ink, out = _Ink(_color_mode()), sys.stdout
    finished = False
    try:
        out.write(HIDE + "\n" * (n - 1) + "\033[%dA\r" % (n - 1))
        start, dt, i = time.perf_counter(), 1.0 / FPS, 0
        while True:
            t = time.perf_counter() - start
            last = t >= DURATION
            lines = frame_fn(min(t, DURATION), ink, left)
            buf = "\033[K\n".join(lines) + "\033[K"
            if last:
                out.write("\r" + buf + "\n")
                out.flush()
                finished = True
                break
            out.write("\r" + buf + "\033[%dA\r" % (n - 1))
            out.flush()
            i += 1
            wait = start + i * dt - time.perf_counter()
            if wait > 0:
                time.sleep(wait)
    finally:
        if not finished:  # interrupted: park the cursor below the block
            out.write("\033[%dB\r\n" % (n - 1))
        out.write(RESET + SHOW)
        out.flush()


def _main(argv):
    if "--frame" in argv:  # debug: print one frame at time T, no cursor tricks
        t = float(argv[argv.index("--frame") + 1])
        fn, left, _ = _layout()
        fn = fn or _frame_tiny
        sys.stdout.write("\n".join(fn(t, _Ink(_color_mode()), left)) + RESET + "\n")
        return 0
    play_startup_animation(skip="--no-anim" in argv)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
