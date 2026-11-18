"""Stockage SQLite des rendez-vous et des demandes clients (devis, reprise, rappel)."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path


class Store:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS rendez_vous (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cree_le TEXT NOT NULL,
                debut TEXT NOT NULL,
                fin TEXT NOT NULL,
                prestation TEXT NOT NULL,
                nom TEXT NOT NULL,
                telephone TEXT NOT NULL,
                email TEXT,
                vehicule TEXT,
                immatriculation TEXT,
                commentaire TEXT,
                statut TEXT NOT NULL DEFAULT 'a_confirmer'
            );
            CREATE TABLE IF NOT EXISTS demandes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cree_le TEXT NOT NULL,
                type TEXT NOT NULL,
                nom TEXT NOT NULL,
                telephone TEXT NOT NULL,
                email TEXT,
                details TEXT NOT NULL,
                statut TEXT NOT NULL DEFAULT 'nouveau'
            );
            CREATE TABLE IF NOT EXISTS ventes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_vente TEXT NOT NULL,
                ref TEXT NOT NULL,
                vehicule TEXT NOT NULL,
                prix_affiche INTEGER,
                prix_vente INTEGER NOT NULL,
                client TEXT,
                note TEXT
            );
            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                horodatage TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT NOT NULL
            );
            """
        )
        for table in ("rendez_vous", "demandes"):
            cols = {r[1] for r in self._conn.execute(f"PRAGMA table_info({table})")}
            if "note" not in cols:
                self._conn.execute(f"ALTER TABLE {table} ADD COLUMN note TEXT")
        self._conn.commit()

    # --- rendez-vous -------------------------------------------------------
    def rdv_entre(self, debut: datetime, fin: datetime) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM rendez_vous WHERE statut != 'annule' AND debut < ? AND fin > ?",
                (fin.isoformat(), debut.isoformat()),
            ).fetchall()
        return [dict(r) for r in rows]

    def ajouter_rdv(self, **champs) -> int:
        champs["cree_le"] = datetime.now().isoformat(timespec="seconds")
        cols = ", ".join(champs)
        marks = ", ".join("?" for _ in champs)
        with self._lock:
            cur = self._conn.execute(
                f"INSERT INTO rendez_vous ({cols}) VALUES ({marks})", tuple(champs.values())
            )
            self._conn.commit()
            return int(cur.lastrowid)

    # --- demandes ----------------------------------------------------------
    def ajouter_demande(self, type_: str, nom: str, telephone: str, email: str | None, details: dict) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO demandes (cree_le, type, nom, telephone, email, details) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    datetime.now().isoformat(timespec="seconds"),
                    type_,
                    nom,
                    telephone,
                    email,
                    json.dumps(details, ensure_ascii=False),
                ),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    # --- gestion -----------------------------------------------------------
    def _select(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def get(self, table: str, id_: int) -> dict | None:
        if table not in ("rendez_vous", "demandes"):
            raise ValueError(table)
        rows = self._select(f"SELECT * FROM {table} WHERE id = ?", (id_,))
        if not rows:
            return None
        r = rows[0]
        if "details" in r:
            r["details"] = json.loads(r["details"])
        return r

    def maj(self, table: str, id_: int, **champs) -> None:
        if table not in ("rendez_vous", "demandes"):
            raise ValueError(table)
        autorises = {"rendez_vous": {"statut", "debut", "fin", "note"}, "demandes": {"statut", "note"}}[table]
        champs = {k: v for k, v in champs.items() if k in autorises}
        if not champs:
            return
        sets = ", ".join(f"{k} = ?" for k in champs)
        with self._lock:
            self._conn.execute(f"UPDATE {table} SET {sets} WHERE id = ?", (*champs.values(), id_))
            self._conn.commit()

    def rdv_periode(self, debut: str, fin: str) -> list[dict]:
        return self._select(
            "SELECT * FROM rendez_vous WHERE debut >= ? AND debut < ? ORDER BY debut", (debut, fin))

    def demandes_filtre(self, statut: str | None, type_: str | None, limite: int = 50) -> list[dict]:
        sql, params = "SELECT * FROM demandes WHERE 1=1", []
        if statut:
            sql += " AND statut = ?"; params.append(statut)
        if type_:
            sql += " AND type = ?"; params.append(type_)
        sql += " ORDER BY id DESC LIMIT ?"; params.append(limite)
        out = self._select(sql, tuple(params))
        for r in out:
            r["details"] = json.loads(r["details"])
        return out

    def ajouter_vente(self, **champs) -> int:
        cols = ", ".join(champs)
        marks = ", ".join("?" for _ in champs)
        with self._lock:
            cur = self._conn.execute(f"INSERT INTO ventes ({cols}) VALUES ({marks})", tuple(champs.values()))
            self._conn.commit()
            return int(cur.lastrowid)

    def ventes_depuis(self, depuis: str) -> list[dict]:
        return self._select("SELECT * FROM ventes WHERE date_vente >= ? ORDER BY date_vente", (depuis,))

    def compter(self, sql: str, params: tuple = ()) -> list[dict]:
        return self._select(sql, params)

    def journaliser(self, action: str, details: dict) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO journal (horodatage, action, details) VALUES (?, ?, ?)",
                (datetime.now().isoformat(timespec="seconds"), action, json.dumps(details, ensure_ascii=False)),
            )
            self._conn.commit()

    # --- lecture (admin) ---------------------------------------------------
    def lister(self, table: str, limite: int = 200) -> list[dict]:
        if table not in ("rendez_vous", "demandes", "ventes", "journal"):
            raise ValueError(table)
        with self._lock:
            rows = self._conn.execute(
                f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?", (limite,)
            ).fetchall()
        out = [dict(r) for r in rows]
        for r in out:
            if "details" in r:
                r["details"] = json.loads(r["details"])
        return out
