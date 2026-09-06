# -*- coding: utf-8 -*-
"""Boje, fontovi i skaliranje na DPI ekrana."""

BG    = "#0c0e13"   # pozadina prozora
CARD  = "#151922"   # kartica
FIELD = "#1c2029"   # polje / neizabrano dugme
HOVER = "#232833"
LINE  = "#232935"   # tanke linije i ivice
TXT   = "#eef1f7"
MUTED = "#818b9e"   # sekundarni tekst
DIM   = "#5a6376"   # nalepnice
MINT  = "#34d399"   # akcenat
MINT_HI = "#4fe0ad"
MINT_DK = "#1d3b30"
INK   = "#07130f"   # tekst na mint podlozi
RED   = "#f87171"

YT    = "#f0282d"

FAM   = "Segoe UI"
FAM_B = "Segoe UI Semibold"

SCALE = 1.0


def postavi_skalu(dpi):
    global SCALE
    SCALE = dpi / 96.0


def s(px):
    """Pikseli skalirani na DPI ekrana."""
    return max(1, int(round(px * SCALE)))


def hx(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
