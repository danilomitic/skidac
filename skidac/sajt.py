# -*- coding: utf-8 -*-
"""Preuzimanje celog sajta za čitanje van mreže.

Ide u širinu od zadate adrese, ostaje na istom domenu, snima stranice i
ono što one koriste (slike, CSS, JS), pa prepravlja linkove da pokazuju
na lokalne fajlove.

Ponaša se pristojno: čita robots.txt i preskače što je zabranjeno, pravi
pauzu između zahteva, predstavlja se u User-Agent-u i ima gornju granicu
broja strana. Nije alat za obaranje tuđeg servera.
"""

import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

UA = "Skidac/1.0 (licna arhiva sajta; +https://github.com/danilomitic/ytconverter)"
PAUZA = 0.35             # sekundi između zahteva ka istom serveru
NAJVECI_FAJL = 25 * 1024 * 1024

STRANICA = ("text/html", "application/xhtml+xml")

# href="...", src="...", poster="..." — i sa navodnicima i bez njih
VEZE = re.compile(
    r"""(?i)\b(href|src|poster|data-src)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""")
SRCSET = re.compile(r"""(?i)\bsrcset\s*=\s*(?:"([^"]*)"|'([^']*)')""")
CSS_URL = re.compile(r"""(?i)url\(\s*(['"]?)([^)'"]+)\1\s*\)""")
NEDOZVOLJENO = re.compile(r'[<>:"|?*\x00-\x1f]')


class Zaustavljeno(Exception):
    """Korisnik je prekinuo preuzimanje."""


def _bez_sidra(url):
    delovi = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(delovi._replace(fragment=""))


def _isti_domen(a, b):
    da = urllib.parse.urlsplit(a).netloc.lower().removeprefix("www.")
    db = urllib.parse.urlsplit(b).netloc.lower().removeprefix("www.")
    return da == db


def lokalna_putanja(url):
    """Adresa -> putanja u folderu. Deterministički, da se linkovi poklope."""
    d = urllib.parse.urlsplit(url)
    put = urllib.parse.unquote(d.path)
    if put.endswith("/") or not put:
        put += "index.html"
    elif "." not in put.rsplit("/", 1)[-1]:
        put += "/index.html"

    delovi = [NEDOZVOLJENO.sub("_", x) for x in put.strip("/").split("/") if x]
    if d.query:
        koren, tacka, nastavak = delovi[-1].rpartition(".")
        oznaka = NEDOZVOLJENO.sub("_", d.query)[:40]
        delovi[-1] = (f"{koren}__{oznaka}{tacka}{nastavak}" if tacka
                      else f"{delovi[-1]}__{oznaka}")
    domen = NEDOZVOLJENO.sub("_", d.netloc)
    return os.path.join(domen, *delovi)


