# -*- coding: utf-8 -*-
"""Sve što dodiruje yt-dlp i fajl sistem — bez ijednog widgeta."""

import glob
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


class Prekid(Exception):
    """Korisnik je zaustavio skidanje."""


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
    if izvor == "sajt" and not re.match(r"^https?://[^/\s.]+\.[^/\s]", url):
        return None, "To ne liči na adresu sajta."
    if izvor == "lista" and not re.match(r"^https?://[^/\s.]+\.[^/\s]", url):
        return None, "To ne liči na link."
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


# ---------------------------------------------------------------- lista

# U listi ne znamo unapred koje rezolucije svaki klip ima, pa se nudi
# gornja granica a bira se najbolje sto klip ima do nje.
GRANICE = (2160, 1440, 1080, 720, 480, 360)


def procitaj_listu(url, kolacici=False):
    """[(url, naslov, trajanje), ...] — cela plejlista ili jedan klip."""
    o = {"quiet": True, "no_warnings": True}
    if FFMPEG:
        o["ffmpeg_location"] = FFMPEG
    if kolacici:
        o["cookiesfrombrowser"] = ("chrome",)

    plejlista = "list=" in url or "/playlist" in url
    o["noplaylist"] = not plejlista
    if plejlista:
        o["extract_flat"] = "in_playlist"

    with YoutubeDL(o) as ydl:
        info = ydl.extract_info(url, download=False)

    if info.get("_type") == "playlist":
        stavke = []
        for u in info.get("entries") or []:
            if not u:
                continue
            adresa = u.get("url") or u.get("webpage_url")
            if adresa and not adresa.startswith("http") and u.get("id"):
                adresa = "https://www.youtube.com/watch?v=" + u["id"]
            if adresa:
                stavke.append((adresa, u.get("title") or "Bez naslova",
                               u.get("duration")))
        if not stavke:
            raise RuntimeError("Plejlista je prazna ili nedostupna.")
        return stavke

    return [(info.get("webpage_url") or url, info.get("title") or "Bez naslova",
             info.get("duration"))]


# ---------------------------------------------------------------- titlovi

JEZICI = {
    "sr": "Srpski", "hr": "Hrvatski", "bs": "Bosanski", "sh": "Srpskohrvatski",
    "en": "Engleski", "de": "Nemacki", "fr": "Francuski", "es": "Spanski",
    "it": "Italijanski", "ru": "Ruski", "tr": "Turski", "sl": "Slovenacki",
    "mk": "Makedonski", "sq": "Albanski", "hu": "Madjarski", "pt": "Portugalski",
}
PREDNOST = ("sr", "hr", "bs", "sh", "en")


def _ime_jezika(kod):
    osnova = kod.split("-")[0].lower()
    return JEZICI.get(osnova, kod)


def jezici_titlova(info):
    """[(labela, kod), ...] — prvo rucni titlovi, pa nekoliko automatskih.

    Automatskih ume da bude i preko sto, pa se prikazuju samo oni koji
    imaju smisla: nas jezik, engleski i jezik samog videa.
    """
    rucni = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    stavke, videni = [], set()

    for kod in sorted(rucni, key=lambda k: (k.split("-")[0] not in PREDNOST, k)):
        if kod.split("-")[0] in videni:
            continue
        videni.add(kod.split("-")[0])
        stavke.append((_ime_jezika(kod), kod))
        if len(stavke) >= 6:
            break

    zeljeni = list(PREDNOST)
    if info.get("language"):
        # YouTube ume da vrati "ro-orig" i slicno — to je oznaka originalnog
        # zvuka, ne jezik titla
        zeljeni.insert(0, info["language"].split("-")[0])
    for zelja in zeljeni:
        if zelja in videni:
            continue
        for kod in sorted(auto):
            if kod.endswith("-orig"):
                continue
            if kod.split("-")[0] == zelja:
                videni.add(zelja)
                stavke.append((_ime_jezika(kod) + " (auto)", kod))
                break
    return stavke


def _srt_u_tekst(put_srt):
    """Cist tekst bez vremena i brojeva; automatski titlovi se ponavljaju."""
    with open(put_srt, encoding="utf-8", errors="replace") as f:
        sirovo = f.read()

    redovi = []
    for red in sirovo.splitlines():
        red = red.strip()
        if (not red or red.isdigit() or "-->" in red):
            continue
        red = re.sub(r"<[^>]+>", "", red).strip()
        if red and (not redovi or redovi[-1] != red):
            redovi.append(red)

    put_txt = os.path.splitext(put_srt)[0] + ".txt"
    with open(put_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(redovi) + "\n")
    return put_txt


def skini_transkript(url, izvor, folder, jezik, kolacici=False,
                     na_napredak=None):
    """Skine titl, pretvori ga u .srt i napravi .txt pored njega."""
    o = _osnovno(izvor, kolacici)
    o.update({
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [jezik],
        "subtitlesformat": "srt/vtt/best",
        "outtmpl": os.path.join(folder, "%(title).150B [%(id)s].%(ext)s"),
        "windowsfilenames": True,
        "postprocessors": [{"key": "FFmpegSubtitlesConvertor",
                            "format": "srt"}],
    })
    if na_napredak:
        o["progress_hooks"] = [na_napredak]

    with YoutubeDL(o) as ydl:
        info = ydl.extract_info(url, download=True)

    oznaka = info.get("id", "")
    nadjeni = [p for p in glob.glob(os.path.join(folder, "*.srt"))
               if oznaka in os.path.basename(p)]
    if not nadjeni:
        raise RuntimeError("Ovaj video nema titlove ni automatski prepis.")
    najnoviji = max(nadjeni, key=os.path.getmtime)
    return _srt_u_tekst(najnoviji)


def poruka(e):
    """yt-dlp greške su duge i tehničke — svedi ih na jednu rečenicu."""
    t = re.sub(r"\x1b\[[0-9;]*m", "", str(e)).replace("ERROR: ", "")
    n = t.lower()
    if "unsupported url" in n or "no video" in n:
        return "Ovaj link ne mogu da otvorim — proveri da li je ispravan."
    if "private" in n or "login" in n or "cookies" in n:
        return ("Sadržaj traži prijavu. Uključi opciju sa kolačićima iz "
                "Chrome-a i budi ulogovan u Chrome-u.")
    if "nema titlove" in n:
        return ("Ovaj video nema titlove — ni ručne ni automatske, pa nema "
                "šta da se prepiše.")
    if "no subtitles" in n:
        return "Ovaj video nema titlove na izabranom jeziku."
    if "unavailable" in n:
        return "Klip je nedostupan ili obrisan."
    if "urlopen" in n or "network" in n or "timed out" in n:
        return "Nema interneta ili je veza pukla."
    if "certificate" in n or "ssl" in n:
        return "Sajt ima problem sa sertifikatom, ne mogu bezbedno da ga otvorim."
    if "forbidden" in n or "403" in n:
        return "Server odbija pristup (403)."
    if "ffmpeg" in n:
        return "Problem sa ffmpeg-om — proveri da je ffmpeg.exe pored aplikacije."
    return t.split("\n")[0][:200]
