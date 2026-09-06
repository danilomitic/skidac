@echo off
REM Instalira Skidac i pravi precice na Desktopu i u Start meniju.
REM Pokreni posle build.bat.

set APP=%LOCALAPPDATA%\Programs\Skidac

if not exist "dist\Skidac.exe" (
  echo Nema dist\Skidac.exe - pokreni prvo build.bat
  pause
  exit /b 1
)

taskkill /IM Skidac.exe /F >nul 2>&1
if not exist "%APP%" mkdir "%APP%"
copy /Y "dist\Skidac.exe" "%APP%\Skidac.exe" >nul
copy /Y "icon.ico" "%APP%\icon.ico" >nul

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "foreach ($d in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {" ^
  "  $s = $ws.CreateShortcut(\"$d\Skidac.lnk\");" ^
  "  $s.TargetPath = \"$env:LOCALAPPDATA\Programs\Skidac\Skidac.exe\";" ^
  "  $s.WorkingDirectory = \"$env:LOCALAPPDATA\Programs\Skidac\";" ^
  "  $s.IconLocation = \"$env:LOCALAPPDATA\Programs\Skidac\Skidac.exe,0\";" ^
  "  $s.Description = 'Skidanje video klipova sa YouTube-a i Instagrama';" ^
  "  $s.Save() }"

echo.
echo Instalirano u %APP%
echo Precica je na Desktopu i u Start meniju.
pause
