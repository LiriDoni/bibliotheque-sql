-- ============================================================
--  SYSTÈME DE GESTION DE BIBLIOTHÈQUE
--  seed.sql — Peuplement de la base de données
--
--  Provenance des données :
--  - Livres       : saisis manuellement, œuvres du domaine public
--                   ou livres célèbres avec métadonnées réelles
--  - Utilisateurs : créés manuellement pour les tests
--  - Emprunts     : simulés manuellement pour démonstration
--  - Avis         : rédigés manuellement pour simulation
--  - Codes barres : générés automatiquement par l'application
--                   (codes alphanumériques aléatoires 15 caractères)
--
--  Ordre d'insertion respecté pour les clés étrangères :
--  Admin → Libraire → Client → Maison_edition → Livre →
--  Auteur → Auteur_Livre → Classification → Emprunt → Avis → Log_action
-- ============================================================

PRAGMA foreign_keys = ON;


-- ============================================================
--  1. ADMINISTRATEURS
-- ============================================================

-- Compte super-admin créé manuellement pour les tests.
-- Mot de passe : 1234 (SHA-256)
INSERT INTO "Admin" (Nom, Prenom, Email, Mot_de_passe, code_barre, Date_inscription)
VALUES (
    'Admin', 'Super',
    'superadmin@biblio.com',
    '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4',
    '88e9ec0da7c101e',
    '2026-04-01'
);


-- ============================================================
--  2. LIBRAIRES
-- ============================================================

-- Libraire principal créé manuellement.
-- Mot de passe : 1234 (SHA-256)
INSERT INTO "Libraire" (Nom, Prenom, Email, Mot_de_passe, Poste, Salaire, code_barre, Date_inscription)
VALUES (
    'Bibliotheque', 'Admin',
    'admin@biblio.com',
    '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4',
    'Libraire', 1800.0,
    '4f39751e2c26491',
    '2026-04-01'
);


-- ============================================================
--  3. CLIENTS
-- ============================================================

-- Client de test créé manuellement.
-- Mot de passe : 1234 (SHA-256)
INSERT INTO "Client" (Nom, Prenom, Email, Mot_de_passe, Abonnement, code_barre, Date_inscription)
VALUES (
    'Dupont', 'Marie',
    'marie@email.com',
    '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4',
    10.0,
    'd193c1b59c32abd',
    '2026-04-01'
);


-- ============================================================
--  4. MAISONS D'ÉDITION
--  Données réelles des éditeurs, saisies manuellement.
-- ============================================================

INSERT INTO "Maison_edition" (Nom, Lieu, Collection) VALUES
    ('Gallimard',          'Paris', 'Folio'),
    ('Gallimard Jeunesse', 'Paris', 'Folio Junior'),
    ('Gallimard',          'Paris', 'Folio SF'),
    ('Robert Laffont',     'Paris', 'Ailleurs & Demain'),
    ('Le Livre de Poche',  'Paris', 'Classiques');
-- Note : Gallimard apparaît deux fois (Folio et Folio SF) car
-- ce sont deux collections distinctes avec des ID_edition différents.


-- ============================================================
--  5. LIVRES
--  Métadonnées réelles, ISBN-13 vérifiés, saisis manuellement.
--  Codes barres générés par l'application au premier lancement.
-- ============================================================

INSERT INTO "Livre" (Code_13, Titre, Annee_parution, Langue, Format, Nb_pages, ID_edition, code_barre)
VALUES
    -- L'Étranger — Albert Camus, Gallimard Folio
    (9782070360024, 'L''Étranger',      1942, 'Français', 'Poche',        159,  1, '3ef635a5aea928c'),
    -- Le Petit Prince — Antoine de Saint-Exupéry, Gallimard Jeunesse
    (9782070612758, 'Le Petit Prince',  1943, 'Français', 'Poche',         96,  2, 'c329afd6a5289f5'),
    -- 1984 — George Orwell, Gallimard Folio SF
    (9782070368228, '1984',             1949, 'Français', 'Poche',        438,  3, '0e4e0c4b7b04757'),
    -- Dune — Frank Herbert, Robert Laffont
    (9782221250051, 'Dune',             1965, 'Français', 'Grand format', 896,  4, '8b95d2d3cf79cd1'),
    -- Les Misérables — Victor Hugo, Le Livre de Poche
    (9782253004226, 'Les Misérables',   1862, 'Français', 'Poche',       1232,  5, 'f007b6b8b746841');


