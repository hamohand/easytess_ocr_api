"""
Script de test pour la conversion PDF vers image
"""
import sys
import os

# Ajouter le chemin du backend au PYTHONPATH
backend_path = os.path.join(os.path.dirname(__file__), 'easytess-backend')
sys.path.insert(0, backend_path)

from app.utils.pdf_utils import convert_pdf_to_image

def test_pdf_conversion():
    """
    Test de la conversion PDF
    """
    print("=" * 60)
    print("TEST DE CONVERSION PDF VERS IMAGE")
    print("=" * 60)
    
    # Vérifier que pypdfium2 est installé
    try:
        import pypdfium2
        print("✅ pypdfium2 est installé")
        print(f"   Version: {pypdfium2.__version__ if hasattr(pypdfium2, '__version__') else 'inconnue'}")
    except ImportError:
        print("❌ pypdfium2 n'est pas installé")
        print("   Installez-le avec: pip install pypdfium2")
        return False
    
    print("\n" + "-" * 60)
    print("INSTRUCTIONS POUR TESTER:")
    print("-" * 60)
    print("1. Placez un fichier PDF de test dans le dossier 'easytess-backend/uploads/'")
    print("2. Nommez-le 'test.pdf'")
    print("3. Relancez ce script")
    print()
    
    # Chercher un fichier PDF de test
    test_pdf = os.path.join(backend_path, 'uploads', 'test.pdf')
    
    if not os.path.exists(test_pdf):
        print(f"⚠️  Fichier de test non trouvé: {test_pdf}")
        print("   Créez un fichier 'test.pdf' dans le dossier uploads pour tester")
        return False
    
    print(f"✅ Fichier PDF trouvé: {test_pdf}")
    
    # Tester la conversion
    output_path = os.path.join(backend_path, 'uploads', 'test_converted.jpg')
    
    try:
        print(f"\n🔄 Conversion en cours...")
        result = convert_pdf_to_image(test_pdf, output_path, dpi=300)
        print(f"✅ Conversion réussie!")
        print(f"   Image créée: {result}")
        
        # Vérifier que le fichier existe
        if os.path.exists(result):
            file_size = os.path.getsize(result) / 1024  # En KB
            print(f"   Taille: {file_size:.2f} KB")
            
            # Vérifier les dimensions avec Pillow
            try:
                from PIL import Image
                with Image.open(result) as img:
                    width, height = img.size
                    print(f"   Dimensions: {width}x{height} pixels")
                    print(f"   Format: {img.format}")
            except Exception as e:
                print(f"   ⚠️  Impossible de lire les dimensions: {e}")
            
            return True
        else:
            print(f"❌ Le fichier n'a pas été créé")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de la conversion: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_upload():
    """
    Test de l'API d'upload avec un PDF
    """
    print("\n" + "=" * 60)
    print("TEST DE L'API D'UPLOAD")
    print("=" * 60)
    
    print("\nPour tester l'API avec un PDF:")
    print("1. Assurez-vous que le serveur backend est lancé (python run.py)")
    print("2. Utilisez curl ou Postman pour envoyer un PDF:")
    print()
    print("   curl -X POST http://localhost:8082/api/upload \\")
    print("        -F 'image=@chemin/vers/votre/fichier.pdf'")
    print()
    print("3. Vérifiez la réponse JSON avec le chemin de l'image convertie")

if __name__ == "__main__":
    print("\n🧪 TESTS DE SUPPORT PDF\n")
    
    # Test 1: Conversion PDF
    success = test_pdf_conversion()
    
    # Test 2: Instructions API
    test_api_upload()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTS TERMINÉS AVEC SUCCÈS")
    else:
        print("⚠️  TESTS INCOMPLETS - Voir les instructions ci-dessus")
    print("=" * 60)
    print()
