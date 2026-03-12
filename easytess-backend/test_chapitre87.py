"""
Recherche spécifique pour l'étiquette "Chapitre 87"
Affiche toutes les valeurs trouvées sous cette étiquette.
"""
import requests, json, re, os, glob

API_URL = "http://localhost:5000/api/extract-pdf"
pdfs = glob.glob(os.path.join(os.path.dirname(__file__), "uploads", "*chapitre_544-567.pdf"))
pdf_path = pdfs[0]

with open(pdf_path, 'rb') as f:
    response = requests.post(API_URL, files={"file": f})

content = response.json().get('contenu', [])

print("=" * 60)
print("VALEURS ASSOCIÉES À L'ÉTIQUETTE 'Chapitre 87'")
print("=" * 60)

found = False
for block in content:
    if block.get('type') == 'tableau':
        for ligne in block.get('lignes', []):
            if 'Chapitre 87' in ligne:
                found = True
                val = str(ligne['Chapitre 87'])
                # Afficher la ligne complète pour voir où est le code
                print(f"Page {block.get('page')}, Tab {block.get('numero')}:")
                print(f"  -> Valeur 'Chapitre 87' : \"{val}\"")
                print(f"  -> Ligne complète       : {ligne}")
                print("-" * 40)

if not found:
    print("Aucune ligne ne possède la clé 'Chapitre 87'")
