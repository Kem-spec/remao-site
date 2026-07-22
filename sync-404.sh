#!/bin/sh
# GitHub Pages ne sait pas reecrire les URL : il sert 404.html pour toute adresse
# sans fichier correspondant (/assises, /pays/ci...). Ce fichier doit donc etre
# une copie exacte d'index.html, sinon ces adresses afficheront une version perimee.
# A executer apres CHAQUE modification d'index.html.
cd "$(dirname "$0")" && cp index.html 404.html && echo "404.html resynchronise"
