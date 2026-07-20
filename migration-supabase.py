#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration des contenus REMAO de l'ancien projet Supabase (compte personnel)
vers le nouveau projet institutionnel.

Ce que fait le script :
  1. lit les 25 fiches de l'ancien projet (lecture publique, aucune clé secrète)
  2. télécharge les 44 fichiers du bucket « medias » (bucket public)
  3. les réenvoie dans le bucket « medias » du nouveau projet, mêmes chemins
  4. réécrit les URL des fichiers dans les fiches
  5. insère les fiches dans le nouveau projet, en gardant les dates de création

La clé service_role n'est jamais écrite dans ce fichier : le script la lit dans
une variable d'environnement, elle ne quitte donc pas ton ordinateur.

Utilisation (PowerShell) :
    $env:NEW_SUPA_SERVICE_KEY = "la_cle_service_role"
    python migration-supabase.py

Ajoute --dry-run pour voir ce qui serait fait sans rien écrire.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

ANCIEN_URL = "https://tfsumqrvqfbjpbuqhxrs.supabase.co"
ANCIEN_KEY = "sb_publishable_3lxVbDUkuD9nE6AXWq-Xuw_9XD7WIMx"
# Projet institutionnel REMAOWAMS. Redéfinissable par NEW_SUPA_URL au besoin.
NOUVEAU_URL_DEFAUT = "https://aohfgaxmahcowatzlvyi.supabase.co"
BUCKET = "medias"

DRY = "--dry-run" in sys.argv


def http(url, method="GET", data=None, headers=None, brut=False):
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=120) as r:
        contenu = r.read()
    return contenu if brut else json.loads(contenu.decode("utf-8") or "null")


def echec(msg):
    print("\n  ERREUR : " + msg)
    sys.exit(1)


nouveau_url = (os.environ.get("NEW_SUPA_URL") or NOUVEAU_URL_DEFAUT).rstrip("/")
service_key = os.environ.get("NEW_SUPA_SERVICE_KEY") or ""

if not DRY and not service_key:
    echec(
        "il manque NEW_SUPA_SERVICE_KEY.\n"
        "  Dans PowerShell, avec la clé service_role du nouveau projet\n"
        "  (Settings > API Keys) :\n"
        '    $env:NEW_SUPA_SERVICE_KEY = "la_cle_service_role"'
    )

entetes_new = {
    "apikey": service_key,
    "Authorization": "Bearer " + service_key,
}

print("=" * 62)
print("  Migration REMAO vers le nouveau projet Supabase")
if DRY:
    print("  MODE SIMULATION : aucune écriture")
print("=" * 62)

# ---------------------------------------------------------------- 1. lecture
print("\n[1/5] Lecture de l'ancien projet…")
lignes = http(
    ANCIEN_URL + "/rest/v1/contenus?select=id,type,data,created_at&order=created_at",
    headers={"apikey": ANCIEN_KEY},
)
print("      %d fiches trouvées." % len(lignes))
par_type = {}
for l in lignes:
    par_type[l["type"]] = par_type.get(l["type"], 0) + 1
for t in sorted(par_type):
    print("        - %-12s %d" % (t, par_type[t]))

# ------------------------------------------------- 2. inventaire des fichiers
prefixe_ancien = ANCIEN_URL + "/storage/v1/object/public/" + BUCKET + "/"
brut = json.dumps(lignes, ensure_ascii=False)
chemins = set()
i = 0
while True:
    i = brut.find(prefixe_ancien, i)
    if i == -1:
        break
    j = i + len(prefixe_ancien)
    # L'URL s'arrête au premier caractère qui ne peut pas en faire partie.
    while j < len(brut) and brut[j] not in '"\\ \t\n<>)':
        j += 1
    chemins.add(brut[i + len(prefixe_ancien):j])
    i = j

print("\n[2/5] %d fichiers référencés dans le bucket « %s »." % (len(chemins), BUCKET))

