# -*- coding: utf-8 -*-
"""Boje, fontovi i skaliranje na DPI ekrana.

Pozadina je zeleni gradijent i sve je staklo, pa su boje ovde uglavnom
tekst i akcenti — povrsine se racunaju iz same pozadine (vidi draw.py).
"""

DUBINA   = "#010403"      # najtamnija tacka gradijenta
ZELENA   = "#052a20"
SMARAGD  = "#074b39"
TIRKIZ   = "#07403d"
MENTA    = "#3ff0ae"
MENTA_HI = "#6bffc9"

TXT      = "#f4faf7"      # glavni tekst
TXT2     = "#d8ece4"      # sekundarni
TXT3     = "#a6c2b6"      # sitne nalepnice
INK      = "#05261a"      # tekst na mentol podlozi
CRVENA   = "#ff9a90"

FAM      = "Segoe UI"
FAM_B    = "Segoe UI Semibold"
FAM_N    = "Segoe UI"     # naslovi; zameni se ako postoji Segoe UI Variable

SCALE = 1.0


def postavi_skalu(dpi):
    global SCALE
    SCALE = dpi / 96.0


def izaberi_fontove(root):
    """Windows 11 ima Segoe UI Variable — lepsi je za naslove."""
    global FAM_N
    try:
        from tkinter import font
        if "Segoe UI Variable Display" in set(font.families(root)):
            FAM_N = "Segoe UI Variable Display"
    except Exception:
        pass


def s(px):
    """Pikseli skalirani na DPI ekrana."""
    return max(1, int(round(px * SCALE)))


def hx(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
