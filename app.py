import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import os
import secrets
import string
import barcode
from barcode.writer import ImageWriter
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bibliotheque.db")
BC_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "barcodes")
os.makedirs(BC_DIR, exist_ok=True)

BG      = "#0f0f13"
SURFACE = "#1a1a24"
CARD    = "#22222f"
ACCENT  = "#7c6af7"
ACCENT2 = "#a78bfa"
TEXT    = "#e8e6f0"
MUTED   = "#7a788a"
SUCCESS = "#4ade80"
WARN    = "#f97316"
DANGER  = "#f87171"
BORDER  = "#2e2e3f"
GOLD    = "#fbbf24"
RED2    = "#ef4444"
TEAL    = "#2dd4bf"

FONT_TITLE = ("Georgia", 22, "bold")
FONT_HERO  = ("Georgia", 36, "bold")
FONT_SUB   = ("Georgia", 13, "italic")
FONT_LABEL = ("Courier New", 10, "bold")
FONT_BODY  = ("Courier New", 11)
FONT_SMALL = ("Courier New", 9)
FONT_BTN   = ("Courier New", 10, "bold")

MAX_BORROWS = 3
MAX_DAYS    = 30
ALPHABET    = string.ascii_lowercase + string.digits

# ── Barcode ───────────────────────────────────────────────────────────────────
def gen_code():
    return ''.join(secrets.choice(ALPHABET) for _ in range(15))

def make_barcode_png(code, filename):
    path = os.path.join(BC_DIR, filename)
    c128 = barcode.get("code128", code, writer=ImageWriter())
    return c128.save(path, options={
        "module_height": 15, "font_size": 8,
        "text_distance": 3, "quiet_zone": 4, "write_text": True})

def gen_user_barcode(role, uid, name, code):
    return make_barcode_png(code, f"{role}_{uid}_{name.replace(' ','_')}")

def gen_book_barcode(code, isbn, titre):
    safe = "".join(c for c in titre[:25] if c.isalnum() or c in " _-")
    return make_barcode_png(code, f"BK_{isbn}_{safe.replace(' ','_')}")

# ── DB ────────────────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def scan_login(code):
    code = code.strip()
    if len(code) != 15: return None, None
    conn = get_conn()
    for table, role in [("Admin","admin"),("Libraire","libraire"),("Client","client")]:
        row = conn.execute(f"SELECT * FROM {table} WHERE code_barre=?", (code,)).fetchone()
        if row:
            conn.close()
            return dict(row), role
    conn.close()
    return None, None

def scan_book(code):
    code = code.strip()
    if len(code) != 15: return None
    conn = get_conn()
    row = conn.execute("SELECT * FROM Livre WHERE code_barre=?", (code,)).fetchone()
    conn.close()
    return dict(row) if row else None

def unique_code_for_table(table):
    conn = get_conn()
    while True:
        c = gen_code()
        if not conn.execute(f"SELECT 1 FROM {table} WHERE code_barre=?", (c,)).fetchone():
            conn.close()
            return c

def is_timed_out(client):
    t = client.get("timeout_jusqu_au")
    if not t: return False, None
    try:
        end = date.fromisoformat(t)
        if date.today() <= end:
            return True, end.strftime("%d/%m/%Y")
    except Exception: pass
    return False, None

def log_action(libraire_id, action, detail=""):
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO Log_action (ID_libraire,Action,Detail) VALUES (?,?,?)",
            (libraire_id, action, detail))
        conn.commit(); conn.close()
    except Exception: pass

def count_pending_returns():
    """Count emprunts waiting for librarian confirmation."""
    try:
        conn = get_conn()
        n = conn.execute("""
            SELECT COUNT(*) FROM Emprunt
            WHERE Statut='retour_demande' AND Type='emprunt'
        """).fetchone()[0]
        conn.close()
        return n
    except Exception:
        return 0

# ── UI helpers ────────────────────────────────────────────────────────────────
def make_entry(parent, show=None):
    f = tk.Frame(parent, bg=SURFACE,
                 highlightbackground=BORDER, highlightthickness=1)
    e = tk.Entry(f, font=FONT_BODY, bg=SURFACE, fg=TEXT,
                 insertbackground=ACCENT2, relief="flat", bd=10, show=show)
    e.pack(fill="x")
    e.bind("<FocusIn>",  lambda _: f.config(highlightbackground=ACCENT))
    e.bind("<FocusOut>", lambda _: f.config(highlightbackground=BORDER))
    return f, e

def make_btn(parent, text, cmd, accent=True, danger=False, gold=False, red=False, teal=False):
    if red:      bg, hov, fg = RED2,   "#fca5a5", "#ffffff"
    elif danger: bg, hov, fg = DANGER, "#fca5a5", BG
    elif gold:   bg, hov, fg = GOLD,   "#fde68a", BG
    elif teal:   bg, hov, fg = TEAL,   "#99f6e4", BG
    elif accent: bg, hov, fg = ACCENT, ACCENT2,   "#ffffff"
    else:        bg, hov, fg = CARD,   BORDER,    ACCENT2
    b = tk.Button(parent, text=text, font=FONT_BTN,
                  bg=bg, fg=fg, activebackground=hov, activeforeground=fg,
                  relief="flat", bd=0, padx=14, pady=9, cursor="hand2", command=cmd)
    b.bind("<Enter>", lambda e: b.config(bg=hov))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b

def styled_table(parent, columns, heights=10):
    style = ttk.Style()
    style.theme_use("default")
    style.configure("L.Treeview",
                    background=SURFACE, foreground=TEXT,
                    fieldbackground=SURFACE, rowheight=28,
                    font=FONT_SMALL, borderwidth=0)
    style.configure("L.Treeview.Heading",
                    background=CARD, foreground=MUTED,
                    font=FONT_LABEL, relief="flat")
    style.map("L.Treeview",
              background=[("selected", ACCENT)],
              foreground=[("selected", "#ffffff")])
    tree = ttk.Treeview(parent, columns=columns, show="headings",
                        style="L.Treeview", height=heights)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="w", width=120)
    sb = tk.Scrollbar(parent, orient="vertical", command=tree.yview,
                      bg=SURFACE, troughcolor=SURFACE)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    return tree

def header_bar(parent, title, subtitle, color, name, on_logout):
    h = tk.Frame(parent, bg=BG)
    h.pack(fill="x", padx=32, pady=(20,0))
    tk.Label(h, text=title, font=FONT_TITLE, bg=BG, fg=color).pack(side="left")
    tk.Label(h, text=f"  {subtitle}", font=FONT_SUB,
             bg=BG, fg=MUTED).pack(side="left", pady=(6,0))
    uf = tk.Frame(h, bg=BG)
    uf.pack(side="right")
    tk.Label(uf, text=name, font=FONT_LABEL, bg=BG, fg=color).pack(side="left")
    make_btn(uf, "  DÉCONNEXION  ", on_logout,
             accent=False).pack(side="left", padx=(12,0))
    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=32, pady=12)


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN SCREEN
# ══════════════════════════════════════════════════════════════════════════════
class LoginScreen(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BG)
        self._build()

    def on_scan(self, code):
        self.indicator_var.set("")
        user, role = scan_login(code)
        if not user:
            self.msg_var.set("Code non reconnu. Essayez encore.")
            self.after(2000, lambda: self.msg_var.set(""))
            return
        if role == "client":
            timed_out, end_date = is_timed_out(user)
            if timed_out:
                self.msg_var.set(f"Compte suspendu jusqu'au {end_date}.")
                return
        self.master._on_login(user, role)

    def on_char(self, char):
        cur = self.indicator_var.get()
        self.indicator_var.set(cur + "▌" if len(cur) < 20 else "▌" * 20)

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(99, weight=1)

        card = tk.Frame(self, bg=CARD,
                        highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=1, column=0, padx=100, pady=50,
                  ipadx=60, ipady=50, sticky="nsew")
        card.columnconfigure(0, weight=1)

        tk.Label(card, text="BIBLIOTHÈQUE", font=FONT_HERO,
                 bg=CARD, fg=ACCENT2).pack(pady=(0,8))
        tk.Label(card, text="système de gestion", font=FONT_SUB,
                 bg=CARD, fg=MUTED).pack(pady=(0,32))
        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", pady=(0,32))

        tk.Label(card, text="▌▌▌", font=("Courier New", 48),
                 bg=CARD, fg=ACCENT).pack()
        tk.Label(card, text="Scannez votre code barre pour vous connecter",
                 font=("Georgia", 16), bg=CARD, fg=TEXT).pack(pady=(16,8))
        tk.Label(card, text="Présentez votre carte ou badge au lecteur",
                 font=FONT_SUB, bg=CARD, fg=MUTED).pack(pady=(0,24))

        self.indicator_var = tk.StringVar(value="")
        tk.Label(card, textvariable=self.indicator_var,
                 font=("Courier New", 20), bg=CARD, fg=ACCENT2,
                 width=22).pack(pady=(0,8))

        self.msg_var = tk.StringVar(value="")
        tk.Label(card, textvariable=self.msg_var,
                 font=FONT_BODY, bg=CARD, fg=DANGER).pack(pady=(0,8))

        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", pady=(16,16))
        make_btn(card, "＋  CRÉER UN COMPTE CLIENT",
                 self._open_register, accent=False).pack()

    def _open_register(self):
        win = tk.Toplevel(self, bg=BG)
        win.title("Créer un compte client")
        win.geometry("400x280")
        win.resizable(False, False)

        tk.Label(win, text="NOUVEAU CLIENT", font=FONT_TITLE,
                 bg=BG, fg=ACCENT2).pack(padx=24, pady=(24,4))
        tk.Label(win, text="Abonnement mensuel : 10,00 €",
                 font=FONT_SMALL, bg=ACCENT, fg="#ffffff",
                 padx=8, pady=4).pack(padx=24, anchor="w", pady=(8,16))

        f = tk.Frame(win, bg=BG)
        f.pack(fill="x", padx=24)
        row = tk.Frame(f, bg=BG)
        row.pack(fill="x", pady=(0,12))
        row.columnconfigure(0, weight=1); row.columnconfigure(1, weight=1)
        left = tk.Frame(row, bg=BG)
        left.grid(row=0, column=0, sticky="ew", padx=(0,6))
        tk.Label(left, text="NOM", font=FONT_LABEL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0,4))
        _, nom_e = make_entry(left)
        nom_e.master.pack(fill="x")
        right = tk.Frame(row, bg=BG)
        right.grid(row=0, column=1, sticky="ew", padx=(6,0))
        tk.Label(right, text="PRÉNOM", font=FONT_LABEL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0,4))
        _, prenom_e = make_entry(right)
        prenom_e.master.pack(fill="x")

        msg = tk.StringVar()
        tk.Label(win, textvariable=msg, font=FONT_SMALL, bg=BG, fg=DANGER).pack(pady=(8,0))

        def create():
            nom    = nom_e.get().strip()
            prenom = prenom_e.get().strip()
            if not nom or not prenom:
                msg.set("Nom et prénom sont obligatoires."); return
            code = unique_code_for_table("Client")
            try:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO Client (Nom,Prenom,Mot_de_passe,Abonnement,code_barre) VALUES (?,?,?,10.0,?)",
                    (nom, prenom, "", code))
                conn.commit()
                row = conn.execute("SELECT * FROM Client WHERE code_barre=?", (code,)).fetchone()
                conn.close()
                bc_path = gen_user_barcode("CLT", row["ID_client"], f"{prenom}_{nom}", code)
                win.destroy()
                messagebox.showinfo("Compte créé",
                    f"Compte créé pour {prenom} {nom}.\n"
                    f"Code barre sauvegardé :\n{bc_path}")
            except Exception as ex:
                msg.set(str(ex))

        make_btn(win, "CRÉER ET GÉNÉRER LE CODE BARRE →", create).pack(padx=24, pady=12, fill="x")


