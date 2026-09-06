# Skidac

Desktop aplikacija za Windows — skida video sa YouTube-a i Instagrama kao MP4 ili MP3.

## Kako se koristi

1. Pokreni `Skidac.exe`
2. Izaberi **YouTube** ili **Instagram**
3. Nalepi link i klikni **Proveri**
4. Izaberi MP4 (rezolucija do 4K) ili MP3 (do 320 kbps)
5. **Skini** — folder se otvara sam kad zavrsi

Instagram objave koje traze prijavu: cekiraj opciju za kolacice iz Chrome-a
(moras biti ulogovan na Instagram u Chrome-u).

## Svoja pozadina

Stavi `pozadina.png` (ili .jpg) pored `Skidac.exe` i aplikacija ce je
koristiti umesto zelenog gradijenta. Slika se sece na sredini i uklapa u
prozor, pa neka bude uspravna ili kvadratna, najmanje 1400x1600 px.
Automatski se pritamni da tekst ostane citljiv.

## Kako je slozeno

```
app.py              ulazna tacka (DPI + pokretanje)
skidac/theme.py     boje, fontovi, skaliranje na DPI
skidac/draw.py      gradijent pozadine, staklo, senke, ikonice
skidac/widgets.py   kontrole nacrtane na platnu (dugme, cip, segment...)
skidac/core.py      sve oko yt-dlp i fajlova, bez ijednog widgeta
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
