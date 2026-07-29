@echo off
echo ===================================================
echo [Photoalbum Orderer] Avvio Installazione/Aggiornamento
echo ===================================================

:: Verifica se Python e installato nel PATH di sistema
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] Python non e installato o non e presente nel PATH di sistema.
    echo Per favore, installa Python 3.x e riprova.
    pause
    exit /b 1
)

:: Verifica se la cartella .venv esiste
if not exist .venv (
    echo [INFO] Creazione dell'ambiente virtuale venv...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERRORE] Impossibile creare l'ambiente virtuale.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Ambiente virtuale venv gia esistente.
)

echo [INFO] Aggiornamento di pip e installazione delle dipendenze...
.venv\Scripts\python -m pip install --upgrade pip
if errorlevel 1 (
    echo [AVVISO] Impossibile aggiornare pip. Procedo comunque con l'installazione delle dipendenze.
)

if exist requirements.txt (
    .venv\Scripts\python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERRORE] Errore durante l'installazione delle dipendenze.
        pause
        exit /b 1
    )
) else (
    echo [ERRORE] File requirements.txt non trovato.
    pause
    exit /b 1
)

echo ===================================================
echo [Photoalbum Orderer] Installazione completata con successo!
echo ===================================================
