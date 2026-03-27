import os, sys, json, base64, re, shutil
from pathlib import Path

import anthropic

MENU = {
    "MARGHARITA": "Tomate, fromage",
    "ANCHOIS": "Tomate, fromage, anchois",
    "ROMAINE": "Tomate, fromage, jambon",
    "MERGUEZ": "Tomate, fromage, merguez",
    "CHORIZO": "Tomate, fromage, chorizo",
    "REINE": "Tomate, fromage, jambon, champignons",
    "ROYALE": "Tomate, fromage, jambon, champignons, oeuf",
    "CANADIENNE": "Tomate, fromage, bacon, oeuf",
    "EL PASO": "Tomate, fromage, chorizo, poivrons",
    "NORDISTE": "Tomate, fromage, jambon, champignons, maroilles",
    "FORESTIERE": "Tomate, fromage, lardons, oignons, champignons",
    "PAYSANNE": "Tomate, fromage, chevre, lardons, jambon cru",
    "MEGAROYALE": "Tomate, fromage, pommes de terre, jambon, champignons, oignons, oeuf",
    "COCHONAILLE": "Tomate, fromage, jambon, bacon, lardons, jambon cru, moutarde",
    "SWEET CHORIZO": "Tomate, fromage, chorizo, champignons, poivrons, oignons",
    "CAMPAGNARDE": "Tomate, fromage, lardons, oignons, champignons, chevre, creme",
    "TARTUFO": "Tomate, fromage, jambon, mozza di bufala, huile de truffe",
    "GRANDIOSA": "Tomate, jambon, champignons, mozza, huile de truffe",
    "MOZZA DI BUFALA": "Tomate, fromage, mozza di bufala, basilic",
    "MOZZA": "Tomate, fromage, mozzarella",
    "CHEVRE": "Tomate, fromage, chevre",
    "PARMESANE": "Tomate, parmesan, fromage, mozzarella, creme",
    "3 FRO": "Tomate, fromage, mozzarella, chevre",
    "4 FRO": "Tomate, fromage, mozzarella, roquefort, chevre",
    "MEGAFRO": "Tomate, fromage, mozzarella, roquefort, chevre, raclette",
    "CHEVRE-MIEL": "Tomate, fromage, chevre, miel",
    "PISSALADIERE": "Tomate, fromage, anchois, oignons",
    "CATALANE": "Tomate, fromage, thon",
    "FRUIT DE MER": "Tomate, fromage, fruits de mer",
    "THONCAPRE": "Tomate, fromage, thon, capres, persillade",
    "SAINT JACQUES": "Tomate, fromage, fruits de mer, noix de St Jacques, persillade",
    "MONTAGNARDE": "Tomate, fromage, raclette, reblochon",
    "PYRENEENNE": "Tomate, fromage, jambon, jambon cru, raclette",
    "SAVOYARDE": "Tomate, fromage, jambon cru, reblochon",
    "RACLON": "Tomate, fromage, jambon, bacon, pomme de terre, raclette",
    "MILANO": "Tomate, aubergines, fromage, chevre, persillade",
    "ACROPOLIS": "Tomate, fromage, aubergines, poivrons, mozzarella, basilic",
    "4 SAISONS": "Tomate, fromage, jambon, champignons, poivrons, artichaut",
    "VEGETARIENNE": "Tomate, aubergines, fromage, champignons, poivrons, artichaut, basilic",
    "MOUSSAKA": "Tomate, aubergines, viande hachee, fromage, mozzarella, basilic",
    "BUFFALO": "Tomate, fromage, viande hachee, oignons",
    "ARMENIENNE": "Tomate, fromage, viande hachee, oignons, poivrons",
    "BOLOGNAISE": "Tomate, fromage, viande hachee, oignons, champignons",
    "MANHATTAN": "Tomate, fromage, viande hachee, oignons, chevre",
    "BARAKO": "Tomate, fromage, viande hachee, bacon, oignons",
    "CIRCUS": "Tomate, fromage, viande hachee, chorizo, merguez, oignons",
    "WANABIE": "Tomate, fromage, viande hachee, oignons, champignons, sauce BBQ",
    "KEBAB": "Tomate, fromage, kebab, oignons, sauce blanche",
    "INDIANA": "Tomate, fromage, pomme de terre, poulet, sauce Curry",
    "CHILIENNE": "Tomate, fromage, poulet, poivrons, sauce Curry",
    "HAWAIENNE": "Tomate, fromage, poulet, poivrons, ananas, Curry",
    "FAR WEST": "Tomate, fromage, poulet, oignons, poivrons, champignons, sauce BBQ",
    "ORIENTALE": "Tomate, fromage, merguez, oignons, poivrons",
    "KIDECHIRE": "Tomate, fromage, chorizo, merguez, Tabasco",
    "BURGER": "Tomate, fromage, viande hachee, oignons, cheddar, cornichons, sauce Burger",
    "MEXICAINE": "Tomate, fromage, chorizo, poulet, cheddar, Tabasco",
    "APHRODITE": "Tomate, fromage, viande hachee, bacon, poulet, merguez, poivrons, sauce BBQ",
    "FLAMKEUCH": "Fromage, creme, lardons, oignons",
    "BERGERE": "Fromage, creme, chevre, champignons",
    "DAME BLANCHE": "Fromage, creme, chevre, mozzarella",
    "NAPOLI": "Fromage, creme, chevre, mozzarella, roquefort",
    "SWEETY-CHEVRE": "Fromage, creme, chevre, lardons, oignons, miel",
    "SAUMON": "Fromage, creme, saumon",
    "CAMEMBERT": "Fromage, creme, jambon, pomme de terre, oignons, camembert, persillade",
    "DAUPHINOISE": "Fromage, creme, viande hachee, pomme de terre, lardons, oignons, persillade",
    "TARTIFLETTE": "Fromage, creme, pomme de terre, lardons, oignons, reblochon",
    "XENA": "Fromage, creme, viande hachee, merguez, oignons, tabasco",
    "RAVIOLE BASILIC": "Fromage, creme, ravioles, basilic",
    "RAVIOLE SAUMON": "Fromage, creme, ravioles, saumon",
    "CHTI": "Fromage, creme, lardons, oignons, champignons, maroilles",
    "DELICIEUSE": "Fromage, creme, jambon, champignons, mozzarella",
    "BARAKA": "Fromage, creme, jambon cru, champignons, mozzarella, raclette",
    "MONT BLANC": "Fromage, creme, jambon, bacon, pomme de terre, raclette",
}

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def build_prompt():
    lines = [f"- {nom}: {ing}" for nom, ing in MENU.items()]
    return "\n".join(lines)


