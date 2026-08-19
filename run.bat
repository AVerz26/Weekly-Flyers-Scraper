@echo off
title FlyerScout AI - Instagram Supermarket Flyers Scraper
color 0A

echo ============================================================
echo   FlyerScout AI - Iniciar Aplicacao
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Verificando dependencias...
pip install -r requirements.txt --quiet

echo [2/3] Iniciando Servidor Web (FastAPI)...
echo.
echo ============================================================
echo   Aplicacao rodando em: http://localhost:8000
echo   Pressione Ctrl+C para encerrar o servidor
echo ============================================================
echo.

python app.py
pause
