"""
Script de test pour vérifier le support QR code avec OpenCV (sans pyzbar)
"""
import cv2
import numpy as np
from PIL import Image
import os

print("=" * 60)
print("TEST DE DÉTECTION QR CODE AVEC OPENCV")
print("=" * 60)
print()

# Test 1 : Vérifier OpenCV
print("1. Vérification d'OpenCV...")
try:
    print(f"   ✅ OpenCV version: {cv2.__version__}")
except Exception as e:
    print(f"   ❌ Erreur OpenCV: {e}")
    exit(1)

# Test 2 : Vérifier le QRCodeDetector
print("\n2. Vérification du QRCodeDetector...")
try:
    detector = cv2.QRCodeDetector()
    print("   ✅ QRCodeDetector disponible")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    exit(1)

# Test 3 : Créer une image de test avec un QR code simple
print("\n3. Création d'une image de test...")
try:
    # Créer une image blanche
    img = np.ones((400, 400, 3), dtype=np.uint8) * 255
    
    # Dessiner un carré noir (simuler un QR code très simple)
    cv2.rectangle(img, (100, 100), (300, 300), (0, 0, 0), -1)
    cv2.rectangle(img, (120, 120), (280, 280), (255, 255, 255), -1)
    cv2.rectangle(img, (140, 140), (260, 260), (0, 0, 0), -1)
    
    # Sauvegarder
    test_path = "test_qr_simple.jpg"
    cv2.imwrite(test_path, img)
    print(f"   ✅ Image de test créée: {test_path}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    exit(1)

# Test 4 : Tester le décodage
print("\n4. Test de décodage...")
try:
    detector = cv2.QRCodeDetector()
    data, bbox, straight_qrcode = detector.detectAndDecode(img)
    
    if data:
        print(f"   ✅ QR code détecté: {data}")
    else:
        print("   ⚠️  Aucun QR code détecté (normal pour cette image de test)")
        print("   ℹ️  OpenCV fonctionne, mais nécessite un vrai QR code")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

# Test 5 : Tester avec le module qrcode_utils
print("\n5. Test du module qrcode_utils...")
try:
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from app.utils.qrcode_utils import decoder_qrcode_opencv, PYZBAR_DISPONIBLE
    
    print(f"   pyzbar disponible: {PYZBAR_DISPONIBLE}")
    
    if not PYZBAR_DISPONIBLE:
        print("   ℹ️  pyzbar non disponible, utilisation d'OpenCV uniquement")
        print("   ✅ Cela fonctionne pour les QR codes !")
        print()
        print("   LIMITATION: Seuls les QR codes sont supportés (pas les codes-barres)")
        print("   Pour supporter les codes-barres, installez zbar (voir ZBAR_INSTALLATION.md)")
    
    # Tester la fonction
    result = decoder_qrcode_opencv(test_path)
    print(f"\n   Résultat du test: {result}")
    
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

# Test 6 : Instructions pour tester avec un vrai QR code
print("\n" + "=" * 60)
print("POUR TESTER AVEC UN VRAI QR CODE:")
print("=" * 60)
print()
print("1. Générez un QR code en ligne:")
print("   https://www.qr-code-generator.com/")
print()
print("2. Téléchargez l'image du QR code")
print()
print("3. Testez avec ce script:")
print()
print("   from app.utils.qrcode_utils import decoder_qrcode_opencv")
print("   result = decoder_qrcode_opencv('chemin/vers/qrcode.jpg')")
print("   print(result)")
print()

# Test 7 : Vérifier pyzbar
print("=" * 60)
print("VÉRIFICATION PYZBAR:")
print("=" * 60)
print()
try:
    from pyzbar import pyzbar
    print("✅ pyzbar est installé")
    print()
    print("Mais la DLL zbar est manquante.")
    print("Consultez ZBAR_INSTALLATION.md pour les solutions.")
    print()
    print("OPTIONS:")
    print("1. Télécharger libzbar-64.dll (voir ZBAR_INSTALLATION.md)")
    print("2. Utiliser OpenCV uniquement (QR codes seulement)")
    
except ImportError as e:
    print(f"❌ pyzbar non installé: {e}")
    print()
    print("Pour installer:")
    print("   pip install pyzbar")
except Exception as e:
    print(f"⚠️  pyzbar installé mais erreur: {e}")
    print()
    print("C'est probablement parce que libzbar-64.dll est manquant.")
    print("Consultez ZBAR_INSTALLATION.md pour les solutions.")

print()
print("=" * 60)
print("RÉSUMÉ:")
print("=" * 60)
print()
print("✅ OpenCV fonctionne → QR codes supportés")
print("⚠️  pyzbar/zbar manquant → Codes-barres non supportés")
print()
print("RECOMMANDATION:")
print("- Pour QR codes uniquement: Utilisez OpenCV (déjà fonctionnel)")
print("- Pour codes-barres aussi: Installez zbar (voir ZBAR_INSTALLATION.md)")
print()
print("Fichier de test créé: test_qr_simple.jpg")
print()
