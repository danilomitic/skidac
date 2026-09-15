# -*- coding: utf-8 -*-
"""Prozor: izbor platforme, pa link i skidanje.

Sve stoji na jednom platnu. Pozadina (gradijent + senke + stakleni paneli)
je jedna slika, a kontrole se renderuju iz nje — zato staklo stvarno
propušta ono što je iza njega. Zbog toga se ekran gradi u jednom prolazu:
prvo se slika sklopi do kraja, pa se tek onda dodaju kontrole.
"""

import ctypes
import io
import math
import os
import queue
import threading
import time
import traceback
import tkinter as tk
import urllib.request
from tkinter import filedialog

from PIL import Image, ImageTk

from . import core, draw, sajt
from .theme import (CRVENA, FAM, FAM_B, FAM_N, KLJUC, MENTA, MENTA_HI, TXT,
                    TXT2, TXT3, izaberi_fontove, postavi_skalu, s)
from .widgets import (Cip, Dugme, Element, Polje, Segment, Traka, nalepnica,
                      ocisti_kes, tekst)

PLATFORME = {
    "youtube":   ("YouTube", "Video, zvuk ili prepis govora", draw.ikona_youtube,
                  "https://www.youtube.com/watch?v=…"),
    "instagram": ("Instagram", "Reels, objave, IGTV", draw.ikona_instagram,
                  "https://www.instagram.com/reel/…"),
    "sajt":      ("Sajt", "Ceo sajt za čitanje bez interneta", draw.ikona_sajt,
                  "https://primer.rs"),
    "soundcloud": ("SoundCloud", "Pesme, plejliste i profili izvođača",
                   draw.ikona_soundcloud,
                   "https://soundcloud.com/izvodjac/pesma ili /sets/…"),
    "lista":     ("Lista", "Dodaj vise linkova pa skini sve odjednom",
                  draw.ikona_lista, "Nalepi link pa klikni Dodaj"),
}

LISTE = ("lista", "soundcloud")   # izvori koji rade kao spisak za skidanje

VIDLJIVIH = 8          # koliko redova liste se ispisuje
NAJVISE_ODJEDNOM = 200  # koliko stavki najvise ulazi iz jedne plejliste
NAJVECA_LISTA = 500

STRANA = (50, 200, 500, 1500)          # ponudjene granice broja strana


