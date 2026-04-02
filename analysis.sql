-- ============================================================
--  SYSTÈME DE GESTION DE BIBLIOTHÈQUE
--  analysis.sql — Requêtes d'analyse
--
--  Ce fichier contient des requêtes qui extraient de l'information
--  utile pour les utilisateurs du système : clients, libraires
--  et administrateurs.
--
--  Fonctionnalités SQL utilisées :
--  JOIN, LEFT JOIN, GROUP BY, HAVING, sous-requêtes,
--  CASE, agrégations (COUNT, AVG, SUM, MAX, MIN),
--  WITH (CTE), julianday(), date(), ORDER BY, LIMIT
--
--  Sections :
--  1. Profil client — historique et situation personnelle
--  2. Recherche de livres — disponibilité et localisation
--  3. Statistiques globales — livres, clients, emprunts
--  4. Analyse du personnel — activité des libraires
-- ============================================================

PRAGMA foreign_keys = ON;


-- ============================================================
--  1. PROFIL CLIENT
--  Requêtes déclenchées quand un client scanne sa carte
--  ou consulte son espace personnel.
-- ============================================================

-- ── Fiche complète d'un client ────────────────────────────────────────────
-- Affiche toutes les informations d'un client : nom, abonnement,
-- nombre de livres en cours, statut de suspension.
-- Utilise CASE pour rendre le statut lisible.
SELECT
    c.ID_client,
    c.Prenom || ' ' || c.Nom                   AS Nom_complet,
    c.Email,
    c.Abonnement                                AS Abonnement_mensuel,
    c.Date_inscription,
    COUNT(CASE WHEN e.Statut IN ('en cours','retour_demande') THEN 1 END)
                                                AS Livres_en_cours,
    COUNT(CASE WHEN e.Statut = 'rendu' THEN 1 END)
                                                AS Livres_rendus,
    COUNT(CASE WHEN e.Type = 'souhait' THEN 1 END)
                                                AS Livres_souhaites,
    CASE
        WHEN c.timeout_jusqu_au IS NOT NULL
         AND c.timeout_jusqu_au >= date('now')
        THEN 'Suspendu jusqu''au ' || c.timeout_jusqu_au
        ELSE 'Actif'
    END                                         AS Statut_compte
FROM Client c
LEFT JOIN Emprunt e ON c.ID_client = e.ID_client
WHERE c.ID_client = 1   -- remplacer par l'ID du client scanné
GROUP BY c.ID_client;


-- ── Historique complet des emprunts d'un client ───────────────────────────
-- Affiche tous les livres empruntés, rendus et souhaités par un client,
-- avec le nombre de jours d'emprunt et un indicateur de retard.
-- Utilise julianday() pour calculer les durées.
SELECT
    l.Titre,
    e.Type,
    e.Date_ajout                                AS Debut,
    e.Date_prevu                                AS Retour_prevu,
    e.Date_rendu                                AS Retour_effectif,
    e.Statut,
    CASE
        WHEN e.Statut = 'rendu' AND e.Date_rendu IS NOT NULL
        THEN ROUND(julianday(e.Date_rendu) - julianday(e.Date_ajout))
        WHEN e.Statut IN ('en cours','retour_demande')
        THEN ROUND(julianday('now') - julianday(e.Date_ajout))
        ELSE NULL
    END                                         AS Jours_emprunt,
    CASE
        WHEN e.Statut = 'en cours' AND e.Date_prevu < date('now')
        THEN '⚠ EN RETARD de ' ||
             CAST(ROUND(julianday('now') - julianday(e.Date_prevu)) AS INTEGER) ||
             ' jour(s)'
        WHEN e.Statut = 'rendu' AND e.Date_rendu > e.Date_prevu
        THEN 'Rendu en retard'
        ELSE 'Dans les délais'
    END                                         AS Ponctualite
FROM Emprunt e
JOIN Livre l ON e.Code_13 = l.Code_13
WHERE e.ID_client = 1
ORDER BY e.Date_ajout DESC;


-- ── Liste de souhaits d'un client avec disponibilité ─────────────────────
-- Affiche la liste de souhaits du client en indiquant si le livre
-- est maintenant disponible (il peut venir l'emprunter).
-- Utilise une sous-requête corrélée pour vérifier la disponibilité.
SELECT
    l.Titre,
    l.Langue,
    l.Format,
    GROUP_CONCAT(a.Prenom || ' ' || a.Nom, ', ') AS Auteurs,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM Emprunt e2
            WHERE e2.Code_13 = l.Code_13
              AND e2.Type    = 'emprunt'
              AND e2.Statut  IN ('en cours','retour_demande')
        )
        THEN 'Indisponible — toujours en attente'
        ELSE '✓ Disponible — venez l''emprunter !'
    END                                           AS Disponibilite,
    e.Date_ajout                                  AS Souhait_depuis
