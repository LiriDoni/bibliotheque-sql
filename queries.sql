-- ============================================================
--  SYSTÈME DE GESTION DE BIBLIOTHÈQUE
--  queries.sql — Requêtes de manipulation quotidienne
--
--  Ce fichier simule les opérations courantes effectuées
--  par les trois types d'utilisateurs du système :
--  clients, libraires et administrateurs.
--
--  Sections :
--  1. Insertions
--  2. Mises à jour
--  3. Suppressions
--  4. Requêtes de consultation (SELECT utiles)
-- ============================================================

PRAGMA foreign_keys = ON;


-- ============================================================
--  1. INSERTIONS
-- ============================================================

-- ── Ajouter un nouveau client ─────────────────────────────────────────────
-- Opération déclenchée lorsqu'un nouveau lecteur s'inscrit à la bibliothèque.
-- Le code_barre est généré aléatoirement par l'application avant l'insertion.
-- Le mot de passe est hashé en SHA-256 côté application (ici : "motdepasse").
INSERT INTO "Client" (Nom, Prenom, Email, Mot_de_passe, Abonnement, code_barre)
VALUES (
    'Martin', 'Lucas',
    'lucas.martin@email.com',
    'e3b73f3f3c7a7d2e0b2e3f3a1c2d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d',
    10.0,
    'a1b2c3d4e5f6789'
);


-- ── Ajouter un nouveau libraire ───────────────────────────────────────────
-- Opération réservée à l'administrateur.
-- Le code_barre généré sera imprimé et remis au libraire comme badge.
INSERT INTO "Libraire" (Nom, Prenom, Email, Mot_de_passe, Poste, Salaire, code_barre)
VALUES (
    'Bernard', 'Sophie',
    'sophie.bernard@biblio.com',
    '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4',
    'Libraire', 1800.0,
    'z9y8x7w6v5u4t3s'
);


-- ── Ajouter un nouvel éditeur ─────────────────────────────────────────────
-- Nécessaire avant d'insérer un livre dont l'éditeur n'existe pas encore.
-- L'application vérifie d'abord si l'éditeur existe avant de l'insérer.
INSERT INTO "Maison_edition" (Nom, Lieu, Collection)
VALUES ('Flammarion', 'Paris', 'GF Flammarion');


-- ── Ajouter un nouveau livre ──────────────────────────────────────────────
-- Opération effectuée par le libraire via le formulaire d'ajout.
-- L'ISBN-13 est la clé primaire — il doit être unique.
-- Le code_barre est généré automatiquement par l'application.
INSERT INTO "Livre" (Code_13, Titre, Annee_parution, Langue, Format, Nb_pages, ID_edition, code_barre)
VALUES (
    9782081354098, 'Madame Bovary',
    1857, 'Français', 'Poche', 468,
    (SELECT ID_edition FROM Maison_edition WHERE Nom = 'Flammarion'),
    'b2c3d4e5f6a7891'
);
-- Note : la sous-requête récupère l'ID de l'éditeur par son nom,
-- ce qui évite de coder l'ID en dur.


-- ── Ajouter un auteur ─────────────────────────────────────────────────────
-- L'ISNI est l'identifiant international de l'auteur.
INSERT INTO "Auteur" (ISNI, Nom, Prenom, Nationalite, Role)
VALUES (222333444, 'Flaubert', 'Gustave', 'Française', 'Auteur');


-- ── Lier l'auteur au livre ────────────────────────────────────────────────
-- La table de jonction Auteur_Livre est nécessaire car la relation
-- entre auteurs et livres est de type N:N.
INSERT INTO "Auteur_Livre" (ISNI, Code_13, Role)
VALUES (222333444, 9782081354098, 'Auteur');


-- ── Ajouter la classification du livre ───────────────────────────────────
INSERT INTO "Classification" (Code_13, Dewey, Genre, Section)
VALUES (9782081354098, 843.8, 'Roman réaliste', 'Littérature française');


-- ── Emprunter un livre ────────────────────────────────────────────────────
-- Déclenché lorsqu'un client scanne un livre disponible.
-- Date_prevu = aujourd'hui + 30 jours (durée maximale d'emprunt).
-- Statut initial : 'en cours'.
INSERT INTO "Emprunt" (ID_client, Code_13, Type, Date_prevu, Statut)
VALUES (
    1,                    -- ID de Marie Dupont
    9782081354098,        -- Madame Bovary
    'emprunt',
    date('now', '+30 days'),
    'en cours'
);


-- ── Ajouter un livre à la liste de souhaits ───────────────────────────────
-- Le client peut souhaiter un livre indisponible.
-- Le Type est 'souhait' et le Statut 'en attente'.
INSERT INTO "Emprunt" (ID_client, Code_13, Type, Statut)
VALUES (1, 9782070368228, 'souhait', 'en attente');


