# -*- coding: utf-8 -*-
"""Kontrole nacrtane na platnu (Canvas), a ne obični tkinter widgeti.

Razlog: staklo mora da pokaže pozadinu ispod sebe. Obican tk.Label ima
jednu punu boju i napravio bi ružnu pravougaonu rupu preko gradijenta.
Zato je sve — i tekst i dugmad — nacrtano na jednom platnu.
"""

import tkinter as tk

from .draw import maska, na_platno, staklo
from .theme import (FAM, FAM_B, INK, MENTA, MENTA_HI, TXT, TXT2, TXT3, s)

_kes = {}


def _staklo_slika(baza, x, y, w, h, r, **kw):
    """Renderovano staklo za jedno mesto — keširano, da hover bude trenutan."""
    kljuc = (x, y, w, h, r, tuple(sorted(kw.items())))
    if kljuc not in _kes:
        _kes[kljuc] = na_platno(staklo(baza, x, y, w, h, r, **kw))
    return _kes[kljuc]


def ocisti_kes():
    _kes.clear()


# ---------------------------------------------------------------- tekst

def tekst(platno, x, y, sadrzaj, font, boja=TXT, sidro="nw", sirina=None,
          senka=False):
    """Tekst na platnu; senka=True za naslove direktno na gradijentu."""
    if senka:
        # dva pomeraja daju gusciju senku — tekst na pozadini mora da se drzi
        # i kad je iza njega svetao deo radne povrsine
        for dx, dy in ((1, 1), (2, 2)):
            platno.create_text(x + dx, y + dy, text=sadrzaj, font=font,
                               anchor=sidro, fill="#05100c", width=sirina)
    return platno.create_text(x, y, text=sadrzaj, font=font, anchor=sidro,
                              fill=boja, width=sirina)


def nalepnica(platno, x, y, sadrzaj):
    """Sitan naslov iznad grupe kontrola."""
    return tekst(platno, x, y, sadrzaj.upper(), (FAM_B, 8), TXT3)


# ---------------------------------------------------------------- osnova

class Element:
    """Slika + tekst na platnu, sa hover i klik stanjima."""

    def __init__(self, platno, baza, x, y, w, h):
        self.p, self.baza = platno, baza
        self.x, self.y, self.w, self.h = x, y, w, h
        self.oznaka = f"el{id(self)}"
        self.ukljuceno = True
        self.slika_id = platno.create_image(x, y, anchor="nw", tags=self.oznaka)
        self.tekst_id = None

        platno.tag_bind(self.oznaka, "<Enter>", self._ulaz)
        platno.tag_bind(self.oznaka, "<Leave>", self._izlaz)
        platno.tag_bind(self.oznaka, "<Button-1>", self._klik)

    def _ulaz(self, _e=None):
        if self.ukljuceno:
            self.p.config(cursor="hand2")
            self.crtaj("hover")

    def _izlaz(self, _e=None):
        self.p.config(cursor="")
        if self.ukljuceno:
            self.crtaj("mirno")

    def _klik(self, _e=None):
        pass

    def crtaj(self, stanje="mirno"):
        raise NotImplementedError

    def _postavi(self, slika, boja_teksta=None):
        self.p.itemconfig(self.slika_id, image=slika)
        self.slika = slika                       # referenca, da GC ne pojede
        if self.tekst_id is not None and boja_teksta:
            self.p.itemconfig(self.tekst_id, fill=boja_teksta)

    def obrisi(self):
        try:
            self.p.delete(self.oznaka)
            if self.tekst_id is not None:
                self.p.delete(self.tekst_id)
        except tk.TclError:
            pass                         # platno je vec unisteno


class Dugme(Element):

    STILOVI = {
        # stanje: (belina, tint, jacina tinta, ivica, boja teksta)
        "glavno": {
            "mirno": (0.08, MENTA, 0.58, 0.38, TXT),
            "hover": (0.13, MENTA_HI, 0.70, 0.55, TXT),
            "klik":  (0.04, MENTA, 0.50, 0.28, TXT),
            "gasi":  (0.05, None, 0.0, 0.14, TXT3),
        },
        "tiho": {
            "mirno": (0.11, None, 0.0, 0.26, TXT),
            "hover": (0.19, None, 0.0, 0.42, TXT),
            "klik":  (0.07, None, 0.0, 0.20, TXT),
            "gasi":  (0.05, None, 0.0, 0.14, TXT3),
        },
    }

    def __init__(self, platno, baza, x, y, w, h, sadrzaj, komanda,
                 stil="tiho", font=None, r=None):
        super().__init__(platno, baza, x, y, w, h)
        self.stil, self.komanda = stil, komanda
        self.r = r if r is not None else h // 2
        self.tekst_id = tekst(platno, x + w // 2, y + h // 2, sadrzaj,
                              font or (FAM_B, 10), sidro="center")
        self.crtaj()

    def crtaj(self, stanje="mirno"):
        if not self.ukljuceno:
            stanje = "gasi"
        belina, tint, jak, ivica, boja = self.STILOVI[self.stil][stanje]
        self._postavi(_staklo_slika(self.baza, self.x, self.y, self.w, self.h,
                                    self.r, belina=belina, tint=tint,
                                    tint_jak=jak, ivica=ivica), boja)

    def _klik(self, _e=None):
        if self.ukljuceno:
            self.crtaj("klik")
            self.p.after(90, lambda: self.crtaj("hover"))
            self.komanda()

    def ukljuci(self, on):
        self.ukljuceno = on
        self.crtaj()

    def natpis(self, t):
        self.p.itemconfig(self.tekst_id, text=t)