class Preuzimac:

    def __init__(self, pocetna, folder, najvise_strana=200, na_napredak=None,
                 stani=None):
        if not re.match(r"^https?://", pocetna):
            pocetna = "https://" + pocetna
        self.pocetna = _bez_sidra(pocetna)
        self.koren = folder
        self.najvise_strana = najvise_strana
        self.na_napredak = na_napredak
        self.stani = stani or (lambda: False)

        self.videno = set()
        self.red = [self.pocetna]
        self.strana = 0
        self.fajlova = 0
        self.preskoceno = 0
        self.poslednji_zahtev = 0.0
        self.robots = self._robots()

    # ---------------------------------------------------------- mreža

    def _robots(self):
        d = urllib.parse.urlsplit(self.pocetna)
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{d.scheme}://{d.netloc}/robots.txt")
        try:
            rp.read()
        except Exception:
            return None          # nema robots.txt ili je nedostupan
        return rp

    def _sme(self, url):
        if self.robots is None:
            return True
        try:
            return self.robots.can_fetch(UA, url)
        except Exception:
            return True

    def _uzmi(self, url):
        cekaj = PAUZA - (time.time() - self.poslednji_zahtev)
        if cekaj > 0:
            time.sleep(cekaj)
        self.poslednji_zahtev = time.time()

        zahtev = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        })
        with urllib.request.urlopen(zahtev, timeout=20) as odgovor:
            vrsta = odgovor.headers.get_content_type()
            sadrzaj = odgovor.read(NAJVECI_FAJL + 1)
            kodiranje = odgovor.headers.get_content_charset()
        if len(sadrzaj) > NAJVECI_FAJL:
            raise ValueError("fajl je prevelik")
        return vrsta, sadrzaj, kodiranje

    # ---------------------------------------------------------- disk

    def _upisi(self, url, podaci):
        put = os.path.join(self.koren, lokalna_putanja(url))
        os.makedirs(os.path.dirname(put), exist_ok=True)
        rezim = "wb" if isinstance(podaci, bytes) else "w"
        with open(put, rezim, **({} if rezim == "wb"
                                 else {"encoding": "utf-8"})) as f:
            f.write(podaci)
        self.fajlova += 1
        return put

    # ---------------------------------------------------------- linkovi

    def _preveri(self, apsolutna, sa_strane):
        """Vrati relativan lokalni link, i ubaci adresu u red ako treba."""
        if not _isti_domen(apsolutna, self.pocetna):
            return None
        if urllib.parse.urlsplit(apsolutna).scheme not in ("http", "https"):
            return None

        cilj = os.path.join(self.koren, lokalna_putanja(apsolutna))
        odakle = os.path.dirname(os.path.join(self.koren,
                                              lokalna_putanja(sa_strane)))
        veza = os.path.relpath(cilj, odakle).replace("\\", "/")

        if apsolutna not in self.videno:
            self.videno.add(apsolutna)
            self.red.append(apsolutna)
        return urllib.parse.quote(veza, safe="/._-~%()")

    def _prepravi_html(self, tekst, sa_strane):
        def veza(m):
            atribut = m.group(1)
            vrednost = m.group(2) or m.group(3) or m.group(4) or ""
            if not vrednost or vrednost.startswith(
                    ("#", "mailto:", "tel:", "javascript:", "data:")):
                return m.group(0)
            nova = self._preveri(
                _bez_sidra(urllib.parse.urljoin(sa_strane, vrednost)), sa_strane)
            if nova is None:
                return m.group(0)
            sidro = ""
            if "#" in vrednost:
                sidro = "#" + vrednost.split("#", 1)[1]
            return f'{atribut}="{nova}{sidro}"'

        def skup(m):
            sadrzaj = m.group(1) or m.group(2) or ""
            delovi = []
            for stavka in sadrzaj.split(","):
                stavka = stavka.strip()
                if not stavka:
                    continue
                adresa, _, opis = stavka.partition(" ")
                nova = self._preveri(
                    _bez_sidra(urllib.parse.urljoin(sa_strane, adresa)), sa_strane)
                delovi.append(f"{nova or adresa} {opis}".strip())
            return 'srcset="' + ", ".join(delovi) + '"'

        tekst = SRCSET.sub(skup, tekst)
        tekst = VEZE.sub(veza, tekst)
        return CSS_URL.sub(lambda m: self._css(m, sa_strane), tekst)

    def _css(self, m, sa_strane):
        vrednost = m.group(2).strip()
        if vrednost.startswith("data:"):
            return m.group(0)
        nova = self._preveri(
            _bez_sidra(urllib.parse.urljoin(sa_strane, vrednost)), sa_strane)
        return f"url({nova})" if nova else m.group(0)

    # ---------------------------------------------------------- glavno

    def kreni(self):
        self.videno.add(self.pocetna)
        while self.red:
            if self.stani():
                raise Zaustavljeno()
            url = self.red.pop(0)

            if not self._sme(url):
                self.preskoceno += 1
                continue
            try:
                vrsta, sadrzaj, kodiranje = self._uzmi(url)
            except (urllib.error.URLError, urllib.error.HTTPError, ValueError,
                    OSError):
                self.preskoceno += 1
                continue

            if vrsta in STRANICA:
                if self.strana >= self.najvise_strana:
                    continue                 # granica: ne otvaramo nove strane
                self.strana += 1
                tekst = sadrzaj.decode(kodiranje or "utf-8", errors="replace")
                self._upisi(url, self._prepravi_html(tekst, url))
            elif vrsta == "text/css":
                tekst = sadrzaj.decode(kodiranje or "utf-8", errors="replace")
                self._upisi(url, CSS_URL.sub(
                    lambda m: self._css(m, url), tekst))
            else:
                self._upisi(url, sadrzaj)

            if self.na_napredak:
                self.na_napredak(self.strana, self.fajlova, len(self.red), url)

        return {"strana": self.strana, "fajlova": self.fajlova,
                "preskoceno": self.preskoceno,
                "folder": os.path.join(self.koren,
                                       lokalna_putanja(self.pocetna).split(
                                           os.sep)[0])}


def naslov_i_domen(url):
    """Brza provera pre preuzimanja: da li adresa radi i kako se zove."""
    if not re.match(r"^https?://", url):
        url = "https://" + url
    zahtev = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(zahtev, timeout=15) as odgovor:
        podaci = odgovor.read(200_000)
        kodiranje = odgovor.headers.get_content_charset() or "utf-8"
        konacna = odgovor.geturl()
    tekst = podaci.decode(kodiranje, errors="replace")
    poklapanje = re.search(r"(?is)<title[^>]*>(.*?)</title>", tekst)
    naslov = re.sub(r"\s+", " ", poklapanje.group(1)).strip() if poklapanje else ""
    return {"url": konacna, "naslov": naslov or urllib.parse.urlsplit(konacna).netloc,
            "domen": urllib.parse.urlsplit(konacna).netloc}
