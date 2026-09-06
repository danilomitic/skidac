# -*- coding: utf-8 -*-
"""Pozadinski gradijent, staklo i ikonice — sve se crta Pillow-om.

Tkinter nema ni providnost ni blur. Zato se cela pozadina prozora
generiše kao slika, a svaki stakleni panel se pravi tako što se isečak
pozadine ISPOD njega zamuti i posvetli. To je pravo staklo, ne imitacija —
panel stvarno pokazuje ono što je iza njega.
"""

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageTk

from .theme import DUBINA, MENTA, SMARAGD, TIRKIZ, ZELENA, hx

SS = 4              # supersampling za glatke ivice
_poz_kes = {}
_ikone = {}


# ---------------------------------------------------------------- pozadina

def pozadina(w, h):
    """Zeleni mesh gradijent: mrlje boje, jako zamućene, pa zrno preko."""
    if (w, h) in _poz_kes:
        return _poz_kes[(w, h)]

    mw, mh = max(8, w // 6), max(8, h // 6)
    im = Image.new("RGB", (mw, mh), hx(DUBINA))
    d = ImageDraw.Draw(im)

    # (x, y, poluprečnik, boja) — u udelima veličine, da radi na svakom DPI
    # manje mrlje, sa tamnim prostorom izmedju — inace se sve slije u jednu zelenu
    for fx, fy, fr, boja in (
        (0.04, -0.04, 0.34, "#3ff0ae"),
        (0.40, 0.08, 0.24, SMARAGD),
        (1.02, 0.14, 0.30, "#0ea5a0"),
        (0.72, 0.52, 0.26, ZELENA),
        (-0.04, 0.66, 0.24, TIRKIZ),
        (0.98, 0.98, 0.30, SMARAGD),
    ):
        x, y, r = fx * mw, fy * mh, fr * min(mw, mh)
        d.ellipse([x - r, y - r, x + r, y + r], fill=hx(boja))

    im = im.filter(ImageFilter.GaussianBlur(min(mw, mh) * 0.26))
    im = im.resize((w, h), Image.BICUBIC)
    im = ImageEnhance.Brightness(im).enhance(0.62)   # neka ostane duboko
    im = ImageEnhance.Color(im).enhance(1.15)

    # sve tamnije ka dnu, da tekst ima gde da sedne
    pad = Image.new("L", (1, h))
    for y in range(h):
        pad.putpixel((0, y), int(18 + 200 * (y / max(1, h - 1)) ** 1.35))
    im = Image.composite(Image.new("RGB", (w, h), hx(DUBINA)), im,
                         pad.resize((w, h)))

    # vinjeta: uglovi tamniji
    v = Image.new("L", (w, h), 0)
    ImageDraw.Draw(v).ellipse([-w * 0.18, -h * 0.18, w * 1.18, h * 1.18],
                              fill=255)
    v = v.filter(ImageFilter.GaussianBlur(min(w, h) * 0.16))
    im = Image.composite(im, Image.new("RGB", (w, h), hx(DUBINA)), v)

    # zrno — bez njega gradijent pravi vidljive trake
    im = Image.blend(im, Image.effect_noise((w, h), 26).convert("RGB"), 0.028)
    _poz_kes[(w, h)] = im
    return im


# ---------------------------------------------------------------- staklo

def maska(w, h, r):
    m = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(m).rounded_rectangle(
        [0, 0, w * SS - 1, h * SS - 1], radius=r * SS, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def staklo(poz, x, y, w, h, r, belina=0.14, blur=22, tint=None, tint_jak=0.0,
           ivica=0.55, sjaj=True):
    """Isečak pozadine pretvoren u stakleni panel.

    belina  — koliko je mlečno
    tint / tint_jak — bojenje (npr. mentol dugme)
    ivica   — jačina svetle ivice, sjaj — odsjaj uz gornju ivicu
    """
    w, h = max(1, int(w)), max(1, int(h))
    g = poz.crop((x, y, x + w, y + h)).filter(ImageFilter.GaussianBlur(blur))
    g = ImageEnhance.Color(g).enhance(1.45)
    g = ImageEnhance.Brightness(g).enhance(1.10)

    if tint and tint_jak:
        g = Image.blend(g, Image.new("RGB", (w, h), hx(tint)), tint_jak)
    if belina:
        g = Image.blend(g, Image.new("RGB", (w, h), (255, 255, 255)), belina)

    belo = Image.new("RGB", (w, h), (255, 255, 255))
    if sjaj:
        g.paste(belo, (0, 0), _sjaj(w, h, r))
    if ivica:
        g.paste(belo, (0, 0), _ivica(w, h, r, ivica))
    return g


def _ivica(w, h, r, jacina):
    """Svetla ivica, jača gore a slabija dole — kao staklo na svetlu."""
    o = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(o).rounded_rectangle(
        [0, 0, w * SS - 1, h * SS - 1], radius=r * SS, outline=255,
        width=max(1, int(1.4 * SS)))
    o = o.resize((w, h), Image.LANCZOS)

    pad = Image.new("L", (1, h))
    for i in range(h):
        pad.putpixel((0, i), int(255 * jacina *
                                 (1.0 - 0.70 * (i / max(1, h - 1)))))
    return Image.composite(o, Image.new("L", (w, h), 0), pad.resize((w, h)))


def _sjaj(w, h, r):
    """Mekani odsjaj odmah ispod gornje ivice."""
    vis = max(2, int(h * 0.45))
    o = Image.new("L", (w, h), 0)
    ImageDraw.Draw(o).rounded_rectangle([1, 1, w - 2, vis],
                                        radius=max(1, r - 1), fill=78)
    o = o.filter(ImageFilter.GaussianBlur(max(2, h * 0.13)))

    pad = Image.new("L", (1, h))
    for i in range(h):
        pad.putpixel((0, i), int(255 * max(0.0, 1.0 - (i / vis) ** 0.75)))
    o = Image.composite(o, Image.new("L", (w, h), 0), pad.resize((w, h)))
    return Image.composite(o, Image.new("L", (w, h), 0), maska(w, h, r))


def senka(poz, x, y, w, h, r, pomak=12, blur=16, jacina=0.5):
    """Mekana senka ispod panela — upisuje se pravo u pozadinu."""
    ivi = blur * 3
    sloj = Image.new("L", (w + ivi * 2, h + ivi * 2), 0)
    ImageDraw.Draw(sloj).rounded_rectangle(
        [ivi, ivi, ivi + w, ivi + h], radius=r, fill=int(255 * jacina))
    sloj = sloj.filter(ImageFilter.GaussianBlur(blur))
    poz.paste(Image.new("RGB", sloj.size, (0, 0, 0)),
              (x - ivi, y - ivi + pomak), sloj)


def panel(poz, x, y, w, h, r, pomak=12, s_blur=16, s_jak=0.5, **kw):
    """Senka + staklo, upisano u sliku pozadine."""
    senka(poz, x, y, w, h, r, pomak=pomak, blur=s_blur, jacina=s_jak)
    poz.paste(staklo(poz, x, y, w, h, r, **kw), (x, y), maska(w, h, r))


def na_platno(im):
    return ImageTk.PhotoImage(im)


# ---------------------------------------------------------------- sličica

def uklopi(im, w, h):
    """Iseci na zadati odnos stranica pa smanji."""
    ci, ch = im.size
    cilj = w / h
    if ci / ch > cilj:
        nova = int(ch * cilj)
        im = im.crop(((ci - nova) // 2, 0, (ci + nova) // 2, ch))
    else:
        nova = int(ci / cilj)
        im = im.crop((0, (ch - nova) // 2, ci, (ch + nova) // 2))
    return im.resize((w, h), Image.LANCZOS)


# ---------------------------------------------------------------- ikonice

def ikona_youtube(velicina):
    kljuc = ("yt", velicina)
    if kljuc not in _ikone:
        u = velicina * SS
        im = Image.new("RGBA", (u, u), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, u - 1, u - 1], radius=int(u * 0.30),
                            fill=(240, 40, 45, 255))
        d.polygon([(u * 0.40, u * 0.29), (u * 0.40, u * 0.71),
                   (u * 0.73, u * 0.50)], fill=(255, 255, 255, 255))
        _ikone[kljuc] = im.resize((velicina, velicina), Image.LANCZOS)
    return _ikone[kljuc]


def ikona_instagram(velicina):
    kljuc = ("ig", velicina)
    if kljuc in _ikone:
        return _ikone[kljuc]

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
                boja = tuple(int(ca[n] + (cb[n] - ca[n]) * ((t - a) / (b - a)))
                             for n in range(3))
                break
        d.line([(i, 0), (0, i)], fill=boja, width=2)

    im = grad.convert("RGBA")
    m = Image.new("L", (u, u), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, u - 1, u - 1],
                                        radius=int(u * 0.30), fill=255)
    im.putalpha(m)

    d = ImageDraw.Draw(im)
    lw, b = max(1, int(u * 0.055)), (255, 255, 255, 255)
    d.rounded_rectangle([u * 0.24, u * 0.24, u * 0.76, u * 0.76],
                        radius=int(u * 0.17), outline=b, width=lw)
    d.ellipse([u * 0.38, u * 0.38, u * 0.62, u * 0.62], outline=b, width=lw)
    d.ellipse([u * 0.63, u * 0.31, u * 0.70, u * 0.38], fill=b)
    _ikone[kljuc] = im.resize((velicina, velicina), Image.LANCZOS)
    return _ikone[kljuc]
