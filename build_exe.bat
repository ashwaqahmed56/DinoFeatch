@echo off
REM Build DinoFetch.exe  (single file, includes ffmpeg + templates + icons)
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller DinoFetch.spec --noconfirm --clean
if errorlevel 1 (
  echo BUILD FAILED
  pause
  exit /b 1
)
echo.
echo Built: dist\DinoFetch.exe
echo Downloads are saved next to the exe, in the downloads\ folder.
pause