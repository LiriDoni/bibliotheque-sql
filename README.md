#  Système de Gestion de Bibliothèque

## Présentation du projet

Ce projet est un **système de gestion de bibliothèque** développé dans le cadre d'un projet scolaire. Il simule le fonctionnement complet d'une bibliothèque réelle, depuis la gestion du catalogue de livres jusqu'aux emprunts des clients, en passant par l'administration du personnel.

### Problème résolu

La gestion manuelle d'une bibliothèque (registres papier, fiches d'emprunt, suivi des retours) est lente, peu fiable et difficile à maintenir. Ce système centralise toutes ces opérations dans une base de données relationnelle accompagnée d'une interface graphique intuitive, permettant :

- De **suivre les emprunts** en temps réel
- D'**automatiser les retours** via scan de code barre
- De **gérer le personnel** (libraires) et les clients depuis un seul outil
- D'**alerter** les libraires lorsqu'un retour est en attente de confirmation

---

## Utilisateurs cibles

Le système est conçu pour trois types d'utilisateurs, chacun avec son propre espace :

| Rôle | Description |
|------|-------------|
| **Super Admin** | Gère les libraires (ajout, suppression, salaire, poste), consulte les logs d'activité et peut suspendre des clients |
| **Libraire** | Ajoute des livres au catalogue, gère les emprunts, confirme les retours via scan |
| **Client** | Emprunte et retourne des livres via scan de code barre, laisse des avis, gère sa liste de souhaits |

Chaque utilisateur se connecte en **scannant son code barre personnel** — aucun mot de passe requis au quotidien.

---

## Sources de données

Les données utilisées dans ce projet sont **entièrement générées manuellement** à des fins de test et de démonstration :

- **Livres** : titres, auteurs, éditeurs et métadonnées saisis manuellement (œuvres du domaine public : *L'Étranger*, *Le Petit Prince*, *1984*, *Dune*, *Les Misérables*, etc.)
- **Clients et libraires** : comptes créés directement via l'interface
- **Emprunts et avis** : simulés pour tester le fonctionnement du système
- **Codes barres** : générés automatiquement par le programme à partir de codes aléatoires de 15 caractères

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Base de données | SQLite 3 |
| Interface graphique | Python — Tkinter |
| Génération de codes barres | `python-barcode` + `Pillow` |
| Langage principal | Python 3.x |

---

## Structure de la base de données

La base contient **12 tables** organisées autour du livre comme entité centrale :

```
Client        → emprunteurs (abonnement, code barre, suspension)
Libraire      → personnel (poste, salaire, code barre)
Admin         → super administrateurs
Livre         → catalogue (ISBN, titre, format, code barre)
Auteur        → auteurs des livres
Auteur_Livre  → liaison N:N entre auteurs et livres
Maison_edition → éditeurs et collections
Classification → classification Dewey, genre, section
Emprunt       → historique des emprunts et listes de souhaits
Avis          → notes et commentaires des clients
Log_action    → journal des actions des libraires
```

---

## Fonctionnalités principales

-  **Connexion par scan de code barre** — chaque utilisateur a un code unique de 15 caractères
-  **Emprunt instantané** — scanner un livre l'emprunte directement
-  **Retour en deux étapes** — le client initie, le libraire confirme par scan
-  **Notification en temps réel** — le libraire voit les retours en attente avec badge et compteur
-  **Suspension de clients** — l'admin peut bloquer un compte pour N jours
-  **Logs d'activité** — toutes les actions des libraires sont tracées
-  **Génération automatique de codes barres** — PNG prêts à imprimer à chaque création
-  **Système d'avis** — notes de 1 à 5 étoiles avec commentaires
-  **Liste de souhaits** — les clients peuvent réserver des livres indisponibles

---

## Application graphique (bonus)

En plus de la base de données, une interface graphique complète a été développée en **Python + Tkinter** permettant d'utiliser le système sans écrire de SQL.

### Prérequis

\```
pip install python-barcode[images] Pillow
\```

### Lancer l'application

\```
python app.py
\```

### Fonctionnement

L'application se lance sur un écran de scan. Chaque utilisateur possède un **code barre unique de 15 caractères** à scanner pour se connecter — aucun mot de passe requis au quotidien.

| Fichier | Rôle |
|---------|------|
| `app.py` | Application principale |
| `bibliotheque.db` | Base de données SQLite |
| `barcodes/` | Codes barres générés automatiquement (PNG) |
