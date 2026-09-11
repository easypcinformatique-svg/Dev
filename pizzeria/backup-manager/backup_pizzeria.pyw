"""
Pizza Napoli - Backup Manager
Double-cliquez pour lancer l'application
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import urllib.request
import urllib.error
import os
import sys
from datetime import datetime

# ============================================
# CONFIGURATION
# ============================================
GITHUB_TOKEN = "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"
REPO_DEV = "easypcinformatique-svg/Dev"
REPO_PROD = "carpentraspizzanapoli-design/pizza-napoli"
BACKUP_WORKFLOW = "backup-pizzeria.yml"
RESTORE_WORKFLOW = "restore-pizzeria.yml"


# ============================================
# GITHUB API
# ============================================
class GitHubAPI:
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "PizzaNapoli-BackupManager"
        }

    def _request(self, method, url, data=None):
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 204:
                    return None
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            raise Exception(f"GitHub API {e.code}: {error_body}")

    def trigger_backup(self, reason="Backup manuel"):
        url = f"https://api.github.com/repos/{REPO_DEV}/actions/workflows/{BACKUP_WORKFLOW}/dispatches"
        self._request("POST", url, {"ref": "master", "inputs": {"reason": reason}})

    def trigger_restore(self, tag):
        url = f"https://api.github.com/repos/{REPO_DEV}/actions/workflows/{RESTORE_WORKFLOW}/dispatches"
        self._request("POST", url, {"ref": "master", "inputs": {"tag_or_commit": tag, "confirm": "CONFIRMER"}})

    def list_releases(self):
        url = f"https://api.github.com/repos/{REPO_DEV}/releases?per_page=30"
        releases = self._request("GET", url)
        backups = []
        for r in releases:
            if "backup" in r.get("tag_name", "").lower():
                size = ""
                download_url = ""
                for asset in r.get("assets", []):
                    size = f"{asset['size'] // 1024 // 1024} MB"
                    download_url = asset["browser_download_url"]
                backups.append({
                    "name": r["name"],
                    "tag": r["tag_name"],
                    "date": r["created_at"][:10],
                    "time": r["created_at"][11:16],
                    "size": size,
                    "url": r["html_url"],
                    "download": download_url,
                    "body": r.get("body", "")
                })
        return backups

    def get_latest_workflow_run(self, workflow):
        url = f"https://api.github.com/repos/{REPO_DEV}/actions/workflows/{workflow}/runs?per_page=1"
        data = self._request("GET", url)
        if data and data.get("workflow_runs"):
            run = data["workflow_runs"][0]
            return {
                "status": run["status"],
                "conclusion": run.get("conclusion", ""),
                "created_at": run["created_at"],
                "url": run["html_url"]
            }
        return None


# ============================================
# APPLICATION
# ============================================
class BackupApp:
    def __init__(self):
        self.api = GitHubAPI(GITHUB_TOKEN)
        self.root = tk.Tk()
        self.root.title("Pizza Napoli - Backup Manager")
        self.root.geometry("700x600")
        self.root.configure(bg="#1a0a00")
        self.root.resizable(True, True)

        # Icon
        try:
            self.root.iconbitmap(default="")
        except:
            pass

        self._build_ui()
        self._refresh_backups()

    def _build_ui(self):
        # Styles
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Title.TLabel", background="#1a0a00", foreground="#f39c12",
                        font=("Georgia", 18, "bold"))
        style.configure("Sub.TLabel", background="#1a0a00", foreground="#ffffff",
                        font=("Arial", 10))
        style.configure("Status.TLabel", background="#1a0a00", foreground="#27ae60",
                        font=("Arial", 9))
        style.configure("Red.TButton", font=("Arial", 11, "bold"))
        style.configure("Green.TButton", font=("Arial", 11, "bold"))
        style.configure("Treeview", font=("Arial", 9), rowheight=28)
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

        # ---- Header ----
        header = tk.Frame(self.root, bg="#1a0a00", pady=15)
        header.pack(fill="x")

        ttk.Label(header, text="Pizza Napoli Carpentras", style="Title.TLabel").pack()
        ttk.Label(header, text="Gestionnaire de Backups", style="Sub.TLabel").pack()

        # ---- Status bar ----
        self.status_var = tk.StringVar(value="Pret")
        self.status_label = ttk.Label(header, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.pack(pady=(5, 0))

        # ---- Separator ----
        tk.Frame(self.root, bg="#c0392b", height=3).pack(fill="x")

        # ---- Buttons ----
        btn_frame = tk.Frame(self.root, bg="#2c2c2c", pady=15, padx=20)
        btn_frame.pack(fill="x")

        # Backup button
        self.backup_btn = tk.Button(
            btn_frame, text="BACKUP MAINTENANT",
            bg="#27ae60", fg="white", font=("Arial", 12, "bold"),
            relief="flat", padx=20, pady=10, cursor="hand2",
            activebackground="#2ecc71", activeforeground="white",
            command=self._do_backup
        )
        self.backup_btn.pack(side="left", padx=(0, 10))

        # Restore button
        self.restore_btn = tk.Button(
            btn_frame, text="RESTAURER",
            bg="#e67e22", fg="white", font=("Arial", 12, "bold"),
            relief="flat", padx=20, pady=10, cursor="hand2",
            activebackground="#f39c12", activeforeground="white",
            command=self._do_restore
        )
        self.restore_btn.pack(side="left", padx=(0, 10))

        # Refresh button
        self.refresh_btn = tk.Button(
            btn_frame, text="Rafraichir",
            bg="#3498db", fg="white", font=("Arial", 10),
            relief="flat", padx=15, pady=10, cursor="hand2",
            activebackground="#2980b9", activeforeground="white",
            command=self._refresh_backups
        )
        self.refresh_btn.pack(side="right")

        # ---- Italian flag stripe ----
        flag = tk.Frame(self.root, height=4)
        flag.pack(fill="x")
        colors = ["#009246", "#ffffff", "#ce2b37"]
        for c in colors:
            tk.Frame(flag, bg=c, height=4).pack(side="left", fill="x", expand=True)

        # ---- Backup list ----
        list_frame = tk.Frame(self.root, bg="#1a0a00", padx=20, pady=10)
        list_frame.pack(fill="both", expand=True)

        ttk.Label(list_frame, text="Historique des backups", style="Sub.TLabel").pack(anchor="w", pady=(0, 5))

        # Treeview
        columns = ("date", "heure", "taille", "tag")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        self.tree.heading("date", text="Date")
        self.tree.heading("heure", text="Heure")
        self.tree.heading("taille", text="Taille")
        self.tree.heading("tag", text="Tag de restauration")
        self.tree.column("date", width=100)
        self.tree.column("heure", width=60)
        self.tree.column("taille", width=70)
        self.tree.column("tag", width=400)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ---- Footer ----
        footer = tk.Frame(self.root, bg="#1a0a00", pady=8)
        footer.pack(fill="x")
        ttk.Label(footer, text="Backups auto: chaque dimanche 3h | Stockage: GitHub Releases",
                  style="Status.TLabel").pack()

    def _set_status(self, text, color="#27ae60"):
        self.status_var.set(text)
        style = ttk.Style()
        style.configure("Status.TLabel", foreground=color)

    def _refresh_backups(self):
        self._set_status("Chargement des backups...", "#f39c12")
        self.tree.delete(*self.tree.get_children())

        def fetch():
            try:
                backups = self.api.list_releases()
                self.root.after(0, lambda: self._populate_backups(backups))
            except Exception as e:
                self.root.after(0, lambda: self._set_status(f"Erreur: {e}", "#e74c3c"))

        threading.Thread(target=fetch, daemon=True).start()

    def _populate_backups(self, backups):
        self.tree.delete(*self.tree.get_children())
        self.backups = backups
        for b in backups:
            # Extract production tag from body
            prod_tag = b["tag"]
            body = b.get("body", "")
            for line in body.split("\n"):
                if "Tag production" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        prod_tag = parts[-1].strip().strip("`")
                        break

            self.tree.insert("", "end", values=(
                b["date"],
                b["time"],
                b["size"],
                prod_tag
            ))
        count = len(backups)
        self._set_status(f"{count} backup(s) disponible(s)", "#27ae60")

    def _do_backup(self):
        if not messagebox.askyesno("Backup", "Lancer un backup maintenant ?"):
            return

        self.backup_btn.configure(state="disabled", bg="#95a5a6")
        self._set_status("Backup en cours...", "#f39c12")

        def run():
            try:
                self.api.trigger_backup("Backup manuel depuis l'application")
                self.root.after(0, lambda: self._set_status("Backup lance ! Attente du resultat...", "#f39c12"))

                # Poll status
                import time
                for i in range(30):
                    time.sleep(5)
                    run_info = self.api.get_latest_workflow_run(BACKUP_WORKFLOW)
                    if run_info and run_info["status"] == "completed":
                        if run_info["conclusion"] == "success":
                            self.root.after(0, lambda: self._set_status("Backup termine avec succes !", "#27ae60"))
                            self.root.after(0, self._refresh_backups)
                        else:
                            self.root.after(0, lambda: self._set_status(
                                f"Backup echoue: {run_info['conclusion']}", "#e74c3c"))
                        break
                    self.root.after(0, lambda i=i: self._set_status(
                        f"Backup en cours... ({(i+1)*5}s)", "#f39c12"))
                else:
                    self.root.after(0, lambda: self._set_status("Timeout - verifiez sur GitHub", "#e74c3c"))

            except Exception as e:
                self.root.after(0, lambda: self._set_status(f"Erreur: {e}", "#e74c3c"))
            finally:
                self.root.after(0, lambda: self.backup_btn.configure(state="normal", bg="#27ae60"))

        threading.Thread(target=run, daemon=True).start()

    def _do_restore(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Restauration", "Selectionne un backup dans la liste d'abord !")
            return

        values = self.tree.item(selected[0])["values"]
        tag = values[3]
        date = values[0]

        confirm = messagebox.askyesno(
            "Restauration",
            f"ATTENTION : Tu vas restaurer le site au {date}\n\n"
            f"Tag : {tag}\n\n"
            f"Le site actuel sera ecrase. Continuer ?"
        )
        if not confirm:
            return

        self.restore_btn.configure(state="disabled", bg="#95a5a6")
        self._set_status("Restauration en cours...", "#e67e22")

        def run():
            try:
                self.api.trigger_restore(tag)
                self.root.after(0, lambda: self._set_status("Restauration lancee ! Attente...", "#e67e22"))

                import time
                for i in range(30):
                    time.sleep(5)
                    run_info = self.api.get_latest_workflow_run(RESTORE_WORKFLOW)
                    if run_info and run_info["status"] == "completed":
                        if run_info["conclusion"] == "success":
                            self.root.after(0, lambda: self._set_status(
                                f"Site restaure au {date} avec succes !", "#27ae60"))
                        else:
                            self.root.after(0, lambda: self._set_status(
                                f"Restauration echouee: {run_info['conclusion']}", "#e74c3c"))
                        break
                    self.root.after(0, lambda i=i: self._set_status(
                        f"Restauration en cours... ({(i+1)*5}s)", "#e67e22"))
                else:
                    self.root.after(0, lambda: self._set_status("Timeout - verifiez sur GitHub", "#e74c3c"))

            except Exception as e:
                self.root.after(0, lambda: self._set_status(f"Erreur: {e}", "#e74c3c"))
            finally:
                self.root.after(0, lambda: self.restore_btn.configure(state="normal", bg="#e67e22"))

        threading.Thread(target=run, daemon=True).start()

    def run(self):
        self.root.mainloop()


# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    app = BackupApp()
    app.run()