# ══════════════════════════════════════════════════════════════════════════════
# CLIENT SCREEN
# ══════════════════════════════════════════════════════════════════════════════
class LibraryScreen(tk.Frame):
    def __init__(self, master, client, on_logout):
        super().__init__(master, bg=BG)
        self.client         = client
        self.on_logout      = on_logout
        self.books          = []
        self._current_books = []
        self.selected_book  = None
        self._build()
        self._load_all()

    def on_char(self, char): pass

    def on_scan(self, code):
        book = scan_book(code)
        if not book:
            self.status_var.set("Code barre non reconnu.")
            self._flash(DANGER); return

        isbn      = book["Code_13"]
        client_id = self.client["ID_client"]
        try:
            conn = get_conn()
            # Check if this client currently has this book borrowed (en cours)
            existing = conn.execute("""
                SELECT ID_emprunt FROM Emprunt
                WHERE ID_client=? AND Code_13=? AND Type='emprunt' AND Statut='en cours'
            """, (client_id, isbn)).fetchone()

            if existing:
                # Mark as return requested — librarian must confirm
                conn.execute("""
                    UPDATE Emprunt SET Statut='retour_demande'
                    WHERE ID_emprunt=?
                """, (existing["ID_emprunt"],))
                conn.commit(); conn.close()
                self.status_var.set(
                    f"↩ « {book['Titre']} » — retour demandé. "
                    "Un libraire doit scanner le livre pour confirmer.")
                self._flash(TEAL)
            else:
                # Check if already requested
                pending = conn.execute("""
                    SELECT ID_emprunt FROM Emprunt
                    WHERE ID_client=? AND Code_13=? AND Type='emprunt' AND Statut='retour_demande'
                """, (client_id, isbn)).fetchone()
                if pending:
                    conn.close()
                    self.status_var.set(
                        f"⏳ Retour de « {book['Titre']} » déjà en attente de confirmation.")
                    self._flash(WARN); return

                # Borrow
                n = conn.execute("""
                    SELECT COUNT(*) FROM Emprunt
                    WHERE ID_client=? AND Type='emprunt' AND Statut='en cours'
                """, (client_id,)).fetchone()[0]
                if n >= MAX_BORROWS:
                    conn.close()
                    self.status_var.set(f"Limite de {MAX_BORROWS} livres atteinte.")
                    self._flash(DANGER); return
                taken = conn.execute("""
                    SELECT COUNT(*) FROM Emprunt
                    WHERE Code_13=? AND Type='emprunt' AND Statut='en cours'
                """, (isbn,)).fetchone()[0]
                if taken:
                    conn.close()
                    self.status_var.set(f"« {book['Titre']} » est déjà emprunté.")
                    self._flash(WARN); return
                conn.execute("""
                    INSERT INTO Emprunt (ID_client,Code_13,Type,Date_prevu,Statut)
                    VALUES (?,?,'emprunt',date('now','+30 days'),'en cours')
                """, (client_id, isbn))
                conn.commit(); conn.close()
                self.status_var.set(
                    f"📖 « {book['Titre']} » emprunté — retour dans {MAX_DAYS} jours.")
                self._flash(SUCCESS)
            self._load_all()
        except Exception as ex:
            self.status_var.set(str(ex))

    def _flash(self, color):
        lbl = getattr(self, "_status_lbl", None)
        if lbl:
            lbl.config(fg=color)
            self.after(2500, lambda: lbl.config(fg=MUTED))

    def _build(self):
        header_bar(self, "BIBLIOTHÈQUE", "espace client", ACCENT2,
                   f"{self.client.get('Prenom','')} {self.client.get('Nom','')}",
                   self.on_logout)
        abo = self.client.get("Abonnement", 10.0)
        tk.Label(self, text=f"  Abonnement : {abo:.2f} €/mois  ",
                 font=FONT_SMALL, bg=ACCENT, fg="#ffffff").pack(anchor="e", padx=32)
        self.counter_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.counter_var,
                 font=FONT_LABEL, bg=BG, fg=WARN).pack(anchor="e", padx=32)
        tk.Label(self,
                 text="▌▌ Scannez un livre pour emprunter  ·  Scannez à nouveau pour demander le retour",
                 font=FONT_SMALL, bg=SURFACE, fg=ACCENT2, pady=6).pack(fill="x", padx=32, pady=(0,8))

        sf = tk.Frame(self, bg=BG)
        sf.pack(fill="x", padx=32, pady=(0,12))
        tk.Label(sf, text="RECHERCHER UN LIVRE", font=FONT_LABEL,
                 bg=BG, fg=MUTED).pack(anchor="w")
        bar = tk.Frame(sf, bg=SURFACE,
                       highlightbackground=ACCENT, highlightthickness=1)
        bar.pack(fill="x", pady=(6,0))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)
        tk.Entry(bar, textvariable=self.search_var, font=FONT_BODY,
                 bg=SURFACE, fg=TEXT, insertbackground=ACCENT2,
                 relief="flat", bd=10).pack(side="left", fill="x", expand=True)
        tk.Label(bar, text="⌕", font=("Courier New",14),
                 bg=SURFACE, fg=MUTED).pack(side="right", padx=12)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(0,12))
        body.columnconfigure(0, weight=2); body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,12))
        tk.Label(left, text="RÉSULTATS", font=FONT_LABEL,
                 bg=BG, fg=MUTED).pack(anchor="w", pady=(0,6))
        lf = tk.Frame(left, bg=SURFACE,
                      highlightbackground=BORDER, highlightthickness=1)
        lf.pack(fill="both", expand=True)
        sb = tk.Scrollbar(lf, bg=SURFACE, troughcolor=SURFACE, activebackground=ACCENT)
        sb.pack(side="right", fill="y")
        self.listbox = tk.Listbox(lf, font=FONT_BODY, bg=SURFACE, fg=TEXT,
                                  selectbackground=ACCENT, selectforeground="#ffffff",
                                  activestyle="none", relief="flat", bd=0,
                                  yscrollcommand=sb.set, cursor="hand2")
        self.listbox.pack(fill="both", expand=True, padx=2)
        sb.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        tk.Label(right, text="DÉTAIL DU LIVRE", font=FONT_LABEL,
                 bg=BG, fg=MUTED).pack(anchor="w", pady=(0,6))
        self.detail_frame = tk.Frame(right, bg=CARD,
                                     highlightbackground=BORDER, highlightthickness=1)
        self.detail_frame.pack(fill="both", expand=True)
        self._show_placeholder()

        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", padx=32, pady=(0,6))
        make_btn(btn_row,"＋  LISTE DE SOUHAITS",self._add_wishlist).pack(side="left",padx=(0,8))
        make_btn(btn_row,"📖  EMPRUNTER",self._borrow).pack(side="left",padx=(0,8))
        make_btn(btn_row,"★  LAISSER UN AVIS",self._rate,accent=False).pack(side="left")

        self.status_var = tk.StringVar(value="Prêt — scannez un livre ou sélectionnez-en un.")
        self._status_lbl = tk.Label(self, textvariable=self.status_var,
                                    font=FONT_SMALL, bg=BG, fg=MUTED, anchor="w")
        self._status_lbl.pack(fill="x", padx=32, pady=(0,6))

    def _active_borrows(self):
        try:
            conn = get_conn()
            n = conn.execute("""
                SELECT COUNT(*) FROM Emprunt
                WHERE ID_client=? AND Type='emprunt' AND Statut IN ('en cours','retour_demande')
            """, (self.client["ID_client"],)).fetchone()[0]
            conn.close(); return n
        except Exception: return 0

    def _load_all(self):
        try:
            conn = get_conn()
            rows = conn.execute("""
                SELECT l.Code_13, l.Titre, l.Annee_parution, l.Langue,
                       l.Format, l.Nb_pages,
                       me.Nom AS Editeur, me.Collection,
                       cl.Dewey, cl.Genre, cl.Section,
                       GROUP_CONCAT(DISTINCT a.Prenom||' '||a.Nom) AS Auteurs,
                       ROUND(AVG(av.Note),1) AS Note_moy,
                       COUNT(DISTINCT av.ID_avis) AS Nb_avis,
                       CASE WHEN COUNT(CASE WHEN e.Statut IN ('en cours','retour_demande') THEN 1 END)>0
                            THEN 'Indisponible' ELSE 'Disponible' END AS Dispo
                FROM Livre l
                LEFT JOIN Maison_edition me ON l.ID_edition=me.ID_edition
                LEFT JOIN Classification cl ON l.Code_13=cl.Code_13
                LEFT JOIN Auteur_Livre al   ON l.Code_13=al.Code_13
                LEFT JOIN Auteur a          ON al.ISNI=a.ISNI
                LEFT JOIN Avis av           ON l.Code_13=av.Code_13
                LEFT JOIN Emprunt e         ON l.Code_13=e.Code_13 AND e.Type='emprunt'
                GROUP BY l.Code_13 ORDER BY l.Titre
            """).fetchall()
            conn.close()
            self.books = [dict(r) for r in rows]
            self._current_books = self.books
            self._refresh_list(self.books)
            n = self._active_borrows()
            self.counter_var.set(f"📚 {n}/{MAX_BORROWS} livres empruntés" if n > 0 else "")
        except Exception as ex:
            messagebox.showerror("Erreur DB", str(ex))

    def _refresh_list(self, books):
        self.listbox.delete(0,"end")
        for b in books:
            mark = "●" if b["Dispo"]=="Disponible" else "○"
            self.listbox.insert("end", f"  {mark}  {b['Titre']}")
        for i,b in enumerate(books):
            self.listbox.itemconfig(i, fg=SUCCESS if b["Dispo"]=="Disponible" else WARN)

    def _on_search(self, *_):
        q = self.search_var.get().lower()
        filtered = [b for b in self.books
                    if q in (b["Titre"] or "").lower()
                    or q in (b["Auteurs"] or "").lower()
                    or q in (b["Genre"] or "").lower()]
        self._current_books = filtered
        self._refresh_list(filtered)

    def _on_select(self, _):
        sel = self.listbox.curselection()
        if not sel: return
        idx = sel[0]
        if idx >= len(self._current_books): return
        self.selected_book = self._current_books[idx]
        self._show_detail(self.selected_book)

    def _show_placeholder(self):
        for w in self.detail_frame.winfo_children(): w.destroy()
        tk.Label(self.detail_frame, text="← Sélectionnez un livre",
                 font=FONT_SUB, bg=CARD, fg=MUTED).pack(expand=True)

    def _field(self, parent, label, value, row):
        tk.Label(parent, text=label, font=FONT_LABEL,
                 bg=CARD, fg=MUTED, anchor="w").grid(
                 row=row, column=0, sticky="w", padx=18, pady=(8,0))
        tk.Label(parent, text=value or "—", font=FONT_BODY,
                 bg=CARD, fg=TEXT, anchor="w",
                 wraplength=280, justify="left").grid(
                 row=row+1, column=0, sticky="w", padx=18, pady=(2,0))

    def _show_detail(self, b):
        for w in self.detail_frame.winfo_children(): w.destroy()
        self.detail_frame.columnconfigure(0, weight=1)
        tk.Label(self.detail_frame, text=b["Titre"],
                 font=("Georgia",15,"bold"), bg=CARD, fg=ACCENT2,
                 wraplength=300, justify="left").grid(
                 row=0, column=0, sticky="w", padx=18, pady=(18,4))
        dispo_c = SUCCESS if b["Dispo"]=="Disponible" else WARN
        tk.Label(self.detail_frame, text=f"  {b['Dispo']}  ",
                 font=FONT_SMALL, bg=dispo_c, fg=BG).grid(
                 row=1, column=0, sticky="w", padx=18, pady=(0,8))
        fields = [
            ("AUTEUR(S)",       b["Auteurs"]),
            ("ÉDITEUR",         f"{b['Editeur'] or '—'}  ·  {b['Collection'] or ''}"),
            ("ANNÉE",           str(b["Annee_parution"] or "—")),
            ("GENRE",           b["Genre"]),
            ("DEWEY / SECTION", f"{b['Dewey'] or '—'}  ·  {b['Section'] or '—'}"),
            ("FORMAT",          f"{b['Format'] or '—'}  ·  {b['Nb_pages'] or '—'} pages"),
            ("LANGUE",          b["Langue"]),
            ("NOTE MOYENNE",    f"{'★'*int(b['Note_moy'] or 0)}  {b['Note_moy'] or 'Aucun avis'}  ({b['Nb_avis']} avis)"),
        ]
        for i,(lbl,val) in enumerate(fields):
            self._field(self.detail_frame, lbl, val, row=2+i*2)
        tk.Label(self.detail_frame, text=f"ISBN-13 : {b['Code_13']}",
                 font=FONT_SMALL, bg=CARD, fg=MUTED).grid(
                 row=2+len(fields)*2+1, column=0, sticky="w", padx=18, pady=(12,18))

    def _require_selection(self):
        if not self.selected_book:
            messagebox.showwarning("Attention","Sélectionnez d'abord un livre.")
            return False
        return True

    def _add_wishlist(self):
        if not self._require_selection(): return
        try:
            conn = get_conn()
            conn.execute(
                "INSERT INTO Emprunt (ID_client,Code_13,Type,Statut) VALUES (?,?,'souhait','en attente')",
                (self.client["ID_client"], self.selected_book["Code_13"]))
            conn.commit(); conn.close()
            self.status_var.set(f"« {self.selected_book['Titre']} » ajouté à votre liste de souhaits.")
        except sqlite3.IntegrityError:
            self.status_var.set("Ce livre est déjà dans votre liste.")
        except Exception as ex:
            messagebox.showerror("Erreur", str(ex))

    def _borrow(self):
        if not self._require_selection(): return
        n = self._active_borrows()
        if n >= MAX_BORROWS:
            messagebox.showwarning("Limite atteinte",
                f"Vous avez déjà {MAX_BORROWS} livres empruntés.")
            return
        if self.selected_book["Dispo"] == "Indisponible":
            if messagebox.askyesno("Indisponible",
                "Ce livre est déjà emprunté.\nL'ajouter à votre liste de souhaits ?"):
                self._add_wishlist()
            return
        try:
            conn = get_conn()
            conn.execute("""
                INSERT INTO Emprunt (ID_client,Code_13,Type,Date_prevu,Statut)
                VALUES (?,?,'emprunt',date('now','+30 days'),'en cours')
            """, (self.client["ID_client"], self.selected_book["Code_13"]))
            conn.commit(); conn.close()
            self.status_var.set(
                f"« {self.selected_book['Titre']} » emprunté — retour dans {MAX_DAYS} jours.")
            self._load_all(); self._show_detail(self.selected_book)
        except Exception as ex:
            messagebox.showerror("Erreur", str(ex))

    def _rate(self):
        if not self._require_selection(): return
        win = tk.Toplevel(self, bg=BG)
        win.title("Laisser un avis")
        win.geometry("360x300")
        win.resizable(False, False)
        tk.Label(win, text=self.selected_book["Titre"],
                 font=("Georgia",12,"bold"), bg=BG, fg=ACCENT2,
                 wraplength=300).pack(padx=24, pady=(20,16))
        tk.Label(win, text="NOTE", font=FONT_LABEL, bg=BG, fg=MUTED).pack(anchor="w", padx=24)
        note_var = tk.IntVar(value=5)
        stars = tk.Frame(win, bg=BG)
        stars.pack(anchor="w", padx=24, pady=(4,14))
        for n in range(1,6):
            tk.Radiobutton(stars, text=f"{'★'*n}", variable=note_var,
                           value=n, font=FONT_BODY, bg=BG, fg=ACCENT2,
                           selectcolor=BG, activebackground=BG).pack(side="left")
        tk.Label(win, text="COMMENTAIRE", font=FONT_LABEL, bg=BG, fg=MUTED).pack(anchor="w", padx=24)
        comment = tk.Text(win, font=FONT_SMALL, bg=SURFACE, fg=TEXT,
                          insertbackground=ACCENT2, relief="flat", bd=8, height=4)
        comment.pack(fill="x", padx=24, pady=(4,14))
        msg = tk.StringVar()
        tk.Label(win, textvariable=msg, font=FONT_SMALL, bg=BG, fg=DANGER).pack()
        def submit():
            try:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO Avis (ID_client,Code_13,Note,Commentaire) VALUES (?,?,?,?)",
                    (self.client["ID_client"], self.selected_book["Code_13"],
                     note_var.get(), comment.get("1.0","end").strip()))
                conn.commit(); conn.close()
                self.status_var.set("Avis enregistré.")
                win.destroy(); self._load_all(); self._show_detail(self.selected_book)
            except sqlite3.IntegrityError:
                msg.set("Vous avez déjà laissé un avis pour ce livre.")
            except Exception as ex:
                msg.set(str(ex))
        make_btn(win, "ENVOYER →", submit).pack(pady=(0,16))


