@echo off
REM Lance l'interface sur http://localhost:5173 (l'API doit tourner sur http://localhost:8000).
REM Premier lancement : installe les dependances (npm install).
cd /d "%~dp0"
if not exist node_modules call npm install
call npm run dev
