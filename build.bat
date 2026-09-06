@echo off
REM Pakuje aplikaciju u jedan Skidac.exe (ffmpeg ide unutra)
py -m PyInstaller --noconfirm --clean ^
  --onefile --windowed ^
  --name Skidac ^
  --icon icon.ico ^
  --add-binary "ffmpeg.exe;." ^
  --add-data "icon.ico;." ^
  app.py
echo.
echo Gotovo: dist\Skidac.exe
pause
