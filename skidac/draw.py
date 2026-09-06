# -*- coding: utf-8 -*-
"""Crtanje pozadina i ikonica.

Tkinter nema zaobljene ivice ni antialiasing, pa se sve crta Pillow-om
u 4x rezoluciji pa smanjuje na LANCZOS — ivice ispadnu glatke.
"""

from PIL import Image, ImageDraw, ImageTk

from .theme import CARD, YT, hx

SS = 4          # supersampling
_kes = {}       # gotove slike, da se ne crta na svaki hover


def rr(w, h, r, fill, bg, outline=None, ow=1):
    """Zaobljeni pravougaonik kao slika, već spojen sa pozadinom."""
    kljuc = (w, h, r, fill, bg, outline, ow)
    if kljuc in _kes:
        return _kes[kljuc]
    w, h = max(1, int(w)), max(1, int(h))
    im = Image.new("RGB", (w * SS, h * SS), hx(bg))
    ImageDraw.Draw(im).rounded_rectangle(
        [0, 0, w * SS - 1, h * SS - 1], radius=r * SS, fill=hx(fill),
        outline=hx(outline) if outline else None, width=ow * SS)
    slika = ImageTk.PhotoImage(im.resize((w, h), Image.LANCZOS))
    _kes[kljuc] = slika
    return slika


def zaobli(im, r):
    """Zaobli uglove fotografije."""
    w, h = im.size
    maska = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(maska).rounded_rectangle(
        [0, 0, w * SS - 1, h * SS - 1], radius=r * SS, fill=255)
    im.putalpha(maska.resize((w, h), Image.LANCZOS))
    return im


def uklopi(im, w, h):
    """Iseci sliku na zadati odnos stranica i smanji."""
    ci, ch = im.size
    cilj = w / h
    if ci / ch > cilj:
        nova = int(ch * cilj)
        im = im.crop(((ci - nova) // 2, 0, (ci + nova) // 2, ch))
    else:
        nova = int(ci / cilj)
        im = im.crop((0, (ch - nova) // 2, ci, (ch + nova) // 2))
    return im.resize((w, h), Image.LANCZOS)


def _okvir(velicina, bg):
    u = velicina * SS
    im = Image.new("RGB", (u, u), hx(bg))
    return im, ImageDraw.Draw(im), u


def ikona_youtube(velicina, bg=CARD):
    im, d, u = _okvir(velicina, bg)
    d.rounded_rectangle([0, 0, u - 1, u - 1], radius=int(u * 0.28), fill=hx(YT))
    d.polygon([(u * 0.40, u * 0.29), (u * 0.40, u * 0.71), (u * 0.73, u * 0.50)],
              fill=(255, 255, 255))
    return ImageTk.PhotoImage(im.resize((velicina, velicina), Image.LANCZOS))


def ikona_instagram(velicina, bg=CARD):
    """Instagram gradijent (žuta → roze → ljubičasta) po dijagonali."""
    u = velicina * SS
    grad = Image.new("RGB", (u, u))
    d = ImageDraw.Draw(grad)
    stope = [(0.0, hx("#f9ce34")), (0.45, hx("#ee2a7b")), (1.0, hx("#6228d7"))]
    for i in range(2 * u):
        t = i / (2 * u - 1)
        for j in range(len(stope) - 1):
            a, ca = stope[j]
            b, cb = stope[j + 1]
            if a <= t <= b:
                k = (t - a) / (b - a)
                boja = tuple(int(ca[n] + (cb[n] - ca[n]) * k) for n in range(3))
                break
        d.line([(i, 0), (0, i)], fill=boja, width=2)

    maska = Image.new("L", (u, u), 0)
    ImageDraw.Draw(maska).rounded_rectangle(
        [0, 0, u - 1, u - 1], radius=int(u * 0.28), fill=255)
    im = Image.new("RGB", (u, u), hx(bg))
    im.paste(grad, (0, 0), maska)

    d = ImageDraw.Draw(im)
    lw = max(1, int(u * 0.055))
    b = (255, 255, 255)
    d.rounded_rectangle([u * 0.24, u * 0.24, u * 0.76, u * 0.76],
                        radius=int(u * 0.17), outline=b, width=lw)
    d.ellipse([u * 0.38, u * 0.38, u * 0.62, u * 0.62], outline=b, width=lw)
    d.ellipse([u * 0.63, u * 0.31, u * 0.70, u * 0.38], fill=b)
    return ImageTk.PhotoImage(im.resize((velicina, velicina), Image.LANCZOS))