-- ── Laisser un avis sur un livre ──────────────────────────────────────────
-- Un client ne peut laisser qu'un seul avis par livre
-- (contrainte UNIQUE sur ID_client + Code_13).
-- Ici Lucas Martin laisse un avis sur Madame Bovary.
INSERT INTO "Avis" (ID_client, Code_13, Note, Commentaire)
VALUES (
    (SELECT ID_client FROM Client WHERE Email = 'lucas.martin@email.com'),
    9782081354098,
    4,
    'Écriture magnifique, récit parfois lent mais très puissant.'
);


-- ── Enregistrer une action dans le journal ────────────────────────────────
-- Chaque action significative d'un libraire est tracée automatiquement.
INSERT INTO "Log_action" (ID_libraire, Action, Detail)
VALUES (
    1,
    'ajout_livre',
    'Madame Bovary (ISBN 9782081354098)'
);


-- ============================================================
--  2. MISES À JOUR
-- ============================================================

-- ── Demande de retour par le client ──────────────────────────────────────
-- Déclenché quand le client scanne un livre qu'il a emprunté.
-- Le statut passe à 'retour_demande' : le libraire doit confirmer.
UPDATE "Emprunt"
SET Statut = 'retour_demande'
WHERE ID_client = 1
  AND Code_13   = 9782070360024
  AND Type      = 'emprunt'
  AND Statut    = 'en cours';


-- ── Confirmer le retour par le libraire ──────────────────────────────────
-- Déclenché quand le libraire scanne le livre rapporté.
-- Date_rendu est enregistrée pour l'historique.
-- Le livre redevient disponible automatiquement (Statut = 'rendu').
UPDATE "Emprunt"
SET Statut     = 'rendu',
    Date_rendu = date('now')
WHERE Code_13  = 9782070360024
  AND Type     = 'emprunt'
  AND Statut   = 'retour_demande';


-- ── Prolonger un emprunt ─────────────────────────────────────────────────
-- Le libraire peut accorder une prolongation de 15 jours.
-- On ne prolonge que les emprunts en cours, pas ceux déjà en retard.
UPDATE "Emprunt"
SET Date_prevu = date(Date_prevu, '+15 days')
WHERE ID_emprunt = 1
  AND Statut     = 'en cours'
  AND Date_prevu >= date('now');   -- on ne prolonge pas un emprunt déjà en retard


-- ── Suspendre un client ───────────────────────────────────────────────────
-- L'administrateur peut bloquer un compte pour un nombre de jours défini.
-- Ici : suspension de 14 jours à partir d'aujourd'hui.
-- La vérification se fait côté application à la connexion.
UPDATE "Client"
SET timeout_jusqu_au = date('now', '+14 days')
WHERE ID_client = 1;


-- ── Lever la suspension d'un client ──────────────────────────────────────
-- Remet le champ à NULL pour réactiver le compte immédiatement.
UPDATE "Client"
SET timeout_jusqu_au = NULL
WHERE ID_client = 1;


-- ── Modifier le salaire d'un libraire ────────────────────────────────────
-- Opération réservée à l'administrateur, effectuée via l'édition inline.
UPDATE "Libraire"
SET Salaire = 1950.0
WHERE ID_libraire = 1;


-- ── Modifier le poste d'un libraire ──────────────────────────────────────
UPDATE "Libraire"
SET Poste = 'Responsable de section'
WHERE ID_libraire = 1;


-- ── Mettre à jour l'email d'un client ────────────────────────────────────
UPDATE "Client"
SET Email = 'marie.dupont@nouvelemail.com'
WHERE ID_client = 1;


-- ============================================================
--  3. SUPPRESSIONS
-- ============================================================

-- ── Retirer un livre du catalogue ────────────────────────────────────────
-- ON DELETE CASCADE est défini sur Auteur_Livre et Classification,
-- donc supprimer le livre supprime aussi ses entrées associées.
-- Les emprunts et avis liés sont également supprimés par CASCADE.
-- Attention : ne pas supprimer un livre actuellement emprunté.
DELETE FROM "Livre"
WHERE Code_13 = 9782081354098
  AND Code_13 NOT IN (
      SELECT Code_13 FROM Emprunt
      WHERE Type = 'emprunt' AND Statut IN ('en cours', 'retour_demande')
  );
-- La sous-requête protège contre la suppression accidentelle
-- d'un livre actuellement entre les mains d'un client.


-- ── Supprimer un libraire ─────────────────────────────────────────────────
-- Les logs de ce libraire sont conservés (ON DELETE SET NULL sur ID_libraire),
-- ce qui permet de garder la traçabilité des actions même après son départ.
DELETE FROM "Libraire"
WHERE ID_libraire = (SELECT ID_libraire FROM Libraire WHERE Email = 'sophie.bernard@biblio.com');


