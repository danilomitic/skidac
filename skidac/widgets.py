# -*- coding: utf-8 -*-
"""Sitni widgeti sa zaobljenim ivicama — tkinter ih nema."""

import tkinter as tk

from .draw import rr
from .theme import (BG, CARD, DIM, FAM, FAM_B, FIELD, HOVER, INK, LINE, MINT,
                    MINT_DK, MINT_HI, MUTED, TXT, s)


class Dugme(tk.Canvas):
    """Zaobljeno dugme: slika kao pozadina, tekst preko nje."""

    STILOVI = {
        "glavno": (MINT, MINT_HI, MINT_DK, INK),
        "tiho":   (FIELD, HOVER, FIELD, TXT),
    }

    def __init__(self, master, text, command, bg=CARD, stil="tiho",
                 width=None, height=None, font=None):
        self.stil, self.command, self.pozadina = stil, command, bg
        self.font = font or (FAM_B, 10)
        self.ukljuceno = True

        h = height or s(44)
        if width is None:
            proba = tk.Label(master, text=text, font=self.font)
            width = proba.winfo_reqwidth() + s(40)
            proba.destroy()

        super().__init__(master, width=width, height=h, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.w, self.h = width, h
        self._slika = self.create_image(0, 0, anchor="nw")
        self._tekst = self.create_text(width // 2, h // 2, text=text,
                                       font=self.font)
        self._crtaj(0)
        self.bind("<Enter>", lambda _e: self._crtaj(1))
        self.bind("<Leave>", lambda _e: self._crtaj(0))
        self.bind("<Button-1>", self._klik)
        self.bind("<Configure>", self._razvuci)

    def _razvuci(self, e):
        """Canvas ne raste sam uz fill="x" — pomerimo tekst i preslikamo."""
        if e.width != self.w:
            self.w = e.width
            self.coords(self._tekst, e.width // 2, self.h // 2)
            self._crtaj(0)

    def _crtaj(self, stanje):
        norm, hover, pritisk, fg = self.STILOVI[self.stil]
        if not self.ukljuceno:
            fill, fg = "#191d26", DIM
        else:
            fill = (norm, hover, pritisk)[stanje]
        self.itemconfig(self._slika,
                        image=rr(self.w, self.h, s(10), fill, self.pozadina))
        self.itemconfig(self._tekst, fill=fg)

    def _klik(self, _e):
        if self.ukljuceno:
            self._crtaj(2)
            self.after(90, lambda: self._crtaj(1))
            self.command()

    def ukljuci(self, on):
        self.ukljuceno = on
        self.config(cursor="hand2" if on else "arrow")
        self._crtaj(0)

    def natpis(self, t):
        self.itemconfig(self._tekst, text=t)


class Cip(tk.Canvas):
    """Mala pilula za izbor kvaliteta — bira se jedna iz grupe."""

    def __init__(self, master, text, vrednost, command, bg=CARD):
        self.vrednost, self.command, self.pozadina = vrednost, command, bg
        self.izabran = False
        font = (FAM_B, 9)
        proba = tk.Label(master, text=text, font=font)
        w, h = max(s(76), proba.winfo_reqwidth() + s(26)), s(34)
        proba.destroy()

        super().__init__(master, width=w, height=h, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.w, self.h = w, h
        self._slika = self.create_image(0, 0, anchor="nw")
        self._tekst = self.create_text(w // 2, h // 2, text=text, font=font)
        self._crtaj()
        self.bind("<Enter>", lambda _e: self._crtaj(True))
        self.bind("<Leave>", lambda _e: self._crtaj(False))
        self.bind("<Button-1>", lambda _e: self.command(vrednost))

    def _crtaj(self, hover=False):
        if self.izabran:
            fill, ivica, fg = MINT, MINT, INK
        else:
            fill, ivica, fg = (HOVER if hover else FIELD), LINE, TXT
        self.itemconfig(self._slika, image=rr(self.w, self.h, s(9), fill,
                                              self.pozadina, ivica, 1))
        self.itemconfig(self._tekst, fill=fg)

    def izaberi(self, on):
        self.izabran = on
        self._crtaj()


class Segment(tk.Canvas):
    """Prekidač sa dve opcije — pilula stoji ispod izabrane."""

    def __init__(self, master, opcije, command, bg=CARD, width=None):
        self.opcije, self.command, self.pozadina = opcije, command, bg
        self.izbor = opcije[0][1]
        w, h = width or s(280), s(42)
        super().__init__(master, width=w, height=h, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.w, self.h = w, h
        self._trag = self.create_image(0, 0, anchor="nw")
        self._pilula = self.create_image(0, 0, anchor="nw")
        n = len(opcije)
        self._natpisi = [
            self.create_text(int(w / n * (i + 0.5)), h // 2, text=lab,
                             font=(FAM_B, 10))
            for i, (lab, _v) in enumerate(opcije)]
        self.bind("<Button-1>", self._klik)
        self._crtaj()

    def _crtaj(self):
        n = len(self.opcije)
        self.itemconfig(self._trag,
                        image=rr(self.w, self.h, s(11), FIELD, self.pozadina))
        i = [v for _l, v in self.opcije].index(self.izbor)
        pad = s(4)
        self.coords(self._pilula, int(self.w / n * i) + pad, pad)
        self.itemconfig(self._pilula, image=rr(int(self.w / n) - pad * 2,
                                               self.h - pad * 2, s(8),
                                               MINT, FIELD))
        for j, t in enumerate(self._natpisi):
            self.itemconfig(t, fill=INK if j == i else MUTED)

    def _klik(self, e):
        i = min(len(self.opcije) - 1, max(0, int(e.x / (self.w / len(self.opcije)))))
        vrednost = self.opcije[i][1]
        if vrednost != self.izbor:
            self.izbor = vrednost
            self._crtaj()
            self.command(vrednost)


class Polje(tk.Frame):
    """Entry u zaobljenom okviru, sa sivim tekstom-nagoveštajem."""

    def __init__(self, master, bg=CARD, height=None, font=None, nagovestaj=""):
        h = height or s(46)
        super().__init__(master, bg=bg, height=h)
        self.pack_propagate(False)
        self.h, self.pozadina, self.nagovestaj = h, bg, nagovestaj
        self.prazno = False

        self.platno = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.platno.pack(fill="both", expand=True)
        self._slika = self.platno.create_image(0, 0, anchor="nw")
        self.entry = tk.Entry(self.platno, bg=FIELD, fg=TXT,
                              font=font or (FAM, 10), relief="flat", bd=0,
                              insertbackground=MINT, highlightthickness=0)
        self._prozor = self.platno.create_window(s(15), h // 2, anchor="w",
                                                 window=self.entry)
        self.bind("<Configure>", self._razmesti)
        self.entry.bind("<FocusIn>", self._fokus_in)
        self.entry.bind("<FocusOut>", self._fokus_out)
        self.entry.bind("<Key>", self._taster)
        self.entry.bind("<<Paste>>", lambda _e: self._obrisi_nagovestaj())
        if nagovestaj:
            self._nagovesti()

    def _razmesti(self, _e=None):
        w = self.winfo_width()
        if w > 1:
            self.platno.itemconfigure(self._prozor, width=w - s(30))
            self._crtaj(self.focus_get() is self.entry)

    def _crtaj(self, fokus):
        w = max(self.winfo_width(), 1)
        self.platno.itemconfig(self._slika, image=rr(
            w, self.h, s(11), FIELD, self.pozadina, MINT if fokus else LINE, 1))

    def _nagovesti(self):
        self.entry.delete(0, "end")
        self.entry.insert(0, self.nagovestaj)
        self.entry.config(fg=DIM)
        self.prazno = True

    def _obrisi_nagovestaj(self):
        if self.prazno:
            self.entry.delete(0, "end")
            self.entry.config(fg=TXT)
            self.prazno = False

    def _taster(self, e):
        """Nagovestaj se sklanja tek kad se stvarno nesto kuca."""
        if self.prazno and e.keysym not in (
                "Shift_L", "Shift_R", "Control_L", "Control_R",
                "Alt_L", "Alt_R", "Tab", "Escape", "Caps_Lock"):
            self._obrisi_nagovestaj()

    def _fokus_in(self, _e):
        if self.prazno:
            self.entry.icursor(0)
        self._crtaj(True)

    def _fokus_out(self, _e):
        if self.nagovestaj and not self.entry.get().strip():
            self._nagovesti()
        self._crtaj(False)

    def get(self):
        return "" if self.prazno else self.entry.get()

    def fokusiraj(self):
        self.entry.focus_set()


class Traka(tk.Canvas):
    """Zaobljena traka napretka."""

    def __init__(self, master, bg=CARD, height=None):
        h = height or s(6)
        super().__init__(master, height=h, bg=bg, highlightthickness=0, bd=0)
        self.pozadina, self.h, self.pct = bg, h, 0
        self._trag = self.create_image(0, 0, anchor="nw")
        self._ispuna = self.create_image(0, 0, anchor="nw")
        self.bind("<Configure>", lambda _e: self.postavi(self.pct))

    def postavi(self, pct):
        self.pct = max(0, min(100, pct))
        w = max(self.winfo_width(), 1)
        if w < 2:
            return
        self.itemconfig(self._trag,
                        image=rr(w, self.h, self.h // 2, FIELD, self.pozadina))
        fw = int(w * self.pct / 100)
        if fw >= self.h:
            self.itemconfig(self._ispuna, state="normal",
                            image=rr(fw, self.h, self.h // 2, MINT, FIELD))
        else:
            self.itemconfig(self._ispuna, state="hidden")


class Kartica(tk.Frame):
    """Zaobljena kartica: canvas kao pozadina, sadržaj ide u .telo."""

    def __init__(self, master, bg=BG, fill=CARD, pad=None, ivica=LINE):
        super().__init__(master, bg=bg)
        self.fill, self.pozadina, self.ivica = fill, bg, ivica
        self.platno = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.platno.place(x=0, y=0, relwidth=1, relheight=1)
        self._slika = self.platno.create_image(0, 0, anchor="nw")
        self.telo = tk.Frame(self, bg=fill)
        self.telo.pack(fill="both", expand=True,
                       padx=pad if pad is not None else s(22),
                       pady=pad if pad is not None else s(22))
        self.bind("<Configure>", self.osvezi)

    def osvezi(self, _e=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w > 1 and h > 1:
            self.platno.itemconfig(self._slika, image=rr(
                w, h, s(16), self.fill, self.pozadina, self.ivica, 1))

    def oboji(self, fill):
        """Prefarba karticu i sve u njoj — za hover efekat."""
        self.fill = fill
        self.osvezi()
        for w in [self.telo] + potomci(self.telo):
            try:
                w.config(bg=fill)
            except tk.TclError:
                pass


def potomci(widget):
    out = []
    for c in widget.winfo_children():
        out.append(c)
        out.extend(potomci(c))
    return out


def nalepnica(master, tekst, bg=CARD):
    """Sitan naslov iznad grupe kontrola."""
    n = tk.Label(master, text=tekst.upper(), bg=bg, fg=DIM, font=(FAM_B, 8))
    n.pack(anchor="w")
    return n


def veza(master, tekst, command, bg=CARD, font=None):
    """Tekst koji se ponaša kao link."""
    n = tk.Label(master, text=tekst, bg=bg, fg=MINT, font=font or (FAM_B, 9),
                 cursor="hand2")
    n.bind("<Button-1>", lambda _e: command())
    n.bind("<Enter>", lambda _e: n.config(fg=MINT_HI))
    n.bind("<Leave>", lambda _e: n.config(fg=MINT))
    return n
