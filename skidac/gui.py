# -*- coding: utf-8 -*-
"""Prozor aplikacije — dva ekrana: izbor platforme, pa link i skidanje."""

import io
import os
import queue
import threading
import tkinter as tk
import urllib.request
from tkinter import filedialog

from PIL import Image, ImageTk

from . import core
from .draw import ikona_instagram, ikona_youtube, rr, uklopi, zaobli
from .theme import (BG, CARD, DIM, FAM, FAM_B, FIELD, LINE, MINT, MUTED, RED,
                    TXT, postavi_skalu, s)
from .widgets import (Cip, Dugme, Kartica, Polje, Segment, Traka, nalepnica,
                      potomci, veza)

PLATFORME = {
    "youtube":   ("YouTube", "Video, Shorts, plejliste", ikona_youtube,
                  "https://www.youtube.com/watch?v=…"),
    "instagram": ("Instagram", "Reels, objave, IGTV", ikona_instagram,
                  "https://www.instagram.com/reel/…"),
}


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        postavi_skalu(self.winfo_fpixels("1i"))
        self.tk.call("tk", "scaling", self.winfo_fpixels("1i") / 72.0)

        self.title("Skidac")
        self.configure(bg=BG)
        self._centriraj(s(660), s(720))
        self.minsize(s(620), s(680))
        try:
            self.iconbitmap(core.resource_path("icon.ico"))
        except tk.TclError:
            pass

        self.izvor = None
        self.info = None
        self.url = ""
        self.formati = []
        self.tip = "mp4"
        self.kvalitet = None
        self.folder = core.podrazumevani_folder()
        self.kolacici = tk.BooleanVar(value=False)
        self.red = queue.Queue()
        self.slike = []          # reference, da GC ne pojede slike

        self.ekran_izbor()
        self.after(100, self._pumpa)

    def _centriraj(self, w, h):
        x = (self.winfo_screenwidth() - w) // 2
        y = max(0, (self.winfo_screenheight() - h) // 2 - s(30))
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _ocisti(self):
        for w in self.winfo_children():
            w.destroy()
        self.slike.clear()

    # ============================================= ekran 1: platforma

    def ekran_izbor(self):
        self._ocisti()
        okvir = tk.Frame(self, bg=BG)
        okvir.pack(fill="both", expand=True, padx=s(52))

        # sadrzaj po sredini visine, da ne visi uz vrh
        sredina = tk.Frame(okvir, bg=BG)
        sredina.place(relx=0, rely=0.5, relwidth=1.0, anchor="w")
        okvir = sredina

        tk.Label(okvir, text="Skidac", bg=BG, fg=TXT,
                 font=(FAM_B, 24)).pack(anchor="w")
        tk.Label(okvir, text="Odakle skidaš?", bg=BG, fg=MUTED,
                 font=(FAM, 11)).pack(anchor="w", pady=(s(6), s(34)))

        for kljuc, (naziv, opis, ikona, _n) in PLATFORME.items():
            self._kartica_platforme(okvir, kljuc, naziv, opis, ikona)

    def _kartica_platforme(self, master, kljuc, naziv, opis, ikona):
        k = Kartica(master, bg=BG, pad=s(18))
        k.pack(fill="x", pady=s(6))
        k.configure(height=s(88))
        k.pack_propagate(False)

        slika = ikona(s(44))
        self.slike.append(slika)
        tk.Label(k.telo, image=slika, bg=CARD, bd=0).pack(side="left",
                                                          padx=(0, s(16)))
        tekst = tk.Frame(k.telo, bg=CARD)
        tekst.pack(side="left", fill="y")
        tk.Label(tekst, text=naziv, bg=CARD, fg=TXT,
                 font=(FAM_B, 13)).pack(anchor="w")
        tk.Label(tekst, text=opis, bg=CARD, fg=MUTED,
                 font=(FAM, 9)).pack(anchor="w", pady=(s(3), 0))
        strelica = tk.Label(k.telo, text="›", bg=CARD, fg=DIM, font=(FAM, 18))
        strelica.pack(side="right")

        def uđi(_e=None):
            k.oboji(FIELD)
            strelica.config(fg=MINT)

        def izađi(_e=None):
            k.oboji(CARD)
            strelica.config(fg=DIM)

        for w in [k, k.platno, k.telo] + potomci(k.telo):
            w.bind("<Button-1>", lambda _e: self.ekran_link(kljuc))
            w.bind("<Enter>", uđi)
            w.bind("<Leave>", izađi)
            try:
                w.config(cursor="hand2")
            except tk.TclError:
                pass

    # ============================================= ekran 2: link

    def ekran_link(self, izvor):
        self.izvor = izvor
        self.info = None
        self._ocisti()
        naziv, _opis, ikona, nagovestaj = PLATFORME[izvor]

        glava = tk.Frame(self, bg=BG)
        glava.pack(fill="x", padx=s(38), pady=(s(24), 0))
        nazad = tk.Label(glava, text="‹  Nazad", bg=BG, fg=MUTED,
                         font=(FAM, 10), cursor="hand2")
        nazad.pack(side="left")
        nazad.bind("<Button-1>", lambda _e: self.ekran_izbor())
        nazad.bind("<Enter>", lambda _e: nazad.config(fg=TXT))
        nazad.bind("<Leave>", lambda _e: nazad.config(fg=MUTED))

        znak = ikona(s(20), bg=BG)
        self.slike.append(znak)
        desno = tk.Frame(glava, bg=BG)
        desno.pack(side="right")
        tk.Label(desno, text=naziv, bg=BG, fg=MUTED,
                 font=(FAM_B, 10)).pack(side="right", padx=(s(8), 0))
        tk.Label(desno, image=znak, bg=BG, bd=0).pack(side="right")

        telo = tk.Frame(self, bg=BG)
        telo.pack(fill="both", expand=True, padx=s(38), pady=(s(20), s(26)))

        red_link = tk.Frame(telo, bg=BG)
        red_link.pack(fill="x")
        self.polje = Polje(red_link, bg=BG, nagovestaj=nagovestaj)
        self.polje.pack(side="left", fill="x", expand=True)
        self.polje.entry.bind("<Return>", lambda _e: self.proveri())
        self.dug_proveri = Dugme(red_link, "Proveri", self.proveri, bg=BG,
                                 stil="glavno", height=s(46), width=s(108))
        self.dug_proveri.pack(side="left", padx=(s(10), 0))

        if izvor == "instagram":
            tk.Checkbutton(
                telo, text="Objava traži prijavu — uzmi kolačiće iz Chrome-a",
                variable=self.kolacici, bg=BG, fg=MUTED, font=(FAM, 9),
                selectcolor=FIELD, activebackground=BG, activeforeground=TXT,
                highlightthickness=0, bd=0, cursor="hand2").pack(
                    anchor="w", pady=(s(12), 0))

        self.status = tk.Label(telo, text="", bg=BG, fg=MUTED, font=(FAM, 9),
                               wraplength=s(540), justify="left")
        self.status.pack(anchor="w", pady=(s(12), 0))

        self._status("Kopiraj link iz pretraživača i nalepi ga ovde — Ctrl+V.")
        self.kartica = Kartica(telo, bg=BG, pad=s(22))
        self.after(150, self.polje.fokusiraj)

    # ============================================= provera linka

    def proveri(self):
        url, greska = core.sredi_url(self.polje.get(), self.izvor)
        if greska:
            return self._status(greska, RED)

        self.kartica.pack_forget()
        self.dug_proveri.ukljuci(False)
        self.dug_proveri.natpis("Čitam…")
        self._status("Tražim podatke o klipu…")
        threading.Thread(target=self._citaj, args=(url,), daemon=True).start()

    def _citaj(self, url):
        try:
            info = core.procitaj(url, self.izvor, self.kolacici.get())
            self.red.put(("info", (url, info)))
        except Exception as e:
            self.red.put(("greska_info", core.poruka(e)))

    def _citaj_slicicu(self, url, w, h):
        try:
            zahtev = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"})
            sirovo = urllib.request.urlopen(zahtev, timeout=12).read()
            im = Image.open(io.BytesIO(sirovo)).convert("RGB")
            self.red.put(("slicica", zaobli(uklopi(im, w, h), s(10))))
        except Exception:
            pass

    # ============================================= kartica sa klipom

    def prikazi(self, url, info):
        self.url, self.info = url, info
        self.formati = core.rezolucije(info)
        self.dug_proveri.ukljuci(True)
        self.dug_proveri.natpis("Proveri")
        self._status("")

        for w in self.kartica.telo.winfo_children():
            w.destroy()
        self.kartica.pack(fill="x", pady=(s(14), 0))
        telo = self.kartica.telo

        self._zaglavlje(telo, info)
        tk.Frame(telo, bg=LINE, height=1).pack(fill="x", pady=(s(18), s(16)))
        self._izbor_formata(telo)
        self._izbor_kvaliteta(telo)
        self._red_foldera(telo)

        self.dug_skini = Dugme(telo, "Skini", self.skini, bg=CARD,
                               stil="glavno", height=s(48), font=(FAM_B, 11))
        self.dug_skini.pack(fill="x")

        self.traka = Traka(telo, bg=CARD)
        self.napredak = tk.Label(telo, text="", bg=CARD, fg=MUTED,
                                 font=(FAM, 9), wraplength=s(500),
                                 justify="left")

        if not core.FFMPEG:
            tk.Label(telo, text="⚠  Nema ffmpeg-a — MP3 i 1080p+ neće raditi.",
                     bg=CARD, fg=RED, font=(FAM, 9)).pack(anchor="w",
                                                          pady=(s(12), 0))

    def _zaglavlje(self, telo, info):
        vrh = tk.Frame(telo, bg=CARD)
        vrh.pack(fill="x")

        tw, th = s(152), s(86)
        prazno = rr(tw, th, s(10), FIELD, CARD)
        self.slike.append(prazno)
        self.slicica = tk.Label(vrh, image=prazno, bg=CARD, bd=0)
        self.slicica.pack(side="left")
        if info.get("thumbnail"):
            threading.Thread(target=self._citaj_slicicu,
                             args=(info["thumbnail"], tw, th),
                             daemon=True).start()

        desno = tk.Frame(vrh, bg=CARD)
        desno.pack(side="left", fill="both", expand=True, padx=(s(16), 0))
        tk.Label(desno, text=core.skrati(info.get("title") or "Bez naslova", 72),
                 bg=CARD, fg=TXT, font=(FAM_B, 11), wraplength=s(360),
                 justify="left").pack(anchor="w")

        meta = []
        if info.get("uploader"):
            meta.append(core.skrati(info["uploader"], 26))
        if info.get("duration"):
            meta.append(core.trajanje(info["duration"]))
        if self.formati and self.formati[0][1]:
            meta.append(f"do {self.formati[0][1]}p")
        tk.Label(desno, text="   ·   ".join(meta), bg=CARD, fg=MUTED,
                 font=(FAM, 9)).pack(anchor="w", pady=(s(7), 0))

    def _izbor_formata(self, telo):
        nalepnica(telo, "Format")
        Segment(telo, [("MP4  ·  video", "mp4"), ("MP3  ·  zvuk", "mp3")],
                self._promeni_tip, bg=CARD,
                width=s(280)).pack(anchor="w", pady=(s(8), s(16)))

    def _izbor_kvaliteta(self, telo):
        self.natpis_kval = nalepnica(telo, "Rezolucija")
        self.mreza = tk.Frame(telo, bg=CARD)
        self.mreza.pack(fill="x", pady=(s(8), s(14)))
        self.cipovi = []
        self._napuni_cipove()

    def _napuni_cipove(self):
        for c in self.cipovi:
            c.destroy()
        self.cipovi = []

        if self.tip == "mp4":
            stavke = list(self.formati)
        else:
            stavke = [(f"{b} kbps", b) for b in core.BITRATE]
        self.kvalitet = stavke[0][1] if self.tip == "mp4" else 192

        for i, (labela, vrednost) in enumerate(stavke):
            c = Cip(self.mreza, labela, vrednost, self._izaberi_kvalitet, bg=CARD)
            c.grid(row=i // 4, column=i % 4, padx=(0, s(8)), pady=(0, s(8)),
                   sticky="w")
            c.izaberi(vrednost == self.kvalitet)
            self.cipovi.append(c)

    def _izaberi_kvalitet(self, vrednost):
        self.kvalitet = vrednost
        for c in self.cipovi:
            c.izaberi(c.vrednost == vrednost)

    def _promeni_tip(self, vrednost):
        self.tip = vrednost
        self.natpis_kval.config(
            text="REZOLUCIJA" if vrednost == "mp4" else "BITRATE ZVUKA")
        self._napuni_cipove()

    def _red_foldera(self, telo):
        red = tk.Frame(telo, bg=CARD)
        red.pack(fill="x", pady=(0, s(18)))
        tk.Label(red, text="Čuvam u", bg=CARD, fg=DIM,
                 font=(FAM_B, 8)).pack(side="left")
        self.natpis_folder = tk.Label(red, text=self._kratak_put(), bg=CARD,
                                      fg=MUTED, font=(FAM, 9))
        self.natpis_folder.pack(side="left", padx=(s(10), 0))
        veza(red, "Promeni", self._izaberi_folder, bg=CARD).pack(side="right")

    def _kratak_put(self):
        delovi = self.folder.replace("/", "\\").split("\\")
        return "…\\" + "\\".join(delovi[-2:]) if len(delovi) > 3 else self.folder

    def _izaberi_folder(self):
        d = filedialog.askdirectory(initialdir=self.folder)
        if d:
            self.folder = os.path.normpath(d)
            self.natpis_folder.config(text=self._kratak_put())

    # ============================================= skidanje

    def skini(self):
        if not os.path.isdir(self.folder):
            return self._status("Taj folder ne postoji.", RED)
        if self.tip == "mp3" and not core.FFMPEG:
            return self._status("Za MP3 je potreban ffmpeg.", RED)

        self.dug_skini.ukljuci(False)
        self.dug_skini.natpis("Skidam…")
        self.dug_proveri.ukljuci(False)
        self.traka.pack(fill="x", pady=(s(16), s(8)))
        self.traka.postavi(0)
        self.napredak.pack(anchor="w")
        self.napredak.config(text="Krećem…", fg=MUTED)
        threading.Thread(target=self._skidaj, daemon=True).start()

    def _skidaj(self):
        try:
            core.skini(self.url, self.izvor, self.folder, self.tip,
                       self.kvalitet, self.kolacici.get(),
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
                    slika = ImageTk.PhotoImage(podatak)
                    self.slike.append(slika)
                    self.slicica.config(image=slika)

                elif vrsta == "greska_info":
                    self.dug_proveri.ukljuci(True)
                    self.dug_proveri.natpis("Proveri")
                    self._status(podatak, RED)

                elif vrsta == "napredak":
                    pct, tekst = podatak
                    self.traka.postavi(pct)
                    self.napredak.config(text=tekst, fg=MUTED)

                elif vrsta == "gotovo":
                    self.traka.postavi(100)
                    self.napredak.config(text="✓  Gotovo — fajl je u folderu.",
                                         fg=MINT)
                    self._odblokiraj()
                    try:
                        os.startfile(self.folder)
                    except OSError:
                        pass

                elif vrsta == "greska":
                    self.napredak.config(text=podatak, fg=RED)
                    self._odblokiraj()
        except queue.Empty:
            pass
        self.after(120, self._pumpa)

    def _odblokiraj(self):
        self.dug_skini.ukljuci(True)
        self.dug_skini.natpis("Skini")
        self.dug_proveri.ukljuci(True)

    def _status(self, tekst, boja=MUTED):
        self.status.config(text=tekst, fg=boja)