class KarticaPlatforme(Element):
    """Velika staklena kartica sa ikonicom — YouTube / Instagram."""

    def __init__(self, platno, baza, x, y, w, h, naziv, opis, ikona, komanda):
        super().__init__(platno, baza, x, y, w, h)
        self.komanda = komanda
        self.r = s(28)
        self.ikona = ikona(s(50))
        self.ipoz = (s(24), (h - s(50)) // 2)
        self._slike = {}

        tx, ty = x + s(24) + s(50) + s(20), y + h // 2
        self.naslov_id = tekst(platno, tx, ty - s(13), naziv, (FAM_B, 13), TXT)
        self.opis_id = tekst(platno, tx, ty + s(5), opis, (FAM, 9), TXT3)
        self.strelica_id = tekst(platno, x + w - s(26), ty, "›", (FAM, 20),
                                 TXT3, sidro="e")
        self.crtaj()

    def _slika(self, stanje):
        if stanje not in self._slike:
            par = (dict(belina=0.17, ivica=0.40) if stanje == "hover"
                   else dict(belina=0.10, ivica=0.22))
            g = draw.staklo(self.baza, self.x, self.y, self.w, self.h,
                            self.r, **par)
            g.paste(self.ikona, self.ipoz, self.ikona)
            self._slike[stanje] = ImageTk.PhotoImage(g)
        return self._slike[stanje]

    def crtaj(self, stanje="mirno"):
        self._postavi(self._slika(stanje))
        self.p.itemconfig(self.strelica_id,
                          fill=MENTA if stanje == "hover" else TXT3)
        for i in (self.naslov_id, self.opis_id, self.strelica_id):
            self.p.tag_raise(i)

    def _klik(self, _e=None):
        self.komanda()


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        dpi = self.winfo_fpixels("1i")
        postavi_skalu(dpi)
        self.tk.call("tk", "scaling", dpi / 72.0)
        izaberi_fontove(self)

        self.W, self.H = s(700), s(790)
        self.title("Skidac")
        self.configure(bg=KLJUC)
        self.resizable(False, False)
        try:
            self.iconbitmap(core.resource_path("icon.ico"))
        except tk.TclError:
            pass

        self.withdraw()
        self.prozirnost = 0.93
        self._providno = self._ukljuci_providnost()
        if not self._providno:
            draw.PROVIDNO = False       # rezerva: crtana pozadina
            draw.uslikaj_ekran()
        self._tamna_traka()

        self.izvor = None
        self.info = None
        self.url = ""
        self.formati = []
        self.jezici = []
        self._liste = {}          # lista i SoundCloud ne mesaju stavke
        self.lista = []
        self.tip = "mp4"
        self.kvalitet = None
        self.folder = core.podrazumevani_folder()
        self.kolacici = False
        self.skida = False
        self._stani = False
        self.poruka_uvod = ""
        self.red = queue.Queue()

        self._postavljen = False
        self.generacija = 0
        self._animacija = 0
        self._od_visine = 0
        self.px, self.py = 0, 0
        self._animiram = False
        self._posao_pomeranja = None
        self._ponovo = self.ekran_izbor
        self.platno = None
        self._kljuc_tapete = draw.kljuc_tapete()
        self.ekran_izbor()
        self.deiconify()
        self.bind("<Configure>", self._na_pomeranje)
        self._pojavi_se()
        self.after(100, self._pumpa)
        self.after(3000, self._prati_tapetu)

    def _ukljuci_providnost(self):
        """Rupa u prozoru + zivi blur Windows-a iza nje.

        Pikseli boje KLJUC postaju potpuno providni, a ostatak prozora ide
        na blagu prozirnost, pa se i kroz panele malo vidi sta je iza.
        Vraca False ako sistem to ne podrzava, pa se vracamo na crtanu
        pozadinu.
        """
        try:
            self.attributes("-transparentcolor", KLJUC)
        except tk.TclError:
            return False
        try:
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())

            class ACCENT(ctypes.Structure):
                _fields_ = [("stanje", ctypes.c_int), ("zastavice", ctypes.c_int),
                            ("boja", ctypes.c_uint), ("animacija", ctypes.c_int)]

            class PODACI(ctypes.Structure):
                _fields_ = [("atribut", ctypes.c_int),
                            ("podaci", ctypes.POINTER(ACCENT)),
                            ("velicina", ctypes.c_size_t)]

            akcenat = ACCENT()
            akcenat.stanje = 4          # ACCENT_ENABLE_ACRYLICBLURBEHIND
            akcenat.zastavice = 2       # vazi za ceo prozor
            akcenat.boja = 0x2E141210   # AABBGGRR — blaga tamna nijansa
            podaci = PODACI(19, ctypes.pointer(akcenat), ctypes.sizeof(akcenat))
            ctypes.windll.user32.SetWindowCompositionAttribute(
                hwnd, ctypes.byref(podaci))
        except Exception:
            pass                        # bez blura, ali providnost i dalje radi
        return True

    def _tamna_traka(self):
        """Windows inace nacrta svetlu naslovnu traku iznad tamnog prozora."""
        try:
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            vrednost = ctypes.c_int(1)
            for atribut in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, atribut, ctypes.byref(vrednost), ctypes.sizeof(vrednost))
        except Exception:
            pass

    @staticmethod
    def _uspori(t):
        """Ease-out: kreni brzo pa se smiri — tako se ponasa i Start meni."""
        return 1 - (1 - t) ** 3

    def _pojavi_se(self, trajanje=0.28, pomak=None):
        """Prozor isklizne odozdo i stopi se, kao Start meni."""
        pomak = pomak if pomak is not None else s(64)
        self.update_idletasks()
        x, kraj_y = self.winfo_x(), self.winfo_y()
        try:
            self.attributes("-alpha", 0.0)
        except tk.TclError:
            return
        pocetak = time.perf_counter()
        self._animiram = True
        # sigurnosna kocnica: prozor ne sme da ostane neproziran ako nesto pukne
        self.after(int(trajanje * 1000) + 400,
                   lambda: self.attributes("-alpha", self.prozirnost))

        def korak():
            t = min(1.0, (time.perf_counter() - pocetak) / trajanje)
            e = self._uspori(t)
            self.geometry(f"{self.W}x{self.H}+{x}+{int(kraj_y + pomak * (1 - e))}")
            self.attributes("-alpha", min(self.prozirnost, e * 1.3))
            if t < 1.0:
                self.after(10, korak)
            else:
                self.geometry(f"{self.W}x{self.H}+{x}+{kraj_y}")
                self.attributes("-alpha", self.prozirnost)
                self._animiram = False

        korak()

    def _visina(self, h):
        """Zapamti odakle krecemo; platno se pravi vec u konacnoj visini."""
        self._od_visine = self.H
        self.H = h
        if not self._postavljen:
            x = (self.winfo_screenwidth() - self.W) // 2
            y = max(0, (self.winfo_screenheight() - h) // 2 - s(24))
            self._postavljen = True
            self.geometry(f"{self.W}x{h}+{x}+{y}")
        else:
            x, y = self.winfo_x(), self.winfo_y()
            y = min(y, max(0, self.winfo_screenheight() - h - s(60)))
        self.px, self.py = x, y

    def _zavrsi_visinu(self, trajanje=0.22):
        """Glatko razvlacenje — inace prozor skoci kad se klip ucita.

        Menja se i visina platna, ne samo geometrija prozora: uz
        resizable(False, False) Tk namesti prozor na trazenu velicinu
        platna i preko toga pregazi zadatu geometriju.
        """
        od, do = self._od_visine, self.H
        x, y = self.px, self.py
        self._animacija += 1
        oznaka = self._animacija

        if abs(do - od) < s(24):
            self.platno.config(height=do)
            self.geometry(f"{self.W}x{do}+{x}+{y}")
            return

        self.platno.config(height=od)
        self.geometry(f"{self.W}x{od}+{x}+{y}")
        pocetak = time.perf_counter()
        self._animiram = True

        def korak():
            if oznaka != self._animacija:
                return                    # krenula je novija animacija
            t = min(1.0, (time.perf_counter() - pocetak) / trajanje)
            h = int(od + (do - od) * self._uspori(t))
            self.platno.config(height=h)
            self.geometry(f"{self.W}x{h}+{x}+{y}")
            if t < 1.0:
                self.after(10, korak)
            else:
                self.platno.config(height=do)
                self.geometry(f"{self.W}x{do}+{x}+{y}")
                self._animiram = False

        korak()

    # ------------------------------------------------- platno

    def _na_pomeranje(self, e):
        """Kad se prozor pomeri, kroz staklo mora da se vidi novo mesto."""
        if e.widget is not self or self._animiram:
            return
        if (self.winfo_x(), self.winfo_y()) == (self.px, self.py):
            return
        if self._posao_pomeranja:
            self.after_cancel(self._posao_pomeranja)
        self._posao_pomeranja = self.after(220, self._osvezi_pozadinu)

    def _prati_tapetu(self):
        """Ako korisnik promeni tapetu, staklo mora da pokaze novu."""
        try:
            if not self.skida and not self._providno:
                kljuc = draw.kljuc_tapete()
                if kljuc != self._kljuc_tapete:
                    self._kljuc_tapete = kljuc
                    draw.zaboravi_pozadinu()
                    self._ponovo()
        except Exception:
            pass
        finally:
            self.after(3000, self._prati_tapetu)

    def _osvezi_pozadinu(self):
        self._posao_pomeranja = None
        if (self.winfo_x(), self.winfo_y()) == (self.px, self.py):
            return
        self.px, self.py = self.winfo_x(), self.winfo_y()
        self._ponovo()          # nov isecak tapete za novo mesto

    def _novo_platno(self):
        """Sveže platno i sveža kopija pozadine, spremna za panele."""
        if self.platno:
            self.platno.destroy()
        self.generacija += 1
        ocisti_kes()
        self.platno = tk.Canvas(self, width=self.W, height=self.H,
                                highlightthickness=0, bd=0, bg=KLJUC)
        self.platno.pack(fill="both", expand=True)
        return draw.pozadina(self.W, self.H, self.px, self.py).copy()

    def _prikazi_bazu(self, baza):
        self.baza = baza
        self.slika_baze = ImageTk.PhotoImage(baza)
        self.platno.create_image(0, 0, anchor="nw", image=self.slika_baze)

    def _veza(self, x, y, sadrzaj, komanda, sidro="nw", boja=MENTA,
              font=None):
        i = tekst(self.platno, x, y, sadrzaj, font or (FAM_B, 9), boja,
                  sidro=sidro)
        self.platno.tag_bind(i, "<Button-1>", lambda _e: komanda())
        self.platno.tag_bind(i, "<Enter>", lambda _e: (
            self.platno.itemconfig(i, fill=MENTA_HI),
            self.platno.config(cursor="hand2")))
        self.platno.tag_bind(i, "<Leave>", lambda _e: (
            self.platno.itemconfig(i, fill=boja),
            self.platno.config(cursor="")))
        return i

    # ============================================= ekran 1: platforma

    def ekran_izbor(self):
        self.info = None
        self._ponovo = self.ekran_izbor
        pad, razmak = s(56), s(16)
        kh = s(104) if len(PLATFORME) <= 4 else s(88)
        # visina se racuna iz stvarnog broja opcija — dok je bila zakucana za
        # dve kartice, cetvrta je ispadala izvan prozora
        koliko = len(PLATFORME)
        blok = (s(54) + s(22) + s(46) + koliko * kh + (koliko - 1) * razmak)
        self._visina(min(blok + s(96) * 2,
                         self.winfo_screenheight() - s(130)))
        baza = self._novo_platno()
        kw = self.W - pad * 2
        y = (self.H - blok) // 2

        self._prikazi_bazu(baza)
        tekst(self.platno, pad, y, "Skidac", (FAM_N, 30), TXT, senka=True)
        tekst(self.platno, pad, y + s(54), "Odakle skidaš?", (FAM, 12), TXT2,
              senka=True)

        ky = y + s(54) + s(22) + s(46)
        for kljuc, (naziv, opis, ikona, _n) in PLATFORME.items():
            KarticaPlatforme(self.platno, baza, pad, ky, kw, kh, naziv, opis,
                             ikona, lambda k=kljuc: self.ekran_link(k))
            ky += kh + razmak
        self._zavrsi_visinu()

    # ============================================= ekran 2: link

    def ekran_link(self, izvor):
        self.izvor = izvor
        self.url = ""
        self.skida = False
        if izvor in LISTE:
            self.info = {"lista": True}     # kartica se vidi i dok je prazna
            self.lista = self._liste.setdefault(izvor, [])
            if izvor == "soundcloud":
                self.tip = "mp3"
                self.poruka_uvod = ("Pesma, set ili ceo profil — sve ulazi u "
                                    "spisak i skida se kao MP3.")
            else:
                self.tip = "mp4"
                self.poruka_uvod = ("Dodaj koliko hoces linkova, pa skini sve "
                                    "odjednom.")
        else:
            self.info = None
            self.poruka_uvod = "Kopiraj link i nalepi ga ovde — Ctrl+V."
        self._crtaj_link()

    def prikazi(self, url, info):
        self.url, self.info = url, info
        self.skida = False
        self.poruka_uvod = ""
        if self.izvor == "sajt":
            self.tip = "sajt"
            self.kvalitet = STRANA[1]
        else:
            self.formati = core.rezolucije(info)
            self.jezici = core.jezici_titlova(info)
            self.tip = "mp4"
            self.kvalitet = self.formati[0][1]
        self._crtaj_link()

    def _opcije_formata(self):
        """Treca opcija — prepis — ima smisla samo tamo gde ima titlova."""
        osnovne = [("MP4  ·  video", "mp4"), ("MP3  ·  zvuk", "mp3")]
        if self.izvor == "soundcloud":
            return [("MP3  ·  zvuk", "mp3")]    # SoundCloud nema video
        if self.izvor == "lista":
            return osnovne
        if self.izvor == "youtube":
            osnovne.append(("TXT  ·  prepis", "txt"))
        return osnovne

    def _raspored(self):
        """Sve koordinate unapred — panel mora u sliku pre nego što se crta."""
        r = {}
        pad = s(46)
        r["pad"] = pad
        r["polje_y"] = s(88)
        r["polje_h"] = s(54)
        r["dug_w"] = s(122)
        r["polje_w"] = self.W - pad * 2 - r["dug_w"] - s(12)

        y = r["polje_y"] + r["polje_h"] + s(18)
        if self.izvor == "instagram":
            r["kolacici_y"] = y
            y += s(26)
        r["status_y"] = y
        y += s(30)

        if not self.info:
            r["visina"] = y + s(26)
            return r

        r["kx"], r["kw"] = pad, self.W - pad * 2
        r["ky"] = y
        up = s(24)
        r["ux"] = r["kx"] + up
        r["uw"] = r["kw"] - up * 2
        r["tw"], r["th"] = s(172), s(97)
        r["cip_w"] = (r["uw"] - s(8) * 3) // 4
        r["cip_h"] = s(38)
        redovi = math.ceil(len(self._stavke()) / 4)

        y = r["ky"] + up
        if self.izvor in LISTE:
            r["y_zaglavlje"] = y
            y += s(28)
            r["y_redovi"] = y
            y += max(1, min(len(self.lista), VIDLJIVIH)) * s(26)
            if len(self.lista) > VIDLJIVIH:
                y += s(20)
            y += s(12)
            r["y_linija"] = y
            y += s(20)
            if len(self._opcije_formata()) > 1:
                r["y_nal_format"] = y
                y += s(16)
                r["y_segment"] = y
                y += s(42) + s(20)
        elif self.izvor == "sajt":
            # sajt nema sličicu ni izbor formata — samo naslov i koliko strana
            r["y_naslov"] = y
            y += s(52)
            r["y_linija"] = y
            y += s(20)
        else:
            r["y_slicica"] = y
            y += r["th"] + s(22)
            r["y_linija"] = y
            y += s(20)
            r["y_nal_format"] = y
            y += s(16)
            r["y_segment"] = y
            y += s(42) + s(20)
        r["y_nal_kval"] = y
        y += s(16)
        r["y_cipovi"] = y
        y += redovi * (r["cip_h"] + s(8)) - s(8) + s(20)
        r["y_folder"] = y
        y += s(28)
        r["y_dugme"] = y
        y += s(50)
        if self.skida:
            y += s(16)
            r["y_traka"] = y
            y += s(6) + s(14)
            r["y_napredak"] = y
            y += s(16)
        else:
            r["y_napredak"] = y + s(10)     # prazan red, ne zauzima visinu
        r["kh"] = y + up - r["ky"]
        r["visina"] = r["ky"] + r["kh"] + s(34)
        return r

    def _crtaj_link(self):
        self._ponovo = self._crtaj_link
        r = self._raspored()
        naziv, _opis, ikona, nagovestaj = PLATFORME[self.izvor]
        pad = r["pad"]

        self._visina(r["visina"])
        baza = self._novo_platno()
        ik = ikona(s(22))
        baza.paste(ik, (self.W - pad - s(22), s(34)), ik)
        if self.info:
            draw.panel(baza, r["kx"], r["ky"], r["kw"], r["kh"], s(30),
                       belina=0.10, ivica=0.26, pomak=s(14), s_blur=s(18),
                       s_jak=0.60)
        self._prikazi_bazu(baza)
        p = self.platno

        # --- zaglavlje
        self._veza(pad, s(40), "‹  Nazad", self.ekran_izbor, boja=TXT2,
                   font=(FAM, 10))
        tekst(p, self.W - pad - s(30), s(45), naziv, (FAM_B, 10), TXT2,
              sidro="e", senka=True)

        self.polje = Polje(p, baza, pad, r["polje_y"], r["polje_w"],
                           r["polje_h"], nagovestaj=nagovestaj)
        self.polje.entry.bind("<Return>", lambda _e: self.proveri())
        if self.url:
            self.polje.postavi(self.url)
        if self.izvor in LISTE:
            self.after(150, self.polje.fokusiraj)
        self.dug_proveri = Dugme(p, baza, self.W - pad - r["dug_w"],
                                 r["polje_y"], r["dug_w"], r["polje_h"],
                                 "Dodaj" if self.izvor in LISTE else "Proveri",
                                 self.proveri, stil="glavno", font=(FAM_B, 11))

        if self.izvor == "instagram":
            self._kvacica(pad, r["kolacici_y"])

        self.status_id = tekst(p, pad, r["status_y"], self.poruka_uvod,
                               (FAM, 9), TXT3, sirina=self.W - pad * 2,
                               senka=True)

        if self.info:
            self._crtaj_karticu(r)
        else:
            self.after(150, self.polje.fokusiraj)
        self._zavrsi_visinu()

    def _kvacica(self, x, y):
        """Prekidač za kolačiće — sitan, samo za Instagram."""
        def prebaci():
            self.kolacici = not self.kolacici
            self.platno.itemconfig(self.kv_id,
                                   text="●" if self.kolacici else "○",
                                   fill=MENTA if self.kolacici else TXT3)
        self.kv_id = tekst(self.platno, x, y, "●" if self.kolacici else "○",
                           (FAM, 10), MENTA if self.kolacici else TXT3)
        opis = self._veza(x + s(18), y + s(1),
                          "Objava traži prijavu — uzmi kolačiće iz Chrome-a",
                          prebaci, boja=TXT3, font=(FAM, 9))
        self.platno.tag_bind(self.kv_id, "<Button-1>", lambda _e: prebaci())
        self.platno.tag_bind(self.kv_id, "<Enter>",
                             lambda _e: self.platno.config(cursor="hand2"))
        self.platno.tag_bind(self.kv_id, "<Leave>",
                             lambda _e: self.platno.config(cursor=""))
        return opis

    # ============================================= kartica sa klipom

    def _crtaj_karticu(self, r):
        if self.izvor == "sajt":
            return self._kartica_sajta(r)
        if self.izvor in LISTE:
            return self._kartica_liste(r)

        p, baza, info = self.platno, self.baza, self.info
        ux, uw = r["ux"], r["uw"]

        self.slicica_box = (ux, r["y_slicica"], r["tw"], r["th"])
        self.slicica_id = p.create_image(ux, r["y_slicica"], anchor="nw")
        self._slicica_prazna()
        if info.get("thumbnail"):
            threading.Thread(target=self._citaj_slicicu,
                             args=(info["thumbnail"], r["tw"], r["th"],
                                   self.generacija), daemon=True).start()

        nx = ux + r["tw"] + s(20)
        naslov_id = tekst(p, nx, r["y_slicica"] + s(4),
                          core.skrati(info.get("title") or "Bez naslova", 80),
                          (FAM_B, 12), TXT, sirina=uw - r["tw"] - s(20))
        meta = []
        if info.get("uploader"):
            meta.append(core.skrati(info["uploader"], 24))
        if info.get("duration"):
            meta.append(core.trajanje(info["duration"]))
        if self.formati and self.formati[0][1]:
            meta.append(f"do {self.formati[0][1]}p")
        # meta ide ispod stvarne visine naslova — naslov ume da ide u dva reda
        donja_ivica = p.bbox(naslov_id)[3]
        tekst(p, nx, donja_ivica + s(8), "   ·   ".join(meta), (FAM, 9), TXT3)

        p.create_line(ux, r["y_linija"], ux + uw, r["y_linija"],
                      fill="#22453a")

        opcije = self._opcije_formata()
        nalepnica(p, ux, r["y_nal_format"], "Format")
        self.segment = Segment(p, baza, ux, r["y_segment"],
                               s(140) * len(opcije), s(42), opcije,
                               self._promeni_tip)

        self.nal_kval_id = nalepnica(p, ux, r["y_nal_kval"], "Rezolucija")
        self.cip_raspored = (ux, r["y_cipovi"], r["cip_w"], r["cip_h"])
        self.cipovi = []
        self._napuni_cipove()

        nalepnica(p, ux, r["y_folder"] + s(4), "Čuvam u")
        self.folder_id = tekst(p, ux + s(70), r["y_folder"] + s(3),
                               self._kratak_put(), (FAM, 9), TXT2)
        self._veza(ux + uw, r["y_folder"] + s(3), "Promeni",
                   self._izaberi_folder, sidro="ne")

        self.dug_skini = Dugme(p, baza, ux, r["y_dugme"], uw, s(50), "Skini",
                               self.skini, stil="glavno", font=(FAM_B, 12))
        self.traka = (Traka(p, baza, ux, r["y_traka"], uw, s(6))
                      if self.skida else None)
        self.napredak_id = tekst(p, ux, r["y_napredak"], "", (FAM, 9), TXT2,
                                 sirina=uw)
        if not core.FFMPEG:
            self._status("⚠  Nema ffmpeg-a — MP3 i 1080p+ neće raditi.", CRVENA)

    def _kartica_sajta(self, r):
        """Sajt nema format ni rezoluciju — bira se samo dokle da ide."""
        p, baza, info = self.platno, self.baza, self.info
        ux, uw = r["ux"], r["uw"]

        tekst(p, ux, r["y_naslov"], core.skrati(info["naslov"], 70),
              (FAM_B, 12), TXT, sirina=uw)
        tekst(p, ux, r["y_naslov"] + s(26), info["domen"], (FAM, 9), TXT3)
        p.create_line(ux, r["y_linija"], ux + uw, r["y_linija"], fill="#22453a")

        self.nal_kval_id = nalepnica(p, ux, r["y_nal_kval"], "Najviše strana")
        self.cip_raspored = (ux, r["y_cipovi"], r["cip_w"], r["cip_h"])
        self.cipovi = []
        self._napuni_cipove()

        self._red_foldera(r)
        self.dug_skini = Dugme(p, baza, ux, r["y_dugme"], uw, s(50),
                               "Skini sajt", self.skini, stil="glavno",
                               font=(FAM_B, 12))
        self.traka = (Traka(p, baza, ux, r["y_traka"], uw, s(6))
                      if self.skida else None)
        self.napredak_id = tekst(p, ux, r["y_napredak"], "", (FAM, 9), TXT2,
                                 sirina=uw)

    def _kartica_liste(self, r):
        """Spisak onoga sto ce se skinuti, pa format i kvalitet za sve."""
        p, baza = self.platno, self.baza
        ux, uw = r["ux"], r["uw"]
        broj = len(self.lista)

        tekst(p, ux, r["y_zaglavlje"],
              "Lista je prazna" if not broj else
              f"{broj} {'stavka' if broj == 1 else 'stavki'} u listi",
              (FAM_B, 11), TXT)
        if broj:
            self._veza(ux + uw, r["y_zaglavlje"] + s(2), "Isprazni",
                       self._isprazni_listu, sidro="ne")

        if not broj:
            tekst(p, ux, r["y_redovi"] + s(4),
                  "Nalepi link gore i klikni Dodaj. Moze i cela plejlista.",
                  (FAM, 9), TXT3)
        else:
            for i, (_u, naslov, koliko) in enumerate(self.lista[:VIDLJIVIH]):
                y = r["y_redovi"] + i * s(26)
                tekst(p, ux, y, f"{i + 1}.", (FAM, 9), TXT3)
                tekst(p, ux + s(24), y, core.skrati(naslov, 44), (FAM, 10), TXT2)
                if koliko:
                    tekst(p, ux + uw - s(28), y, core.trajanje(koliko),
                          (FAM, 9), TXT3, sidro="ne")
                self._veza(ux + uw, y, "✕", lambda k=i: self._izbaci(k),
                           sidro="ne", boja=TXT3, font=(FAM, 10))
            if broj > VIDLJIVIH:
                tekst(p, ux, r["y_redovi"] + VIDLJIVIH * s(26) + s(4),
                      f"… i jos {broj - VIDLJIVIH}", (FAM, 9), TXT3)

        p.create_line(ux, r["y_linija"], ux + uw, r["y_linija"], fill="#22453a")

        opcije = self._opcije_formata()
        if len(opcije) > 1:
            nalepnica(p, ux, r["y_nal_format"], "Format")
            self.segment = Segment(p, baza, ux, r["y_segment"],
                                   s(140) * len(opcije), s(42), opcije,
                                   self._promeni_tip)

        self.nal_kval_id = nalepnica(
            p, ux, r["y_nal_kval"],
            "Bitrate MP3" if self.tip == "mp3" else "Kvalitet")
        self.cip_raspored = (ux, r["y_cipovi"], r["cip_w"], r["cip_h"])
        self.cipovi = []
        self._napuni_cipove()

        self._red_foldera(r)
        self.dug_skini = Dugme(p, baza, ux, r["y_dugme"], uw, s(50),
                               f"Skini sve ({broj})" if broj else "Skini sve",
                               self.skini, stil="glavno", font=(FAM_B, 12))
        self.dug_skini.ukljuci(bool(broj))
        self.traka = (Traka(p, baza, ux, r["y_traka"], uw, s(6))
                      if self.skida else None)
        self.napredak_id = tekst(p, ux, r["y_napredak"], "", (FAM, 9), TXT2,
                                 sirina=uw)

    def _izbaci(self, i):
        if 0 <= i < len(self.lista):
            self.lista.pop(i)
            self._crtaj_link()

    def _isprazni_listu(self):
        self.lista.clear()      # ne novi spisak — ostaje vezan za svoj izvor
        self._crtaj_link()

    def _red_foldera(self, r):
        p, ux, uw = self.platno, r["ux"], r["uw"]
        nalepnica(p, ux, r["y_folder"] + s(4), "Čuvam u")
        self.folder_id = tekst(p, ux + s(70), r["y_folder"] + s(3),
                               self._kratak_put(), (FAM, 9), TXT2)
        self._veza(ux + uw, r["y_folder"] + s(3), "Promeni",
                   self._izaberi_folder, sidro="ne")

    def _slicica_prazna(self):
        x, y, w, h = self.slicica_box
        self.sl_slicica = ImageTk.PhotoImage(
            draw.staklo(self.baza, x, y, w, h, s(20), belina=0.08, ivica=0.20))
        self.platno.itemconfig(self.slicica_id, image=self.sl_slicica)

    # ============================================= provera linka

    def proveri(self):
        url, greska = core.sredi_url(self.polje.get(), self.izvor)
        if greska:
            return self._status(greska, CRVENA)
        self.dug_proveri.ukljuci(False)
        self.dug_proveri.natpis("Čitam…")
        self._status({"sajt": "Otvaram sajt…",
                      "lista": "Čitam link…",
                      "soundcloud": "Čitam sa SoundCloud-a…"}.get(self.izvor,
                                                  "Tražim podatke o klipu…"))
        threading.Thread(target=self._citaj, args=(url,), daemon=True).start()

    def _citaj(self, url):
        try:
            if self.izvor in LISTE:
                self.red.put(("dodato", core.procitaj_listu(url)))
            elif self.izvor == "sajt":
                podaci = sajt.naslov_i_domen(url)
                self.red.put(("info", (podaci["url"], podaci)))
            else:
                self.red.put(("info", (url, core.procitaj(url, self.izvor,
                                                          self.kolacici))))
        except Exception as e:
            self.red.put(("greska_info", core.poruka(e)))

    def _citaj_slicicu(self, url, w, h, generacija):
        try:
            zahtev = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"})
            sirovo = urllib.request.urlopen(zahtev, timeout=12).read()
            im = Image.open(io.BytesIO(sirovo)).convert("RGB")
            self.red.put(("slicica", (generacija, draw.uklopi(im, w, h))))
        except Exception:
            pass

    # ============================================= izbori

    def _stavke(self):
        if self.izvor == "lista" and self.tip == "mp4":
            return [("do %dp" % v, v) for v in core.GRANICE]
        if self.tip == "sajt":
            return [(f"{n} strana", n) for n in STRANA]
        if self.tip == "mp4":
            return list(self.formati)
        if self.tip == "txt":
            return list(self.jezici) or [("Nema titlova", None)]
        return [(f"{b} kbps", b) for b in core.BITRATE]

    def _podrazumevani_kvalitet(self, stavke):
        if self.tip == "mp3":
            return 192
        if self.tip == "sajt":
            return STRANA[1]
        if self.izvor == "lista":
            return 1080
        return stavke[0][1]

    def _napuni_cipove(self):
        for c in self.cipovi:
            c.obrisi()
        self.cipovi = []
        x0, y0, cw, ch = self.cip_raspored
        stavke = self._stavke()
        self.kvalitet = self._podrazumevani_kvalitet(stavke)

        for i, (labela, vrednost) in enumerate(stavke):
            c = Cip(self.platno, self.baza,
                    x0 + (i % 4) * (cw + s(8)), y0 + (i // 4) * (ch + s(8)),
                    cw, ch, labela, vrednost, self._izaberi_kvalitet)
            c.izaberi(vrednost == self.kvalitet)
            self.cipovi.append(c)

    def _izaberi_kvalitet(self, vrednost):
        self.kvalitet = vrednost
        for c in self.cipovi:
            c.izaberi(c.vrednost == vrednost)

    NASLOVI_KVALITETA = {
        "mp4": "Rezolucija",
        "mp3": "Bitrate zvuka",
        "txt": "Jezik prepisa",
        "sajt": "Najviše strana",
    }

    def _promeni_tip(self, vrednost):
        self.tip = vrednost
        self.platno.itemconfig(
            self.nal_kval_id,
            text=self.NASLOVI_KVALITETA[vrednost].upper())
        self._napuni_cipove()
        if vrednost == "txt" and not self.jezici:
            self._napredak("Ovaj video nema titlove, pa nema šta da se prepiše.",
                           CRVENA)
        else:
            self._napredak("")

    def _kratak_put(self):
        delovi = self.folder.replace("/", "\\").split("\\")
        return "…\\" + "\\".join(delovi[-2:]) if len(delovi) > 3 else self.folder

    def _izaberi_folder(self):
        d = filedialog.askdirectory(initialdir=self.folder)
        if d:
            self.folder = os.path.normpath(d)
            self.platno.itemconfig(self.folder_id, text=self._kratak_put())

    # ============================================= skidanje

    def skini(self):
        if self.skida:
            return self._zaustavi()
        if self.izvor in LISTE and not self.lista:
            return self._napredak("Lista je prazna.", CRVENA)
        if not os.path.isdir(self.folder):
            return self._napredak("Taj folder ne postoji.", CRVENA)
        if self.tip in ("mp3", "txt") and not core.FFMPEG:
            return self._napredak("Za ovo je potreban ffmpeg.", CRVENA)
        if self.tip == "txt" and not self.kvalitet:
            return self._napredak("Ovaj video nema titlove.", CRVENA)

        self.skida = True
        self._stani = False
        self._crtaj_link()                      # kartica se produzi za traku
        self.dug_skini.natpis("Zaustavi")
        self.dug_proveri.ukljuci(False)
        self._napredak("Krećem…")
        threading.Thread(target=self._skidaj, daemon=True).start()

    def _zaustavi(self):
        self._stani = True
        self.dug_skini.ukljuci(False)
        self.dug_skini.natpis("Zaustavljam…")
        self._napredak("Prekidam…")

    def _skidaj(self):
        try:
            if self.izvor in LISTE:
                self._skidaj_listu()
            elif self.izvor == "sajt":
                self._skidaj_sajt()
            elif self.tip == "txt":
                put = core.skini_transkript(
                    self.url, self.izvor, self.folder, self.kvalitet,
                    self.kolacici, na_napredak=self._kuka)
                self.red.put(("gotovo", os.path.basename(put)))
            else:
                core.skini(self.url, self.izvor, self.folder, self.tip,
                           self.kvalitet, self.kolacici,
                           na_napredak=self._kuka, na_obradu=self._kuka_obrada)
                self.red.put(("gotovo", None))
        except sajt.Zaustavljeno:
            self.red.put(("prekinuto", None))
        except core.Prekid:
            self.red.put(("prekinuto", None))
        except Exception as e:
            self.red.put(("greska", core.poruka(e)))

    def _skidaj_listu(self):
        """Jedna po jedna; greska na jednoj ne rusi ostatak."""
        ukupno = len(self.lista)
        palo = []
        for i, (url, naslov, _t) in enumerate(list(self.lista)):
            if self._stani:
                raise core.Prekid()
            self._redni, self._ukupno, self._naslov = i, ukupno, naslov
            try:
                core.skini(url, self.izvor, self.folder, self.tip,
                           self.kvalitet, self.kolacici,
                           na_napredak=self._kuka, na_obradu=self._kuka_obrada)
            except core.Prekid:
                raise
            except Exception:
                palo.append(naslov)
        self.red.put(("gotova_lista", (ukupno, palo)))

    def _skidaj_sajt(self):
        preuzimac = sajt.Preuzimac(
            self.url, self.folder, najvise_strana=self.kvalitet,
            na_napredak=self._kuka_sajt, stani=lambda: self._stani)
        ishod = preuzimac.kreni()
        self.red.put(("gotov_sajt", ishod))

    def _kuka_sajt(self, strana, fajlova, u_redu, url):
        pct = min(99, strana / max(1, self.kvalitet) * 100)
        ime = url.split("/")[-1] or "index"
        self.red.put(("napredak", (
            pct,
            f"{strana} strana   ·   {fajlova} fajlova   ·   "
            f"{u_redu} u redu   ·   {core.skrati(ime, 34)}")))

    def _kuka(self, d):
        if self._stani:
            raise core.Prekid()
        if d["status"] == "downloading":
            ukupno = d.get("total_bytes") or d.get("total_bytes_estimate")
            gotovo = d.get("downloaded_bytes") or 0
            pct = (gotovo / ukupno * 100) if ukupno else 0
            if self.izvor in LISTE:
                return self._napredak_liste(pct, d)
            delovi = [f"{pct:.0f}%",
                      f"{core.velicina(gotovo)} / {core.velicina(ukupno)}"]
            if d.get("speed"):
                delovi.append(f"{core.velicina(d['speed'])}/s")
            if d.get("eta"):
                delovi.append(f"još {core.trajanje(d['eta'])}")
            self.red.put(("napredak", (pct, "   ·   ".join(delovi))))
        elif d["status"] == "finished":
            self.red.put(("napredak", (100, "Preuzeto — obrađujem fajl…")))

    def _napredak_liste(self, pct, d):
        """Traka pokazuje celu listu, tekst pokazuje trenutnu stavku."""
        ceo = (self._redni + pct / 100) / max(1, self._ukupno) * 100
        delovi = ["%d/%d" % (self._redni + 1, self._ukupno),
                  core.skrati(self._naslov, 32), "%.0f%%" % pct]
        if d.get("speed"):
            delovi.append(core.velicina(d["speed"]) + "/s")
        self.red.put(("napredak", (ceo, "   \u00b7   ".join(delovi))))

    def _kuka_obrada(self, d):
        if d["status"] == "started":
            self.red.put(("napredak", (100, "Konvertujem…")))

    # ============================================= poruke iz niti

    def _pumpa(self):
        try:
            while True:
                vrsta, podatak = self.red.get_nowait()

                if vrsta == "info":
                    self.prikazi(*podatak)

                elif vrsta == "slicica":
                    self._stavi_slicicu(*podatak)

                elif vrsta == "greska_info":
                    self.dug_proveri.ukljuci(True)
                    self.dug_proveri.natpis("Proveri")
                    self._status(podatak, CRVENA)

                elif vrsta == "napredak":
                    pct, poruka = podatak
                    if self.traka:
                        self.traka.postavi(pct)
                    self._napredak(poruka)

                elif vrsta == "gotovo":
                    if self.traka:
                        self.traka.postavi(100)
                    self._napredak("✓  Gotovo — " + (podatak or "fajl") +
                                   " je u folderu.", MENTA)
                    self._odblokiraj()
                    self._otvori(self.folder)

                elif vrsta == "dodato":
                    self._dodaj_u_listu(podatak)

                elif vrsta == "gotova_lista":
                    ukupno, palo = podatak
                    if self.traka:
                        self.traka.postavi(100)
                    poruka = "\u2713  Gotovo \u2014 skinuto %d/%d." % (
                        ukupno - len(palo), ukupno)
                    if palo:
                        poruka += "  Nije uspelo: " + core.skrati(palo[0], 28)
                        if len(palo) > 1:
                            poruka += " i jos %d" % (len(palo) - 1)
                    self._napredak(poruka, CRVENA if palo else MENTA)
                    self._odblokiraj()
                    self._otvori(self.folder)

                elif vrsta == "gotov_sajt":
                    if self.traka:
                        self.traka.postavi(100)
                    poruka = (f"✓  Gotovo — {podatak['strana']} strana i "
                              f"{podatak['fajlova']} fajlova.")
                    if podatak["preskoceno"]:
                        poruka += (f"  Preskočeno {podatak['preskoceno']} "
                                   "(robots.txt ili greška).")
                    self._napredak(poruka, MENTA)
                    self._odblokiraj()
                    self._otvori(podatak["folder"])

                elif vrsta == "prekinuto":
                    self._napredak("Zaustavljeno — što je skinuto ostaje.",
                                   TXT2)
                    self._odblokiraj()

                elif vrsta == "greska":
                    self._napredak(podatak, CRVENA)
                    self._odblokiraj()
        except queue.Empty:
            pass
        except Exception:
            traceback.print_exc()
        finally:
            self.after(120, self._pumpa)

    def _dodaj_u_listu(self, stavke):
        """Plejlista ume da ima na stotine stavki — uzimamo razuman deo."""
        self.dug_proveri.ukljuci(True)
        self.dug_proveri.natpis("Dodaj")

        postojeci = {u for u, _n, _t in self.lista}
        nove = [x for x in stavke[:NAJVISE_ODJEDNOM] if x[0] not in postojeci]
        mesta = max(0, NAJVECA_LISTA - len(self.lista))
        odbaceno = len(nove) - mesta
        nove = nove[:mesta]
        self.lista.extend(nove)

        if not nove:
            poruke = ["To je vec u listi."]
        else:
            poruke = ["Dodato %d." % len(nove)]
            if len(stavke) > NAJVISE_ODJEDNOM:
                poruke.append("Plejlista ima %d, uzeto prvih %d."
                              % (len(stavke), NAJVISE_ODJEDNOM))
            if odbaceno > 0:
                poruke.append("Lista je puna (%d)." % NAJVECA_LISTA)
        self.poruka_uvod = "  ".join(poruke)
        self.url = ""
        self._crtaj_link()

    def _stavi_slicicu(self, generacija, im):
        if generacija != self.generacija:
            return                       # ekran je u medjuvremenu pregradjen
        """Slika se spaja sa pozadinom u Pillow-u — pouzdanije od alfe na platnu."""
        x, y, w, h = self.slicica_box
        podloga = self.baza.crop((x, y, x + w, y + h))
        slika = im.copy()
        slika.putalpha(draw.maska(w, h, s(20)))
        podloga.paste(slika, (0, 0), slika)
        self.sl_slicica = ImageTk.PhotoImage(podloga)
        self.platno.itemconfig(self.slicica_id, image=self.sl_slicica)

    def _otvori(self, folder):
        try:
            os.startfile(folder)
        except OSError:
            pass

    def _odblokiraj(self):
        self.skida = False
        self._stani = False
        self.dug_skini.ukljuci(True)
        self.dug_skini.natpis("Skini sajt" if self.izvor == "sajt" else "Skini")
        self.dug_proveri.ukljuci(True)

    def _status(self, sadrzaj, boja=TXT3):
        self.platno.itemconfig(self.status_id, text=sadrzaj, fill=boja)

    def _napredak(self, sadrzaj, boja=TXT2):
        self.platno.itemconfig(self.napredak_id, text=sadrzaj, fill=boja)
