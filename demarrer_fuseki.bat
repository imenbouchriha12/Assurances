@echo off
REM Demarre Fuseki sur http://localhost:3030 avec le jeu de donnees persistant /assurance (TDB2).
REM --update autorise les requetes INSERT / DELETE (CRUD). Ctrl+C pour arreter.
REM --localhost : ecoute seulement sur cette machine (sinon le CRUD anonyme est ouvert a tout le reseau local).
REM Au premier lancement, executer ensuite recharger_donnees.bat pour charger l'ontologie.
REM (fichier sans accents : cmd.exe lit les .bat dans l'encodage OEM)
cd /d "%~dp0fuseki"
set FUSEKI_BASE=%~dp0fuseki\run
if not exist databases\assurance mkdir databases\assurance
java -Xmx1G -jar fuseki-server.jar --localhost --update --tdb2 --loc=databases\assurance /assurance