-- ============================================================
--  6. AUTEURS
--  Données réelles des auteurs, saisies manuellement.
--  ISNI : identifiants simplifiés pour les tests
--  (les ISNI réels sont des codes à 16 chiffres).
-- ============================================================

INSERT INTO "Auteur" (ISNI, Nom, Prenom, Nationalite, Role) VALUES
    (123456789, 'Camus',              'Albert',    'Française',    'Auteur'),
    (987654321, 'de Saint-Exupéry',   'Antoine',   'Française',    'Auteur'),
    (111222333, 'Orwell',             'George',    'Britannique',  'Auteur'),
    (444555666, 'Herbert',            'Frank',     'Américaine',   'Auteur'),
    (777888999, 'Hugo',               'Victor',    'Française',    'Auteur');


-- ============================================================
--  7. LIAISON AUTEUR ↔ LIVRE
-- ============================================================

INSERT INTO "Auteur_Livre" (ISNI, Code_13, Role) VALUES
    (123456789, 9782070360024, 'Auteur'),  -- Camus → L'Étranger
    (987654321, 9782070612758, 'Auteur'),  -- Saint-Exupéry → Le Petit Prince
    (111222333, 9782070368228, 'Auteur'),  -- Orwell → 1984
    (444555666, 9782221250051, 'Auteur'),  -- Herbert → Dune
    (777888999, 9782253004226, 'Auteur');  -- Hugo → Les Misérables


-- ============================================================
--  8. CLASSIFICATION
--  Indices Dewey réels, genres et sections saisis manuellement.
-- ============================================================

INSERT INTO "Classification" (Code_13, Dewey, Genre, Section) VALUES
    (9782070360024, 843.914, 'Roman',            'Littérature française'),
    (9782070612758, 843.912, 'Conte',             'Littérature française'),
    (9782070368228, 823.912, 'Roman dystopique',  'Littérature anglophone'),
    (9782221250051, 813.54,  'Science-fiction',   'Littérature anglophone'),
    (9782253004226, 843.8,   'Roman historique',  'Littérature française');


-- ============================================================
--  9. EMPRUNTS (simulés pour démonstration)
-- ============================================================

-- Marie emprunte L'Étranger — en cours
INSERT INTO "Emprunt" (ID_client, Code_13, Type, Date_prevu, Statut)
VALUES (1, 9782070360024, 'emprunt', '2026-05-01', 'en cours');

-- Marie emprunte Le Petit Prince — retourné
INSERT INTO "Emprunt" (ID_client, Code_13, Type, Date_prevu, Date_rendu, Statut)
VALUES (1, 9782070612758, 'emprunt', '2026-04-15', '2026-04-10', 'rendu');

-- Marie met Dune dans sa liste de souhaits
INSERT INTO "Emprunt" (ID_client, Code_13, Type, Statut)
VALUES (1, 9782221250051, 'souhait', 'en attente');


-- ============================================================
--  10. AVIS (rédigés manuellement pour simulation)
-- ============================================================

-- Marie note Le Petit Prince — livre déjà rendu donc avis possible
INSERT INTO "Avis" (ID_client, Code_13, Note, Commentaire)
VALUES (
    1, 9782070612758, 5,
    'Un classique indémodable, une lecture poétique et profonde. À lire absolument.'
);

-- Marie note L'Étranger
INSERT INTO "Avis" (ID_client, Code_13, Note, Commentaire)
VALUES (
    1, 9782070360024, 4,
    'Très bon livre, style minimaliste saisissant. Un peu court à mon goût.'
);


-- ============================================================
--  11. LOGS D'ACTION (simulés pour démonstration)
-- ============================================================

-- Le libraire a ajouté les 5 livres du catalogue
INSERT INTO "Log_action" (ID_libraire, Action, Detail, Date_action) VALUES
    (1, 'ajout_livre',      'L''Étranger (ISBN 9782070360024)',     '2026-04-01 09:00:00'),
    (1, 'ajout_livre',      'Le Petit Prince (ISBN 9782070612758)',  '2026-04-01 09:05:00'),
    (1, 'ajout_livre',      '1984 (ISBN 9782070368228)',             '2026-04-01 09:10:00'),
    (1, 'ajout_livre',      'Dune (ISBN 9782221250051)',             '2026-04-01 09:15:00'),
    (1, 'ajout_livre',      'Les Misérables (ISBN 9782253004226)',   '2026-04-01 09:20:00'),
    (1, 'retour_confirme',  'Le Petit Prince — client: Marie Dupont','2026-04-10 14:30:00');
