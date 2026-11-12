@echo off
REM EasyDoc — build the Windows 10/11 .exe installer
REM Run this on a Windows 10/11 PC (run as Administrator the first time).
REM Developed by Mahmudul Hasan.
REM
REM 1. Install Python 3.11+ from python.org and tick "Add Python to PATH".
REM 2. Install LibreOffice (free) from libreoffice.org — needed for
REM    Word/PowerPoint/Excel -> PDF with correct page breaks.
REM 3. Install Tesseract OCR (optional, for OCR): https://github.com/UB-Mannheim/tesseract/wiki
REM 4. Double-click this file. It creates EasyDoc.exe in dist\ and
REM    EasyDoc-Setup.exe (installer) if Inno Setup is installed.

python --version || (echo Python is not installed. Install Python 3.11+ first. & pause & exit /b 1)
pip install -r ..\requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name EasyDoc ^
  --add-data "..\src\easydoc;easydoc" ^
  ..\src\easydoc\gui.py
echo.
echo Built: dist\EasyDoc\EasyDoc.exe
echo If Inno Setup is installed, run windows\EasyDoc.iss to make EasyDoc-Setup.exe
pause
