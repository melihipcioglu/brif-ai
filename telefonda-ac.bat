@echo off
chcp 65001 >nul
title YOKDIL Fen - Telefon Sunucusu
cd /d "%~dp0"

echo.
echo === YOKDIL Fen: telefondan acmak icin sunucu hazirlaniyor ===
echo.

rem Windows Guvenlik Duvari kurali (yalnizca ilk seferde yonetici izni ister)
netsh advfirewall firewall show rule name="YOKDIL Fen" >nul 2>&1
if errorlevel 1 (
  echo Guvenlik duvari izni ekleniyor. Acilan "Evet" penceresini onaylayin...
  powershell -NoProfile -Command "Start-Process netsh -ArgumentList 'advfirewall firewall add rule name=\"YOKDIL Fen\" dir=in action=allow protocol=TCP localport=4173 profile=any' -Verb RunAs -Wait"
)

call npm run build:app
if errorlevel 1 (
  echo Derleme basarisiz.
  pause
  exit /b 1
)

set IP=
for /f %%i in ('powershell -NoProfile -Command "(Get-NetIPConfiguration ^| Where-Object IPv4DefaultGateway).IPv4Address.IPAddress"') do set IP=%%i

echo.
echo ================================================================
echo  Telefonunuz bu bilgisayarla AYNI Wi-Fi aginda olmali.
echo  Telefon tarayicisinda su adresi acin:
echo.
echo      http://%IP%:4173
echo.
echo  Bu pencere acik kaldigi surece uygulama erisilebilir.
echo ================================================================
echo.

call npm run preview:app
pause
