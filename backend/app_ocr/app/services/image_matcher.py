"""
image_matcher.py - Détection robuste de template image (ORB + Multi-Scale Pixel Matching).

Améliorations vs version précédente:
- ORB: min_matches 10→5, nfeatures 1000→2000
- Pixel matching: multi-échelle (50% à 200%)
- Pré-traitement: CLAHE (normalisation du contraste)
- Meilleur logging pour le diagnostic
"""
import cv2
import numpy as np
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _preprocess_image(img_gray):
    """
    Pré-traitement pour améliorer la détection:
    - CLAHE (Contrast Limited Adaptive Histogram Equalization) pour normaliser le contraste
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(img_gray)


def find_template_orb(image_path: str, template_path: str, min_matches: int = 5) -> dict:
    """
    Détection robuste de template image avec 2 méthodes en cascade:
    
    1. ORB (Oriented FAST and Rotated BRIEF) — Invariant à l'échelle et rotation
    2. Multi-Scale Pixel Matching — Teste le template à plusieurs échelles
    
    Args:
        image_path: Chemin de l'image cible (où chercher).
        template_path: Chemin du template à trouver.
        min_matches: Nombre minimum de correspondances ORB (défaut: 5).
    
    Returns:
        dict: {
            'found': bool,
            'x': float,  # Centre X (0-1 relatif)
            'y': float,  # Centre Y (0-1 relatif)
            'x_min': float,  # Bounding box min X
            'y_min': float,
            'x_max': float,
            'y_max': float,
            'confidence': float,  # Score de confiance (0-1, 1 = parfait)
            'method': str,  # 'orb' ou 'pixel_multiscale'
            'scale': float  # Échelle où le template a été trouvé (1.0 = même taille)
        }
    """
    try:
        # Charger les images en niveaux de gris
        img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
        
        if img is None:
            logger.error(f"Could not load target image: {image_path}")
            return {'found': False, 'error': 'Could not load target image'}
        
        if template is None:
            logger.error(f"Could not load template image: {template_path}")
            return {'found': False, 'error': 'Could not load template image'}
            
        h, w = img.shape
        th, tw = template.shape
        
        # Pré-traitement CLAHE pour améliorer le contraste
        img_processed = _preprocess_image(img)
        template_processed = _preprocess_image(template)

        # --- Méthode 1: ORB (Feature Invariant) ---
        orb_result = _try_orb_matching(img_processed, template_processed, w, h, tw, th, min_matches)
        if orb_result.get('found'):
            return orb_result
        orb_error = orb_result.get('error', 'Unknown')
            
        # --- Méthode 2: Multi-Scale Pixel Matching ---
        logger.info(f"⚠️ ORB échoué ({orb_error}) → Tentative Pixel Matching multi-échelle...")
        pixel_result = _try_multiscale_pixel_matching(img_processed, template_processed, w, h, tw, th)
        if pixel_result.get('found'):
            return pixel_result
        pixel_error = pixel_result.get('error', 'Unknown')

        # --- Méthode 3: Edge Matching (contours Canny + matchTemplate multi-échelle) ---
        # Même algorithme que Pixel mais sur des cartes de contours → invariant couleur/texture
        logger.info(f"⚠️ Pixel échoué ({pixel_error}) → Tentative Edge Matching (contours)...")
        edge_result = _try_edge_matching(img_processed, template_processed, w, h, tw, th)
        if edge_result.get('found'):
            return edge_result
        edge_error = edge_result.get('error', 'Unknown')

        # Toutes les méthodes ont échoué
        logger.warning(f"❌ Template non trouvé. ORB: {orb_error}. Pixel: {pixel_error}. Edge: {edge_error}")
        return {'found': False, 'error': f"ORB: {orb_error}. Pixel: {pixel_error}. Edge: {edge_error}"}

    except Exception as e:
        logger.error(f"Error in template matching: {e}")
        return {'found': False, 'error': str(e)}


def _try_orb_matching(img, template, w, h, tw, th, min_matches):
    """
    Méthode 1: ORB Feature Matching.
    Invariant à l'échelle et la rotation.
    """
    try:
        # Plus de features pour de meilleurs résultats
        orb = cv2.ORB_create(nfeatures=2000)
        kp1, des1 = orb.detectAndCompute(template, None)
        kp2, des2 = orb.detectAndCompute(img, None)
        
        n_kp_template = len(kp1) if kp1 else 0
        n_kp_image = len(kp2) if kp2 else 0
        
        if des1 is None or n_kp_template < 4 or des2 is None or n_kp_image < 4:
            return {'found': False, 'error': f"Features insuffisantes (Template: {n_kp_template}, Image: {n_kp_image})"}
        
        # BFMatcher avec crossCheck pour éliminer les doublons
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)
        
        if len(matches) < min_matches:
            return {'found': False, 'error': f"Matches insuffisants: {len(matches)}/{min_matches}"}
        
        # Prendre les meilleurs matches (2x min_matches, max 50)
        good_matches = matches[:min(min_matches * 3, len(matches), 50)]
        
        # Extraire les positions des matches
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        
        # Calculer l'homographie pour la bounding box précise
        is_valid_transform = False
        if len(good_matches) >= 4:
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            
            if M is not None:
                pts_corners = np.float32([[0, 0], [0, th-1], [tw-1, th-1], [tw-1, 0]]).reshape(-1, 1, 2)
                dst_corners = cv2.perspectiveTransform(pts_corners, M)
                
                area = cv2.contourArea(dst_corners)
                orig_area = tw * th
                is_convex = cv2.isContourConvex(np.int32(dst_corners))
                
                if is_convex and (0.1 * orig_area < area < 10.0 * orig_area):
                    is_valid_transform = True
                    center = np.mean(dst_corners[:, 0, :], axis=0)
                    x_min = np.min(dst_corners[:, 0, 0])
                    y_min = np.min(dst_corners[:, 0, 1])
                    x_max = np.max(dst_corners[:, 0, 0])
                    y_max = np.max(dst_corners[:, 0, 1])
                    
        if not is_valid_transform:
            # Fallback: utiliser le centroïde des keypoints
            pts = dst_pts.reshape(-1, 2)
            center = pts.mean(axis=0)
            x_min, y_min = pts.min(axis=0)
            x_max, y_max = pts.max(axis=0)
            
        avg_distance = np.mean([m.distance for m in good_matches])
        confidence = float(1.0 - (avg_distance / 256))
        
        result = {
            'found': True,
            'x': float(center[0] / w),
            'y': float(center[1] / h),
            'x_min': float(max(0, x_min) / w),
            'y_min': float(max(0, y_min) / h),
            'x_max': float(min(w, x_max) / w),
            'y_max': float(min(h, y_max) / h),
            'confidence': confidence,
            'method': 'orb',
            'scale': 1.0,
            'source': 'image_template'
        }
        logger.info(
            f"✅ ORB: Template trouvé à ({result['x']:.3f}, {result['y']:.3f}) "
            f"avec {len(good_matches)} matches, confiance={confidence:.2f}"
        )
        return result
        
    except Exception as e:
        return {'found': False, 'error': str(e)}


def _try_multiscale_pixel_matching(img, template, w, h, tw, th):
    """
    Méthode 2: Multi-Scale Pixel Matching.
    Teste le template à plusieurs échelles pour gérer les différences de résolution.
    
    Échelles testées: 50% à 200% par pas de 10%
    """
    # Définir les échelles à tester
    # On commence par 1.0 (échelle originale) puis on s'en éloigne progressivement
    scales = [1.0]
    for delta in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        scales.append(1.0 + delta)  # Plus grand
        scales.append(1.0 - delta)  # Plus petit (min 0.1)
    scales = [s for s in scales if s >= 0.2]  # Éliminer les échelles trop petites
    scales = sorted(set(scales))  # Dédupliquer et trier
    
    best_val = -1
    best_result = None
    best_scale = 1.0
    threshold = 0.60  # Seuil de confiance minimum (assoupli vs 0.65 avant)
    
    for scale in scales:
        # Redimensionner le template à cette échelle
        new_tw = int(tw * scale)
        new_th = int(th * scale)
        
        # Vérifier que le template redimensionné est valide
        if new_tw < 5 or new_th < 5:
            continue  # Template trop petit
        if new_tw > w or new_th > h:
            continue  # Template plus grand que l'image
        
        try:
            resized_template = cv2.resize(template, (new_tw, new_th), interpolation=cv2.INTER_AREA)
            
            res = cv2.matchTemplate(img, resized_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            if max_val > best_val:
                best_val = max_val
                best_scale = scale
                best_result = {
                    'top_left': max_loc,
                    'tw': new_tw,
                    'th': new_th,
                }
        except Exception:
            continue
    
    if best_val >= threshold and best_result:
        top_left = best_result['top_left']
        matched_tw = best_result['tw']
        matched_th = best_result['th']
        
        bottom_right = (top_left[0] + matched_tw, top_left[1] + matched_th)
        center_x = top_left[0] + matched_tw / 2
        center_y = top_left[1] + matched_th / 2
        
        result = {
            'found': True,
            'x': float(center_x / w),
            'y': float(center_y / h),
            'x_min': float(top_left[0] / w),
            'y_min': float(top_left[1] / h),
            'x_max': float(bottom_right[0] / w),
            'y_max': float(bottom_right[1] / h),
            'confidence': float(best_val),
            'method': 'pixel_multiscale',
            'scale': best_scale,
            'source': 'image_template'
        }
        logger.info(
            f"✅ Pixel Multi-Scale: Template trouvé à ({result['x']:.3f}, {result['y']:.3f}) "
            f"échelle={best_scale:.1f}x, confiance={best_val:.2f}"
        )
        return result
    else:
        return {
            'found': False, 
            'error': f"Meilleure confiance={best_val:.2f} à échelle={best_scale:.1f}x (seuil={threshold})"
        }


def _to_edges(img_gray):
    """
    Convertit une image en niveaux de gris en carte de contours Canny.
    Utilise des seuils adaptatifs basés sur la médiane de l'image.
    """
    blurred = cv2.GaussianBlur(img_gray, (5, 5), 0)
    median = np.median(blurred)
    low = int(max(0, 0.4 * median))
    high = int(min(255, 1.4 * median))
    return cv2.Canny(blurred, low, high)


def _try_edge_matching(img, template, w, h, tw, th):
    """
    Méthode 3: Edge Matching multi-échelle.
    
    Même principe que le Pixel Matching multi-échelle, mais appliqué sur des
    cartes de contours Canny au lieu des pixels bruts.
    
    Avantages:
    - Invariant à la couleur et à la texture (seuls les contours comptent)
    - Très bon pour les formes distinctives (cartes, logos, symboles)
    - Même précision de localisation que cv2.matchTemplate
    """
    # Convertir en cartes de contours
    img_edges = _to_edges(img)
    template_edges = _to_edges(template)
    
    # Vérifier qu'il y a assez de contours dans le template
    edge_density = np.count_nonzero(template_edges) / template_edges.size
    if edge_density < 0.01:  # Moins de 1% de pixels de contour
        return {'found': False, 'error': f"Template sans contours significatifs (densité={edge_density:.3f})"}
    
    # Mêmes échelles que le pixel matching
    scales = [1.0]
    for delta in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        scales.append(1.0 + delta)
        scales.append(1.0 - delta)
    scales = [s for s in scales if s >= 0.2]
    scales = sorted(set(scales))
    
    best_val = -1
    best_result = None
    best_scale = 1.0
    threshold = 0.30  # Seuil plus bas que pixel (corrélation sur edges est naturellement plus basse)
    
    for scale in scales:
        new_tw = int(tw * scale)
        new_th = int(th * scale)
        
        if new_tw < 5 or new_th < 5:
            continue
        if new_tw > w or new_th > h:
            continue
        
        try:
            resized_edges = cv2.resize(template_edges, (new_tw, new_th), interpolation=cv2.INTER_AREA)
            
            res = cv2.matchTemplate(img_edges, resized_edges, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            if max_val > best_val:
                best_val = max_val
                best_scale = scale
                best_result = {
                    'top_left': max_loc,
                    'tw': new_tw,
                    'th': new_th,
                }
        except Exception:
            continue
    
    if best_val >= threshold and best_result:
        top_left = best_result['top_left']
        matched_tw = best_result['tw']
        matched_th = best_result['th']
        
        bottom_right = (top_left[0] + matched_tw, top_left[1] + matched_th)
        center_x = top_left[0] + matched_tw / 2
        center_y = top_left[1] + matched_th / 2
        
        result = {
            'found': True,
            'x': float(center_x / w),
            'y': float(center_y / h),
            'x_min': float(top_left[0] / w),
            'y_min': float(top_left[1] / h),
            'x_max': float(bottom_right[0] / w),
            'y_max': float(bottom_right[1] / h),
            'confidence': float(best_val),
            'method': 'edge_multiscale',
            'scale': best_scale,
            'source': 'image_template'
        }
        logger.info(
            f"✅ Edge Multi-Scale: Template trouvé à ({result['x']:.3f}, {result['y']:.3f}) "
            f"échelle={best_scale:.1f}x, confiance={best_val:.2f}"
        )
        return result
    else:
        return {
            'found': False, 
            'error': f"Meilleure confiance edges={best_val:.2f} à échelle={best_scale:.1f}x (seuil={threshold})"
        }


def extract_and_save_template(image_path: str, coords: list, output_path: str) -> bool:
    """
    Extract a region from an image and save as a template.
    
    Args:
        image_path: Path to the source image.
        coords: [x1, y1, x2, y2] in relative coordinates (0-1).
        output_path: Path to save the extracted template.
    
    Returns:
        bool: True if successful.
    """
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            logger.error(f"Could not load image: {image_path}")
            return False
        
        h, w = img.shape[:2]
        x1, y1, x2, y2 = coords
        
        # Convert relative to absolute coordinates
        abs_x1 = int(x1 * w)
        abs_y1 = int(y1 * h)
        abs_x2 = int(x2 * w)
        abs_y2 = int(y2 * h)
        
        # Extract region
        template = img[abs_y1:abs_y2, abs_x1:abs_x2]
        
        if template.size == 0:
            logger.error(f"Empty template region: {coords}")
            return False
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save template
        cv2.imwrite(str(output_path), template)
        logger.info(f"✅ Template saved: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error extracting template: {e}")
        return False
