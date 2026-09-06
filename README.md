# Skidac

Desktop aplikacija za Windows — skida video sa YouTube-a i Instagrama kao MP4 ili MP3.

## Kako se koristi

1. Pokreni `Skidac.exe`
2. Izaberi **YouTube**, **Instagram** ili **Sajt**
3. Nalepi link i klikni **Proveri**
4. Izaberi sta hoces:
   - **MP4** — video, rezolucija do 4K
   - **MP3** — samo zvuk, do 320 kbps
   - **TXT** — prepis govora iz titlova (samo YouTube), daje .srt i .txt
   - kod sajta: koliko strana najvise da skine
5. **Skini** — folder se otvara sam kad zavrsi. Dok traje, dugme postaje
   **Zaustavi**; sto je do tada skinuto ostaje na disku.

## Prepis videa

Koristi titlove koje YouTube vec ima — prvo rucne, pa automatske.
Ponudjeni su nas jezik, engleski i jezik samog videa. Dobijas dva fajla:
`.srt` (sa vremenima) i `.txt` (cist tekst). Ako video nema nikakve
titlove, nema ni prepisa.

## Preuzimanje sajta

Ide u sirinu od zadate adrese, ostaje na istom domenu, snima strane i ono
sto one koriste (slike, CSS, JS), pa prepravlja linkove da pokazuju na
lokalne fajlove — sajt se posle otvara duplim klikom na `index.html`,
bez interneta.

Ponasa se pristojno: cita `robots.txt` i preskace sto je zabranjeno, pravi
pauzu izmedju zahteva, predstavlja se u User-Agent-u i ima granicu broja
strana. Nije alat za obaranje tudjeg servera. Strane preko granice se ne
otvaraju, pa linkovi ka njima ostaju neispunjeni.

Instagram objave koje traze prijavu: cekiraj opciju za kolacice iz Chrome-a
(moras biti ulogovan na Instagram u Chrome-u).

## Izgled

Prozor je stvarno providan. Pikseli boje `KLJUC` (theme.py) postaju rupa
u prozoru, a Windows iza nje radi zivi blur (acrylic). Ostatak prozora
ide na 93% neprozirnosti, pa se i kroz panele malo vidi sta je iza.
Vidi se sve sto je stvarno iza — druga aplikacija, video, bilo sta — i
menja se uzivo.

**Cena:** kroz providne delove klik prolazi na aplikaciju ispod. Kartice i
dugmad rade normalno, ali prozor se pomera samo za naslovnu traku. To je
kako Windows radi sa kljucnom bojom i ne moze da se zaobidje bez gubitka
providnosti.

Ako sistem ne podrzava providnost, vraca se na crtanu pozadinu: tapeta
(citana iz Windows-a, sa stilom prikaza), pa snimak radne povrsine, pa
zeleni gradijent.

Paneli su namerno TAMNIJI od radne povrsine ispod sebe. Da su svetliji,
beli tekst bi nestao cim je iza nesto svetlo.

Ako umesto radne povrsine hoces svoju sliku, stavi `pozadina.png` (ili
.jpg) pored `Skidac.exe` — najmanje 1400x1600 px, uspravna ili kvadratna.
Ako snimak ekrana ne uspe, vraca se na zeleni gradijent.

## Kako je slozeno

```
app.py              ulazna tacka (DPI + pokretanje)
skidac/theme.py     boje, fontovi, skaliranje na DPI
skidac/draw.py      gradijent pozadine, staklo, senke, ikonice
skidac/widgets.py   kontrole nacrtane na platnu (dugme, cip, segment...)
skidac/core.py      sve oko yt-dlp i fajlova, bez ijednog widgeta
skidac/sajt.py      obilazak i preuzimanje celog sajta
skidac/gui.py       dva ekrana i njihova logika
```

## Build

```
pip install -r requirements.txt
build.bat
```

`build.bat` ocekuje `ffmpeg.exe` u istom folderu (Windows build sa
https://www.gyan.dev/ffmpeg/builds/). Gotov `.exe` je u `dist/`.

## Instalacija

`install.bat` kopira `dist\Skidac.exe` u `%LOCALAPPDATA%\Programs\Skidac`
i pravi precice na Desktopu i u Start meniju.
