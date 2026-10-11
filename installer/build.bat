@echo off
REM Reconstruye Authenticator.exe y Authenticator-Setup.exe.
python -m PyInstaller --noconfirm --clean Authenticator.spec
python -m PyInstaller --noconfirm --clean Authenticator-Setup.spec
echo Listo: dist\Authenticator.exe y dist\Authenticator-Setup.exe
