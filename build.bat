@echo off
echo Installing dependencies...
pip install --user pyinstaller PyQt5

echo.
echo Building exe...
python -m PyInstaller --onefile --windowed --name "DesktopFinder" main.py

echo.
echo Done! Output: dist/DesktopFinder.exe
pause
