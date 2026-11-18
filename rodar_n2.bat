@echo off
REM ==========================================================================
REM rodar_n2.bat - Executa o pipeline completo da N2 no Windows
REM Integrantes: Luiz Eduardo Bacha dos Santos - RA 10425296
REM              Guilherme Haddad Borro - RA 10427699
REM Historico: 2026-11-17 | Luiz Eduardo Bacha dos Santos | criacao
REM ==========================================================================
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py
echo Instalando dependencias...
%PY% -m pip install -q -r requirements.txt
echo.
echo [1/3] Assistente LLM na amostra - baixa os editais e chama o modelo
%PY% src\assistente_edital.py --amostra 30
echo.
echo [2/3] Linha de base por regras
%PY% src\baseline_regras.py
echo.
echo [3/3] Avaliacao e figuras
%PY% src\avaliar.py
echo.
echo FIM. Pode avisar no chat que terminou.
pause
