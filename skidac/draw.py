# -*- coding: utf-8 -*-
"""Pozadinski gradijent, staklo i ikonice — sve se crta Pillow-om.

Tkinter nema ni providnost ni blur. Zato se cela pozadina prozora
generiše kao slika, a svaki stakleni panel se pravi tako što se isečak
pozadine ISPOD njega zamuti i posvetli. To je pravo staklo, ne imitacija —
panel stvarno pokazuje ono što je iza njega.
"""

import ctypes
import os
import sys
import winreg

from PIL import (Image, ImageDraw, ImageEnhance, ImageFilter, ImageGrab,
                   ImageTk)

from .theme import (DUBINA, KLJUC, MENTA, SMARAGD, STAKLO, TIRKIZ, ZELENA,
                    hx)

PROVIDNO = True     # prozor je stvarno providan, blur radi Windows

SS = 4              # supersampling za glatke ivice
_poz_kes = {}
_ikone = {}
_ekran = None       # snimak radne povrsine (rezerva ako tapeta ne procita)
_tapeta = None      # (kljuc, slika preko celog ekrana)


# ---------------------------------------------------------------- tapeta

def _put_tapete():
    """Putanja do slike koja je trenutno na radnoj povrsini."""
    bafer = ctypes.create_unicode_buffer(520)
    # SPI_GETDESKWALLPAPER = 0x0073
    if ctypes.windll.user32.SystemParametersInfoW(0x0073, 520, bafer, 0):
        if bafer.value and os.path.isfile(bafer.value):
            return bafer.value
    # Windows drzi i prekodiranu kopiju — nju vraca kad je original nedostupan
    rezerva = os.path.join(os.environ.get("APPDATA", ""), "Microsoft",
                           "Windows", "Themes", "TranscodedWallpaper")
    return rezerva if os.path.isfile(rezerva) else None


