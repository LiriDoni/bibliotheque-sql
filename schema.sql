-- ============================================================
--  SYSTÈME DE GESTION DE BIBLIOTHÈQUE
--  schema.sql — Création complète de la base de données
--  SQLite 3
-- ============================================================

PRAGMA foreign_keys = ON;
-- Active la vérification des clés étrangères.
-- SQLite ne les applique pas par défaut — cette ligne est indispensable.


-- ============================================================
--  1. UTILISATEURS
-- ============================================================

-- Table Admin
-- Contient les super-administrateurs du système.
-- Séparée de Client et Libraire pour isoler les privilèges
-- et éviter toute confusion de rôle au niveau des requêtes.
CREATE TABLE IF NOT EXISTS "Admin" (
    "ID_admin"         INTEGER  PRIMARY KEY AUTOINCREMENT,
    "Nom"              TEXT     NOT NULL,
    "Prenom"           TEXT     NOT NULL,
    "Email"            TEXT     UNIQUE,
    "Mot_de_passe"     TEXT,                      -- hashé en SHA-256 côté application
    "code_barre"       TEXT     UNIQUE,            -- code alphanumérique 15 caractères pour scan
    "Date_inscription" TEXT     DEFAULT (date('now'))
);

-- Table Libraire
-- Contient le personnel de la bibliothèque.
-- Possède des colonnes spécifiques au rôle (Poste, Salaire)
-- qui n'auraient pas leur place dans une table Client.
CREATE TABLE IF NOT EXISTS "Libraire" (
    "ID_libraire"      INTEGER  PRIMARY KEY AUTOINCREMENT,
    "Nom"              TEXT     NOT NULL,
    "Prenom"           TEXT     NOT NULL,
    "Email"            TEXT     UNIQUE,
    "Mot_de_passe"     TEXT,
    "Poste"            TEXT     DEFAULT 'Libraire',
    "Salaire"          REAL     DEFAULT 1800.0,
    "code_barre"       TEXT     UNIQUE,
    "Date_inscription" TEXT     DEFAULT (date('now'))
);

-- Table Client
-- Contient les emprunteurs de la bibliothèque.
-- Le champ timeout_jusqu_au permet de suspendre temporairement
-- un compte sans le supprimer.
CREATE TABLE IF NOT EXISTS "Client" (
    "ID_client"        INTEGER  PRIMARY KEY AUTOINCREMENT,
    "Nom"              TEXT     NOT NULL,
    "Prenom"           TEXT     NOT NULL,
    "Email"            TEXT     UNIQUE,
    "Mot_de_passe"     TEXT,
    "Abonnement"       REAL     DEFAULT 10.0,      -- montant mensuel en euros
    "timeout_jusqu_au" TEXT     DEFAULT NULL,      -- date ISO au-delà de laquelle le compte est réactivé
    "code_barre"       TEXT     UNIQUE,
    "Date_inscription" TEXT     DEFAULT (date('now'))
);


-- ============================================================
--  2. CATALOGUE
-- ============================================================

-- Table Maison_edition
-- Créée avant Livre car Livre y fait référence via clé étrangère.
-- Une maison d'édition peut publier plusieurs livres (1:N).
CREATE TABLE IF NOT EXISTS "Maison_edition" (
    "ID_edition"  INTEGER  PRIMARY KEY AUTOINCREMENT,
    "Nom"         TEXT     NOT NULL,
    "Lieu"        TEXT,
    "Collection"  TEXT
);

-- Table Livre
-- Entité centrale du système.
-- L'ISBN-13 est utilisé comme clé primaire car c'est un identifiant
-- international standardisé et naturellement unique par édition.
CREATE TABLE IF NOT EXISTS "Livre" (
    "Code_13"        INTEGER  PRIMARY KEY,         -- ISBN-13
    "Titre"          TEXT     NOT NULL,
    "Annee_parution" INTEGER,
    "Langue"         TEXT,
    "Format"         TEXT,                         -- ex : Poche, Grand format, Numérique
    "Nb_pages"       INTEGER,
    "ID_edition"     INTEGER  REFERENCES "Maison_edition"("ID_edition") ON DELETE SET NULL,
    "code_barre"     TEXT     UNIQUE               -- code généré pour le scan physique du livre
);

-- Table Auteur
-- L'ISNI (International Standard Name Identifier) est l'identifiant
-- international officiel des auteurs — utilisé comme clé primaire naturelle.
CREATE TABLE IF NOT EXISTS "Auteur" (
    "ISNI"          INTEGER  PRIMARY KEY,
    "Nom"           TEXT     NOT NULL,
    "Prenom"        TEXT,
    "Pseudo"        TEXT,
    "Date_naissance" TEXT,
    "Nationalite"   TEXT,
    "Role"          TEXT                           -- rôle principal : Auteur, Traducteur…
);

