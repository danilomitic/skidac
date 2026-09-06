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
import traceback
import tkinter as tk
import urllib.request
from tkinter import filedialog

from PIL import Image, ImageTk

from . import core, draw
from .theme import (CRVENA, FAM, FAM_B, FAM_N, MENTA, MENTA_HI, TXT, TXT2,
                    TXT3, izaberi_fontove, postavi_skalu, s)
from .widgets import (Cip, Dugme, Element, Polje, Segment, Traka, nalepnica,
                      ocisti_kes, tekst)

PLATFORME = {
    "youtube":   ("YouTube", "Video, Shorts, plejliste", draw.ikona_youtube,
                  "https://www.youtube.com/watch?v=…"),
    "instagram": ("Instagram", "Reels, objave, IGTV", draw.ikona_instagram,
                  "https://www.instagram.com/reel/…"),
}


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
        self.configure(bg="#020705")
        self.resizable(False, False)
        try:
            self.iconbitmap(core.resource_path("icon.ico"))
        except tk.TclError:
            pass

        self._tamna_traka()

        self.izvor = None
        self.info = None
        self.url = ""
        self.formati = []
        self.tip = "mp4"
        self.kvalitet = None
        self.folder = core.podrazumevani_folder()
        self.kolacici = False
        self.skida = False
        self.poruka_uvod = ""
        self.red = queue.Queue()

        self._postavljen = False
        self.generacija = 0
        self.platno = None
        self.ekran_izbor()
        self.after(100, self._pumpa)

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

    def _visina(self, h):
        """Prozor raste prema sadrzaju, umesto da zjapi prazan."""
        self.H = h
        if not self._postavljen:
            x = (self.winfo_screenwidth() - self.W) // 2
            y = max(0, (self.winfo_screenheight() - self.H) // 2 - s(24))
            self._postavljen = True
        else:
            x, y = self.winfo_x(), self.winfo_y()
            y = min(y, max(0, self.winfo_screenheight() - h - s(60)))
        self.geometry(f"{self.W}x{self.H}+{x}+{y}")

    # ------------------------------------------------- platno

    def _novo_platno(self):
        """Sveže platno i sveža kopija pozadine, spremna za panele."""
        if self.platno:
            self.platno.destroy()
        self.generacija += 1
        ocisti_kes()
        self.platno = tk.Canvas(self, width=self.W, height=self.H,
                                highlightthickness=0, bd=0, bg="#020705")
        self.platno.pack(fill="both", expand=True)
        return draw.pozadina(self.W, self.H).copy()

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
        pad, kh, razmak = s(56), s(104), s(16)
        blok = s(54) + s(22) + s(46) + kh + razmak + kh
        self._visina(blok + s(150) * 2)
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

    # ============================================= ekran 2: link

    def ekran_link(self, izvor):
        self.izvor = izvor
        self.info = None
        self.url = ""
        self.skida = False
        self.poruka_uvod = "Kopiraj link i nalepi ga ovde — Ctrl+V."
        self._crtaj_link()

    def prikazi(self, url, info):
        self.url, self.info = url, info
        self.formati = core.rezolucije(info)
        self.skida = False
        self.tip = "mp4"
        self.kvalitet = self.formati[0][1]
        self.poruka_uvod = ""
        self._crtaj_link()

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
              sidro="e")

        self.polje = Polje(p, baza, pad, r["polje_y"], r["polje_w"],
                           r["polje_h"], nagovestaj=nagovestaj)
        self.polje.entry.bind("<Return>", lambda _e: self.proveri())
        if self.url:
            self.polje.postavi(self.url)
        self.dug_proveri = Dugme(p, baza, self.W - pad - r["dug_w"],
                                 r["polje_y"], r["dug_w"], r["polje_h"],
                                 "Proveri", self.proveri, stil="glavno",
                                 font=(FAM_B, 11))

        if self.izvor == "instagram":
            self._kvacica(pad, r["kolacici_y"])

        self.status_id = tekst(p, pad, r["status_y"], self.poruka_uvod,
                               (FAM, 9), TXT3, sirina=self.W - pad * 2)

        if self.info:
            self._crtaj_karticu(r)
        else:
            self.after(150, self.polje.fokusiraj)

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

        nalepnica(p, ux, r["y_nal_format"], "Format")
        self.segment = Segment(p, baza, ux, r["y_segment"], s(296), s(42),
                               [("MP4  ·  video", "mp4"),
                                ("MP3  ·  zvuk", "mp3")], self._promeni_tip)

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
        self._status("Tražim podatke o klipu…")
        threading.Thread(target=self._citaj, args=(url,), daemon=True).start()

    def _citaj(self, url):
        try:
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
        if self.tip == "mp4":
            return list(self.formati)
        return [(f"{b} kbps", b) for b in core.BITRATE]

    def _napuni_cipove(self):
        for c in self.cipovi:
            c.obrisi()
        self.cipovi = []
        x0, y0, cw, ch = self.cip_raspored
        stavke = self._stavke()
        self.kvalitet = stavke[0][1] if self.tip == "mp4" else 192

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

    def _promeni_tip(self, vrednost):
        self.tip = vrednost
        self.platno.itemconfig(
            self.nal_kval_id,
            text="REZOLUCIJA" if vrednost == "mp4" else "BITRATE ZVUKA")
        self._napuni_cipove()

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
        if not os.path.isdir(self.folder):
            return self._napredak("Taj folder ne postoji.", CRVENA)
        if self.tip == "mp3" and not core.FFMPEG:
            return self._napredak("Za MP3 je potreban ffmpeg.", CRVENA)

        self.skida = True
        self._crtaj_link()                      # kartica se produzi za traku
        self.dug_skini.ukljuci(False)
        self.dug_skini.natpis("Skidam…")
        self.dug_proveri.ukljuci(False)
        self._napredak("Krećem…")
        threading.Thread(target=self._skidaj, daemon=True).start()

    def _skidaj(self):
        try:
            core.skini(self.url, self.izvor, self.folder, self.tip,
                       self.kvalitet, self.kolacici,
                       na_napredak=self._kuka, na_obradu=self._kuka_obrada)
            self.red.put(("gotovo", None))
        except Exception as e:
            self.red.put(("greska", core.poruka(e)))

    def _kuka(self, d):
        if d["status"] == "downloading":
            ukupno = d.get("total_bytes") or d.get("total_bytes_estimate")
            gotovo = d.get("downloaded_bytes") or 0
            pct = (gotovo / ukupno * 100) if ukupno else 0
            delovi = [f"{pct:.0f}%",
                      f"{core.velicina(gotovo)} / {core.velicina(ukupno)}"]
            if d.get("speed"):
                delovi.append(f"{core.velicina(d['speed'])}/s")
            if d.get("eta"):
                delovi.append(f"još {core.trajanje(d['eta'])}")
            self.red.put(("napredak", (pct, "   ·   ".join(delovi))))
        elif d["status"] == "finished":
            self.red.put(("napredak", (100, "Preuzeto — obrađujem fajl…")))

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
                    self._napredak("✓  Gotovo — fajl je u folderu.", MENTA)
                    self._odblokiraj()
                    try:
                        os.startfile(self.folder)
                    except OSError:
                        pass

                elif vrsta == "greska":
                    self._napredak(podatak, CRVENA)
                    self._odblokiraj()
        except queue.Empty:
            pass
        except Exception:
            traceback.print_exc()
        finally:
            self.after(120, self._pumpa)

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

    def _odblokiraj(self):
        self.dug_skini.ukljuci(True)
        self.dug_skini.natpis("Skini")
        self.dug_proveri.ukljuci(True)

    def _status(self, sadrzaj, boja=TXT3):
        self.platno.itemconfig(self.status_id, text=sadrzaj, fill=boja)

    def _napredak(self, sadrzaj, boja=TXT2):
        self.platno.itemconfig(self.napredak_id, text=sadrzaj, fill=boja)
