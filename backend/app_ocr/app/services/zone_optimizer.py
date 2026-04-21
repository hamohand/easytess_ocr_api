import os
import logging
import uuid
import numpy as np
from difflib import SequenceMatcher
from PIL import Image

from app.services.ocr_engine import (
    analyser_avec_tesseract,
    analyser_avec_easyocr,
    analyser_hybride,
    TESSERACT_DISPONIBLE,
    EASYOCR_DISPONIBLE
)

logger = logging.getLogger(__name__)

# Paramètres d'optimisation
PASSE1_PAS = 0.02       
PASSE1_RANGE = 0.15     
PASSE2_PAS = 0.005      
PASSE2_RANGE = 0.03     

def calculer_similarite(texte_ocr, texte_attendu):
    """Calcule la similarité entre le texte OCR et le texte attendu."""
    if not texte_ocr or not texte_attendu:
        return 0.0
    t1 = texte_ocr.strip()
    t2 = texte_attendu.strip()
    if not t1:
        return 0.0
    sim = SequenceMatcher(None, t1, t2).ratio()
    if t2 in t1:
        sim = max(sim, 0.95)
    return sim

def preparer_image_de_travail(image_path, entity):
    """
    Prépare l'image de travail en appliquant le rognage du cadre de référence.
    Returns:
        tuple: (image_path_effective, cadre_info, crop_path_a_nettoyer)
    """
    cadre_reference = entity.get('cadre_reference')
    if not cadre_reference:
        return image_path, None, None

    zones_fictives = {
        '_optimizer_probe': {
            'coords': [0.4, 0.4, 0.6, 0.6],
            'lang': 'ara',
            'preprocess': 'arabic_textured',
            'type': 'text'
        }
    }

    try:
        _, _, cadre_detecte = analyser_hybride(image_path, zones_fictives, cadre_reference)
    except Exception as e:
        logger.warning(f"⚠️ analyser_hybride a échoué: {e} → image brute")
        return image_path, None, None

    if not cadre_detecte:
        return image_path, None, None

    try:
        with Image.open(image_path) as img:
            orig_w, orig_h = img.size
            left   = int(cadre_detecte['x']      * orig_w)
            top    = int(cadre_detecte['y']       * orig_h)
            right  = int((cadre_detecte['x'] + cadre_detecte['width'])  * orig_w)
            bottom = int((cadre_detecte['y'] + cadre_detecte['height']) * orig_h)

            left, top = max(0, left), max(0, top)
            right, bottom = min(orig_w, right), min(orig_h, bottom)

            if right <= left or bottom <= top:
                return image_path, cadre_detecte, None

            img_crop = img.crop((left, top, right, bottom))
            if img_crop.mode in ('RGBA', 'P', 'LA'):
                img_crop = img_crop.convert('RGB')

            crop_path = os.path.join(
                os.path.dirname(image_path),
                f"_optimizer_crop_{uuid.uuid4().hex[:8]}.jpg"
            )
            img_crop.save(crop_path)
            return crop_path, cadre_detecte, crop_path
    except Exception as e:
        logger.warning(f"⚠️ Erreur lors du rognage manuel: {e} → image brute")
        return image_path, None, None

def ocr_zone_unique(image_path, nom_zone, coords, lang='ara', preprocess='arabic_textured', use_tesseract=True, use_easyocr=False):
    """
    Exécute l'OCR sur une seule zone et retourne le résultat.
    """
    zones_config = {
        nom_zone: {
            'coords': coords,
            'lang': lang,
            'preprocess': preprocess,
            'type': 'text'
        }
    }
    
    best_result = {'texte': '', 'confiance': 0.0, 'moteur': 'aucun'}
    
    if use_tesseract and TESSERACT_DISPONIBLE:
        try:
            resultats = analyser_avec_tesseract(image_path, zones_config)
            if nom_zone in resultats:
                r = resultats[nom_zone]
                if r['confiance_auto'] > best_result['confiance']:
                    best_result = {
                        'texte': r['texte_auto'],
                        'confiance': r['confiance_auto'],
                        'moteur': 'tesseract'
                    }
        except Exception:
            pass
            
    if use_easyocr and EASYOCR_DISPONIBLE:
        try:
            resultats = analyser_avec_easyocr(image_path, zones_config)
            if nom_zone in resultats:
                r = resultats[nom_zone]
                if r['confiance_auto'] > best_result['confiance']:
                    best_result = {
                        'texte': r['texte_auto'],
                        'confiance': r['confiance_auto'],
                        'moteur': 'easyocr'
                    }
        except Exception:
            pass
            
    return best_result

