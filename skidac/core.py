# -*- coding: utf-8 -*-
"""Sve što dodiruje yt-dlp i fajl sistem — bez ijednog widgeta."""

import os
import re
import sys
from shutil import which

from yt_dlp import YoutubeDL


def resource_path(rel):
    """Fajl upakovan u .exe, ili pored skripte kad se radi iz koda."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    return os.path.join(base, rel)


def nadji_ffmpeg():
    for p in (resource_path("ffmpeg.exe"),
              os.path.join(os.path.dirname(sys.executable), "ffmpeg.exe")):
        if os.path.isfile(p):
            return p
    return which("ffmpeg")


FFMPEG = nadji_ffmpeg()
BITRATE = (320, 256, 192, 128)


def podrazumevani_folder():
    d = os.path.join(os.path.expanduser("~"), "Downloads")
    return d if os.path.isdir(d) else os.path.expanduser("~")


# ---------------------------------------------------------------- formati

def velicina(n):
    if not n:
        return "?"
    for jed in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {jed}" if jed == "B" else f"{n:.1f} {jed}"
        n /= 1024
    return f"{n:.1f} TB"


def trajanje(sek):
    if sek is None:
        return "?"
    sek = int(sek)
    h, ost = divmod(sek, 3600)
    m, sk = divmod(ost, 60)
    return f"{h}:{m:02d}:{sk:02d}" if h else f"{m}:{sk:02d}"


def skrati(t, n):
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


IMENA = {4320: "8K ", 2160: "4K ", 1440: "2K "}


def rezolucije(info):
    """[(labela, visina), ...] od najbolje ka najgoroj."""
    visine = {int(f["height"]) for f in (info.get("formats") or [])
              if f.get("vcodec") not in (None, "none") and f.get("height")}
    if not visine and info.get("height"):
        visine = {int(info["height"])}
    poredak = sorted(visine, reverse=True)
    if not poredak:
        return [("Najbolje", 0)]
    return [(f"{IMENA.get(v, '')}{v}p", v) for v in poredak]


# ---------------------------------------------------------------- yt-dlp

def sredi_url(url, izvor):
    """Vrati (url, greska)."""
    url = url.strip()
    if not url:
        return None, "Nalepi link prvo."
    if not re.match(r"^https?://", url):
        url = "https://" + url
    if izvor == "youtube" and "instagram.com" in url:
        return None, "To je Instagram link — vrati se i izaberi Instagram."
    if izvor == "instagram" and "instagram.com" not in url:
        return None, "To ne liči na Instagram link."
    return url, None


def _osnovno(izvor, kolacici):
    o = {"quiet": True, "no_warnings": True, "noplaylist": True}
    if FFMPEG:
        o["ffmpeg_location"] = FFMPEG
    if izvor == "instagram" and kolacici:
        o["cookiesfrombrowser"] = ("chrome",)
    return o


def procitaj(url, izvor, kolacici=False):
    """Metapodaci o klipu, bez skidanja."""
    with YoutubeDL(_osnovno(izvor, kolacici)) as ydl:
        info = ydl.extract_info(url, download=False)
    if info.get("_type") == "playlist":
        info = info["entries"][0]
    return info


def skini(url, izvor, folder, tip, kvalitet, kolacici=False,
          na_napredak=None, na_obradu=None):
    """tip: 'mp4' (kvalitet = visina) ili 'mp3' (kvalitet = kbps)."""
    o = _osnovno(izvor, kolacici)
    o.update({
        "outtmpl": os.path.join(folder, "%(title).150B [%(id)s].%(ext)s"),
        "windowsfilenames": True,
        "overwrites": False,
        "retries": 5,
        "fragment_retries": 5,
        "concurrent_fragment_downloads": 4,
    })
    if na_napredak:
        o["progress_hooks"] = [na_napredak]
    if na_obradu:
        o["postprocessor_hooks"] = [na_obradu]

    if tip == "mp3":
        o["format"] = "bestaudio/best"
        o["postprocessors"] = [{"key": "FFmpegExtractAudio",
                                "preferredcodec": "mp3",
                                "preferredquality": str(kvalitet)}]
    else:
        v = kvalitet or 0
        o["format"] = (
            f"bestvideo[height<={v}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={v}]+bestaudio/best[height<={v}]/best"
        ) if v else "bestvideo+bestaudio/best"
        o["merge_output_format"] = "mp4"

    with YoutubeDL(o) as ydl:
        ydl.download([url])


def poruka(e):
    """yt-dlp greške su duge i tehničke — svedi ih na jednu rečenicu."""
    t = re.sub(r"\x1b\[[0-9;]*m", "", str(e)).replace("ERROR: ", "")
    n = t.lower()
    if "unsupported url" in n or "no video" in n:
        return "Ovaj link ne mogu da otvorim — proveri da li je ispravan."
    if "private" in n or "login" in n or "cookies" in n:
        return ("Sadržaj traži prijavu. Uključi opciju sa kolačićima iz "
                "Chrome-a i budi ulogovan u Chrome-u.")
    if "unavailable" in n:
        return "Klip je nedostupan ili obrisan."
    if "urlopen" in n or "network" in n or "timed out" in n:
        return "Nema interneta ili je veza pukla."
    if "ffmpeg" in n:
        return "Problem sa ffmpeg-om — proveri da je ffmpeg.exe pored aplikacije."
    return t.split("\n")[0][:200]
