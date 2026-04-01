#!/usr/bin/env python3
"""
Script pour deployer les fichiers du mini-site livraison vers les repos GitHub
de carpentrasxpizzanapoli-design.

Usage:
1. Cree un token GitHub : https://github.com/settings/tokens/new
   - Coche "repo" (Full control of private repositories)
   - Clique "Generate token"
   - Copie le token

2. Lance le script :
   python3 deploy_to_github.py VOTRE_TOKEN_GITHUB
"""

import sys
import os
import base64
import json
import urllib.request
import urllib.error

# Configuration
ORG = "carpentrasxpizzanapoli-design"
API = "https://api.github.com"

# Mapping : fichier local -> (repo, fichier distant)
FILE_MAP = {
    "monteux.html": ("livraison-pizza-monteux", "index.html"),
    "serres.html": ("livraison-pizza-serres", "index.html"),
    "pernes.html": ("livraison-pizza-pernes-les-fontaines", "index.html"),
    "aubignan.html": ("livraison-pizza-aubignan", "index.html"),
    "loriol.html": ("livraison-pizza-loriol-du-comtat", "index.html"),
    "caromb.html": ("livraison-pizza-caromb", "index.html"),
    "mazan.html": ("livraison-pizza-mazan", "index.html"),
    "saint-didier.html": ("livraison-pizza-saint-didier", "index.html"),
    "index.html": ("livraison-pizza-carpentras", "index.html"),
}

# style.css va dans tous les repos
STYLE_REPOS = [repo for _, (repo, _) in FILE_MAP.items()]
EXTRA_FILES = {
    "robots.txt": ("livraison-pizza-carpentras", "robots.txt"),
    "sitemap.xml": ("livraison-pizza-carpentras", "sitemap.xml"),
}


def github_request(url, token, method="GET", data=None):
    """Fait une requete a l'API GitHub."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "PizzaNapoli-Deploy",
    }
    if data:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return {"error": e.code, "message": body}


def get_file_sha(token, repo, path, branch="main"):
    """Recupere le SHA d'un fichier existant (necessaire pour update)."""
    url = f"{API}/repos/{ORG}/{repo}/contents/{path}?ref={branch}"
    result = github_request(url, token)
    if "sha" in result:
        return result["sha"]
    return None


def push_file(token, repo, remote_path, content, branch="main"):
    """Pousse un fichier vers un repo GitHub."""
    url = f"{API}/repos/{ORG}/{repo}/contents/{remote_path}"

    # Encode en base64
    content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    # Verifie si le fichier existe deja
    sha = get_file_sha(token, repo, remote_path, branch)

    data = {
        "message": f"Update {remote_path} - Pizza Napoli livraison",
        "content": content_b64,
        "branch": branch,
    }
    if sha:
        data["sha"] = sha

    result = github_request(url, token, method="PUT", data=data)

    if "content" in result:
        return True, "OK"
    elif "error" in result:
        return False, result["message"]
    return False, str(result)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 deploy_to_github.py VOTRE_TOKEN_GITHUB")
        print()
        print("Pour creer un token : https://github.com/settings/tokens/new")
        print("Cochez 'repo' puis 'Generate token'")
        sys.exit(1)

    token = sys.argv[1]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    livraison_dir = os.path.join(script_dir, "livraison-site")

    print(f"=== Deploiement Pizza Napoli vers {ORG} ===\n")

    # Verification du token
    me = github_request(f"{API}/user", token)
    if "login" in me:
        print(f"Connecte en tant que : {me['login']}\n")
    else:
        print("ERREUR: Token invalide ou expire.")
        sys.exit(1)

    # Lire le style.css une seule fois
    style_path = os.path.join(livraison_dir, "style.css")
    with open(style_path, "r", encoding="utf-8") as f:
        style_content = f.read()

    success_count = 0
    error_count = 0

    # Deployer chaque fichier HTML
    for local_file, (repo, remote_file) in FILE_MAP.items():
        local_path = os.path.join(livraison_dir, local_file)
        if not os.path.exists(local_path):
            print(f"  SKIP {local_file} (fichier non trouve)")
            continue

        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Tente main puis master
        for branch in ["main", "master"]:
            ok, msg = push_file(token, repo, remote_file, content, branch)
            if ok:
                print(f"  OK   {local_file} -> {repo}/{remote_file} ({branch})")
                success_count += 1
                break
        else:
            print(f"  FAIL {local_file} -> {repo}/{remote_file}: {msg}")
            error_count += 1

        # Pousser style.css dans le meme repo
        for branch in ["main", "master"]:
            ok, msg = push_file(token, repo, "style.css", style_content, branch)
            if ok:
                print(f"  OK   style.css -> {repo}/style.css ({branch})")
                success_count += 1
                break
        else:
            print(f"  FAIL style.css -> {repo}/style.css: {msg}")
            error_count += 1

    # Fichiers extras (robots.txt, sitemap.xml)
    for local_file, (repo, remote_file) in EXTRA_FILES.items():
        local_path = os.path.join(livraison_dir, local_file)
        if not os.path.exists(local_path):
            continue

        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()

        for branch in ["main", "master"]:
            ok, msg = push_file(token, repo, remote_file, content, branch)
            if ok:
                print(f"  OK   {local_file} -> {repo}/{remote_file} ({branch})")
                success_count += 1
                break
        else:
            print(f"  FAIL {local_file} -> {repo}/{remote_file}: {msg}")
            error_count += 1

    print(f"\n=== Termine : {success_count} OK, {error_count} erreurs ===")


if __name__ == "__main__":
    main()