class Cip(Element):
    """Pilula za izbor kvaliteta — bira se jedna iz grupe."""

    def __init__(self, platno, baza, x, y, w, h, sadrzaj, vrednost, komanda):
        super().__init__(platno, baza, x, y, w, h)
        self.vrednost, self.komanda = vrednost, komanda
        self.izabran = False
        self.r = h // 2
        self.tekst_id = tekst(platno, x + w // 2, y + h // 2, sadrzaj,
                              (FAM_B, 9), sidro="center")
        self.crtaj()

    def crtaj(self, stanje="mirno"):
        if self.izabran:
            par = dict(belina=0.09, tint=MENTA, tint_jak=0.56, ivica=0.50)
            boja = TXT
        elif stanje == "hover":
            par = dict(belina=0.18, ivica=0.34)
            boja = TXT
        else:
            par = dict(belina=0.09, ivica=0.18)
            boja = TXT2
        self._postavi(_staklo_slika(self.baza, self.x, self.y, self.w, self.h,
                                    self.r, **par), boja)

    def _klik(self, _e=None):
        self.komanda(self.vrednost)

    def izaberi(self, on):
        self.izabran = on
        self.crtaj()


class Segment(Element):
    """Prekidač sa dve opcije — staklena pilula stoji ispod izabrane."""

    def __init__(self, platno, baza, x, y, w, h, opcije, komanda):
        super().__init__(platno, baza, x, y, w, h)
        self.opcije, self.komanda = opcije, komanda
        self.izbor = opcije[0][1]
        self.r = h // 2

        # trag (cela traka) se ne menja, pa se crta odmah
        trag = staklo(baza, x, y, w, h, self.r, belina=0.06, ivica=0.16)
        self._postavi(na_platno(trag))
        self.baza = baza.copy()          # pilula se spaja sa tragom ispod sebe
        self.baza.paste(trag, (x, y))
        n = len(opcije)
        self.pad = s(4)
        self.pw = int(w / n) - self.pad * 2
        self.ph = h - self.pad * 2
        self.pilula_id = platno.create_image(0, 0, anchor="nw",
                                             tags=self.oznaka)
        self.natpisi = [
            tekst(platno, int(x + w / n * (i + 0.5)), y + h // 2, lab,
                  (FAM_B, 10), sidro="center")
            for i, (lab, _v) in enumerate(opcije)]
        self.crtaj()

    def crtaj(self, stanje="mirno"):
        n = len(self.opcije)
        i = [v for _l, v in self.opcije].index(self.izbor)
        px = int(self.x + self.w / n * i) + self.pad
        py = self.y + self.pad
        self.p.coords(self.pilula_id, px, py)
        self.pilula = _staklo_slika(self.baza, px, py, self.pw, self.ph,
                                    self.ph // 2, belina=0.10,
                                    tint=MENTA, tint_jak=0.40, ivica=0.45)
        self.p.itemconfig(self.pilula_id, image=self.pilula)
        for j, t in enumerate(self.natpisi):
            self.p.itemconfig(t, fill=TXT if j == i else TXT2)
        self.p.tag_raise(self.pilula_id)
        for t in self.natpisi:
            self.p.tag_raise(t)

    def _ulaz(self, _e=None):
        self.p.config(cursor="hand2")

    def _izlaz(self, _e=None):
        self.p.config(cursor="")

    def _klik(self, e):
        n = len(self.opcije)
        i = min(n - 1, max(0, int((e.x - self.x) / (self.w / n))))
        vrednost = self.opcije[i][1]
        if vrednost != self.izbor:
            self.izbor = vrednost
            self.crtaj()
            self.komanda(vrednost)