FROM Emprunt e
JOIN Livre l        ON e.Code_13 = l.Code_13
LEFT JOIN Auteur_Livre al ON l.Code_13 = al.Code_13
LEFT JOIN Auteur a        ON al.ISNI    = a.ISNI
WHERE e.ID_client = 1
  AND e.Type      = 'souhait'
GROUP BY l.Code_13
ORDER BY e.Date_ajout;


-- ── Retards accumulés par un client ──────────────────────────────────────
-- Compte le nombre de fois qu'un client a rendu un livre en retard
-- et calcule le retard moyen en jours.
-- Utile pour l'administrateur qui décide de suspendre un compte.
SELECT
    c.Prenom || ' ' || c.Nom               AS Client,
    COUNT(*)                                AS Nb_retards,
    ROUND(AVG(
        julianday(e.Date_rendu) - julianday(e.Date_prevu)
    ))                                      AS Retard_moyen_jours,
    MAX(
        julianday(e.Date_rendu) - julianday(e.Date_prevu)
    )                                       AS Retard_max_jours
FROM Emprunt e
JOIN Client c ON e.ID_client = c.ID_client
WHERE e.Type       = 'emprunt'
  AND e.Statut     = 'rendu'
  AND e.Date_rendu > e.Date_prevu
  AND e.ID_client  = 1
GROUP BY c.ID_client;


-- ============================================================
--  2. RECHERCHE DE LIVRES
--  Requêtes déclenchées lors d'une recherche ou d'un scan.
-- ============================================================

-- ── Recherche par titre, auteur ou genre ──────────────────────────────────
-- Recherche partielle (LIKE) sur le titre, le nom de l'auteur et le genre.
-- Retourne la disponibilité de chaque résultat.
-- Simule la barre de recherche de l'interface client.
SELECT
    l.Code_13,
    l.Titre,
    GROUP_CONCAT(DISTINCT a.Prenom || ' ' || a.Nom) AS Auteurs,
    cl.Genre,
    cl.Section,
    me.Nom                                          AS Editeur,
    l.Annee_parution,
    ROUND(AVG(av.Note), 1)                          AS Note_moyenne,
    CASE
        WHEN COUNT(CASE WHEN e.Statut IN ('en cours','retour_demande') THEN 1 END) > 0
        THEN 'Indisponible'
        ELSE 'Disponible'
    END                                             AS Disponibilite
FROM Livre l
LEFT JOIN Auteur_Livre al  ON l.Code_13    = al.Code_13
LEFT JOIN Auteur a         ON al.ISNI      = a.ISNI
LEFT JOIN Classification cl ON l.Code_13   = cl.Code_13
LEFT JOIN Maison_edition me ON l.ID_edition = me.ID_edition
LEFT JOIN Avis av          ON l.Code_13    = av.Code_13
LEFT JOIN Emprunt e        ON l.Code_13    = e.Code_13 AND e.Type = 'emprunt'
WHERE l.Titre    LIKE '%étranger%'   -- mot-clé de recherche
   OR a.Nom      LIKE '%étranger%'
   OR cl.Genre   LIKE '%étranger%'
GROUP BY l.Code_13
ORDER BY Disponibilite, Note_moyenne DESC;


-- ── Fiche détaillée d'un livre par code barre ─────────────────────────────
-- Déclenché quand un client scanne un livre pour voir ses infos.
-- Regroupe toutes les données en une seule requête.
SELECT
    l.Code_13                                       AS ISBN,
    l.Titre,
    GROUP_CONCAT(DISTINCT a.Prenom || ' ' || a.Nom) AS Auteurs,
    me.Nom                                          AS Editeur,
    me.Collection,
    l.Annee_parution,
    l.Langue,
    l.Format,
    l.Nb_pages,
    cl.Genre,
    cl.Section,
    cl.Dewey,
    ROUND(AVG(av.Note), 1)                          AS Note_moyenne,
    COUNT(DISTINCT av.ID_avis)                      AS Nb_avis,
    CASE
        WHEN COUNT(CASE WHEN e.Statut IN ('en cours','retour_demande') THEN 1 END) > 0
        THEN 'Indisponible'
        ELSE 'Disponible'
    END                                             AS Disponibilite
