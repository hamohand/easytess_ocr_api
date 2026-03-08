"""
Script de test pour les fonctionnalités d'extraction et conversion de documents.
Teste:
  1. Extraction PDF (texte + tableaux)
  2. Extraction DOCX (texte + tableaux)
  3. Conversion PDF → DOCX
  4. Route unifiée (simulation)

Usage: python test_document_extraction.py [fichier.pdf ou fichier.docx]
       python test_document_extraction.py  (utilise les fichiers de test intégrés)
"""
import sys
import os
import json
import tempfile

# Ajouter le répertoire courant au path
sys.path.insert(0, os.path.dirname(__file__))


def test_pdf_extraction(pdf_path):
    """Test 1: Extraction du contenu PDF."""
    from app.services.pdf_extractor import extract_pdf

    print("\n" + "=" * 60)
    print("TEST 1: Extraction PDF")
    print("=" * 60)
    print(f"Fichier: {pdf_path}")

    content, stats = extract_pdf(pdf_path, strategy="auto", include_metadata=True)

    print(f"\n📊 Statistiques:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

    print(f"\n📄 Contenu extrait ({len(content)} blocs):")
    for i, block in enumerate(content):
        if block["type"] == "texte":
            text = block["contenu"][:100] + "..." if len(block.get("contenu", "")) > 100 else block["contenu"]
            print(f"  [{i}] 📝 TEXTE (p.{block.get('page', '?')}): {text}")
        elif block["type"] == "tableau":
            meta = block.get("metadata", {})
            print(f"  [{i}] 📊 TABLEAU #{block['numero']} (p.{block.get('page', '?')}) "
                  f"— {meta.get('nb_lignes', '?')} lignes × {meta.get('nb_colonnes', '?')} cols "
                  f"{'[EN-TÊTE]' if meta.get('a_entete') else ''}")
            if meta.get("entetes"):
                print(f"       En-têtes: {meta['entetes']}")
            for j, ligne in enumerate(block["lignes"][:3]):
                print(f"       Ligne {j}: {ligne}")
            if len(block["lignes"]) > 3:
                print(f"       ... et {len(block['lignes']) - 3} lignes de plus")

    return content, stats


def test_docx_extraction(docx_path):
    """Test 2: Extraction du contenu DOCX."""
    from app.services.docx_extractor import extract_document

    print("\n" + "=" * 60)
    print("TEST 2: Extraction DOCX")
    print("=" * 60)
    print(f"Fichier: {docx_path}")

    content = extract_document(docx_path)

    print(f"\n📄 Contenu extrait ({len(content)} blocs):")
    for i, block in enumerate(content):
        if block["type"] == "texte":
            text = block["contenu"][:100] + "..." if len(block.get("contenu", "")) > 100 else block["contenu"]
            print(f"  [{i}] 📝 TEXTE: {text}")
        elif block["type"] == "tableau":
            print(f"  [{i}] 📊 TABLEAU #{block['numero']} — {len(block['lignes'])} lignes")
            for j, ligne in enumerate(block["lignes"][:3]):
                print(f"       Ligne {j}: {ligne}")
            if len(block["lignes"]) > 3:
                print(f"       ... et {len(block['lignes']) - 3} lignes de plus")

    return content


def test_pdf_to_docx(pdf_path):
    """Test 3: Conversion PDF → DOCX."""
    from app.services.pdf_to_docx import convert_pdf_to_docx

    print("\n" + "=" * 60)
    print("TEST 3: Conversion PDF → DOCX")
    print("=" * 60)
    print(f"Fichier source: {pdf_path}")

    # Créer un fichier temporaire pour la sortie
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
        output_path = tmp.name

    try:
        result_path, stats = convert_pdf_to_docx(pdf_path, output_path)

        file_size = os.path.getsize(result_path)
        print(f"\n✅ Conversion réussie!")
        print(f"   Fichier créé: {result_path}")
        print(f"   Taille: {file_size:,} octets")
        print(f"   Stats: {json.dumps(stats, indent=2, ensure_ascii=False)}")

        # Vérifier que le DOCX est lisible
        from app.services.docx_extractor import extract_document
        verification = extract_document(result_path)
        print(f"\n🔍 Vérification du DOCX généré: {len(verification)} blocs trouvés")
        for i, block in enumerate(verification[:5]):
            if block["type"] == "texte":
                print(f"  [{i}] 📝 {block['contenu'][:80]}")
            elif block["type"] == "tableau":
                print(f"  [{i}] 📊 Tableau #{block['numero']} — {len(block['lignes'])} lignes")

        return result_path

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        raise
    finally:
        # Nettoyer
        if os.path.exists(output_path):
            os.remove(output_path)
            print(f"   Fichier temporaire nettoyé.")


def test_strategies(pdf_path):
    """Test 4: Comparaison des stratégies de détection."""
    from app.services.pdf_extractor import extract_pdf

    print("\n" + "=" * 60)
    print("TEST 4: Comparaison des stratégies")
    print("=" * 60)
    print(f"Fichier: {pdf_path}")

    for strategy in ["standard", "text", "lines_strict", "auto"]:
        try:
            content, stats = extract_pdf(pdf_path, strategy=strategy)
            nb_t = stats["nb_textes"]
            nb_tab = stats["nb_tableaux"]
            print(f"  {strategy:15s}: {nb_t} textes, {nb_tab} tableaux, "
                  f"{stats['total_blocs']} blocs total")
        except Exception as e:
            print(f"  {strategy:15s}: ❌ Erreur — {e}")


def create_test_pdf():
    """Crée un PDF de test avec texte et tableaux."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        print("⚠️ reportlab non disponible, impossible de créer un PDF de test")
        return None

    pdf_path = os.path.join(tempfile.gettempdir(), "test_extraction.pdf")

    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Titre
    elements.append(Paragraph("Document de Test — Extraction", styles['Title']))
    elements.append(Spacer(1, 20))

    # Texte
    elements.append(Paragraph(
        "Ce document contient du texte et des tableaux pour tester "
        "les fonctionnalités d'extraction EasyTess.",
        styles['Normal']
    ))
    elements.append(Spacer(1, 15))

    # Tableau 1
    data1 = [
        ['Nom', 'Prénom', 'Ville'],
        ['Dupont', 'Jean', 'Paris'],
        ['Martin', 'Sophie', 'Lyon'],
        ['Bernard', 'Pierre', 'Marseille'],
    ]
    t1 = Table(data1, colWidths=[150, 120, 120])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(t1)
    elements.append(Spacer(1, 15))

    # Plus de texte
    elements.append(Paragraph(
        "Voici un deuxième paragraphe entre les tableaux.",
        styles['Normal']
    ))
    elements.append(Spacer(1, 15))

    # Tableau 2
    data2 = [
        ['Produit', 'Quantité', 'Prix'],
        ['Widget A', '100', '15.50 €'],
        ['Widget B', '250', '8.20 €'],
    ]
    t2 = Table(data2, colWidths=[150, 100, 100])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(t2)

    doc.build(elements)
    print(f"📄 PDF de test créé: {pdf_path}")
    return pdf_path


def main():
    print("🧪 Test des fonctionnalités d'extraction de documents EasyTess")
    print("=" * 60)

    # Déterminer les fichiers à tester
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if not os.path.exists(filepath):
            print(f"❌ Fichier non trouvé: {filepath}")
            sys.exit(1)

        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.pdf':
            test_pdf_extraction(filepath)
            test_strategies(filepath)
            test_pdf_to_docx(filepath)
        elif ext == '.docx':
            test_docx_extraction(filepath)
        else:
            print(f"❌ Extension non supportée: {ext}")
            sys.exit(1)
    else:
        # Tests avec fichiers générés
        print("\nAucun fichier spécifié. Tentative de création de fichiers de test...")

        # Test DOCX avec le générateur existant
        docx_test = os.path.join(os.path.dirname(__file__), "test_document.docx")
        if os.path.exists(docx_test):
            test_docx_extraction(docx_test)
        else:
            print("⚠️ test_document.docx non trouvé. Lancez d'abord: python generate_test_docx.py")

        # Test PDF
        pdf_test = create_test_pdf()
        if pdf_test:
            test_pdf_extraction(pdf_test)
            test_strategies(pdf_test)
            test_pdf_to_docx(pdf_test)
            os.remove(pdf_test)
            print(f"\n🧹 PDF de test nettoyé.")

    print("\n" + "=" * 60)
    print("🎉 Tests terminés !")


if __name__ == '__main__':
    main()
