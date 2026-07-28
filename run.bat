:: Esegue l'installer per assicurarsi che tutto sia configurato/aggiornato
call install.bat
if errorlevel 1 (
    echo [ERRORE] L'installazione o l'aggiornamento e fallito. Impossibile avviare.
    pause
    exit /b 1
)

@echo off
echo ===================================================
echo [Photoalbum Orderer] Avvio dell'applicazione...
echo ===================================================

echo [INFO] Avvio della GUI in corso...
.venv\Scripts\python run.py
if errorlevel 1 (
    echo [ERRORE] L'applicazione si e interrotta con un errore.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo [Photoalbum Orderer] Applicazione chiusa.
echo ===================================================
pause
