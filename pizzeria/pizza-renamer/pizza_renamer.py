#!/usr/bin/env python3
"""
Pizza Photo Renamer - Reconnaissance automatique de pizzas par IA.

Modes d'utilisation :
  1. MANUEL   : python3 pizza_renamer.py              → traite les photos dans photos_a_renommer/
  2. AUTO     : python3 pizza_renamer.py --watch       → surveille le dossier et renomme automatiquement
  3. FICHIER  : python3 pizza_renamer.py photo.jpg     → traite un fichier spécifique

Nécessite : ANTHROPIC_API_KEY dans l'environnement ou dans un fichier .env
"""

import os
import sys
import json
import base64
import shutil
import argparse
import time
import re
from pathlib import Path
from datetime import datetime

import anthropic
from PIL import Image

# --- Configuration ---
SCRIPT_DIR = Path(__file__).parent.resolve()
MENU_PATH = SCRIPT_DIR / "menu_pizzas.json"
INPUT_DIR = SCRIPT_DIR / "photos_a_renommer"
OUTPUT_DIR = SCRIPT_DIR / "photos_renommees"
LOG_FILE = SCRIPT_DIR / "renamer.log"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB pour l'API


def load_api_key():
    """Charge la clé API depuis l'environnement ou un fichier .env."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    env_file = SCRIPT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def load_menu():
    """Charge le menu de pizzas et retourne la liste complète des noms."""
    with open(MENU_PATH, "r", encoding="utf-8") as f:
        menu = json.load(f)
    pizzas = []
    for category, items in menu.items():
        for pizza in items:
            pizzas.append({
                "nom": pizza["nom"],
                "categorie": category,
                "ingredients": pizza["ingredients"]
            })
    return pizzas


def build_pizza_names_list(pizzas):
    """Construit la liste des noms pour le prompt."""
    return "\n".join(f"- {p['nom']} ({p['categorie']}): {p['ingredients']}" for p in pizzas)


def encode_image(image_path: Path) -> tuple[str, str]:
    """Encode une image en base64, la redimensionne si trop grande."""
    ext = image_path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
        ".gif": "image/gif", ".bmp": "image/png",
    }
    media_type = media_types.get(ext, "image/jpeg")

    file_size = image_path.stat().st_size
    if file_size > MAX_IMAGE_SIZE:
        img = Image.open(image_path)
        img.thumbnail((1600, 1600), Image.LANCZOS)
        from io import BytesIO
        buffer = BytesIO()
        save_format = "PNG" if ext == ".png" else "JPEG"
        img.save(buffer, format=save_format, quality=85)
        data = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")
    else:
        data = base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")

    return data, media_type


def identify_pizza(client, image_path: Path, pizza_list_text: str) -> dict:
    """Utilise Claude pour identifier la pizza sur la photo."""
    image_data, media_type = encode_image(image_path)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": f"""Tu es un expert en identification de pizzas pour une pizzeria.
Analyse cette photo et identifie quelle pizza du menu elle représente.

Voici la liste complète des pizzas du menu :
{pizza_list_text}

IMPORTANT : Réponds UNIQUEMENT en JSON valide avec ce format exact :
{{"nom": "NOM_DE_LA_PIZZA", "confiance": 85, "raison": "courte explication"}}

- "nom" doit correspondre EXACTEMENT à un nom du menu ci-dessus
- "confiance" est un pourcentage de 0 à 100
- Si tu ne peux pas identifier la pizza ou si ce n'est pas une photo de pizza, utilise "nom": "INCONNU"
"""
                }
            ],
        }],
    )

    text = response.content[0].text.strip()
    # Extraire le JSON même s'il y a du texte autour
    json_match = re.search(r'\{[^}]+\}', text)
    if json_match:
        return json.loads(json_match.group())
    return {"nom": "INCONNU", "confiance": 0, "raison": "Impossible de parser la réponse"}


def sanitize_filename(name: str) -> str:
    """Nettoie un nom pour l'utiliser comme nom de fichier."""
    name = name.lower().strip()
    name = name.replace(" ", "_").replace("'", "")
    name = re.sub(r'[^a-z0-9_\-]', '', name)
    return name


def rename_photo(image_path: Path, result: dict, output_dir: Path) -> Path:
    """Renomme et déplace la photo selon le résultat de l'identification."""
    pizza_name = sanitize_filename(result["nom"])
    confiance = result.get("confiance", 0)
    ext = image_path.suffix.lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if pizza_name == "inconnu" or confiance < 50:
        new_name = f"inconnu_{timestamp}{ext}"
    else:
        new_name = f"pizza_{pizza_name}_{timestamp}{ext}"

    # Éviter les doublons
    dest = output_dir / new_name
    counter = 1
    while dest.exists():
        stem = dest.stem
        dest = output_dir / f"{stem}_{counter}{ext}"
        counter += 1

    shutil.move(str(image_path), str(dest))
    return dest