def optimiser_zone(image_path, nom_zone, coords_base, texte_attendu, lang='ara', preprocess='arabic_textured', use_tesseract=True, use_easyocr=False, progress_callback=None, stop_threshold=None):
    """
    Optimise les coordonnées d'une zone pour maximiser le score OCR.
    Permet de s'arrêter tôt si stop_threshold est atteint.
    """
    # Score initial
    result_initial = ocr_zone_unique(image_path, nom_zone, coords_base, lang, preprocess, use_tesseract, use_easyocr)
    sim_initial = calculer_similarite(result_initial['texte'], texte_attendu)
    score_initial = result_initial['confiance'] * sim_initial
    
    all_results = []
    
    best_coords = list(coords_base)
    best_score = score_initial
    best_texte = result_initial['texte']
    best_confiance = result_initial['confiance']
    best_similarite = sim_initial
    
    bord_noms = ['x1', 'y1', 'x2', 'y2']
    
    # helper for tracking
    def report_progress(passe, step, total_steps, current_best):
        if progress_callback:
            progress_callback({
                "passe": passe,
                "step": step,
                "total_steps": total_steps,
                "current_best": current_best
            })

    early_stop_reached = False
    
    # Check if initial score already meets threshold
    if stop_threshold is not None and best_confiance >= stop_threshold and best_similarite > 0.8:
        early_stop_reached = True

    # Passe 1
    if not early_stop_reached:
        total_steps_p1 = sum(int((min(1.0, best_coords[b]+PASSE1_RANGE) - max(0.0, best_coords[b]-PASSE1_RANGE))/PASSE1_PAS)+1 for b in range(4))
        step_count = 0
        for bord_idx in range(4):
            if early_stop_reached: break
            
            val_base = best_coords[bord_idx]
            val_min = max(0.0, val_base - PASSE1_RANGE)
            val_max = min(1.0, val_base + PASSE1_RANGE)
            n_steps = int((val_max - val_min) / PASSE1_PAS) + 1
            
            meilleur_val_bord = best_coords[bord_idx]
            meilleur_score_bord = best_score
            
            for i in range(n_steps):
                if early_stop_reached: break
                
                step_count += 1
                report_progress(1, step_count, total_steps_p1, best_score)
                
                val_new = round(val_min + i * PASSE1_PAS, 6)
                test_coords = list(best_coords)
                test_coords[bord_idx] = val_new
                
                if test_coords[0] >= test_coords[2] - 0.02 or test_coords[1] >= test_coords[3] - 0.02:
                    continue
                    
                result = ocr_zone_unique(image_path, nom_zone, test_coords, lang, preprocess, use_tesseract, use_easyocr)
                sim = calculer_similarite(result['texte'], texte_attendu)
                score = result['confiance'] * sim
                
                all_results.append({
                    'coords': list(test_coords), 'texte': result['texte'], 'confiance': result['confiance'],
                    'similarite': sim, 'score': score, 'bord': bord_noms[bord_idx], 'passe': 1, 'moteur': result['moteur']
                })
                
                if score > meilleur_score_bord:
                    meilleur_score_bord = score
                    meilleur_val_bord = val_new
                
                if stop_threshold is not None and result['confiance'] >= stop_threshold and sim > 0.8:
                    early_stop_reached = True
                    break
                    
            best_coords[bord_idx] = meilleur_val_bord
            if meilleur_score_bord > best_score:
                best_score = meilleur_score_bord
                for r in reversed(all_results):
                    if r['score'] == meilleur_score_bord:
                        best_texte = r['texte']
                        best_confiance = r['confiance']
                        best_similarite = r['similarite']
                        break
                        
    # Passe 2
    if not early_stop_reached:
        total_steps_p2 = sum(int((min(1.0, best_coords[b]+PASSE2_RANGE) - max(0.0, best_coords[b]-PASSE2_RANGE))/PASSE2_PAS)+1 for b in range(4))
        step_count = 0
        for bord_idx in range(4):
            if early_stop_reached: break
            
            val_base = best_coords[bord_idx]
            val_min = max(0.0, val_base - PASSE2_RANGE)
            val_max = min(1.0, val_base + PASSE2_RANGE)
            n_steps = int((val_max - val_min) / PASSE2_PAS) + 1
            
            meilleur_val_bord = best_coords[bord_idx]
            meilleur_score_bord = best_score
            
            for i in range(n_steps):
                if early_stop_reached: break
                
                step_count += 1
                report_progress(2, step_count, total_steps_p2, best_score)
                
                val_new = round(val_min + i * PASSE2_PAS, 6)
                test_coords = list(best_coords)
                test_coords[bord_idx] = val_new
                
                if test_coords[0] >= test_coords[2] - 0.02 or test_coords[1] >= test_coords[3] - 0.02:
                    continue
                    
                result = ocr_zone_unique(image_path, nom_zone, test_coords, lang, preprocess, use_tesseract, use_easyocr)
                sim = calculer_similarite(result['texte'], texte_attendu)
                score = result['confiance'] * sim
                
                all_results.append({
                    'coords': list(test_coords), 'texte': result['texte'], 'confiance': result['confiance'],
                    'similarite': sim, 'score': score, 'bord': bord_noms[bord_idx], 'passe': 2, 'moteur': result['moteur']
                })
                
                if score > meilleur_score_bord:
                    meilleur_score_bord = score
                    meilleur_val_bord = val_new
                    
                if stop_threshold is not None and result['confiance'] >= stop_threshold and sim > 0.8:
                    early_stop_reached = True
                    break
                    
            best_coords[bord_idx] = meilleur_val_bord
            if meilleur_score_bord > best_score:
                best_score = meilleur_score_bord
                for r in reversed(all_results):
                    if r['score'] == meilleur_score_bord:
                        best_texte = r['texte']
                        best_confiance = r['confiance']
                        best_similarite = r['similarite']
                        break
                        
    amelioration = best_score - score_initial
    return {
        'zone': nom_zone,
        'texte_attendu': texte_attendu,
        'initial': {
            'coords': list(coords_base),
            'texte': result_initial['texte'],
            'confiance': result_initial['confiance'],
            'similarite': sim_initial,
            'score': score_initial,
        },
        'optimal': {
            'coords': [round(c, 6) for c in best_coords],
            'texte': best_texte,
            'confiance': best_confiance,
            'similarite': best_similarite,
            'score': best_score,
        },
        'amelioration': amelioration,
        'nb_evaluations': len(all_results)
    }