if DRY:
    print("\n      Simulation terminée. Relance sans --dry-run pour migrer.")
    sys.exit(0)

# --------------------------------------------------- 3. copie des fichiers
print("\n[3/5] Copie des fichiers vers le nouveau bucket…")
TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "webp": "image/webp", "gif": "image/gif", "svg": "image/svg+xml",
    "pdf": "application/pdf",
}
copies, deja, rates = 0, 0, []
for n, chemin in enumerate(sorted(chemins), 1):
    ext = chemin.rsplit(".", 1)[-1].lower()
    mime = TYPES.get(ext, "application/octet-stream")
    court = chemin if len(chemin) <= 52 else chemin[:24] + "…" + chemin[-27:]
    print("      %2d/%d  %s" % (n, len(chemins), court), end=" ")
    try:
        contenu = http(prefixe_ancien + chemin, brut=True)
    except urllib.error.HTTPError as e:
        print("→ introuvable à la source (%s)" % e.code)
        rates.append(chemin)
        continue
    try:
        http(
            nouveau_url + "/storage/v1/object/" + BUCKET + "/" + chemin,
            method="POST",
            data=contenu,
            headers=dict(entetes_new, **{"Content-Type": mime, "x-upsert": "true"}),
        )
        print("→ copié (%d Ko)" % (len(contenu) // 1024))
        copies += 1
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:120]
        if e.code == 409:
            print("→ déjà présent")
            deja += 1
        else:
            print("→ échec (%s) %s" % (e.code, detail))
            rates.append(chemin)
    time.sleep(0.05)

print("      %d copiés, %d déjà présents, %d en échec." % (copies, deja, len(rates)))
if rates:
    print("      Fichiers non copiés :")
    for c in rates:
        print("        " + c)

# ------------------------------------------- 4. réécriture des URL + insertion
print("\n[4/5] Réécriture des URL et insertion des fiches…")
prefixe_nouveau = nouveau_url + "/storage/v1/object/public/" + BUCKET + "/"
charge = []
for l in lignes:
    data = json.loads(
        json.dumps(l["data"], ensure_ascii=False).replace(prefixe_ancien, prefixe_nouveau)
    )
    # On garde l'id et la date de création : les liens déjà partagés vers un
    # article (#article/<id>) continuent de fonctionner après la bascule.
    charge.append({
        "id": l["id"],
        "type": l["type"],
        "data": data,
        "created_at": l["created_at"],
    })

try:
    http(
        nouveau_url + "/rest/v1/contenus",
        method="POST",
        data=json.dumps(charge, ensure_ascii=False).encode("utf-8"),
        headers=dict(entetes_new, **{
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }),
    )
except urllib.error.HTTPError as e:
    echec("insertion refusée (%s) : %s\n  As-tu bien exécuté supabase-schema.sql "
          "dans le SQL Editor du nouveau projet ?" % (e.code, e.read().decode("utf-8", "replace")[:300]))

print("      %d fiches insérées." % len(charge))

# ------------------------------------------------------------ 5. vérification
print("\n[5/5] Vérification du nouveau projet…")
verif = http(
    nouveau_url + "/rest/v1/contenus?select=id,type",
    headers={"apikey": service_key, "Authorization": "Bearer " + service_key},
)
compte = {}
for l in verif:
    compte[l["type"]] = compte.get(l["type"], 0) + 1
print("      %d fiches en base :" % len(verif))
for t in sorted(compte):
    marque = "ok" if compte[t] == par_type.get(t) else "ATTENDU %d" % par_type.get(t, 0)
    print("        - %-12s %d  (%s)" % (t, compte[t], marque))

print("\n" + "=" * 62)
print("  Migration terminée.")
print("  Reste à faire :")
print("    1. mettre à jour supabase-config.js (URL + clé publishable)")
print("    2. créer le compte du Bureau dans Authentication > Users")
print("    3. effacer la variable : $env:NEW_SUPA_SERVICE_KEY = $null")
print("=" * 62)