class Traka:
    """Traka napretka: staklena šina i mentol ispuna."""

    def __init__(self, platno, baza, x, y, w, h):
        self.p, self.baza = platno, baza
        self.x, self.y, self.w, self.h = x, y, w, h
        sina = staklo(baza, x, y, w, h, h // 2, belina=0.08, ivica=0.18,
                      sjaj=False)
        self.sina = na_platno(sina)
        self.baza = baza.copy()
        self.baza.paste(sina, (x, y))
        self.sina_id = platno.create_image(x, y, anchor="nw", image=self.sina)
        self.ispuna_id = platno.create_image(x, y, anchor="nw")
        self.pct = -1
        self.postavi(0)

    def postavi(self, pct):
        pct = max(0, min(100, pct))
        if abs(pct - self.pct) < 0.5:
            return
        self.pct = pct
        fw = int(self.w * pct / 100)
        if fw < self.h:
            self.p.itemconfig(self.ispuna_id, state="hidden")
            return
        self.ispuna = _staklo_slika(self.baza, self.x, self.y, fw, self.h,
                                    self.h // 2, belina=0.16, tint=MENTA,
                                    tint_jak=0.72, ivica=0.5, sjaj=False)
        self.p.itemconfig(self.ispuna_id, image=self.ispuna, state="normal")

    def sakrij(self):
        self.p.itemconfig(self.sina_id, state="hidden")
        self.p.itemconfig(self.ispuna_id, state="hidden")


class Polje:
    """Jedini pravi widget — Entry, na staklenoj podlozi.

    Entry mora da bude jedne pune boje, pa se ona uzorkuje iz samog stakla;
    staklo je jako zamućeno i ujednačeno, tako da se spoj ne primeti.
    """

    def __init__(self, platno, baza, x, y, w, h, nagovestaj=""):
        self.p, self.nagovestaj = platno, nagovestaj
        self.x, self.y, self.w, self.h = x, y, w, h
        self.prazno = False
        self.r = h // 2

        self.mirna = staklo(baza, x, y, w, h, self.r, belina=0.09, ivica=0.20)
        self.aktivna = staklo(baza, x, y, w, h, self.r, belina=0.13,
                              tint=MENTA, tint_jak=0.08, ivica=0.55)
        self.sl_mirna, self.sl_aktivna = na_platno(self.mirna), na_platno(self.aktivna)
        self.slika_id = platno.create_image(x, y, anchor="nw",
                                            image=self.sl_mirna)

        self.entry = tk.Entry(platno, bg=self._uzorak(self.mirna), fg=TXT,
                              font=(FAM, 10), relief="flat", bd=0,
                              insertbackground=MENTA, highlightthickness=0,
                              disabledbackground=self._uzorak(self.mirna))
        self.prozor_id = platno.create_window(
            x + s(16), y + h // 2, anchor="w", window=self.entry,
            width=w - s(32), height=h - s(16))

        self.entry.bind("<FocusIn>", self._fokus_in)
        self.entry.bind("<FocusOut>", self._fokus_out)
        self.entry.bind("<Key>", self._taster)
        self.entry.bind("<<Paste>>", lambda _e: self._obrisi_nagovestaj())
        if nagovestaj:
            self._nagovesti()

    @staticmethod
    def _uzorak(im):
        """Prosečna boja sredine stakla — pozadina za Entry."""
        w, h = im.size
        sred = im.crop((w // 4, h // 3, w * 3 // 4, h * 2 // 3))
        r, g, b = sred.resize((1, 1)).getpixel((0, 0))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _nagovesti(self):
        self.entry.delete(0, "end")
        self.entry.insert(0, self.nagovestaj)
        self.entry.config(fg=TXT3)
        self.prazno = True

    def _obrisi_nagovestaj(self):
        if self.prazno:
            self.entry.delete(0, "end")
            self.entry.config(fg=TXT)
            self.prazno = False

    def _taster(self, e):
        if self.prazno and e.keysym not in (
                "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L",
                "Alt_R", "Tab", "Escape", "Caps_Lock"):
            self._obrisi_nagovestaj()

    def _fokus_in(self, _e):
        if self.prazno:
            self.entry.icursor(0)
        self.p.itemconfig(self.slika_id, image=self.sl_aktivna)
        self.entry.config(bg=self._uzorak(self.aktivna))

    def _fokus_out(self, _e):
        if self.nagovestaj and not self.entry.get().strip():
            self._nagovesti()
        self.p.itemconfig(self.slika_id, image=self.sl_mirna)
        self.entry.config(bg=self._uzorak(self.mirna))

    def get(self):
        return "" if self.prazno else self.entry.get()

    def postavi(self, v):
        self._obrisi_nagovestaj()
        self.entry.delete(0, "end")
        self.entry.insert(0, v)

    def fokusiraj(self):
        try:
            self.entry.focus_set()
        except tk.TclError:
            pass          # ekran je pregradjen pre nego sto je fokus stigao