-- Table Auteur_Livre (table de jonction N:N)
-- Un livre peut avoir plusieurs auteurs et un auteur peut avoir
-- écrit plusieurs livres. La colonne Role permet de préciser
-- le rôle spécifique de l'auteur sur ce livre particulier.
CREATE TABLE IF NOT EXISTS "Auteur_Livre" (
    "ISNI"    INTEGER  REFERENCES "Auteur"("ISNI")    ON DELETE CASCADE,
    "Code_13" INTEGER  REFERENCES "Livre"("Code_13")  ON DELETE CASCADE,
    "Role"    TEXT,
    PRIMARY KEY ("ISNI", "Code_13")
);

-- Table Classification
-- Extension 1:1 de Livre contenant la classification Dewey,
-- le genre et la section physique de la bibliothèque.
-- Séparée de Livre pour ne pas surcharger la table principale.
CREATE TABLE IF NOT EXISTS "Classification" (
    "Code_13" INTEGER  PRIMARY KEY
                       REFERENCES "Livre"("Code_13") ON DELETE CASCADE,
    "Dewey"   REAL,                                -- ex : 843.914
    "Genre"   TEXT,                                -- ex : Roman, Essai, BD
    "Section" TEXT                                 -- ex : Littérature française
);


-- ============================================================
--  3. ACTIVITÉ
-- ============================================================

-- Table Emprunt
-- Table la plus active du système — gère à la fois les emprunts
-- réels et les listes de souhaits via la colonne Type.
-- Le statut retour_demande est un état intermédiaire déclenché
-- par le client lorsqu'il rapporte un livre : le libraire doit
-- le confirmer par scan avant que le livre redevienne disponible.
CREATE TABLE IF NOT EXISTS "Emprunt" (
    "ID_emprunt"  INTEGER  PRIMARY KEY AUTOINCREMENT,
    "ID_client"   INTEGER  NOT NULL REFERENCES "Client"("ID_client")  ON DELETE CASCADE,
    "Code_13"     INTEGER  NOT NULL REFERENCES "Livre"("Code_13")     ON DELETE CASCADE,
    "Type"        TEXT     NOT NULL CHECK("Type" IN ('emprunt','souhait')),
    "Date_ajout"  TEXT     DEFAULT (date('now')),
    "Date_prevu"  TEXT,                            -- date de retour prévue (emprunt + 30 jours)
    "Date_rendu"  TEXT,                            -- date de retour effective
    "Statut"      TEXT     DEFAULT 'en cours'
                           -- en cours       : livre actuellement emprunté
                           -- retour_demande : client a scanné pour retourner, attente libraire
                           -- rendu          : retour confirmé par le libraire
                           -- en attente     : souhait en liste d'attente
);

-- Table Avis
-- Un client ne peut laisser qu'un seul avis par livre.
-- La contrainte UNIQUE sur (ID_client, Code_13) l'impose au niveau DB.
-- La note est contrainte entre 1 et 5 par un CHECK.
CREATE TABLE IF NOT EXISTS "Avis" (
    "ID_avis"     INTEGER  PRIMARY KEY AUTOINCREMENT,
    "ID_client"   INTEGER  NOT NULL REFERENCES "Client"("ID_client")  ON DELETE CASCADE,
    "Code_13"     INTEGER  NOT NULL REFERENCES "Livre"("Code_13")     ON DELETE CASCADE,
    "Note"        INTEGER  CHECK("Note" BETWEEN 1 AND 5),
    "Commentaire" TEXT,
    "Date_avis"   TEXT     DEFAULT (date('now')),
    UNIQUE ("ID_client", "Code_13")
);

-- Table Log_action
-- Enregistre toutes les actions effectuées par les libraires.
-- ON DELETE SET NULL sur ID_libraire : si un libraire est supprimé,
-- ses logs sont conservés avec ID_libraire = NULL pour traçabilité.
CREATE TABLE IF NOT EXISTS "Log_action" (
    "ID_log"      INTEGER  PRIMARY KEY AUTOINCREMENT,
    "ID_libraire" INTEGER  REFERENCES "Libraire"("ID_libraire") ON DELETE SET NULL,
    "Action"      TEXT     NOT NULL,               -- ex : ajout_livre, retour_confirme
    "Detail"      TEXT,                            -- description lisible de l'action
    "Date_action" TEXT     DEFAULT (datetime('now'))
);


-- ============================================================
--  4. INDEX
-- ============================================================

-- Index sur code_barre de chaque table utilisateur et de Livre.
-- Le scan de code barre est l'opération la plus fréquente du système :
-- ces index rendent la recherche quasi-instantanée (O log n → O 1).
CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_code    ON Admin(code_barre);
CREATE UNIQUE INDEX IF NOT EXISTS idx_libraire_code ON Libraire(code_barre);
CREATE UNIQUE INDEX IF NOT EXISTS idx_client_code   ON Client(code_barre);
CREATE UNIQUE INDEX IF NOT EXISTS idx_livre_code    ON Livre(code_barre);

-- Index sur Emprunt(ID_client) pour accélérer les requêtes
-- "livres actuellement empruntés par ce client" — très fréquentes
-- lors de la vérification de la limite de 3 emprunts simultanés.
CREATE INDEX IF NOT EXISTS idx_emprunt_client ON Emprunt(ID_client);

-- Index sur Emprunt(Code_13) pour accélérer la vérification
-- de la disponibilité d'un livre lors d'un scan.
CREATE INDEX IF NOT EXISTS idx_emprunt_livre  ON Emprunt(Code_13);