FROM Livre l
LEFT JOIN Auteur_Livre al  ON l.Code_13     = al.Code_13
LEFT JOIN Auteur a         ON al.ISNI       = a.ISNI
LEFT JOIN Maison_edition me ON l.ID_edition = me.ID_edition
LEFT JOIN Classification cl ON l.Code_13    = cl.Code_13
LEFT JOIN Avis av           ON l.Code_13    = av.Code_13
LEFT JOIN Emprunt e         ON l.Code_13    = e.Code_13 AND e.Type = 'emprunt'
WHERE l.code_barre = '3ef635a5aea928c'   -- code scanné
GROUP BY l.Code_13;


-- ── Livres du même auteur ─────────────────────────────────────────────────
-- Quand un client consulte un livre, suggère d'autres livres
-- du même auteur présents dans le catalogue.
SELECT
    l.Titre,
    l.Annee_parution,
    l.Format,
    CASE
        WHEN COUNT(CASE WHEN e.Statut IN ('en cours','retour_demande') THEN 1 END) > 0
        THEN 'Indisponible' ELSE 'Disponible'
    END AS Disponibilite
FROM Livre l
JOIN Auteur_Livre al ON l.Code_13 = al.Code_13
JOIN Emprunt e       ON l.Code_13 = e.Code_13 AND e.Type = 'emprunt'
WHERE al.ISNI = 777888999        -- ISNI de Victor Hugo
  AND l.Code_13 != 9782253004226 -- exclure le livre consulté
GROUP BY l.Code_13;


-- ── Livres disponibles par genre ──────────────────────────────────────────
-- Utile pour la navigation par section en bibliothèque.
-- Retourne uniquement les livres disponibles, triés par note.
SELECT
    cl.Genre,
    cl.Section,
    l.Titre,
    GROUP_CONCAT(DISTINCT a.Prenom || ' ' || a.Nom) AS Auteurs,
    ROUND(AVG(av.Note), 1)                          AS Note_moyenne
FROM Livre l
JOIN Classification cl ON l.Code_13 = cl.Code_13
LEFT JOIN Auteur_Livre al ON l.Code_13 = al.Code_13
LEFT JOIN Auteur a        ON al.ISNI   = a.ISNI
LEFT JOIN Avis av         ON l.Code_13 = av.Code_13
WHERE NOT EXISTS (
    SELECT 1 FROM Emprunt e
    WHERE e.Code_13 = l.Code_13
      AND e.Type    = 'emprunt'
      AND e.Statut  IN ('en cours','retour_demande')
)
GROUP BY l.Code_13
ORDER BY cl.Genre, Note_moyenne DESC;


-- ============================================================
--  3. STATISTIQUES GLOBALES
--  Requêtes utilisées par le tableau de bord administrateur.
-- ============================================================

-- ── Tableau de bord global ────────────────────────────────────────────────
-- Vue d'ensemble de l'état actuel de la bibliothèque en une requête.
-- Utilise des sous-requêtes scalaires pour chaque indicateur.
SELECT
    (SELECT COUNT(*) FROM Livre)                    AS Total_livres,
    (SELECT COUNT(*) FROM Client)                   AS Total_clients,
    (SELECT COUNT(*) FROM Libraire)                 AS Total_libraires,
    (SELECT COUNT(*) FROM Emprunt
     WHERE Type = 'emprunt'
       AND Statut IN ('en cours','retour_demande'))  AS Emprunts_en_cours,
    (SELECT COUNT(*) FROM Emprunt
     WHERE Type = 'emprunt' AND Statut = 'retour_demande')
                                                    AS Retours_en_attente,
    (SELECT COUNT(*) FROM Emprunt
     WHERE Type = 'emprunt'
       AND Statut = 'en cours'
       AND Date_prevu < date('now'))                AS Emprunts_en_retard,
    (SELECT COUNT(*) FROM Livre WHERE Code_13 NOT IN (
         SELECT Code_13 FROM Emprunt
         WHERE Type = 'emprunt'
           AND Statut IN ('en cours','retour_demande')
    ))                                              AS Livres_disponibles;