def _stil_tapete():
    """Kako Windows razvlaci tapetu: popuni / uklopi / rastegni / slozi."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Control Panel\Desktop") as k:
            stil = winreg.QueryValueEx(k, "WallpaperStyle")[0]
            slaganje = winreg.QueryValueEx(k, "TileWallpaper")[0]
    except OSError:
        return "popuni"
    if str(slaganje) == "1":
        return "slozi"
    return {"10": "popuni", "22": "popuni", "6": "uklopi",
            "2": "rastegni", "0": "centriraj"}.get(str(stil), "popuni")


def kljuc_tapete():
    """Sitan otisak — po njemu se vidi da je korisnik promenio tapetu."""
    put = _put_tapete()
    if not put:
        return None
    try:
        return (put, os.path.getmtime(put), _stil_tapete())
    except OSError:
        return (put, 0, _stil_tapete())


def tapeta(w, h):
    """Tapeta razvucena preko celog ekrana, onako kako je Windows prikazuje."""
    global _tapeta
    kljuc = kljuc_tapete()
    if kljuc is None:
        return None
    if _tapeta and _tapeta[0] == kljuc and _tapeta[1].size == (w, h):
        return _tapeta[1]

    try:
        slika = Image.open(kljuc[0]).convert("RGB")
    except Exception:
        return None

    stil = kljuc[2]
    platno = Image.new("RGB", (w, h), (0, 0, 0))
    if stil == "popuni":
        platno = uklopi(slika, w, h)
    elif stil == "rastegni":
        platno = slika.resize((w, h), Image.LANCZOS)
    elif stil == "uklopi":
        odnos = min(w / slika.width, h / slika.height)
        nova = slika.resize((max(1, int(slika.width * odnos)),
                             max(1, int(slika.height * odnos))), Image.LANCZOS)
        platno.paste(nova, ((w - nova.width) // 2, (h - nova.height) // 2))
    elif stil == "slozi":
        for x in range(0, w, slika.width):
            for y in range(0, h, slika.height):
                platno.paste(slika, (x, y))
    else:                                    # centriraj
        platno.paste(slika, ((w - slika.width) // 2, (h - slika.height) // 2))

    _tapeta = (kljuc, platno)
    return platno


def zaboravi_pozadinu():
    """Baci zapamcene isecke — zove se kad se tapeta promeni."""
    _poz_kes.clear()


def _velicina_ekrana():
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def uslikaj_ekran():
    """Snimi radnu povrsinu — to je ono sto ce se videti kroz staklo.

    Slika se uzima dok je prozor jos sakriven, pa nema treperenja i na
    snimku nema nas samih. Posle se samo isecaju delovi po polozaju.
    """
    global _ekran
    try:
        _ekran = ImageGrab.grab().convert("RGB")
    except Exception:
        _ekran = None
    _poz_kes.clear()
    return _ekran is not None


def _isecak(x, y, w, h, izvor=None):
    """Deo podloge ispod prozora; van ivica ekrana ide tamna popuna."""
    platno = Image.new("RGB", (w, h), hx(DUBINA))
    izvor = izvor if izvor is not None else _ekran
    if izvor is None:
        return platno
    ex, ey = izvor.size
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(ex, x + w), min(ey, y + h)
    if x1 <= x0 or y1 <= y0:
        return platno
    platno.paste(izvor.crop((x0, y0, x1, y1)), (x0 - x, y0 - y))
    return platno


# ---------------------------------------------------------------- pozadina

def _svoja_slika():
    """Ako korisnik ostavi pozadina.png/jpg pored aplikacije, koristi nju."""
    mesta = [os.path.dirname(sys.executable),
             os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]
    for mesto in mesta:
        for ime in ("pozadina.png", "pozadina.jpg", "pozadina.jpeg",
                    "pozadina.webp"):
            put = os.path.join(mesto, ime)
            if os.path.isfile(put):
                try:
                    return Image.open(put).convert("RGB")
                except Exception:
                    pass
    return None


def pozadina(w, h, x=0, y=0):
    """Zamucena radna povrsina ispod prozora.

    Redosled: korisnikova slika ako je ostavio, pa snimak ekrana, pa
    zeleni gradijent ako snimak nije uspeo.
    """
    kljuc = (w, h, x, y, PROVIDNO)
    if kljuc in _poz_kes:
        return _poz_kes[kljuc]
    if PROVIDNO:
        _poz_kes[kljuc] = Image.new("RGB", (w, h), hx(KLJUC))
        return _poz_kes[kljuc]
    if len(_poz_kes) > 12:
        _poz_kes.clear()          # pomeranje prozora bi inace gomilalo slike

    svoja = _svoja_slika()
    if svoja is not None:
        im = uklopi(svoja, w, h)
        im = ImageEnhance.Brightness(im).enhance(0.55)   # da tekst ostane citljiv
        im = _pritamni(im, w, h)
        im = Image.blend(im, Image.effect_noise((w, h), 26).convert("RGB"), 0.02)
        _poz_kes[kljuc] = im
        return im

    podloga = tapeta(*_velicina_ekrana()) or _ekran
    if podloga is not None:
        im = _isecak(x, y, w, h, podloga).filter(ImageFilter.GaussianBlur(20))
        im = ImageEnhance.Color(im).enhance(0.68)
        im = ImageEnhance.Brightness(im).enhance(0.44)   # tamnije od radne povrsine
        im = Image.blend(im, Image.effect_noise((w, h), 20).convert("RGB"), 0.02)
        _poz_kes[kljuc] = im
        return im

    mw, mh = max(8, w // 6), max(8, h // 6)
    im = Image.new("RGB", (mw, mh), hx(DUBINA))
    d = ImageDraw.Draw(im)

    # (x, y, poluprečnik, boja) — u udelima veličine, da radi na svakom DPI
    # manje mrlje, sa tamnim prostorom izmedju — inace se sve slije u jednu zelenu
    for fx, fy, fr, boja in (
        (0.02, -0.06, 0.32, "#0a6349"),
        (0.42, 0.06, 0.22, SMARAGD),
        (1.04, 0.12, 0.28, TIRKIZ),
        (0.74, 0.48, 0.24, ZELENA),
        (-0.08, 0.60, 0.24, ZELENA),
        (0.88, 0.92, 0.30, "#07543f"),
        (0.20, 1.04, 0.24, TIRKIZ),
    ):
        x, y, r = fx * mw, fy * mh, fr * min(mw, mh)
        d.ellipse([x - r, y - r, x + r, y + r], fill=hx(boja))

    im = im.filter(ImageFilter.GaussianBlur(min(mw, mh) * 0.26))
    im = im.resize((w, h), Image.BICUBIC)
    im = ImageEnhance.Brightness(im).enhance(0.86)   # baza je vec tamna
    im = ImageEnhance.Color(im).enhance(1.15)

    im = _pritamni(im, w, h)

    # zrno — bez njega gradijent pravi vidljive trake
    im = Image.blend(im, Image.effect_noise((w, h), 26).convert("RGB"), 0.028)
    _poz_kes[kljuc] = im
    return im


def _pritamni(im, w, h):
    """Pad ka dnu i vinjeta — tekst mora da ima gde da sedne."""
    pad = Image.new("L", (1, h))
    for y in range(h):
        pad.putpixel((0, y), int(30 + 160 * (y / max(1, h - 1)) ** 1.15))
    im = Image.composite(Image.new("RGB", (w, h), hx(DUBINA)), im,
                         pad.resize((w, h)))

    v = Image.new("L", (w, h), 0)
    ImageDraw.Draw(v).ellipse([-w * 0.18, -h * 0.18, w * 1.18, h * 1.18],
                              fill=255)
    v = v.filter(ImageFilter.GaussianBlur(min(w, h) * 0.16))
    return Image.composite(im, Image.new("RGB", (w, h), hx(DUBINA)), v)


# ---------------------------------------------------------------- staklo

def maska(w, h, r):
    m = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(m).rounded_rectangle(
        [0, 0, w * SS - 1, h * SS - 1], radius=r * SS, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def staklo(poz, x, y, w, h, r, belina=0.07, blur=26, tint=None, tint_jak=0.0,
           ivica=0.30, sjaj=True):
    """Isečak pozadine pretvoren u stakleni panel.

    belina  — koliko je mlečno
    tint / tint_jak — bojenje (npr. mentol dugme)
    ivica   — jačina svetle ivice, sjaj — odsjaj uz gornju ivicu
    """
    w, h = max(1, int(w)), max(1, int(h))
    podloga = poz.crop((x, y, x + w, y + h))
    if PROVIDNO:
        g = Image.new("RGB", (w, h), hx(STAKLO))
    else:
        g = podloga.filter(ImageFilter.GaussianBlur(blur))
        g = ImageEnhance.Color(g).enhance(0.90)
        g = ImageEnhance.Brightness(g).enhance(0.86)
        g = Image.blend(g, Image.new("RGB", (w, h), (0, 0, 0)), 0.18)

    if tint and tint_jak:
        g = Image.blend(g, Image.new("RGB", (w, h), hx(tint)), tint_jak)
    if belina:
        g = Image.blend(g, Image.new("RGB", (w, h), (255, 255, 255)), belina)

    belo = Image.new("RGB", (w, h), (255, 255, 255))
    if sjaj:
        g.paste(belo, (0, 0), _sjaj(w, h, r))
    if ivica:
        g.paste(belo, (0, 0), _ivica(w, h, r, ivica))

    podloga.paste(g, (0, 0), maska(w, h, r))
    return podloga


def _ivica(w, h, r, jacina):
    """Svetla ivica, jača gore a slabija dole — kao staklo na svetlu."""
    o = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(o).rounded_rectangle(
        [0, 0, w * SS - 1, h * SS - 1], radius=r * SS, outline=255,
        width=max(1, int(1.0 * SS)))
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
                                        radius=max(1, r - 1), fill=52)
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
    if not PROVIDNO:
        senka(poz, x, y, w, h, r, pomak=pomak, blur=s_blur, jacina=s_jak)
    poz.paste(staklo(poz, x, y, w, h, r, **kw), (x, y))


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


def ikona_sajt(velicina):
    """Globus — meridijani i paralele u mentol krugu."""
    kljuc = ("sajt", velicina)
    if kljuc in _ikone:
        return _ikone[kljuc]
    u = velicina * SS
    im = Image.new("RGBA", (u, u), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, u - 1, u - 1], radius=int(u * 0.30),
                        fill=(46, 200, 150, 255))

    b, lw = (255, 255, 255, 255), max(1, int(u * 0.045))
    a, z = u * 0.24, u * 0.76
    d.ellipse([a, a, z, z], outline=b, width=lw)
    d.line([(a, u * 0.5), (z, u * 0.5)], fill=b, width=lw)
    d.line([(u * 0.5, a), (u * 0.5, z)], fill=b, width=lw)
    # dve elipse daju utisak zakrivljenih meridijana
    for sirina in (0.16, 0.30):
        d.ellipse([u * (0.5 - sirina), a, u * (0.5 + sirina), z],
                  outline=b, width=max(1, int(lw * 0.8)))
    _ikone[kljuc] = im.resize((velicina, velicina), Image.LANCZOS)
    return _ikone[kljuc]


def ikona_lista(velicina):
    """Tri reda sa kvacicama — spisak onoga sto ce se skinuti."""
    kljuc = ("lista", velicina)
    if kljuc in _ikone:
        return _ikone[kljuc]
    u = velicina * SS
    im = Image.new("RGBA", (u, u), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, u - 1, u - 1], radius=int(u * 0.30),
                        fill=(120, 96, 232, 255))

    b, lw = (255, 255, 255, 255), max(1, int(u * 0.055))
    for i, y in enumerate((0.33, 0.50, 0.67)):
        d.line([(u * 0.44, u * y), (u * 0.76, u * y)], fill=b, width=lw)
        # kvacica levo od svakog reda
        d.line([(u * 0.24, u * y), (u * 0.30, u * (y + 0.045))], fill=b,
               width=lw)
        d.line([(u * 0.30, u * (y + 0.045)), (u * 0.38, u * (y - 0.06))],
               fill=b, width=lw)
    _ikone[kljuc] = im.resize((velicina, velicina), Image.LANCZOS)
    return _ikone[kljuc]


def ikona_soundcloud(velicina):
    """Narandzasta kockica sa belim oblakom i talasom zvuka."""
    kljuc = ("sc", velicina)
    if kljuc in _ikone:
        return _ikone[kljuc]
    u = velicina * SS
    im = Image.new("RGBA", (u, u), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, u - 1, u - 1], radius=int(u * 0.30),
                        fill=(255, 102, 26, 255))
    b = (255, 255, 255, 255)
    # stubici zvuka levo, sve visi ka oblaku
    for i, visina in enumerate((0.10, 0.15, 0.20, 0.24)):
        x = u * (0.18 + i * 0.065)
        d.rounded_rectangle([x, u * (0.62 - visina), x + u * 0.03, u * 0.62],
                            radius=int(u * 0.015), fill=b)
    # oblak desno
    d.ellipse([u * 0.44, u * 0.34, u * 0.66, u * 0.56], fill=b)
    d.ellipse([u * 0.58, u * 0.42, u * 0.80, u * 0.62], fill=b)
    d.rectangle([u * 0.46, u * 0.48, u * 0.70, u * 0.62], fill=b)
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