def log_result(image_path: Path, dest_path: Path, result: dict):
    """Enregistre le résultat dans le fichier de log."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "original": str(image_path),
        "renamed": str(dest_path),
        "pizza": result.get("nom", "INCONNU"),
        "confiance": result.get("confiance", 0),
        "raison": result.get("raison", ""),
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def process_single(client, image_path: Path, pizza_list_text: str, output_dir: Path):
    """Traite une seule image."""
    print(f"  Analyse de : {image_path.name} ...", end=" ", flush=True)
    result = identify_pizza(client, image_path, pizza_list_text)
    dest = rename_photo(image_path, result, output_dir)
    log_result(image_path, dest, result)

    emoji = "✅" if result.get("confiance", 0) >= 50 else "❓"
    print(f"{emoji} → {dest.name}  ({result['nom']}, confiance: {result.get('confiance', 0)}%)")
    if result.get("raison"):
        print(f"     Raison : {result['raison']}")
    return result


def process_directory(client, input_dir: Path, output_dir: Path, pizza_list_text: str):
    """Traite toutes les images d'un dossier."""
    images = [f for f in input_dir.iterdir()
              if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS]

    if not images:
        print(f"Aucune image trouvée dans {input_dir}")
        return

    print(f"\n{'='*60}")
    print(f"  {len(images)} image(s) à traiter")
    print(f"{'='*60}\n")

    for img in sorted(images):
        process_single(client, img, pizza_list_text, output_dir)
        print()

    print(f"{'='*60}")
    print(f"  Terminé ! Photos renommées dans : {output_dir}")
    print(f"  Log disponible : {LOG_FILE}")
    print(f"{'='*60}")


def watch_directory(client, input_dir: Path, output_dir: Path, pizza_list_text: str):
    """Surveille le dossier et traite automatiquement les nouvelles photos."""
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class PizzaHandler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            path = Path(event.src_path)
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                return
            # Attendre que le fichier soit complètement écrit
            time.sleep(1)
            try:
                process_single(client, path, pizza_list_text, output_dir)
            except Exception as e:
                print(f"  Erreur pour {path.name}: {e}")

    observer = Observer()
    observer.schedule(PizzaHandler(), str(input_dir), recursive=False)
    observer.start()

    print(f"\n{'='*60}")
    print(f"  Mode surveillance actif")
    print(f"  Dossier surveillé : {input_dir}")
    print(f"  Déposez vos photos de pizza dedans !")
    print(f"  Ctrl+C pour arrêter")
    print(f"{'='*60}\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nSurveillance arrêtée.")
    observer.join()


def main():
    parser = argparse.ArgumentParser(
        description="Renomme automatiquement les photos de pizza selon le menu"
    )
    parser.add_argument("files", nargs="*", help="Photos à traiter (optionnel)")
    parser.add_argument("--watch", "-w", action="store_true",
                        help="Surveille le dossier et traite les nouvelles photos")
    parser.add_argument("--input", "-i", type=Path, default=INPUT_DIR,
                        help=f"Dossier d'entrée (défaut: {INPUT_DIR})")
    parser.add_argument("--output", "-o", type=Path, default=OUTPUT_DIR,
                        help=f"Dossier de sortie (défaut: {OUTPUT_DIR})")
    args = parser.parse_args()

    # Vérifier la clé API
    api_key = load_api_key()
    if not api_key:
        print("ERREUR : Clé API Anthropic manquante !")
        print("  → Définissez ANTHROPIC_API_KEY dans l'environnement")
        print(f"  → Ou créez un fichier {SCRIPT_DIR / '.env'} avec :")
        print('     ANTHROPIC_API_KEY=sk-ant-...')
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Charger le menu
    pizzas = load_menu()
    pizza_list_text = build_pizza_names_list(pizzas)
    print(f"Menu chargé : {len(pizzas)} pizzas référencées")

    # Créer les dossiers si nécessaire
    args.input.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)

    if args.files:
        # Mode fichier(s) spécifique(s)
        for f in args.files:
            path = Path(f)
            if not path.exists():
                print(f"Fichier introuvable : {f}")
                continue
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                print(f"Format non supporté : {f}")
                continue
            process_single(client, path, pizza_list_text, args.output)
    elif args.watch:
        watch_directory(client, args.input, args.output, pizza_list_text)
    else:
        process_directory(client, args.input, args.output, pizza_list_text)


if __name__ == "__main__":
    main()