-- ── Les livres les plus empruntés ─────────────────────────────────────────
-- Classement des livres par nombre total d'emprunts.
-- HAVING filtre les livres qui ont eu au moins 1 emprunt.
SELECT
    l.Titre,
    GROUP_CONCAT(DISTINCT a.Prenom || ' ' || a.Nom) AS Auteurs,
    cl.Genre,
    COUNT(e.ID_emprunt)                             AS Total_emprunts,
    ROUND(AVG(av.Note), 1)                          AS Note_moyenne
FROM Livre l
LEFT JOIN Emprunt      e  ON l.Code_13 = e.Code_13 AND e.Type = 'emprunt'
LEFT JOIN Auteur_Livre al ON l.Code_13 = al.Code_13
LEFT JOIN Auteur       a  ON al.ISNI   = a.ISNI
LEFT JOIN Classification cl ON l.Code_13 = cl.Code_13
LEFT JOIN Avis         av ON l.Code_13 = av.Code_13
GROUP BY l.Code_13
HAVING COUNT(e.ID_emprunt) >= 1
ORDER BY Total_emprunts DESC
LIMIT 10;


-- ── Les clients les plus actifs ───────────────────────────────────────────
-- Classement des clients par nombre d'emprunts totaux.
-- Inclut le nombre de retards pour identifier les mauvais payeurs.
SELECT
    c.Prenom || ' ' || c.Nom   AS Client,
    c.Date_inscription,
    COUNT(e.ID_emprunt)         AS Total_emprunts,
    COUNT(CASE WHEN e.Statut = 'rendu'
               AND e.Date_rendu > e.Date_prevu THEN 1 END)
                                AS Nb_retards,
    ROUND(AVG(av.Note), 1)     AS Note_moyenne_donnee
FROM Client c
LEFT JOIN Emprunt e ON c.ID_client = e.ID_client AND e.Type = 'emprunt'
LEFT JOIN Avis av   ON c.ID_client = av.ID_client
GROUP BY c.ID_client
ORDER BY Total_emprunts DESC;


-- ── Taux d'occupation de la bibliothèque ──────────────────────────────────
-- Pourcentage de livres actuellement empruntés.
-- Permet de mesurer l'utilisation du catalogue.
SELECT
    COUNT(*)                                        AS Total_livres,
    SUM(CASE
        WHEN l.Code_13 IN (
            SELECT Code_13 FROM Emprunt
            WHERE Type = 'emprunt'
              AND Statut IN ('en cours','retour_demande')
        ) THEN 1 ELSE 0
    END)                                            AS Livres_empruntes,
    ROUND(
        100.0 * SUM(CASE
            WHEN l.Code_13 IN (
                SELECT Code_13 FROM Emprunt
                WHERE Type = 'emprunt'
                  AND Statut IN ('en cours','retour_demande')
            ) THEN 1 ELSE 0
        END) / COUNT(*), 1
    )                                               AS Taux_occupation_pct
FROM Livre l;


-- ── Durée moyenne d'emprunt par genre ────────────────────────────────────
-- Analyse le comportement de lecture selon le genre littéraire.
-- Utilise julianday() pour calculer les durées en jours.
SELECT
    cl.Genre,
    COUNT(e.ID_emprunt)                             AS Nb_emprunts,
    ROUND(AVG(
        julianday(e.Date_rendu) - julianday(e.Date_ajout)
    ))                                              AS Duree_moyenne_jours,
    ROUND(MIN(
        julianday(e.Date_rendu) - julianday(e.Date_ajout)
    ))                                              AS Duree_min_jours,
    ROUND(MAX(
        julianday(e.Date_rendu) - julianday(e.Date_ajout)
    ))                                              AS Duree_max_jours
FROM Emprunt e
JOIN Livre l         ON e.Code_13 = l.Code_13
JOIN Classification cl ON l.Code_13 = cl.Code_13
WHERE e.Type      = 'emprunt'
  AND e.Statut    = 'rendu'
  AND e.Date_rendu IS NOT NULL
GROUP BY cl.Genre
HAVING COUNT(e.ID_emprunt) >= 1
ORDER BY Duree_moyenne_jours DESC;


-- ── Livres jamais empruntés ───────────────────────────────────────────────
-- Identifie les livres du catalogue qui n'ont jamais été empruntés.
-- Utile pour détecter les titres peu attractifs.
SELECT
    l.Titre,
    GROUP_CONCAT(DISTINCT a.Prenom || ' ' || a.Nom) AS Auteurs,
    cl.Genre,
    l.Annee_parution
