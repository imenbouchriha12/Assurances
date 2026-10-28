@echo off
REM Lance l'API FastAPI sur http://localhost:8000 (documentation interactive : http://localhost:8000/docs).
REM Fuseki doit etre demarre avant (demarrer_fuseki.bat). Installation : voir README.md.
REM (fichier sans accents : cmd.exe lit les .bat dans l'encodage OEM)
cd /d "%~dp0"
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
