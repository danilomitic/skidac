# -*- coding: utf-8 -*-
"""
Skidac — YouTube / Instagram downloader
Tkinter GUI oko yt-dlp. Pravi se u jedan .exe preko PyInstaller-a.
"""

import os
import re
import sys
import queue
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from yt_dlp import YoutubeDL

# ---------------------------------------------------------------- tema

BG      = "#0f1115"
CARD    = "#171a21"
CARD_HI = "#1e222b"
LINE    = "#2a2f3a"
TXT     = "#e8eaf0"
MUTED   = "#8b93a7"
MINT    = "#34d399"
MINT_HI = "#4ee0a8"
RED     = "#f87171"

FONT    = ("Segoe UI", 10)
FONT_B  = ("Segoe UI Semibold", 10)
FONT_H  = ("Segoe UI Semibold", 20)
FONT_S  = ("Segoe UI", 9)


def resource_path(rel):
    """Putanja do fajla koji je upakovan u .exe (ili pored skripte u dev-u)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def find_ffmpeg():
    """ffmpeg.exe: prvo upakovani, pa pored .exe-a, pa iz PATH-a."""
    kandidati = [
        resource_path("ffmpeg.exe"),
        os.path.join(os.path.dirname(sys.executable), "ffmpeg.exe"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe"),
    ]
    for p in kandidati:
        if os.path.isfile(p):
            return p
    from shutil import which
    return which("ffmpeg")


FFMPEG = find_ffmpeg()


def default_dir():
    d = os.path.join(os.path.expanduser("~"), "Downloads")
    return d if os.path.isdir(d) else os.path.expanduser("~")


def human_size(n):
    if not n:
        return "?"
    for jed in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {jed}" if jed == "B" else f"{n:.1f} {jed}"
        n /= 1024
    return f"{n:.1f} TB"


def human_time(sek):
    if sek is None:
        return "?"
    sek = int(sek)
    h, ost = divmod(sek, 3600)
    m, s = divmod(ost, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ---------------------------------------------------------------- widgeti

class Dugme(tk.Label):
    """Ravno dugme sa hover efektom — ttk ne da da se oboji kako treba."""

    def __init__(self, master, text, command, primary=False, small=False, **kw):
        self.primary = primary
        self.command = command
        self.enabled = True
        bg = MINT if primary else CARD_HI
        fg = "#0b1f17" if primary else TXT
        super().__init__(
            master, text=text, bg=bg, fg=fg,
            font=FONT_S if small else FONT_B,
            padx=kw.pop("padx", 14 if small else 22),
            pady=kw.pop("pady", 6 if small else 11),
            cursor="hand2", **kw
        )
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._click)

    def _enter(self, _=None):
        if self.enabled:
            self.config(bg=MINT_HI if self.primary else LINE)

    def _leave(self, _=None):
        if self.enabled:
            self.config(bg=MINT if self.primary else CARD_HI)

    def _click(self, _=None):
        if self.enabled:
            self.command()

    def set_enabled(self, on):
        self.enabled = on
        if on:
            self.config(bg=MINT if self.primary else CARD_HI,
                        fg="#0b1f17" if self.primary else TXT, cursor="hand2")
        else:
            self.config(bg="#232733", fg=MUTED, cursor="arrow")


# ---------------------------------------------------------------- app

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Skidac — YouTube i Instagram")
        self.configure(bg=BG)
        self.geometry("640x680")
        self.minsize(600, 640)

        try:
            self.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass

        self.izvor = None          # "youtube" | "instagram"
        self.info = None           # yt-dlp metapodaci
        self.formati = []          # [(labela, height), ...]
        self.izlaz = tk.StringVar(value=default_dir())
        self.tip = tk.StringVar(value="mp4")
        self.kvalitet = tk.StringVar()
        self.mp3_bitrate = tk.StringVar(value="192")
        self.kolacici = tk.BooleanVar(value=False)
        self.red = queue.Queue()
        self.posao = None

        self._stil()
        self.ekran_izbor()
        self.after(100, self._pumpa)

    def _stil(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Mint.Horizontal.TProgressbar",
                    troughcolor=CARD_HI, bordercolor=CARD_HI,
                    background=MINT, lightcolor=MINT, darkcolor=MINT,
                    thickness=8)
        s.configure("D.TCombobox", fieldbackground=CARD_HI, background=CARD_HI,
                    foreground=TXT, arrowcolor=TXT, bordercolor=LINE,
                    lightcolor=LINE, darkcolor=LINE)
        s.map("D.TCombobox",
              fieldbackground=[("readonly", CARD_HI)],
              foreground=[("readonly", TXT)],
              selectbackground=[("readonly", CARD_HI)],
              selectforeground=[("readonly", TXT)])
        self.option_add("*TCombobox*Listbox.background", CARD_HI)
        self.option_add("*TCombobox*Listbox.foreground", TXT)
        self.option_add("*TCombobox*Listbox.selectBackground", MINT)
        self.option_add("*TCombobox*Listbox.selectForeground", "#0b1f17")

    def _ocisti(self):
        for w in self.winfo_children():
            w.destroy()

    # ------------------------------------------------- ekran 1: izvor

    def ekran_izbor(self):
        self._ocisti()
        okvir = tk.Frame(self, bg=BG)
        okvir.pack(expand=True, fill="both", padx=40)

        tk.Label(okvir, text="Odakle skidaš?", bg=BG, fg=TXT,
                 font=FONT_H).pack(pady=(80, 6))
        tk.Label(okvir, text="Izaberi platformu, pa nalepi link.",
                 bg=BG, fg=MUTED, font=FONT).pack(pady=(0, 40))

        for naziv, kljuc, opis in (
            ("YouTube", "youtube", "Video, Shorts, plejliste"),
            ("Instagram", "instagram", "Reels, objave, IGTV"),
        ):
            k = tk.Frame(okvir, bg=CARD, cursor="hand2", highlightthickness=1,
                         highlightbackground=LINE, highlightcolor=LINE)
            k.pack(fill="x", pady=8)
            unut = tk.Frame(k, bg=CARD)
            unut.pack(fill="x", padx=24, pady=18)
            tk.Label(unut, text=naziv, bg=CARD, fg=TXT,
                     font=("Segoe UI Semibold", 14)).pack(anchor="w")
            tk.Label(unut, text=opis, bg=CARD, fg=MUTED,
                     font=FONT_S).pack(anchor="w", pady=(2, 0))

            def veži(w, kl=kljuc):
                w.bind("<Button-1>", lambda _e: self.ekran_link(kl))
                w.bind("<Enter>", lambda _e, f=k: f.config(bg=CARD_HI) or
                       [c.config(bg=CARD_HI) for c in _svi(f)])
                w.bind("<Leave>", lambda _e, f=k: f.config(bg=CARD) or
                       [c.config(bg=CARD) for c in _svi(f)])
                for c in w.winfo_children():
                    veži(c, kl)

            veži(k)

    # ------------------------------------------------- ekran 2: link

    def ekran_link(self, izvor):
        self.izvor = izvor
        self.info = None
        self._ocisti()

        glava = tk.Frame(self, bg=BG)
        glava.pack(fill="x", padx=32, pady=(24, 0))
        nazad = tk.Label(glava, text="‹  Nazad", bg=BG, fg=MUTED,
                         font=FONT_S, cursor="hand2")
        nazad.pack(side="left")
        nazad.bind("<Button-1>", lambda _e: self.ekran_izbor())
        tk.Label(glava, text="YouTube" if izvor == "youtube" else "Instagram",
                 bg=BG, fg=MINT, font=FONT_B).pack(side="right")

        telo = tk.Frame(self, bg=BG)
        telo.pack(fill="both", expand=True, padx=32, pady=(18, 24))

        tk.Label(telo, text="Nalepi link", bg=BG, fg=TXT,
                 font=("Segoe UI Semibold", 15)).pack(anchor="w")

        red_link = tk.Frame(telo, bg=BG)
        red_link.pack(fill="x", pady=(12, 0))
        self.polje = tk.Entry(red_link, bg=CARD_HI, fg=TXT, font=FONT,
                              relief="flat", insertbackground=MINT,
                              highlightthickness=1, highlightbackground=LINE,
                              highlightcolor=MINT)
        self.polje.pack(side="left", fill="x", expand=True, ipady=9, ipadx=10)
        self.polje.bind("<Return>", lambda _e: self.analiziraj())
        self.polje.focus_set()

        self.dug_analiza = Dugme(red_link, "Proveri", self.analiziraj, primary=True)
        self.dug_analiza.pack(side="left", padx=(10, 0))

        if izvor == "instagram":
            ck = tk.Checkbutton(
                telo, text="Objava traži prijavu — uzmi kolačiće iz Chrome-a",
                variable=self.kolacici, bg=BG, fg=MUTED, font=FONT_S,
                selectcolor=CARD_HI, activebackground=BG, activeforeground=TXT,
                highlightthickness=0, bd=0, cursor="hand2")
            ck.pack(anchor="w", pady=(10, 0))

        self.status = tk.Label(telo, text="", bg=BG, fg=MUTED,
                               font=FONT_S, wraplength=540, justify="left")
        self.status.pack(anchor="w", pady=(14, 0))

        # kartica sa rezultatom — puni se posle provere
        self.kartica = tk.Frame(telo, bg=CARD, highlightthickness=1,
                                highlightbackground=LINE)

    # ------------------------------------------------- provera linka

    def analiziraj(self):
        url = self.polje.get().strip()
        if not url:
            self._status("Nalepi link prvo.", RED)
            return
        if not re.match(r"^https?://", url):
            url = "https://" + url
        if self.izvor == "youtube" and "instagram.com" in url:
            self._status("To je Instagram link — vrati se i izaberi Instagram.", RED)
            return
        if self.izvor == "instagram" and "instagram.com" not in url:
            self._status("To ne liči na Instagram link.", RED)
            return

        self.kartica.pack_forget()
        self.dug_analiza.set_enabled(False)
        self._status("Čitam podatke o klipu…", MUTED)
        threading.Thread(target=self._analiziraj_rad, args=(url,), daemon=True).start()

    def _opcije_osnovne(self):
        o = {"quiet": True, "no_warnings": True, "noplaylist": True}
        if FFMPEG:
            o["ffmpeg_location"] = FFMPEG
        if self.izvor == "instagram" and self.kolacici.get():
            o["cookiesfrombrowser"] = ("chrome",)
        return o

    def _analiziraj_rad(self, url):
        try:
            with YoutubeDL(self._opcije_osnovne()) as ydl:
                info = ydl.extract_info(url, download=False)
            if info.get("_type") == "playlist":
                info = info["entries"][0]
            self.red.put(("info", (url, info)))
        except Exception as e:
            self.red.put(("greska_info", _poruka(e)))

    def _prikazi_info(self, url, info):
        self.url = url
        self.info = info
        self.dug_analiza.set_enabled(True)
        self._status("")

        # skupi dostupne visine
        visine = set()
        for f in info.get("formats") or []:
            if f.get("vcodec") and f["vcodec"] != "none" and f.get("height"):
                visine.add(int(f["height"]))
        if not visine and info.get("height"):
            visine.add(int(info["height"]))
        visine = sorted(visine, reverse=True)

        imena = {2160: "4K", 1440: "2K", 1080: "Full HD", 720: "HD"}
        self.formati = [(f"{v}p" + (f" · {imena[v]}" if v in imena else ""), v)
                        for v in visine]
        if not self.formati:
            self.formati = [("Najbolje dostupno", 0)]

        for w in self.kartica.winfo_children():
            w.destroy()
        self.kartica.pack(fill="both", expand=True, pady=(16, 0))
        unut = tk.Frame(self.kartica, bg=CARD)
        unut.pack(fill="both", expand=True, padx=22, pady=20)

        naslov = info.get("title") or "Bez naslova"
        tk.Label(unut, text=naslov[:110], bg=CARD, fg=TXT, font=FONT_B,
                 wraplength=520, justify="left").pack(anchor="w")

        meta = []
        if info.get("uploader"):
            meta.append(info["uploader"])
        if info.get("duration"):
            meta.append(human_time(info["duration"]))
        if visine:
            meta.append(f"max {visine[0]}p")
        tk.Label(unut, text="  ·  ".join(meta), bg=CARD, fg=MUTED,
                 font=FONT_S).pack(anchor="w", pady=(4, 16))

        # tip fajla
        tk.Label(unut, text="Format", bg=CARD, fg=MUTED,
                 font=FONT_S).pack(anchor="w")
        red_tip = tk.Frame(unut, bg=CARD)
        red_tip.pack(fill="x", pady=(6, 14))
        self._radio(red_tip, "MP4 — video", "mp4").pack(side="left")
        self._radio(red_tip, "MP3 — samo zvuk", "mp3").pack(side="left", padx=(8, 0))

        # kvalitet
        self.okvir_kval = tk.Frame(unut, bg=CARD)
        self.okvir_kval.pack(fill="x")
        self.nalepnica_kval = tk.Label(self.okvir_kval, text="Kvalitet", bg=CARD,
                                       fg=MUTED, font=FONT_S)
        self.nalepnica_kval.pack(anchor="w")
        self.combo = ttk.Combobox(self.okvir_kval, state="readonly",
                                  style="D.TCombobox", font=FONT,
                                  textvariable=self.kvalitet)
        self.combo.pack(fill="x", pady=(6, 14), ipady=4)
        self._osvezi_kvalitet()

        # folder
        tk.Label(unut, text="Sačuvaj u", bg=CARD, fg=MUTED,
                 font=FONT_S).pack(anchor="w")
        red_f = tk.Frame(unut, bg=CARD)
        red_f.pack(fill="x", pady=(6, 18))
        self.polje_f = tk.Entry(red_f, textvariable=self.izlaz, bg=CARD_HI,
                                fg=TXT, font=FONT_S, relief="flat",
                                insertbackground=MINT, highlightthickness=1,
                                highlightbackground=LINE, highlightcolor=LINE)
        self.polje_f.pack(side="left", fill="x", expand=True, ipady=7, ipadx=8)
        Dugme(red_f, "Promeni", self._izaberi_folder, small=True,
              pady=8).pack(side="left", padx=(8, 0))

        self.dug_skidaj = Dugme(unut, "Skini", self.skidaj, primary=True)
        self.dug_skidaj.pack(fill="x")

        self.traka = ttk.Progressbar(unut, style="Mint.Horizontal.TProgressbar",
                                     maximum=100)
        self.napredak = tk.Label(unut, text="", bg=CARD, fg=MUTED, font=FONT_S,
                                 wraplength=520, justify="left")

        if not FFMPEG:
            tk.Label(unut, text="⚠ ffmpeg nije pronađen — MP3 i spajanje 1080p+ "
                                "neće raditi.", bg=CARD, fg=RED,
                     font=FONT_S, wraplength=520,
                     justify="left").pack(anchor="w", pady=(14, 0))

    def _radio(self, master, tekst, vrednost):
        return tk.Radiobutton(
            master, text=tekst, value=vrednost, variable=self.tip,
            command=self._osvezi_kvalitet, bg=CARD, fg=TXT, font=FONT_S,
            selectcolor=CARD_HI, activebackground=CARD, activeforeground=TXT,
            highlightthickness=0, bd=0, cursor="hand2")

    def _osvezi_kvalitet(self):
        if self.tip.get() == "mp4":
            self.nalepnica_kval.config(text="Rezolucija")
            vred = [l for l, _ in self.formati]
            self.combo.config(values=vred, textvariable=self.kvalitet)
            self.kvalitet.set(vred[0])
        else:
            self.nalepnica_kval.config(text="Bitrate zvuka")
            vred = ["320 kbps", "256 kbps", "192 kbps", "128 kbps"]
            self.combo.config(values=vred, textvariable=self.kvalitet)
            self.kvalitet.set("192 kbps")

    def _izaberi_folder(self):
        d = filedialog.askdirectory(initialdir=self.izlaz.get())
        if d:
            self.izlaz.set(d)

    # ------------------------------------------------- skidanje

    def skidaj(self):
        folder = self.izlaz.get().strip()
        if not os.path.isdir(folder):
            self._status("Taj folder ne postoji.", RED)
            return
        if self.tip.get() == "mp3" and not FFMPEG:
            messagebox.showerror("Nema ffmpeg-a",
                                 "Za MP3 je potreban ffmpeg.exe pored aplikacije.")
            return

        self.dug_skidaj.set_enabled(False)
        self.dug_analiza.set_enabled(False)
        self.traka.pack(fill="x", pady=(14, 6))
        self.traka["value"] = 0
        self.napredak.pack(anchor="w")
        self.napredak.config(text="Krećem…", fg=MUTED)

        opcije = self._opcije_skidanja(folder)
        self.posao = threading.Thread(target=self._skidaj_rad,
                                      args=(opcije,), daemon=True)
        self.posao.start()

    def _opcije_skidanja(self, folder):
        o = self._opcije_osnovne()
        o.update({
            "outtmpl": os.path.join(folder, "%(title).150B [%(id)s].%(ext)s"),
            "progress_hooks": [self._kuka],
            "postprocessor_hooks": [self._kuka_pp],
            "restrictfilenames": False,
            "windowsfilenames": True,
            "overwrites": False,
            "retries": 5,
            "fragment_retries": 5,
            "concurrent_fragment_downloads": 4,
        })

        if self.tip.get() == "mp3":
            br = self.kvalitet.get().split()[0]
            o["format"] = "bestaudio/best"
            o["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": br,
            }]
        else:
            visina = dict(self.formati).get(self.kvalitet.get(), 0)
            if visina:
                o["format"] = (
                    f"bestvideo[height<={visina}][ext=mp4]+bestaudio[ext=m4a]/"
                    f"bestvideo[height<={visina}]+bestaudio/"
                    f"best[height<={visina}]/best"
                )
            else:
                o["format"] = "bestvideo+bestaudio/best"
            o["merge_output_format"] = "mp4"
        return o

    def _kuka(self, d):
        if d["status"] == "downloading":
            ukupno = d.get("total_bytes") or d.get("total_bytes_estimate")
            gotovo = d.get("downloaded_bytes") or 0
            pct = (gotovo / ukupno * 100) if ukupno else 0
            brzina = d.get("speed")
            tekst = f"{pct:.1f}%  ·  {human_size(gotovo)} / {human_size(ukupno)}"
            if brzina:
                tekst += f"  ·  {human_size(brzina)}/s"
            if d.get("eta"):
                tekst += f"  ·  još {human_time(d['eta'])}"
            self.red.put(("napredak", (pct, tekst)))
        elif d["status"] == "finished":
            self.red.put(("napredak", (100, "Preuzeto — obrađujem fajl…")))

    def _kuka_pp(self, d):
        if d["status"] == "started":
            self.red.put(("napredak", (100, "Konvertujem…")))

    def _skidaj_rad(self, opcije):
        try:
            with YoutubeDL(opcije) as ydl:
                ydl.download([self.url])
            self.red.put(("gotovo", opcije["outtmpl"]))
        except Exception as e:
            self.red.put(("greska", _poruka(e)))

    # ------------------------------------------------- poruke iz niti

    def _pumpa(self):
        try:
            while True:
                vrsta, podatak = self.red.get_nowait()

                if vrsta == "info":
                    self._prikazi_info(*podatak)

                elif vrsta == "greska_info":
                    self.dug_analiza.set_enabled(True)
                    self._status(podatak, RED)

                elif vrsta == "napredak":
                    pct, tekst = podatak
                    self.traka["value"] = pct
                    self.napredak.config(text=tekst, fg=MUTED)

                elif vrsta == "gotovo":
                    self.traka["value"] = 100
                    self.napredak.config(text="✓ Gotovo — fajl je u izabranom folderu.",
                                         fg=MINT)
                    self.dug_skidaj.set_enabled(True)
                    self.dug_analiza.set_enabled(True)
                    try:
                        os.startfile(self.izlaz.get())
                    except Exception:
                        pass

                elif vrsta == "greska":
                    self.napredak.config(text=podatak, fg=RED)
                    self.dug_skidaj.set_enabled(True)
                    self.dug_analiza.set_enabled(True)
        except queue.Empty:
            pass
        self.after(120, self._pumpa)

    def _status(self, tekst, boja=MUTED):
        self.status.config(text=tekst, fg=boja)


def _svi(widget):
    out = []
    for c in widget.winfo_children():
        out.append(c)
        out.extend(_svi(c))
    return out


def _poruka(e):
    """yt-dlp poruke su dugačke i tehničke — skratimo na nešto čitljivo."""
    t = str(e)
    t = re.sub(r"\x1b\[[0-9;]*m", "", t)
    t = t.replace("ERROR: ", "")
    niska = t.lower()
    if "unsupported url" in niska or "no video" in niska:
        return "Ovaj link ne mogu da otvorim — proveri da li je ispravan."
    if "private" in niska or "login" in niska or "cookies" in niska:
        return ("Sadržaj traži prijavu. Za Instagram uključi opciju sa "
                "kolačićima iz Chrome-a (i budi ulogovan u Chrome-u).")
    if "unavailable" in niska:
        return "Klip je nedostupan ili obrisan."
    if "urlopen" in niska or "network" in niska or "timed out" in niska:
        return "Nema interneta ili je veza pukla."
    if "ffmpeg" in niska:
        return "Problem sa ffmpeg-om — proveri da je ffmpeg.exe pored aplikacije."
    return t.split("\n")[0][:220]


if __name__ == "__main__":
    try:
        App().mainloop()
    except Exception:
        traceback.print_exc()
        try:
            tk.Tk().withdraw()
            messagebox.showerror("Greška", traceback.format_exc()[-1500:])
        except Exception:
            pass
