"""
Script de test pour l'endpoint /api/extract-pdf-columns
Teste l'extraction filtrée des colonnes "Position & Sous" et "Désignation des Produits"
"""
import requests
import json
import os
import glob

API_URL = "http://localhost:5000/api/extract-pdf-columns"

# Trouver un PDF de test (chapitre douanes)
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
pdfs = glob.glob(os.path.join(uploads_dir, "*chapitre_544-567.pdf"))

if not pdfs:
    print("❌ Aucun PDF de test trouvé dans uploads/")
    exit(1)

pdf_path = pdfs[0]
print(f"📄 PDF de test: {os.path.basename(pdf_path)}")
print(f"   Taille: {os.path.getsize(pdf_path) / 1024:.0f} Ko")
print()

# ── Test 1: Colonnes par défaut ──
print("=" * 60)
print("TEST 1: Colonnes par défaut (Position & Sous + Désignation)")
print("=" * 60)

with open(pdf_path, 'rb') as f:
    response = requests.post(API_URL, files={"file": f})

if response.status_code == 200:
    data = response.json()
    print(f"✅ Succès: {data['nb_lignes']} lignes extraites")
    print(f"   Colonnes demandées: {data['colonnes_demandees']}")
    print()
    
    # Afficher les premières lignes
    for i, ligne in enumerate(data['lignes'][:10]):
        page = ligne.pop('_page', '?')
        tab = ligne.pop('_tableau', '?')
        cols = {k: v for k, v in ligne.items()}
        print(f"   [{i+1}] Page {page}, Tab {tab}: {cols}")
    
    if data['nb_lignes'] > 10:
        print(f"   ... et {data['nb_lignes'] - 10} lignes de plus")
    
    # Sauvegarder le résultat complet
    output_file = os.path.join(os.path.dirname(__file__), "result_filtered.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Résultat complet sauvegardé: {output_file}")
else:
    print(f"❌ Erreur {response.status_code}: {response.text}")

print()

# ── Test 2: Colonnes personnalisées ──
print("=" * 60)
print("TEST 2: Colonne unique (Désignation uniquement)")
print("=" * 60)

with open(pdf_path, 'rb') as f:
    response = requests.post(
        API_URL,
        files={"file": f},
        data={"columns": json.dumps(["Désignation"])}
    )

if response.status_code == 200:
    data = response.json()
    print(f"✅ Succès: {data['nb_lignes']} lignes extraites")
    for i, ligne in enumerate(data['lignes'][:5]):
        ligne.pop('_page', None)
        ligne.pop('_tableau', None)
        print(f"   [{i+1}] {ligne}")
else:
    print(f"❌ Erreur {response.status_code}: {response.text}")
