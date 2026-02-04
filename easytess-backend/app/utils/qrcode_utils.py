"""
Module pour la détection et le décodage de QR codes et codes-barres
"""
import cv2
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# Configuration pyzbar
PYZBAR_DISPONIBLE = False
try:
    from pyzbar import pyzbar
    PYZBAR_DISPONIBLE = True
    logger.info("✅ pyzbar disponible pour QR codes et codes-barres")
except ImportError:
    logger.warning("⚠️ pyzbar non disponible. Installez-le avec: pip install pyzbar")
except (OSError, FileNotFoundError) as e:
    logger.warning(f"⚠️ pyzbar installé mais DLL manquante: {e}")
    logger.info("ℹ️  Utilisation d'OpenCV pour les QR codes (codes-barres non supportés)")
except Exception as e:
    logger.warning(f"⚠️ Erreur chargement pyzbar: {e}")
    logger.info("ℹ️  Utilisation d'OpenCV pour les QR codes")

def decoder_qrcode(image_path, coords=None):
    """
    Détecte et décode les QR codes dans une image ou une zone spécifique.
    
    Args:
        image_path: Chemin vers l'image
        coords: [x1, y1, x2, y2] pour une zone spécifique (optionnel)
    
    Returns:
        dict: {
            'success': bool,
            'data': str (contenu du QR code),
            'type': str (type de code),
            'count': int (nombre de codes détectés),
            'all_codes': list (tous les codes si plusieurs)
        }
    """
    if not PYZBAR_DISPONIBLE:
        return {
            'success': False,
            'error': 'pyzbar non installé',
            'data': '',
            'type': 'none',
            'count': 0
        }
    
    try:
        # Charger l'image
        img = Image.open(image_path)
        img_array = np.array(img.convert('RGB'))
        
        # Si des coordonnées sont fournies, extraire la zone
        if coords:
            x1, y1, x2, y2 = coords
            img_w, img_h = img.size
            
            # Gérer les coordonnées relatives
            if all(v <= 1.0 for v in coords):
                x1, y1 = int(x1 * img_w), int(y1 * img_h)
                x2, y2 = int(x2 * img_w), int(y2 * img_h)
            
            # Sécurité
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(img_w, int(x2)), min(img_h, int(y2))
            
            # Extraire la zone
            img_array = img_array[y1:y2, x1:x2]
        
        # Détecter les codes
        decoded_objects = pyzbar.decode(img_array)
        
        if not decoded_objects:
            return {
                'success': False,
                'data': '',
                'type': 'none',
                'count': 0,
                'error': 'Aucun code détecté'
            }
        
        # Premier code détecté (principal)
        main_code = decoded_objects[0]
        
        # Tous les codes détectés
        all_codes = [
            {
                'data': obj.data.decode('utf-8'),
                'type': obj.type,
                'quality': obj.quality if hasattr(obj, 'quality') else None
            }
            for obj in decoded_objects
        ]
        
        return {
            'success': True,
            'data': main_code.data.decode('utf-8'),
            'type': main_code.type,
            'count': len(decoded_objects),
            'all_codes': all_codes
        }
        
    except Exception as e:
        logger.error(f"Erreur décodage QR code: {e}")
        return {
            'success': False,
            'error': str(e),
            'data': '',
            'type': 'none',
            'count': 0
        }

def decoder_qrcode_opencv(image_path, coords=None):
    """
    Alternative avec OpenCV QRCodeDetector (ne nécessite pas pyzbar).
    Fonctionne uniquement pour les QR codes (pas les codes-barres).
    
    Args:
        image_path: Chemin vers l'image
        coords: [x1, y1, x2, y2] pour une zone spécifique (optionnel)
    
    Returns:
        dict: Même format que decoder_qrcode
    """
    try:
        # Charger l'image
        img = cv2.imread(image_path)
        
        if img is None:
            # Essayer avec PIL puis convertir
            pil_img = Image.open(image_path)
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        # Si des coordonnées sont fournies, extraire la zone
        if coords:
            x1, y1, x2, y2 = coords
            img_h, img_w = img.shape[:2]
            
            # Gérer les coordonnées relatives
            if all(v <= 1.0 for v in coords):
                x1, y1 = int(x1 * img_w), int(y1 * img_h)
                x2, y2 = int(x2 * img_w), int(y2 * img_h)
            
            # Sécurité
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(img_w, int(x2)), min(img_h, int(y2))
            
            # Extraire la zone
            img = img[y1:y2, x1:x2]
        
        # Détecter le QR code
        detector = cv2.QRCodeDetector()
        data, bbox, straight_qrcode = detector.detectAndDecode(img)
        
        if data:
            return {
                'success': True,
                'data': data,
                'type': 'QRCODE',
                'count': 1,
                'all_codes': [{'data': data, 'type': 'QRCODE'}]
            }
        else:
            return {
                'success': False,
                'data': '',
                'type': 'none',
                'count': 0,
                'error': 'Aucun QR code détecté'
            }
            
    except Exception as e:
        logger.error(f"Erreur décodage QR code OpenCV: {e}")
        return {
            'success': False,
            'error': str(e),
            'data': '',
            'type': 'none',
            'count': 0
        }

def decoder_code_hybride(image_path, coords=None):
    """
    Essaie d'abord pyzbar (plus complet), puis OpenCV en fallback.
    
    Args:
        image_path: Chemin vers l'image
        coords: [x1, y1, x2, y2] pour une zone spécifique (optionnel)
    
    Returns:
        dict: Résultat du décodage
    """
    # Essai 1: pyzbar (supporte QR codes et codes-barres)
    if PYZBAR_DISPONIBLE:
        result = decoder_qrcode(image_path, coords)
        if result['success']:
            result['moteur'] = 'pyzbar'
            return result
    
    # Essai 2: OpenCV (QR codes uniquement)
    result = decoder_qrcode_opencv(image_path, coords)
    if result['success']:
        result['moteur'] = 'opencv'
        return result
    
    # Aucun code détecté
    return {
        'success': False,
        'data': '',
        'type': 'none',
        'count': 0,
        'error': 'Aucun code détecté avec pyzbar ni OpenCV',
        'moteur': 'aucun'
    }
