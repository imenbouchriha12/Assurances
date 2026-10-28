@echo off
REM Remplace tout le contenu du jeu de donnees /assurance par assurance_sinistres_inferred.owl.
REM Fuseki doit etre demarre. Sert aussi a revenir aux donnees d'origine apres des tests CRUD.
REM Si l'ontologie a change : lancer d'abord "backend\.venv\Scripts\python raisonnement.py" pour regenerer le fichier infere.
cd /d "%~dp0"
curl.exe -s -f -X PUT -H "Content-Type: application/rdf+xml" --data-binary "@assurance_sinistres_inferred.owl" "http://localhost:3030/assurance/data?default"
if errorlevel 1 (
    echo ECHEC : Fuseki est-il demarre ? ^(demarrer_fuseki.bat^)
    exit /b 1
)
echo.
echo Donnees chargees dans http://localhost:3030/assurance