FROM Livre l
LEFT JOIN Auteur_Livre al  ON l.Code_13 = al.Code_13
LEFT JOIN Auteur a         ON al.ISNI   = a.ISNI
LEFT JOIN Classification cl ON l.Code_13 = cl.Code_13
WHERE l.Code_13 NOT IN (
    SELECT DISTINCT Code_13 FROM Emprunt WHERE Type = 'emprunt'
)
GROUP BY l.Code_13
ORDER BY l.Annee_parution;


-- ── Évolution mensuelle des emprunts ──────────────────────────────────────
-- Compte le nombre d'emprunts par mois pour analyser la fréquentation.
-- Utilise strftime() pour extraire l'année et le mois de la date.
SELECT
    strftime('%Y-%m', e.Date_ajout)   AS Mois,
    COUNT(*)                          AS Nb_emprunts,
    COUNT(DISTINCT e.ID_client)       AS Clients_actifs
FROM Emprunt e
WHERE e.Type = 'emprunt'
GROUP BY strftime('%Y-%m', e.Date_ajout)
ORDER BY Mois DESC;


-- ── Clients avec emprunts en cours depuis plus de 25 jours ───────────────
-- Alerte préventive : ces clients approchent de la limite des 30 jours.
-- Utile pour le libraire afin d'anticiper les retards.
SELECT
    c.Prenom || ' ' || c.Nom         AS Client,
    c.Email,
    l.Titre,
    e.Date_ajout                      AS Emprunte_le,
    e.Date_prevu                      AS Retour_prevu,
    CAST(julianday('now') - julianday(e.Date_ajout) AS INTEGER)
                                      AS Jours_ecoules
FROM Emprunt e
JOIN Client c ON e.ID_client = c.ID_client
JOIN Livre  l ON e.Code_13   = l.Code_13
WHERE e.Type   = 'emprunt'
  AND e.Statut = 'en cours'
  AND julianday('now') - julianday(e.Date_ajout) > 25
ORDER BY Jours_ecoules DESC;


-- ============================================================
--  4. ANALYSE DU PERSONNEL
-- ============================================================

-- ── Activité de chaque libraire ───────────────────────────────────────────
-- Compte le nombre d'actions par type pour chaque libraire.
-- Permet à l'administrateur d'évaluer la productivité du personnel.
SELECT
    l.Prenom || ' ' || l.Nom          AS Libraire,
    l.Poste,
    l.Salaire,
    COUNT(lg.ID_log)                   AS Total_actions,
    COUNT(CASE WHEN lg.Action = 'ajout_livre'     THEN 1 END) AS Livres_ajoutes,
    COUNT(CASE WHEN lg.Action = 'retour_confirme' THEN 1 END) AS Retours_confirmes
FROM Libraire l
LEFT JOIN Log_action lg ON l.ID_libraire = lg.ID_libraire
GROUP BY l.ID_libraire
ORDER BY Total_actions DESC;


-- ── Dernières actions de chaque libraire ─────────────────────────────────
-- Affiche la dernière action enregistrée pour chaque libraire.
-- Utilise une CTE (WITH) pour isoler le calcul du MAX par libraire.
WITH DerniereAction AS (
    SELECT
        ID_libraire,
        MAX(Date_action) AS Derniere_date
    FROM Log_action
    GROUP BY ID_libraire
)
SELECT
    l.Prenom || ' ' || l.Nom     AS Libraire,
    l.Poste,
    lg.Action                    AS Derniere_action,
    lg.Detail,
    da.Derniere_date
FROM DerniereAction da
JOIN Libraire    l  ON da.ID_libraire = l.ID_libraire
JOIN Log_action  lg ON da.ID_libraire = lg.ID_libraire
                    AND da.Derniere_date = lg.Date_action
ORDER BY da.Derniere_date DESC;


-- ── Coût salarial total vs nombre de livres gérés ────────────────────────
-- Rapport coût/productivité du personnel.
SELECT
    SUM(l.Salaire)              AS Masse_salariale_mensuelle,
    COUNT(DISTINCT l.ID_libraire) AS Nb_libraires,
    COUNT(DISTINCT lg.ID_log)   AS Total_actions_enregistrees,
    ROUND(SUM(l.Salaire) /
          NULLIF(COUNT(DISTINCT lg.ID_log), 0), 2)
                                AS Cout_par_action
FROM Libraire l
LEFT JOIN Log_action lg ON l.ID_libraire = lg.ID_libraire;
