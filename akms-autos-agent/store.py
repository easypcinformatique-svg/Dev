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
            """
        )
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

    # --- lecture (admin) ---------------------------------------------------
    def lister(self, table: str, limite: int = 200) -> list[dict]:
        if table not in ("rendez_vous", "demandes"):
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