# ══════════════════════════════════════════════════════════════════════════════
# LIBRAIRE SCREEN
# ══════════════════════════════════════════════════════════════════════════════
class LibraireScreen(tk.Frame):
    def __init__(self, master, libraire, on_logout):
        super().__init__(master, bg=BG)
        self.libraire  = libraire
        self.on_logout = on_logout
        self._build()
        # Start polling for pending returns
        self._poll_returns()

    def on_char(self, char): pass

    def on_scan(self, code):
        """Librarian scans a book to confirm its return."""
        book = scan_book(code)
        if not book:
            self.status_var.set("Code barre non reconnu.")
            return
        isbn = book["Code_13"]
        try:
            conn = get_conn()
            pending = conn.execute("""
                SELECT e.ID_emprunt, c.Prenom||' '||c.Nom AS client
                FROM Emprunt e
                JOIN Client c ON e.ID_client=c.ID_client
                WHERE e.Code_13=? AND e.Type='emprunt' AND e.Statut='retour_demande'
            """, (isbn,)).fetchone()

            if not pending:
                conn.close()
                self.status_var.set(
                    f"« {book['Titre']} » — aucun retour en attente pour ce livre.")
                return

            conn.execute("""
                UPDATE Emprunt SET Statut='rendu', Date_rendu=date('now')
                WHERE ID_emprunt=?
            """, (pending["ID_emprunt"],))
            conn.commit(); conn.close()
            log_action(self.libraire["ID_libraire"], "retour_confirme",
                       f"{book['Titre']} — client: {pending['client']}")
            self.status_var.set(
                f"✓ Retour confirmé : « {book['Titre']} » de {pending['client']}.")
            # Flash status green
            self._status_lbl.config(fg=SUCCESS)
            self.after(2500, lambda: self._status_lbl.config(fg=MUTED))
            self._update_notification()
            # Reload borrows if on that tab
            if self.tab_var.get() == "retours":
                self._reload_pending()
            elif self.tab_var.get() == "emprunts":
                self._reload_borrows()
        except Exception as ex:
            self.status_var.set(str(ex))

    def _poll_returns(self):
        """Check for pending returns every 5 seconds and update badge."""
        self._update_notification()
        self.after(5000, self._poll_returns)

    def _update_notification(self):
        n = count_pending_returns()
        if n > 0:
            self._notif_var.set(f"  ↩ {n} retour(s) en attente  ")
            self._notif_lbl.config(bg=TEAL, fg=BG)
        else:
            self._notif_var.set("")
            self._notif_lbl.config(bg=BG, fg=BG)
        # Update tab label
        if hasattr(self, "_tab_btns"):
            label = f"↩  RETOURS ({n})" if n > 0 else "↩  RETOURS"
            self._tab_btns["retours"].config(text=label,
                bg=TEAL if n > 0 and self.tab_var.get() != "retours" else
                   (GOLD if self.tab_var.get() == "retours" else CARD))

    def _build(self):
        header_bar(self, "BIBLIOTHÈQUE", "espace libraire", GOLD,
                   f"{self.libraire.get('Prenom','')} {self.libraire.get('Nom','')}",
                   self.on_logout)
        poste   = self.libraire.get("Poste","Libraire")
        salaire = self.libraire.get("Salaire", 1800.0)
        tk.Label(self, text=f"  {poste}  ·  {salaire:.2f} €/mois  ",
                 font=FONT_SMALL, bg=GOLD, fg=BG).pack(anchor="e", padx=32)

        # Notification banner
        self._notif_var = tk.StringVar(value="")
        self._notif_lbl = tk.Label(self, textvariable=self._notif_var,
                                   font=("Courier New",10,"bold"),
                                   bg=BG, fg=BG, pady=4)
        self._notif_lbl.pack(fill="x", padx=32, pady=(0,4))

        # Scan hint for librarian
        tk.Label(self,
                 text="▌▌ Scannez un livre pour confirmer un retour",
                 font=FONT_SMALL, bg=SURFACE, fg=GOLD, pady=4).pack(fill="x", padx=32, pady=(0,8))

        tabs = tk.Frame(self, bg=BG)
        tabs.pack(fill="x", padx=32, pady=(0,16))
        self.tab_var   = tk.StringVar(value="ajouter")
        self._tab_btns = {}
        for label, key in [("＋  AJOUTER UN LIVRE","ajouter"),
                            ("↩  RETOURS","retours"),
                            ("📋  EMPRUNTS","emprunts"),
                            ("👥  CLIENTS","clients")]:
            b = tk.Radiobutton(tabs, text=label, variable=self.tab_var,
                               value=key, font=FONT_BTN,
                               bg=CARD, fg=MUTED, selectcolor=BG,
                               activebackground=BG, indicatoron=False,
                               relief="flat", padx=14, pady=8,
                               cursor="hand2", command=self._switch_tab)
            b.pack(side="left", padx=(0,4))
            self._tab_btns[key] = b
        self._update_tabs()

        self.content = tk.Frame(self, bg=BG)
        self.content.pack(fill="both", expand=True, padx=32)
        self.status_var = tk.StringVar(value="Prêt — scannez un livre pour confirmer un retour.")
        self._status_lbl = tk.Label(self, textvariable=self.status_var,
                                    font=FONT_SMALL, bg=BG, fg=MUTED, anchor="w")
        self._status_lbl.pack(fill="x", padx=32, pady=(4,8))
        self._show_add_book()

    def _update_tabs(self):
        current = self.tab_var.get()
        n = count_pending_returns()
        for key, btn in self._tab_btns.items():
            if key == "retours":
                active = current == "retours"
                btn.config(bg=GOLD if active else (TEAL if n > 0 else CARD),
                           fg=BG   if active or n > 0 else MUTED)
            else:
                btn.config(bg=GOLD if key==current else CARD,
                           fg=BG   if key==current else MUTED)

    def _switch_tab(self):
        self._update_tabs()
        for w in self.content.winfo_children(): w.destroy()
        tab = self.tab_var.get()
        if tab == "ajouter":   self._show_add_book()
        elif tab == "retours": self._show_pending_returns()
        elif tab == "emprunts":self._show_borrows()
        elif tab == "clients": self._show_clients()

    # ── Pending returns tab ───────────────────────────────────────────────────
    def _show_pending_returns(self):
        c = self.content

        # Big instruction banner
        banner = tk.Frame(c, bg=TEAL)
        banner.pack(fill="x", pady=(0,16), ipadx=16, ipady=12)
        tk.Label(banner,
                 text="▌▌  Scannez le code barre du livre pour confirmer le retour",
                 font=("Courier New",11,"bold"), bg=TEAL, fg=BG).pack()

        tf = tk.Frame(c, bg=BG)
        tf.pack(fill="both", expand=True)
        self.pending_tree = styled_table(tf,
            ("ID","Client","Livre","Emprunté le","Retour demandé le"), heights=12)
        self.pending_tree.column("ID",               width=40,  anchor="center")
        self.pending_tree.column("Client",           width=160)
        self.pending_tree.column("Livre",            width=220)
        self.pending_tree.column("Emprunté le",      width=110)
        self.pending_tree.column("Retour demandé le",width=130)
        self._reload_pending()

        btn_row = tk.Frame(c, bg=BG)
        btn_row.pack(fill="x", pady=(10,0))
        make_btn(btn_row,"✓  CONFIRMER SANS SCANNER",
                 self._confirm_return_manual, teal=True).pack(side="left")
        make_btn(btn_row,"  RAFRAÎCHIR",
                 self._reload_pending, accent=False).pack(side="left", padx=(8,0))

    def _reload_pending(self):
        if not hasattr(self,"pending_tree"): return
        for row in self.pending_tree.get_children(): self.pending_tree.delete(row)
        try:
            conn = get_conn()
            rows = conn.execute("""
                SELECT e.ID_emprunt,
                       c.Prenom||' '||c.Nom AS client,
                       l.Titre,
                       e.Date_ajout,
                       date('now') AS date_demande
                FROM Emprunt e
                JOIN Client c ON e.ID_client=c.ID_client
                JOIN Livre  l ON e.Code_13=l.Code_13
                WHERE e.Type='emprunt' AND e.Statut='retour_demande'
                ORDER BY e.Date_ajout
            """).fetchall()
            conn.close()
            for r in rows:
                self.pending_tree.insert("","end", values=tuple(r))
            n = len(rows)
            self.status_var.set(
                f"{n} retour(s) en attente de confirmation." if n > 0
                else "Aucun retour en attente.")
            self._update_notification()
        except Exception as ex:
            self.status_var.set(str(ex))

    def _confirm_return_manual(self):
        """Confirm return by selecting a row (fallback if scanner unavailable)."""
        sel = self.pending_tree.selection()
        if not sel:
            messagebox.showwarning("Attention",
                "Sélectionnez un retour ou scannez le livre."); return
        item   = self.pending_tree.item(sel[0])
        emp_id = item["values"][0]
        titre  = item["values"][2]
        client = item["values"][1]
        if not messagebox.askyesno("Confirmer",
            f"Confirmer le retour de « {titre} » par {client} ?"): return
        try:
            conn = get_conn()
            conn.execute(
                "UPDATE Emprunt SET Statut='rendu',Date_rendu=date('now') WHERE ID_emprunt=?",
                (emp_id,))
            conn.commit(); conn.close()
            log_action(self.libraire["ID_libraire"],"retour_confirme",
                       f"{titre} — client: {client}")
            self.status_var.set(f"✓ Retour confirmé : « {titre} ».")
            self._reload_pending()
        except Exception as ex:
            self.status_var.set(str(ex))

    # ── Add book tab ──────────────────────────────────────────────────────────
    def _show_add_book(self):
        c = self.content
        canvas = tk.Canvas(c, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(c, orient="vertical", command=canvas.yview,
                          bg=SURFACE, troughcolor=SURFACE)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        form = tk.Frame(canvas, bg=BG)
        wid = canvas.create_window((0,0), window=form, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(wid, width=e.width))
        form.bind("<Configure>",   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def section(txt):
            tk.Label(form, text=txt, font=("Courier New",11,"bold"),
                     bg=BG, fg=GOLD).pack(anchor="w", pady=(0,6))
            tk.Frame(form, bg=BORDER, height=1).pack(fill="x", pady=(0,12))

        def grid_row(items):
            r = tk.Frame(form, bg=BG)
            r.pack(fill="x", pady=(0,4))
            for i in range(len(items)): r.columnconfigure(i, weight=1)
            for i,(lbl,attr) in enumerate(items):
                col = tk.Frame(r, bg=BG)
                col.grid(row=0, column=i, sticky="ew",
                         padx=(0,10) if i<len(items)-1 else 0)
                tk.Label(col, text=lbl, font=FONT_LABEL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0,4))
                _, e = make_entry(col)
                e.master.pack(fill="x", pady=(0,12))
                setattr(self, attr, e)

        section("INFORMATIONS DU LIVRE")
        rr = tk.Frame(form, bg=BG)
        rr.pack(fill="x", pady=(0,4))
        rr.columnconfigure(0, weight=3); rr.columnconfigure(1, weight=1)
        lc = tk.Frame(rr, bg=BG)
        lc.grid(row=0, column=0, sticky="ew", padx=(0,10))
        tk.Label(lc, text="TITRE", font=FONT_LABEL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0,4))
        _, self.f_titre = make_entry(lc)
        self.f_titre.master.pack(fill="x", pady=(0,12))
        rc = tk.Frame(rr, bg=BG)
        rc.grid(row=0, column=1, sticky="ew")
        tk.Label(rc, text="ISBN-13", font=FONT_LABEL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0,4))
        _, self.f_isbn = make_entry(rc)
        self.f_isbn.master.pack(fill="x", pady=(0,12))
        grid_row([("ANNÉE","f_annee"),("LANGUE","f_langue"),("FORMAT","f_format"),("NB PAGES","f_pages")])
        section("MAISON D'ÉDITION")
        grid_row([("NOM ÉDITEUR","f_editeur"),("LIEU","f_lieu"),("COLLECTION","f_collection")])
        section("AUTEUR")
        grid_row([("NOM","f_a_nom"),("PRÉNOM","f_a_prenom"),("NATIONALITÉ","f_a_nat"),("ISNI","f_a_isni")])
        section("CLASSIFICATION")
        grid_row([("GENRE","f_genre"),("SECTION","f_section"),("DEWEY","f_dewey")])

        self.form_msg = tk.StringVar()
        tk.Label(form, textvariable=self.form_msg, font=FONT_SMALL,
                 bg=BG, fg=DANGER).pack(anchor="w", pady=(4,0))
        make_btn(form, "💾  ENREGISTRER + GÉNÉRER CODE BARRE",
                 self._save_book, gold=True).pack(anchor="w", pady=(8,24))

    def _save_book(self):
        isbn=self.f_isbn.get().strip(); titre=self.f_titre.get().strip()
        if not isbn or not titre:
            self.form_msg.set("ISBN et titre sont obligatoires."); return
        if not isbn.isdigit():
            self.form_msg.set("L'ISBN doit être numérique."); return
        annee=self.f_annee.get().strip(); langue=self.f_langue.get().strip()
        fmt=self.f_format.get().strip(); pages=self.f_pages.get().strip()
        editeur=self.f_editeur.get().strip(); lieu=self.f_lieu.get().strip()
        coll=self.f_collection.get().strip()
        a_nom=self.f_a_nom.get().strip(); a_prenom=self.f_a_prenom.get().strip()
        a_nat=self.f_a_nat.get().strip(); a_isni=self.f_a_isni.get().strip()
        genre=self.f_genre.get().strip(); sect=self.f_section.get().strip()
        dewey=self.f_dewey.get().strip()
        try:
            code = unique_code_for_table("Livre")
            conn = get_conn()
            ep = conn.execute("SELECT ID_edition FROM Maison_edition WHERE Nom=?",(editeur,)).fetchone()
            id_ed = ep["ID_edition"] if ep else \
                conn.execute("INSERT INTO Maison_edition (Nom,Lieu,Collection) VALUES (?,?,?)",
                             (editeur or None,lieu or None,coll or None)).lastrowid
            conn.execute("""
                INSERT INTO Livre (Code_13,Titre,Annee_parution,Langue,Format,Nb_pages,ID_edition,code_barre)
                VALUES (?,?,?,?,?,?,?,?)
            """, (int(isbn),titre,
                  int(annee) if annee.isdigit() else None,
                  langue or None,fmt or None,
                  int(pages) if pages.isdigit() else None, id_ed, code))
            if a_isni and a_isni.isdigit():
                if not conn.execute("SELECT 1 FROM Auteur WHERE ISNI=?",(int(a_isni),)).fetchone():
                    conn.execute(
                        "INSERT INTO Auteur (ISNI,Nom,Prenom,Nationalite,Role) VALUES (?,?,?,?,'Auteur')",
                        (int(a_isni),a_nom or None,a_prenom or None,a_nat or None))
                conn.execute("INSERT INTO Auteur_Livre (ISNI,Code_13,Role) VALUES (?,?,'Auteur')",
                             (int(a_isni),int(isbn)))
            if genre or sect or dewey:
                conn.execute(
                    "INSERT INTO Classification (Code_13,Dewey,Genre,Section) VALUES (?,?,?,?)",
                    (int(isbn),float(dewey) if dewey else None,genre or None,sect or None))
            conn.commit(); conn.close()
            bc_path = gen_book_barcode(code, isbn, titre)
            log_action(self.libraire["ID_libraire"],"ajout_livre",f"{titre} (ISBN {isbn})")
            self.form_msg.set("")
            self.status_var.set(f"✓ « {titre} » ajouté — code barre : {bc_path}")
            for attr in ["f_titre","f_isbn","f_annee","f_langue","f_format","f_pages",
                         "f_editeur","f_lieu","f_collection","f_a_nom","f_a_prenom",
                         "f_a_nat","f_a_isni","f_genre","f_section","f_dewey"]:
                getattr(self,attr).delete(0,"end")
        except sqlite3.IntegrityError:
            self.form_msg.set("Un livre avec cet ISBN existe déjà.")
        except Exception as ex:
            self.form_msg.set(str(ex))

    # ── Borrows tab ───────────────────────────────────────────────────────────
    def _show_borrows(self):
        c = self.content
        tf = tk.Frame(c, bg=BG)
        tf.pack(fill="both", expand=True)
        self.borrow_tree = styled_table(tf,
            ("ID","Client","Livre","Emprunté le","Retour prévu","Statut","En retard"), heights=14)
        self.borrow_tree.column("ID",          width=40,  anchor="center")
        self.borrow_tree.column("Client",      width=140)
        self.borrow_tree.column("Livre",       width=180)
        self.borrow_tree.column("Emprunté le", width=90)
        self.borrow_tree.column("Retour prévu",width=90)
        self.borrow_tree.column("Statut",      width=110, anchor="center")
        self.borrow_tree.column("En retard",   width=70,  anchor="center")
        self._reload_borrows()
        btn_row = tk.Frame(c, bg=BG)
        btn_row.pack(fill="x", pady=(10,0))
        make_btn(btn_row,"✓  MARQUER RENDU",self._mark_returned,gold=True).pack(side="left")
        make_btn(btn_row,"  RAFRAÎCHIR",self._reload_borrows,accent=False).pack(side="left",padx=(8,0))

    def _reload_borrows(self):
        if not hasattr(self,"borrow_tree"): return
        for row in self.borrow_tree.get_children(): self.borrow_tree.delete(row)
        try:
            conn = get_conn()
            rows = conn.execute("""
                SELECT e.ID_emprunt, c.Prenom||' '||c.Nom AS client,
                       l.Titre, e.Date_ajout, e.Date_prevu, e.Statut,
                       CASE WHEN e.Statut='en cours' AND e.Date_prevu < date('now')
                            THEN '⚠ OUI' ELSE '—' END AS retard
                FROM Emprunt e
                JOIN Client c ON e.ID_client=c.ID_client
                JOIN Livre  l ON e.Code_13=l.Code_13
                WHERE e.Type='emprunt'
                ORDER BY e.Statut, e.Date_ajout DESC
            """).fetchall()
            conn.close()
            for r in rows:
                if r["Statut"] == "retour_demande":
                    tag = "retour_demande"
                elif r["Statut"] == "en cours" and "OUI" in str(r["retard"]):
                    tag = "retard"
                elif r["Statut"] == "en cours":
                    tag = "encours"
                else:
                    tag = "rendu"
                self.borrow_tree.insert("","end", values=tuple(r), tags=(tag,))
            self.borrow_tree.tag_configure("retour_demande", foreground=TEAL)
            self.borrow_tree.tag_configure("retard",         foreground=DANGER)
            self.borrow_tree.tag_configure("encours",        foreground=WARN)
            self.borrow_tree.tag_configure("rendu",          foreground=SUCCESS)
            self.status_var.set(f"{len(rows)} emprunt(s).")
        except Exception as ex:
            self.status_var.set(str(ex))

    def _mark_returned(self):
        sel = self.borrow_tree.selection()
        if not sel:
            messagebox.showwarning("Attention","Sélectionnez un emprunt d'abord."); return
        item   = self.borrow_tree.item(sel[0])
        emp_id = item["values"][0]
        statut = item["values"][5]
        if statut == "rendu":
            messagebox.showinfo("Info","Ce livre est déjà marqué comme rendu."); return
        try:
            conn = get_conn()
            conn.execute(
                "UPDATE Emprunt SET Statut='rendu',Date_rendu=date('now') WHERE ID_emprunt=?",
                (emp_id,))
            conn.commit(); conn.close()
            log_action(self.libraire["ID_libraire"],"retour_confirme",f"Emprunt #{emp_id}")
            self.status_var.set(f"Emprunt #{emp_id} marqué comme rendu.")
            self._reload_borrows()
            self._update_notification()
        except Exception as ex:
            self.status_var.set(str(ex))

    # ── Clients tab ───────────────────────────────────────────────────────────
    def _show_clients(self):
        c = self.content
        tf = tk.Frame(c, bg=BG)
        tf.pack(fill="both", expand=True)
        tree = styled_table(tf,
            ("ID","Nom","Prénom","Abonnement (€)","Livres","Suspendu jusqu'au","Inscrit le"),
            heights=14)
        tree.column("ID",               width=35,  anchor="center")
        tree.column("Nom",              width=120)
        tree.column("Prénom",           width=120)
        tree.column("Abonnement (€)",   width=100, anchor="center")
        tree.column("Livres",           width=60,  anchor="center")
        tree.column("Suspendu jusqu'au",width=110, anchor="center")
        tree.column("Inscrit le",       width=90)
        try:
            conn = get_conn()
            rows = conn.execute("""
                SELECT c.ID_client, c.Nom, c.Prenom,
                       COALESCE(c.Abonnement,10.0) AS abo,
                       COUNT(CASE WHEN e.Statut IN ('en cours','retour_demande') THEN 1 END) AS nb,
                       c.timeout_jusqu_au, c.Date_inscription
                FROM Client c
                LEFT JOIN Emprunt e ON c.ID_client=e.ID_client AND e.Type='emprunt'
                GROUP BY c.ID_client ORDER BY c.ID_client
            """).fetchall()
            conn.close()
            today = date.today().isoformat()
            for r in rows:
                suspended = r["timeout_jusqu_au"] and r["timeout_jusqu_au"] >= today
                tag = "suspended" if suspended else (
                      "atmax" if r["nb"] >= MAX_BORROWS else "ok")
                vals = (r["ID_client"],r["Nom"],r["Prenom"],
                        f"{r['abo']:.2f}",r["nb"],
                        r["timeout_jusqu_au"] or "—", r["Date_inscription"])
                tree.insert("","end", values=vals, tags=(tag,))
            tree.tag_configure("suspended", foreground=DANGER)
            tree.tag_configure("atmax",     foreground=WARN)
            tree.tag_configure("ok",        foreground=TEXT)
            self.status_var.set(f"{len(rows)} client(s).")
        except Exception as ex:
            self.status_var.set(str(ex))


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN SCREEN
# ══════════════════════════════════════════════════════════════════════════════
class AdminScreen(tk.Frame):
    def __init__(self, master, admin, on_logout):
        super().__init__(master, bg=BG)
        self.admin       = admin
        self.on_logout   = on_logout
        self._edit_entry = None
        self._edit_col   = None
        self._edit_iid   = None
        self._build()

    def on_scan(self, code): pass
    def on_char(self, char): pass

    def _build(self):
        header_bar(self, "BIBLIOTHÈQUE", "super administrateur", RED2,
                   f"{self.admin.get('Prenom','')} {self.admin.get('Nom','')}",
                   self.on_logout)
        tabs = tk.Frame(self, bg=BG)
        tabs.pack(fill="x", padx=32, pady=(0,16))
        self.tab_var   = tk.StringVar(value="libraires")
        self._tab_btns = {}
        for label, key in [("👷  LIBRAIRES","libraires"),
                            ("📋  LOGS","logs"),
                            ("👥  CLIENTS","clients")]:
            b = tk.Radiobutton(tabs, text=label, variable=self.tab_var,
                               value=key, font=FONT_BTN,
                               bg=CARD, fg=MUTED, selectcolor=BG,
                               activebackground=BG, indicatoron=False,
                               relief="flat", padx=16, pady=8,
                               cursor="hand2", command=self._switch_tab)
            b.pack(side="left", padx=(0,4))
            self._tab_btns[key] = b
        self._update_tabs()
        self.content = tk.Frame(self, bg=BG)
        self.content.pack(fill="both", expand=True, padx=32)
        self.status_var = tk.StringVar(value="Prêt.")
        tk.Label(self, textvariable=self.status_var, font=FONT_SMALL,
                 bg=BG, fg=MUTED, anchor="w").pack(fill="x", padx=32, pady=(4,8))
        self._show_libraires()

    def _update_tabs(self):
        current = self.tab_var.get()
        for key, btn in self._tab_btns.items():
            btn.config(bg=RED2 if key==current else CARD,
                       fg=BG   if key==current else MUTED)

    def _switch_tab(self):
        self._cancel_edit()
        self._update_tabs()
        for w in self.content.winfo_children(): w.destroy()
        tab = self.tab_var.get()
        if tab == "libraires": self._show_libraires()
        elif tab == "logs":    self._show_logs()
        elif tab == "clients": self._show_clients()

    def _show_libraires(self):
        c = self.content
        form = tk.Frame(c, bg=CARD,
                        highlightbackground=BORDER, highlightthickness=1)
        form.pack(fill="x", pady=(0,16), ipadx=16, ipady=12)
        tk.Label(form, text="AJOUTER UN LIBRAIRE", font=("Courier New",10,"bold"),
                 bg=CARD, fg=GOLD).pack(anchor="w", padx=16, pady=(12,8))
        row = tk.Frame(form, bg=CARD)
        row.pack(fill="x", padx=16, pady=(0,8))
        for i in range(4): row.columnconfigure(i, weight=1)
        for lbl, attr, ci in [("NOM","w_nom",0),("PRÉNOM","w_prenom",1),("EMAIL (optionnel)","w_email",2)]:
            col = tk.Frame(row, bg=CARD)
            col.grid(row=0, column=ci, sticky="ew", padx=(0,8))
            tk.Label(col, text=lbl, font=FONT_LABEL, bg=CARD, fg=MUTED).pack(anchor="w", pady=(0,4))
            _, e = make_entry(col)
            e.master.pack(fill="x")
            setattr(self, attr, e)
        btn_col = tk.Frame(row, bg=CARD)
        btn_col.grid(row=0, column=3, sticky="ew")
        tk.Label(btn_col, text=" ", font=FONT_LABEL, bg=CARD, fg=MUTED).pack(anchor="w", pady=(0,4))
        make_btn(btn_col, "＋ AJOUTER", self._add_libraire, gold=True).pack(fill="x")
        self.w_msg = tk.StringVar()
        tk.Label(form, textvariable=self.w_msg, font=FONT_SMALL,
                 bg=CARD, fg=DANGER).pack(anchor="w", padx=16, pady=(0,4))

        tk.Label(c, text="💡  Cliquez sur Poste ou Salaire pour modifier inline.",
                 font=FONT_SMALL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0,6))
        tf = tk.Frame(c, bg=BG)
        tf.pack(fill="both", expand=True)
        cols = ("ID","Nom","Prénom","Email","Poste","Salaire (€)","Actions","Code barre","Inscrit le")
        self.lib_tree = styled_table(tf, cols, heights=7)
        self.lib_tree.column("ID",          width=35,  anchor="center")
        self.lib_tree.column("Nom",         width=100)
        self.lib_tree.column("Prénom",      width=100)
        self.lib_tree.column("Email",       width=140)
        self.lib_tree.column("Poste",       width=100)
        self.lib_tree.column("Salaire (€)", width=80,  anchor="center")
        self.lib_tree.column("Actions",     width=60,  anchor="center")
        self.lib_tree.column("Code barre",  width=130)
        self.lib_tree.column("Inscrit le",  width=90)
        self.lib_tree.bind("<ButtonRelease-1>", self._on_lib_click)
        self._reload_libraires()
        btn_row = tk.Frame(c, bg=BG)
        btn_row.pack(fill="x", pady=(8,0))
        make_btn(btn_row,"🗑  SUPPRIMER",self._remove_libraire,red=True).pack(side="left")
        make_btn(btn_row,"🔄  RÉGÉNÉRER CODE BARRE",self._regen_lib_bc,accent=False).pack(side="left",padx=(8,0))
        make_btn(btn_row,"  RAFRAÎCHIR",self._reload_libraires,accent=False).pack(side="left",padx=(8,0))

    def _reload_libraires(self):
        if not hasattr(self,"lib_tree"): return
        self._cancel_edit()
        for row in self.lib_tree.get_children(): self.lib_tree.delete(row)
        try:
            conn = get_conn()
            rows = conn.execute("""
                SELECT l.ID_libraire, l.Nom, l.Prenom,
                       COALESCE(l.Email,'—')        AS Email,
                       COALESCE(l.Poste,'Libraire') AS Poste,
                       COALESCE(l.Salaire,1800.0)   AS Salaire,
                       COUNT(lg.ID_log)             AS nb_actions,
                       l.code_barre,
                       COALESCE(l.Date_inscription,'—') AS Date_inscription
                FROM Libraire l
                LEFT JOIN Log_action lg ON l.ID_libraire=lg.ID_libraire
                GROUP BY l.ID_libraire ORDER BY l.ID_libraire
            """).fetchall()
            conn.close()
            for r in rows:
                self.lib_tree.insert("","end", iid=str(r["ID_libraire"]),
                    values=(r["ID_libraire"],r["Nom"],r["Prenom"],r["Email"],
                            r["Poste"],f"{r['Salaire']:.2f}",
                            r["nb_actions"],r["code_barre"],r["Date_inscription"]))
            self.status_var.set(f"{len(rows)} libraire(s).")
        except Exception as ex:
            self.status_var.set(str(ex))

    def _on_lib_click(self, event):
        tree = self.lib_tree
        if tree.identify_region(event.x, event.y) != "cell": return
        col_id  = tree.identify_column(event.x)
        col_idx = int(col_id.replace("#","")) - 1
        iid     = tree.identify_row(event.y)
        if not iid: return
        col_name = tree["columns"][col_idx]
        if col_name not in ("Poste","Salaire (€)"): return
        self._cancel_edit()
        bbox = tree.bbox(iid, col_id)
        if not bbox: return
        x,y,w,h = bbox
        current_val = tree.item(iid,"values")[col_idx]
        entry = tk.Entry(tree, font=FONT_SMALL, bg=ACCENT, fg="#ffffff",
                         insertbackground="#ffffff", relief="flat", bd=4, justify="center")
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, current_val)
        entry.select_range(0,"end")
        entry.focus_set()
        self._edit_entry = entry
        self._edit_col   = col_name
        self._edit_iid   = iid
        entry.bind("<Return>",   lambda e: self._commit_edit())
        entry.bind("<Escape>",   lambda e: self._cancel_edit())
        entry.bind("<FocusOut>", lambda e: self._commit_edit())

    def _commit_edit(self):
        if not self._edit_entry: return
        new_val  = self._edit_entry.get().strip()
        col_name = self._edit_col
        iid      = self._edit_iid
        lib_id   = int(iid)
        if col_name == "Salaire (€)":
            try:
                val_clean = float(new_val.replace(",","."))
            except ValueError:
                self.status_var.set("Salaire invalide.")
                self._cancel_edit(); return
            db_col = "Salaire"; db_val = val_clean; display = f"{val_clean:.2f}"
        else:
            if not new_val:
                self.status_var.set("Le poste ne peut pas être vide.")
                self._cancel_edit(); return
            db_col = "Poste"; db_val = new_val; display = new_val
        try:
            conn = get_conn()
            conn.execute(f"UPDATE Libraire SET {db_col}=? WHERE ID_libraire=?",
                         (db_val, lib_id))
            conn.commit(); conn.close()
            vals = list(self.lib_tree.item(iid,"values"))
            col_idx = list(self.lib_tree["columns"]).index(col_name)
            vals[col_idx] = display
            self.lib_tree.item(iid, values=vals)
            self.status_var.set(f"Libraire #{lib_id} — {col_name} : {display}")
        except Exception as ex:
            self.status_var.set(str(ex))
        self._cancel_edit()

    def _cancel_edit(self):
        if self._edit_entry:
            try: self._edit_entry.destroy()
            except Exception: pass
            self._edit_entry = None
            self._edit_col   = None
            self._edit_iid   = None

    def _add_libraire(self):
        nom    = self.w_nom.get().strip()
        prenom = self.w_prenom.get().strip()
        email  = self.w_email.get().strip() or None
        if not nom or not prenom:
            self.w_msg.set("Nom et prénom sont obligatoires."); return
        code = unique_code_for_table("Libraire")
        try:
            conn = get_conn()
            conn.execute(
                "INSERT INTO Libraire (Nom,Prenom,Email,Mot_de_passe,Poste,Salaire,code_barre) VALUES (?,?,?,?,'Libraire',1800.0,?)",
                (nom,prenom,email,"",code))
            conn.commit()
            row = conn.execute("SELECT ID_libraire FROM Libraire WHERE code_barre=?",(code,)).fetchone()
            conn.close()
            bc_path = gen_user_barcode("EMP", row["ID_libraire"], f"{prenom}_{nom}", code)
            self.w_msg.set("")
            self.status_var.set(f"Libraire {prenom} {nom} ajouté — code barre : {bc_path}")
            for attr in ["w_nom","w_prenom","w_email"]:
                getattr(self,attr).delete(0,"end")
            self._reload_libraires()
        except Exception as ex:
            self.w_msg.set(str(ex))

    def _regen_lib_bc(self):
        sel = self.lib_tree.selection()
        if not sel:
            messagebox.showwarning("Attention","Sélectionnez un libraire d'abord."); return
        item = self.lib_tree.item(sel[0])
        lid  = item["values"][0]
        code = item["values"][7]
        name = f"{item['values'][2]}_{item['values'][1]}"
        bc_path = gen_user_barcode("EMP", lid, name, code)
        self.status_var.set(f"Code barre régénéré : {bc_path}")

    def _remove_libraire(self):
        sel = self.lib_tree.selection()
        if not sel:
            messagebox.showwarning("Attention","Sélectionnez un libraire d'abord."); return
        item = self.lib_tree.item(sel[0])
        lid  = item["values"][0]
        name = f"{item['values'][2]} {item['values'][1]}"
        if not messagebox.askyesno("Confirmer",f"Supprimer le libraire {name} ?"): return
        try:
            conn = get_conn()
            conn.execute("DELETE FROM Libraire WHERE ID_libraire=?",(lid,))
            conn.commit(); conn.close()
            self.status_var.set(f"Libraire {name} supprimé.")
            self._reload_libraires()
        except Exception as ex:
            self.status_var.set(str(ex))

    def _show_logs(self):
        c = self.content
        sf = tk.Frame(c, bg=BG)
        sf.pack(fill="x", pady=(0,14))
        try:
            conn = get_conn()
            workers = conn.execute("""
                SELECT l.ID_libraire, l.Prenom||' '||l.Nom AS name,
                       COALESCE(l.Poste,'Libraire') AS poste,
                       COALESCE(l.Salaire,1800.0)   AS salaire,
                       COUNT(lg.ID_log)             AS nb
                FROM Libraire l
                LEFT JOIN Log_action lg ON l.ID_libraire=lg.ID_libraire
                GROUP BY l.ID_libraire
            """).fetchall()
            conn.close()
        except Exception:
            workers = []
        for i, w in enumerate(workers):
            card = tk.Frame(sf, bg=CARD,
                            highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=0, column=i, padx=(0,10), ipadx=12, ipady=8, sticky="ew")
            sf.columnconfigure(i, weight=1)
            tk.Label(card, text=w["name"],    font=FONT_LABEL, bg=CARD, fg=GOLD).pack(anchor="w", padx=10, pady=(8,2))
            tk.Label(card, text=w["poste"],   font=FONT_SMALL, bg=CARD, fg=MUTED).pack(anchor="w", padx=10)
            tk.Label(card, text=f"{w['salaire']:.2f} €", font=FONT_SMALL, bg=CARD, fg=SUCCESS).pack(anchor="w", padx=10)
            tk.Label(card, text=f"{w['nb']} action(s)", font=FONT_SMALL, bg=CARD, fg=ACCENT2).pack(anchor="w", padx=10, pady=(0,8))

        frow = tk.Frame(c, bg=BG)
        frow.pack(fill="x", pady=(0,8))
        tk.Label(frow, text="FILTRER :", font=FONT_LABEL,
                 bg=BG, fg=MUTED).pack(side="left", padx=(0,8))
        self.log_filter = tk.StringVar(value="Tous")
        options = ["Tous"] + [f"{w['ID_libraire']} — {w['name']}" for w in workers]
        om = tk.OptionMenu(frow, self.log_filter, *options,
                           command=lambda _: self._reload_logs())
        om.config(font=FONT_SMALL, bg=SURFACE, fg=TEXT,
                  activebackground=ACCENT, activeforeground="#fff",
                  relief="flat", bd=0)
        om.pack(side="left")
        tf = tk.Frame(c, bg=BG)
        tf.pack(fill="both", expand=True)
        self.log_tree = styled_table(tf,
            ("ID","Libraire","Poste","Action","Détail","Date"), heights=10)
        self.log_tree.column("ID",       width=35,  anchor="center")
        self.log_tree.column("Libraire", width=130)
        self.log_tree.column("Poste",    width=100)
        self.log_tree.column("Action",   width=120)
        self.log_tree.column("Détail",   width=240)
        self.log_tree.column("Date",     width=130)
        self._reload_logs()
        make_btn(c,"  RAFRAÎCHIR",self._reload_logs,accent=False).pack(anchor="w",pady=(8,0))

    def _reload_logs(self):
        if not hasattr(self,"log_tree"): return
        for row in self.log_tree.get_children(): self.log_tree.delete(row)
        try:
            filt = self.log_filter.get() if hasattr(self,"log_filter") else "Tous"
            wid  = None
            if filt != "Tous":
                wid = int(filt.split(" — ")[0])
            conn = get_conn()
            if wid:
                rows = conn.execute("""
                    SELECT lg.ID_log, l.Prenom||' '||l.Nom AS libraire,
                           COALESCE(l.Poste,'Libraire') AS poste,
                           lg.Action, lg.Detail, lg.Date_action
                    FROM Log_action lg
                    LEFT JOIN Libraire l ON lg.ID_libraire=l.ID_libraire
                    WHERE lg.ID_libraire=?
                    ORDER BY lg.Date_action DESC
                """, (wid,)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT lg.ID_log, l.Prenom||' '||l.Nom AS libraire,
                           COALESCE(l.Poste,'Libraire') AS poste,
                           lg.Action, lg.Detail, lg.Date_action
                    FROM Log_action lg
                    LEFT JOIN Libraire l ON lg.ID_libraire=l.ID_libraire
                    ORDER BY lg.Date_action DESC
                """).fetchall()
            conn.close()
            for r in rows:
                self.log_tree.insert("","end", values=tuple(r))
            self.status_var.set(f"{len(rows)} action(s).")
        except Exception as ex:
            self.status_var.set(str(ex))

    def _show_clients(self):
        c = self.content
        tk.Label(c, text="💡  Sélectionnez un client pour gérer sa suspension ou régénérer son code barre.",
                 font=FONT_SMALL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0,8))
        tf = tk.Frame(c, bg=BG)
        tf.pack(fill="both", expand=True)
        self.client_tree = styled_table(tf,
            ("ID","Nom","Prénom","Abonnement (€)","Livres","Suspendu jusqu'au","Code barre","Inscrit le"),
            heights=10)
        self.client_tree.column("ID",               width=35,  anchor="center")
        self.client_tree.column("Nom",              width=110)
        self.client_tree.column("Prénom",           width=110)
        self.client_tree.column("Abonnement (€)",   width=100, anchor="center")
        self.client_tree.column("Livres",           width=60,  anchor="center")
        self.client_tree.column("Suspendu jusqu'au",width=110, anchor="center")
        self.client_tree.column("Code barre",       width=130)
        self.client_tree.column("Inscrit le",       width=90)
        self._reload_clients()
        ctrl = tk.Frame(c, bg=BG)
        ctrl.pack(fill="x", pady=(10,0))
        make_btn(ctrl,"⏸  SUSPENDRE",self._timeout_client,red=True).pack(side="left")
        make_btn(ctrl,"✓  LEVER SUSPENSION",self._lift_timeout,gold=True).pack(side="left",padx=(8,0))
        make_btn(ctrl,"🔄  RÉGÉNÉRER CODE BARRE",self._regen_client_bc,accent=False).pack(side="left",padx=(8,0))
        tk.Label(ctrl, text="  Durée :", font=FONT_LABEL,
                 bg=BG, fg=MUTED).pack(side="left", padx=(16,4))
        days_frame = tk.Frame(ctrl, bg=SURFACE,
                              highlightbackground=BORDER, highlightthickness=1)
        days_frame.pack(side="left")
        self.days_var = tk.StringVar(value="7")
        tk.Entry(days_frame, textvariable=self.days_var,
                 font=FONT_BODY, bg=SURFACE, fg=TEXT,
                 insertbackground=ACCENT2, relief="flat",
                 bd=6, width=4, justify="center").pack()
        tk.Label(ctrl, text="jours", font=FONT_LABEL,
                 bg=BG, fg=MUTED).pack(side="left", padx=(6,0))
        make_btn(ctrl,"  RAFRAÎCHIR",self._reload_clients,accent=False).pack(side="right")

    def _reload_clients(self):
        if not hasattr(self,"client_tree"): return
        for row in self.client_tree.get_children(): self.client_tree.delete(row)
        try:
            conn = get_conn()
            rows = conn.execute("""
                SELECT c.ID_client, c.Nom, c.Prenom,
                       COALESCE(c.Abonnement,10.0) AS abo,
                       COUNT(CASE WHEN e.Statut IN ('en cours','retour_demande') THEN 1 END) AS nb,
                       c.timeout_jusqu_au, c.code_barre,
                       COALESCE(c.Date_inscription,'—') AS Date_inscription
                FROM Client c
                LEFT JOIN Emprunt e ON c.ID_client=e.ID_client AND e.Type='emprunt'
                GROUP BY c.ID_client ORDER BY c.ID_client
            """).fetchall()
            conn.close()
            today = date.today().isoformat()
            for r in rows:
                suspended = r["timeout_jusqu_au"] and r["timeout_jusqu_au"] >= today
                tag = "suspended" if suspended else (
                      "atmax" if r["nb"] >= MAX_BORROWS else "ok")
                vals = (r["ID_client"],r["Nom"],r["Prenom"],
                        f"{r['abo']:.2f}",r["nb"],
                        r["timeout_jusqu_au"] or "—",
                        r["code_barre"] or "—", r["Date_inscription"])
                self.client_tree.insert("","end", values=vals, tags=(tag,))
            self.client_tree.tag_configure("suspended", foreground=DANGER)
            self.client_tree.tag_configure("atmax",     foreground=WARN)
            self.client_tree.tag_configure("ok",        foreground=TEXT)
            self.status_var.set(f"{len(rows)} client(s).")
        except Exception as ex:
            self.status_var.set(str(ex))

    def _selected_client(self):
        sel = self.client_tree.selection()
        if not sel:
            messagebox.showwarning("Attention","Sélectionnez un client d'abord.")
            return None
        return self.client_tree.item(sel[0])["values"]

    def _timeout_client(self):
        vals = self._selected_client()
        if not vals: return
        cid = vals[0]
        try:
            days = int(self.days_var.get())
            if days <= 0: raise ValueError
        except ValueError:
            messagebox.showwarning("Erreur","Entrez un nombre de jours valide (> 0)."); return
        end_date = (date.today() + timedelta(days=days)).isoformat()
        name = f"{vals[2]} {vals[1]}"
        if not messagebox.askyesno("Confirmer",
            f"Suspendre {name} pendant {days} jour(s) ?\n(jusqu'au {end_date})"): return
        try:
            conn = get_conn()
            conn.execute("UPDATE Client SET timeout_jusqu_au=? WHERE ID_client=?", (end_date, cid))
            conn.commit(); conn.close()
            self.status_var.set(f"Client #{cid} suspendu jusqu'au {end_date}.")
            self._reload_clients()
        except Exception as ex:
            self.status_var.set(str(ex))

    def _lift_timeout(self):
        vals = self._selected_client()
        if not vals: return
        cid = vals[0]
        try:
            conn = get_conn()
            conn.execute("UPDATE Client SET timeout_jusqu_au=NULL WHERE ID_client=?", (cid,))
            conn.commit(); conn.close()
            self.status_var.set(f"Suspension du client #{cid} levée.")
            self._reload_clients()
        except Exception as ex:
            self.status_var.set(str(ex))

    def _regen_client_bc(self):
        vals = self._selected_client()
        if not vals: return
        cid  = vals[0]
        code = vals[6]
        name = f"{vals[2]}_{vals[1]}"
        if not code or code == "—":
            messagebox.showwarning("Erreur","Ce client n'a pas de code barre."); return
        bc_path = gen_user_barcode("CLT", cid, name, code)
        self.status_var.set(f"Code barre régénéré : {bc_path}")


# ══════════════════════════════════════════════════════════════════════════════
# STARTUP BARCODE GENERATION
# ══════════════════════════════════════════════════════════════════════════════
def generate_all_barcodes():
    try:
        conn = get_conn()
        for r in conn.execute("SELECT ID_admin,Nom,Prenom,code_barre FROM Admin WHERE code_barre IS NOT NULL").fetchall():
            gen_user_barcode("ADM", r["ID_admin"], f"{r['Prenom']}_{r['Nom']}", r["code_barre"])
        for r in conn.execute("SELECT ID_libraire,Nom,Prenom,code_barre FROM Libraire WHERE code_barre IS NOT NULL").fetchall():
            gen_user_barcode("EMP", r["ID_libraire"], f"{r['Prenom']}_{r['Nom']}", r["code_barre"])
        for r in conn.execute("SELECT ID_client,Nom,Prenom,code_barre FROM Client WHERE code_barre IS NOT NULL").fetchall():
            gen_user_barcode("CLT", r["ID_client"], f"{r['Prenom']}_{r['Nom']}", r["code_barre"])
        for r in conn.execute("SELECT Code_13,Titre,code_barre FROM Livre WHERE code_barre IS NOT NULL").fetchall():
            gen_book_barcode(r["code_barre"], r["Code_13"], r["Titre"])
        conn.close()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# ROOT APP
# ══════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bibliothèque")
        self.geometry("960x700")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._current_frame = None
        self._scan_buf = ""
        self.bind("<Key>", self._on_key)
        generate_all_barcodes()
        self._show_login()

    def _on_key(self, event):
        if isinstance(event.widget, tk.Entry): return
        if event.keysym == "Return":
            code = self._scan_buf.strip()
            self._scan_buf = ""
            if code and self._current_frame:
                self._current_frame.on_scan(code)
        elif event.char and event.char.isprintable():
            self._scan_buf += event.char
            if self._current_frame:
                self._current_frame.on_char(event.char)

    def _show_login(self):
        self._switch_to(LoginScreen(self))

    def _on_login(self, user, role):
        if role == "admin":
            self._switch_to(AdminScreen(self, admin=user, on_logout=self._show_login))
        elif role == "libraire":
            self._switch_to(LibraireScreen(self, libraire=user, on_logout=self._show_login))
        else:
            self._switch_to(LibraryScreen(self, client=user, on_logout=self._show_login))

    def _switch_to(self, frame):
        if self._current_frame:
            self._current_frame.destroy()
        self._scan_buf = ""
        self._current_frame = frame
        frame.pack(fill="both", expand=True)

if __name__ == "__main__":
    App().mainloop()
