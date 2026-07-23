#!/bin/sh
# GitHub Pages ne sait pas reecrire les URL. Pour que /assises/ reponde 200 (et non 404,
# ce qui casserait les apercus WhatsApp et le referencement), chaque vue a son propre
# dossier contenant une copie d'index.html. 404.html couvre le reste : articles et
# editions d'Assises, dont les adresses dependent d'identifiants dynamiques.
#
# Les copies etant identiques, git n'en stocke qu'un seul exemplaire.
#
# A EXECUTER APRES CHAQUE MODIFICATION D'index.html.
cd "$(dirname "$0")" || exit 1

VUES="qui-sommes-nous assises revue actualites devenir-membre creer-une-cellule"
PAYS="bj bf ci gn ml ne sn tg"

cp index.html 404.html
for v in $VUES; do
  mkdir -p "$v" && cp index.html "$v/index.html"
done
for p in $PAYS; do
  mkdir -p "pays/$p" && cp index.html "pays/$p/index.html"
done
mkdir -p pays && cp index.html pays/index.html

echo "Pages regenerees : 404.html + $(echo $VUES | wc -w) vues + $(echo $PAYS | wc -w) pays"
