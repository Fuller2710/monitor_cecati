@echo off
cd /d "%~dp0"
echo ========================================================
echo   Ejecutando Robot Monitor de Cursos CECATI 95
echo ========================================================
python monitor_cecati.py --check-now
if %errorlevel% neq 0 (
    echo [ERROR] Ocurrio un error al ejecutar el monitor.
) else (
    echo [OK] Revision completada con exito.
)
timeout /t 5
