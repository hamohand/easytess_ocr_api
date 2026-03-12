"""
Vérification complète: cherche les codes XXXX.XX.XX.XX dans TOUS les blocs
(tableaux ET textes) et liste TOUTES les étiquettes/clés de colonnes.
"""
import requests, json, re, os, glob

API_URL = "http://localhost:5000/api/extract-pdf"
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
pdfs = glob.glob(os.path.join(uploads_dir, "*chapitre_544-567.pdf"))
pdf_path = pdfs[0]

CODE_PATTERN = re.compile(r'\d{4}\.\d{2}\.\d{2}\.\d{2}')

with open(pdf_path, 'rb') as f:
    response = requests.post(API_URL, files={"file": f})

data = response.json()
content = data.get('contenu', [])

# 1. Toutes les étiquettes (clés) uniques dans les tableaux
print("=" * 70)
print("TOUTES LES ÉTIQUETTES DE COLONNES TROUVÉES DANS LES TABLEAUX")
print("=" * 70)
all_keys = set()
for block in content:
    if block.get('type') == 'tableau':
        for ligne in block.get('lignes', []):
            all_keys.update(ligne.keys())

for k in sorted(all_keys):
    print(f"  🏷️  \"{k}\"")
print(f"\nTotal: {len(all_keys)} étiquettes uniques\n")

# 2. Blocs TEXTE contenant des codes tarifaires
print("=" * 70)
print("BLOCS TEXTE CONTENANT DES CODES TARIFAIRES")
print("=" * 70)
for block in content:
    if block.get('type') == 'texte':
        texte = block.get('contenu', '')
        if CODE_PATTERN.search(texte):
            codes = CODE_PATTERN.findall(texte)
            print(f"  Page {block.get('page')}: {codes[:5]}...")
            print(f"    Texte: \"{texte[:100]}\"")

# 3. Chercher spécifiquement "SECTION XVII" / "DOUANES"
print()
print("=" * 70)
print("RECHERCHE DE 'SECTION XVII' / 'DOUANES' DANS TOUS LES BLOCS")
print("=" * 70)
for block in content:
    if block.get('type') == 'texte':
        texte = block.get('contenu', '')
        if 'SECTION' in texte.upper() or 'DOUANES' in texte.upper():
            print(f"  📝 TEXTE Page {block.get('page')}: \"{texte[:120]}\"")
    elif block.get('type') == 'tableau':
        for ligne in block.get('lignes', []):
            for key, val in ligne.items():
                val_str = str(val).upper()
                if 'SECTION' in val_str or 'DOUANES' in val_str:
                    print(f"  📊 TABLEAU Page {block.get('page')}, Tab {block.get('numero')}, Clé \"{key}\": \"{val[:120]}\"")