-- Index sur Emprunt(Statut) pour accélérer les requêtes
-- de filtrage par statut (retours en attente, emprunts en cours…).
CREATE INDEX IF NOT EXISTS idx_emprunt_statut ON Emprunt(Statut);

-- Index sur Log_action(ID_libraire) pour accélérer le filtrage
-- des logs par libraire dans l'interface admin.
CREATE INDEX IF NOT EXISTS idx_log_libraire   ON Log_action(ID_libraire);


-- ============================================================
--  5. VUES
-- ============================================================

-- Vue : Vue_Livre_Complet
-- Assemble en une seule requête toutes les informations d'un livre :
-- titre, auteurs (concaténés), éditeur, collection, classification.
-- Utilisée par l'interface client pour afficher le détail d'un livre.
CREATE VIEW IF NOT EXISTS "Vue_Livre_Complet" AS
SELECT
    l."Code_13",
    l."Titre",
    l."Annee_parution",
    l."Langue",
    l."Format",
    l."Nb_pages",
    me."Nom"        AS "Editeur",
    me."Collection",
    cl."Dewey",
    cl."Genre",
    cl."Section",
    GROUP_CONCAT(a."Prenom" || ' ' || a."Nom", ', ') AS "Auteurs"
FROM "Livre" l
LEFT JOIN "Maison_edition" me  ON l."ID_edition" = me."ID_edition"
LEFT JOIN "Classification" cl  ON l."Code_13"    = cl."Code_13"
LEFT JOIN "Auteur_Livre"   al  ON l."Code_13"    = al."Code_13"
LEFT JOIN "Auteur"         a   ON al."ISNI"       = a."ISNI"
GROUP BY l."Code_13";

-- Vue : Vue_Notes
-- Calcule la note moyenne et le nombre d'avis pour chaque livre.
-- LEFT JOIN : les livres sans avis apparaissent quand même avec NULL.
-- ROUND(..., 1) : arrondi à une décimale pour l'affichage.
CREATE VIEW IF NOT EXISTS "Vue_Notes" AS
SELECT
    l."Code_13",
    l."Titre",
    ROUND(AVG(a."Note"), 1)  AS "Note_moyenne",
    COUNT(a."ID_avis")       AS "Nb_avis"
FROM "Livre" l
LEFT JOIN "Avis" a ON l."Code_13" = a."Code_13"
GROUP BY l."Code_13";

-- Vue : Vue_Disponibilite
-- Indique si un livre est disponible ou non en regardant
-- s'il existe un emprunt actif (en cours ou retour_demande).
-- Un livre en attente de retour n'est pas encore disponible.
CREATE VIEW IF NOT EXISTS "Vue_Disponibilite" AS
SELECT
    l."Code_13",
    l."Titre",
    CASE
        WHEN COUNT(CASE WHEN e."Statut" IN ('en cours','retour_demande') THEN 1 END) > 0
        THEN 'Indisponible'
        ELSE 'Disponible'
    END AS "Statut_disponibilite"
FROM "Livre" l
LEFT JOIN "Emprunt" e ON l."Code_13" = e."Code_13" AND e."Type" = 'emprunt'
GROUP BY l."Code_13";

-- Vue : Vue_Emprunts_En_Cours
-- Liste tous les emprunts actifs avec les informations du client
-- et du livre. Utilisée par le libraire pour suivre les emprunts.
CREATE VIEW IF NOT EXISTS "Vue_Emprunts_En_Cours" AS
SELECT
    e."ID_emprunt",
    c."Prenom" || ' ' || c."Nom"  AS "Client",
    l."Titre",
    e."Date_ajout"                AS "Date_emprunt",
    e."Date_prevu"                AS "Retour_prevu",
    e."Statut",
    CASE
        WHEN e."Statut" = 'en cours' AND e."Date_prevu" < date('now')
        THEN 'OUI'
        ELSE 'NON'
    END AS "En_retard"
FROM "Emprunt" e
JOIN "Client" c ON e."ID_client" = c."ID_client"
JOIN "Livre"  l ON e."Code_13"   = l."Code_13"
WHERE e."Type" = 'emprunt'
  AND e."Statut" IN ('en cours', 'retour_demande');

-- Vue : Vue_Retours_En_Attente
-- Liste les emprunts dont le client a demandé le retour
-- mais que le libraire n'a pas encore confirmé.
-- C'est cette vue qui alimente le badge de notification
-- dans l'interface libraire.
CREATE VIEW IF NOT EXISTS "Vue_Retours_En_Attente" AS
SELECT
    e."ID_emprunt",
    c."Prenom" || ' ' || c."Nom"  AS "Client",
    l."Titre",
    l."Code_13",
    e."Date_ajout"                AS "Date_emprunt"
FROM "Emprunt" e
JOIN "Client" c ON e."ID_client" = c."ID_client"
JOIN "Livre"  l ON e."Code_13"   = l."Code_13"
WHERE e."Type"   = 'emprunt'
  AND e."Statut" = 'retour_demande'
ORDER BY e."Date_ajout";
