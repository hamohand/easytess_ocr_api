"""
Script de test pour le nouvel endpoint /api/extract-tariff-codes
Recherche dynamique de lignes contenant un unique code tarifaire.
"""
import requests
import json
import os
import glob

API_URL = "http://localhost:5000/api/extract-tariff-codes"

# Trouver un PDF de test
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
pdfs = glob.glob(os.path.join(uploads_dir, "*chapitre_544-567.pdf"))

if not pdfs:
    print("❌ Aucun PDF de test trouvé")
    exit(1)

pdf_path = pdfs[0]
print(f"📄 Test avec le PDF: {os.path.basename(pdf_path)}")
print("=" * 60)

with open(pdf_path, 'rb') as f:
    response = requests.post(API_URL, files={"file": f})

if response.status_code == 200:
    data = response.json()
    print(f"✅ {data.get('nb_lignes_trouvees', 0)} lignes trouvées !\n")
    
    donnees = data.get('donnees', [])
    for i, item in enumerate(donnees[:5]):
        print(f"--- Résultat {i+1} ---")
        for k, v in item.items():
            print(f"  {k}: {str(v)[:80]}{'...' if len(str(v)) > 80 else ''}")
        print()
        
    if len(donnees) > 5:
        print(f"... et {len(donnees) - 5} autres objets JSON complets.")
        
    # Sauvegarde du JSON cible
    out_file = os.path.join(os.path.dirname(__file__), "resultat_lignes_completes.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Résultat complet (JSON cible) sauvegardé dans: {out_file}")
    
else:
    print(f"❌ Erreur API ({response.status_code}): {response.text}")
