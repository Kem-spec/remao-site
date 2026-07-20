# Migration vers les comptes institutionnels REMAO

Procédure suivie en juillet 2026 pour faire passer le site des comptes personnels
(GitHub `Kem-spec`, Supabase « Kem-spec's Org ») aux comptes du réseau
(GitHub `REMAOWAMS`, Supabase « REMAOWAMS's Org »).

À conserver : la même procédure servira à toute future passation entre bureaux.

---

## 1. Supabase

### 1.1 Créer le schéma

Dans le nouveau projet : **SQL Editor > New query**, coller tout le contenu de
`supabase-schema.sql`, puis **Run**. Cela crée la table `contenus`, ses règles de
sécurité (lecture publique, écriture réservée aux comptes connectés) et le bucket
public `medias`.

### 1.2 Migrer les contenus et les fichiers

Le script `migration-supabase.py` copie les fiches et les images d'un projet à l'autre.
Il a besoin de la clé **service_role** du nouveau projet (Settings > API Keys).

> Cette clé contourne toutes les règles de sécurité. Elle ne doit jamais être écrite
> dans un fichier du dépôt, ni collée dans une conversation. Le script la lit dans une
> variable d'environnement, elle reste sur le poste.

```powershell
# Vérifier ce qui sera migré, sans rien écrire
python migration-supabase.py --dry-run

# Migrer pour de bon
$env:NEW_SUPA_SERVICE_KEY = "la_cle_service_role"
python migration-supabase.py

# Effacer la clé de la session une fois fini
$env:NEW_SUPA_SERVICE_KEY = $null
```

Le script conserve les identifiants et les dates de création des fiches : les liens
déjà partagés vers un article (`#article/<id>`) continuent de fonctionner.

### 1.3 Brancher le site

Mettre à jour `supabase-config.js` avec l'URL du nouveau projet et sa clé
**publishable** (celle qui commence par `sb_publishable_`). Cette clé est publique par
conception, elle est protégée par les règles de sécurité de la base.

### 1.4 Créer le compte du Bureau

**Authentication > Users > Add user**, avec une adresse institutionnelle du réseau.
C'est ce compte qui ouvre l'administration du site.

---

## 2. GitHub

Deux voies possibles.

**Transfert du dépôt** (garde tout l'historique, et GitHub redirige l'ancienne
adresse) : dans l'ancien dépôt, Settings > General > Danger Zone > Transfer ownership.

**Nouveau dépôt** : créer `remao-site` sur le compte REMAOWAMS, puis

```powershell
git remote set-url origin https://github.com/REMAOWAMS/remao-site.git
git push -u origin main
```

Le poste doit être authentifié sur le nouveau compte. Le plus simple est un jeton
d'accès personnel (Settings > Developer settings > Personal access tokens), demandé
par Git au premier `push`.

Ensuite : **Settings > Pages**, source « Deploy from a branch », branche `main`,
dossier `/ (root)`. Le site est en ligne 1 à 2 minutes plus tard.

---

## 3. Après la bascule

- Les métadonnées Open Graph (`index.html`) doivent pointer vers la nouvelle adresse,
  sinon les aperçus de liens partagés sur WhatsApp restent cassés.
- Communiquer la nouvelle adresse aux cellules nationales.
- L'ancien projet Supabase peut être supprimé une fois la migration vérifiée, mais
  attendre quelques jours : tant qu'il existe, un retour en arrière reste possible.

---

## 4. Ce qui doit se transmettre d'un bureau à l'autre

| Élément | Où |
|---|---|
| Compte GitHub `REMAOWAMS` | identifiants + double authentification |
| Compte Supabase | identifiants + mot de passe de la base Postgres |
| Compte administrateur du site | créé dans Authentication > Users |
| Nom de domaine, s'il est acquis un jour | chez le bureau d'enregistrement |

Recommandation : rattacher tous ces comptes à une adresse institutionnelle du réseau,
jamais à l'adresse personnelle d'un membre du bureau.