def identify(client, path, menu_text):
    ext = path.suffix.lower()
    mt = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
          "webp": "image/webp", "gif": "image/gif", "bmp": "image/png"}
    media = mt.get(ext.lstrip("."), "image/jpeg")
    data = base64.standard_b64encode(path.read_bytes()).decode()

    r = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}},
            {"type": "text", "text": f"""Identifie cette pizza parmi le menu suivant :
{menu_text}

Reponds UNIQUEMENT en JSON : {{"nom": "NOM_EXACT_DU_MENU", "confiance": 85}}
Si ce n'est pas une pizza du menu, utilise "nom": "INCONNU"."""}
        ]}]
    )
    m = re.search(r'\{[^}]+\}', r.content[0].text)
    if m:
        return json.loads(m.group())
    return {"nom": "INCONNU", "confiance": 0}


def safe_name(name):
    n = name.lower().strip().replace(" ", "_").replace("'", "").replace("-", "_")
    return re.sub(r'[^a-z0-9_]', '', n)


def main():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        env = Path(".env")
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        print("ERREUR: Definissez ANTHROPIC_API_KEY")
        print('  set ANTHROPIC_API_KEY=sk-ant-...')
        sys.exit(1)

    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("renommees")
    dst.mkdir(exist_ok=True)

    images = sorted([f for f in src.iterdir() if f.is_file() and f.suffix.lower() in EXTENSIONS])
    if not images:
        print(f"Aucune image dans {src}")
        return

    client = anthropic.Anthropic(api_key=key)
    menu_text = build_prompt()
    counts = {}

    print(f"\n{'='*50}")
    print(f"  {len(images)} photos a identifier")
    print(f"{'='*50}\n")

    for img in images:
        print(f"  {img.name} ...", end=" ", flush=True)
        try:
            res = identify(client, img, menu_text)
        except Exception as e:
            print(f"ERREUR: {e}")
            continue

        nom = res.get("nom", "INCONNU")
        conf = res.get("confiance", 0)
        sn = safe_name(nom) if conf >= 40 else "inconnu"

        counts[sn] = counts.get(sn, 0) + 1
        num = counts[sn]
        new_name = f"pizza_{sn}_{num:02d}{img.suffix.lower()}"
        dest = dst / new_name
        shutil.copy2(str(img), str(dest))

        tag = "OK" if conf >= 50 else "??"
        print(f"[{tag}] -> {new_name}  ({nom}, {conf}%)")

    print(f"\n{'='*50}")
    print(f"  Termine ! Fichiers dans : {dst}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
