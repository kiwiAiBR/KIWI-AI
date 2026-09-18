@echo off
echo ========================================================
echo 🥝 Iniciando o Servidor Web da Kiwi...
echo ========================================================
echo Abrindo seu navegador em http://localhost:5000 ...
timeout /t 2 >nul
start http://localhost:5000
python app.py
pause