-- ── Supprimer un compte client ────────────────────────────────────────────
-- ON DELETE CASCADE supprime aussi ses emprunts et avis.
-- Ne pas supprimer un client avec des emprunts en cours.
DELETE FROM "Client"
WHERE ID_client = (SELECT ID_client FROM Client WHERE Email = 'lucas.martin@email.com')
  AND ID_client NOT IN (
      SELECT ID_client FROM Emprunt
      WHERE Type = 'emprunt' AND Statut IN ('en cours', 'retour_demande')
  );


-- ── Retirer un livre de la liste de souhaits ─────────────────────────────
-- Le client peut supprimer un souhait à tout moment.
DELETE FROM "Emprunt"
WHERE ID_client = 1
  AND Code_13   = 9782070368228
  AND Type      = 'souhait';


-- ── Supprimer un avis ────────────────────────────────────────────────────
-- Le libraire ou l'admin peut supprimer un commentaire inapproprié.
DELETE FROM "Avis"
WHERE ID_client = 1
  AND Code_13   = 9782070360024;


-- ============================================================
--  4. REQUÊTES DE CONSULTATION UTILES
-- ============================================================

-- ── Vérifier la disponibilité d'un livre ─────────────────────────────────
-- Utilisé avant chaque emprunt pour s'assurer que le livre est libre.
SELECT l.Titre,
       CASE WHEN COUNT(CASE WHEN e.Statut IN ('en cours','retour_demande') THEN 1 END) > 0
            THEN 'Indisponible'
            ELSE 'Disponible'
       END AS Disponibilite
FROM Livre l
LEFT JOIN Emprunt e ON l.Code_13 = e.Code_13 AND e.Type = 'emprunt'
WHERE l.Code_13 = 9782070360024
GROUP BY l.Code_13;


-- ── Lister les livres actuellement empruntés par un client ───────────────
-- Vérifie si le client a atteint la limite de 3 emprunts simultanés.
SELECT l.Titre, e.Date_ajout, e.Date_prevu, e.Statut
FROM Emprunt e
JOIN Livre l ON e.Code_13 = l.Code_13
WHERE e.ID_client = 1
  AND e.Type      = 'emprunt'
  AND e.Statut    IN ('en cours', 'retour_demande')
ORDER BY e.Date_ajout;


-- ── Lister tous les retours en attente de confirmation ───────────────────
-- Utilisé par le libraire pour voir quels livres doivent être traités.
SELECT e.ID_emprunt,
       c.Prenom || ' ' || c.Nom AS Client,
       l.Titre,
       e.Date_ajout AS Emprunte_le
FROM Emprunt e
JOIN Client c ON e.ID_client = c.ID_client
JOIN Livre  l ON e.Code_13   = l.Code_13
WHERE e.Type   = 'emprunt'
  AND e.Statut = 'retour_demande'
ORDER BY e.Date_ajout;


-- ── Lister les emprunts en retard ────────────────────────────────────────
-- Un emprunt est en retard si Date_prevu est dépassée et le livre
-- n'a pas encore été rendu.
SELECT c.Prenom || ' ' || c.Nom AS Client,
       c.Email,
       l.Titre,
       e.Date_prevu,
       julianday('now') - julianday(e.Date_prevu) AS Jours_de_retard
FROM Emprunt e
JOIN Client c ON e.ID_client = c.ID_client
JOIN Livre  l ON e.Code_13   = l.Code_13
WHERE e.Type      = 'emprunt'
  AND e.Statut    = 'en cours'
  AND e.Date_prevu < date('now')
ORDER BY Jours_de_retard DESC;


-- ── Note moyenne de chaque livre (au moins 1 avis) ───────────────────────
SELECT l.Titre,
       ROUND(AVG(a.Note), 1) AS Note_moyenne,
       COUNT(a.ID_avis)      AS Nombre_avis
FROM Livre l
JOIN Avis a ON l.Code_13 = a.Code_13
GROUP BY l.Code_13
HAVING COUNT(a.ID_avis) >= 1
ORDER BY Note_moyenne DESC;


-- ── Historique complet des actions d'un libraire ─────────────────────────
SELECT lg.Date_action,
       lg.Action,
       lg.Detail
FROM Log_action lg
WHERE lg.ID_libraire = 1
ORDER BY lg.Date_action DESC;


-- ── Clients avec le plus d'emprunts ──────────────────────────────────────
-- Utile pour identifier les clients les plus actifs.
SELECT c.Prenom || ' ' || c.Nom AS Client,
       COUNT(e.ID_emprunt)      AS Total_emprunts
FROM Client c
JOIN Emprunt e ON c.ID_client = e.ID_client
WHERE e.Type = 'emprunt'
GROUP BY c.ID_client
ORDER BY Total_emprunts DESC;
