@echo off
REM Reconstruye Authenticator.exe y Authenticator-Setup.exe.
pyinstaller --noconfirm --clean --windowed --name Authenticator --icon assets\icon.ico main.py
pyinstaller --noconfirm --clean --windowed --name Authenticator-Setup --icon assets\icon.ico installer\setup_wizard.py
echo Listo: dist\Authenticator\Authenticator.exe y dist\Authenticator-Setup\Authenticator-Setup.exe
