#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
=============================================================================
TEST D'OPTIMISATION DE ZONES D'ENTITÉS OCR
=============================================================================

Ce script trouve la taille optimale d'une zone d'entité pour maximiser
le coefficient de confiance OCR (confiance_auto).

Stratégie : Descente de gradient discrétisée en 2 passes
  - Passe 1 (grossière) : balaye chaque bord avec un pas de 2%
  - Passe 2 (fine)       : affine autour du meilleur résultat avec un pas de 0.5%

Pour chaque variation de coordonnées, on mesure :
  - confiance_auto : score brut de Tesseract/EasyOCR (0-1)
  - similarite     : SequenceMatcher entre le texte OCR et la vérité terrain (0-1)
  - score_composite: confiance × similarité (ce qu'on optimise réellement)

Usage:
  # Optimiser une zone spécifique d'une entité :
  python test_zone_optimizer.py --entite cni_algo_recto_001 --zone nom --texte "حمرون"

  # Avec une image personnalisée :
  python test_zone_optimizer.py --entite pp_01 --zone nom --texte "HAMROUNE" --image chemin/vers/image.jpg

  # Plusieurs zones à la fois :
  python test_zone_optimizer.py --entite cni_algo_recto_001 --zone nom --texte "حمرون" --zone prenom --texte "محمد"

  # Mode dry-run (voir sans appliquer) :
  python test_zone_optimizer.py --entite cni_algo_recto_001 --zone nom --texte "حمرون" --dry-run

  # Sans arguments : utilise la configuration par défaut (cni_algo_recto_001)
  python test_zone_optimizer.py

Sortie:
  - Résultats dans la console avec les coords optimales
  - Rapport JSON dans tests_output/zone_optimization_report.json
  - Rapport HTML visuel dans tests_output/zone_optimization_report.html
"""

import os
import sys
import json
import time
import logging
import argparse
import numpy as np
from datetime import datetime
from difflib import SequenceMatcher
from PIL import Image
from copy import deepcopy

# --- Setup du path pour importer le moteur OCR ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)

from app.services.ocr_engine import (
    analyser_avec_tesseract,
    analyser_avec_easyocr,
    analyser_hybride,
    get_absolute_coords,
    upscale_for_ocr,
    TESSERACT_DISPONIBLE,
    EASYOCR_DISPONIBLE
)

# --- Configuration du logging ---
logging.basicConfig(
    level=logging.WARNING,  # Réduire le bruit des logs OCR pendant l'optimisation
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# =============================================================================
# CONFIGURATION PAR DÉFAUT (utilisée si aucun argument CLI)
# =============================================================================

DEFAULT_ENTITY = "cni_algo_recto_001"
DEFAULT_GROUND_TRUTH = {
    "nom": "حمرون",
    "prenom": "محمد",
}

# Paramètres d'optimisation
PASSE1_PAS = 0.02       # Pas de 2% pour la première passe (grossière)
PASSE1_RANGE = 0.15     # Plage de variation de ±15% autour des coords originales
PASSE2_PAS = 0.005      # Pas de 0.5% pour la deuxième passe (fine)
PASSE2_RANGE = 0.03     # Plage de variation de ±3% autour du meilleur de passe 1

# Moteurs à utiliser
USE_TESSERACT = True
USE_EASYOCR = False  # Plus lent, activer si besoin

# Dossier de sortie
OUTPUT_DIR = os.path.join(BASE_DIR, "tests_output")


def decode_texte(valeur):
    r"""Decode les sequences \uXXXX litterales (solution PowerShell pour l'arabe)."""
    try:
        return valeur.encode("raw_unicode_escape").decode("unicode_escape")
    except Exception:
        return valeur


def parse_args():
    "Parse les arguments de la ligne de commande."
    parser = argparse.ArgumentParser(
        description="Optimisation des zones d entites OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemples:\n"
            "\n"
            "  [PowerShell] Codes Unicode (evite les problemes d encodage RTL) :\n"
            "  python test_zone_optimizer.py -e cni_algo_recto_001 -z nom   -u \"\\u062d\\u0645\\u0631\\u0648\\u0646\"\\n"
            "  python test_zone_optimizer.py -e cni_algo_recto_001 -z ville -u \"\\u0639\\u0632\\u0627\\u0632\\u0642\\u0647\"\\n"
            "\n"
            "  [Recommande] Fichier JSON (le plus simple pour l arabe) :\n"
            "  python test_zone_optimizer.py -e cni_algo_recto_001 -f verite.json\n"
            "  verite.json contient : {\"nom\": \"\u062d\u0645\u0631\u0648\u0646\", \"ville\": \"\u0639\u0632\u0627\u0632\u0642\u0647\"}\n"
            "\n"
            "  Texte direct (si votre terminal supporte l arabe) :\n"
            "  python test_zone_optimizer.py -e cni_algo_recto_001 -z nom -t \"\u062d\u0645\u0631\u0648\u0646\"\n"
        )
    )
    parser.add_argument("-e", "--entite", type=str, default=None,
                        help="Nom de l entite (ex: cni_algo_recto_001)")
    parser.add_argument("-z", "--zone", type=str, action="append", default=None,
                        help="Nom de la zone a optimiser (repetable)")
    parser.add_argument("-t", "--texte", type=str, action="append", default=None,
                        help="Texte attendu directement (meme ordre que --zone)")
    parser.add_argument("-u", "--unicode", type=str, action="append", default=None,
                        dest="unicode_texte",
                        help=r"Texte en codes Unicode ex: \u062d\u0645 [SOLUTION POWERSHELL]")
    parser.add_argument("-f", "--fichier", type=str, default=None,
                        help="Fichier JSON {zone: texte} [RECOMMANDE pour l arabe]")
    parser.add_argument("-i", "--image", type=str, default=None,
                        help="Chemin vers l image de test")
    parser.add_argument("-v", "--visualize", action="store_true",
                        help="Tracer les zones optimales directement sur l image et sauvegarder")
    parser.add_argument("--dry-run", action="store_true",
                        help="Apercu sans modifier l entite")
    parser.add_argument("--easyocr", action="store_true",
                        help="Activer EasyOCR en plus de Tesseract")
    return parser.parse_args()


def resolve_config(args):
    "Resout la configuration finale a partir des arguments CLI."
    entity_name = args.entite or DEFAULT_ENTITY
    entity_file = os.path.join(BASE_DIR, "entities", f"{entity_name}.json")
    if args.image:
        image_file = os.path.abspath(args.image)
    else:
        image_file = os.path.join(BASE_DIR, "uploads", "entities", entity_name, "reference.jpeg")
    ground_truth = None
    # Mode 1 : fichier JSON  (-f)
    if args.fichier:
        if not os.path.exists(args.fichier):
            print(f"Fichier de verite terrain introuvable: {args.fichier}")
            sys.exit(1)
        with open(args.fichier, "r", encoding="utf-8") as fh:
            ground_truth = json.load(fh)
        if args.zone:
            ground_truth = {z: ground_truth[z] for z in args.zone if z in ground_truth}
        print(f"   Verite terrain depuis: {args.fichier}  zones={list(ground_truth.keys())}")
    # Mode 2 : codes Unicode  (-u)
    elif args.unicode_texte:
        if not args.zone:
            print("Erreur: --unicode necessite --zone pour chaque texte"); sys.exit(1)
        if len(args.zone) != len(args.unicode_texte):
            print(f"Erreur: {len(args.zone)} --zone mais {len(args.unicode_texte)} --unicode"); sys.exit(1)
        ground_truth = {z: decode_texte(u) for z, u in zip(args.zone, args.unicode_texte)}
        print("   Textes decodes depuis codes Unicode:")
        for z, t in ground_truth.items():
            print(f"      {z} -> '{t}'")
    # Mode 3 : texte direct  (-t)
    elif args.zone and args.texte:
        if len(args.zone) != len(args.texte):
            print(f"Erreur: {len(args.zone)} --zone mais {len(args.texte)} --texte"); sys.exit(1)
        ground_truth = dict(zip(args.zone, args.texte))
    elif args.zone:
        print("Erreur: specifiez -t, -u, ou -f  |  PowerShell: -u \"\\uXXXX...\"")
        sys.exit(1)
    elif args.entite and not args.zone:
        print("Erreur: specifiez au moins une zone avec --zone"); sys.exit(1)
    else:
        ground_truth = DEFAULT_GROUND_TRUTH
    global USE_EASYOCR
    if args.easyocr:
        USE_EASYOCR = True
    visualize = getattr(args, 'visualize', False)
    return entity_name, entity_file, image_file, ground_truth, args.dry_run, visualize


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def generer_image_annotee(image_orig_path, resultats_zones, cadre_info, output_path):
    """
    Trace les zones optimales (et initiales) directement sur l'image originale.

    Les coordonnées des zones sont relatives au crop du cadre.
    Elles sont remappées en pixels absolus sur l'image originale via cadre_info.

    Code couleur :
      - Rouge pointillé : zone initiale (avant optimisation)
      - Vert plein      : zone optimale (après optimisation)
      - Jaune           : cadre OCR détecté

    Returns:
        str: chemin du fichier image annoté sauvegardé
    """
    import cv2

    img = cv2.imread(image_orig_path)
    if img is None:
        # Fallback PIL
        from PIL import Image as PilImg
        pil = PilImg.open(image_orig_path).convert('RGB')
        img = np.array(pil)[:, :, ::-1].copy()

    h_img, w_img = img.shape[:2]

    # Coordonnées absolues du cadre sur l'image originale
    if cadre_info:
        cx = cadre_info['x'] * w_img
        cy = cadre_info['y'] * h_img
        cw = cadre_info['width']  * w_img
        ch = cadre_info['height'] * h_img
        # Dessiner le cadre OCR en jaune
        cv2.rectangle(img,
                      (int(cx), int(cy)),
                      (int(cx + cw), int(cy + ch)),
                      (0, 220, 220), 2)
        cv2.putText(img, 'CADRE OCR', (int(cx) + 4, int(cy) - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 220), 1)
    else:
        # Pas de cadre -> coords relatives a l'image entiere
        cx, cy, cw, ch = 0, 0, w_img, h_img

    def coords_to_px(coords, zone_w, zone_h, off_x, off_y):
        """Convertit coords relatives a la zone -> pixels absolus image."""
        x1 = int(coords[0] * zone_w + off_x)
        y1 = int(coords[1] * zone_h + off_y)
        x2 = int(coords[2] * zone_w + off_x)
        y2 = int(coords[3] * zone_h + off_y)
        x1, x2 = max(0, x1), min(w_img, x2)
        y1, y2 = max(0, y1), min(h_img, y2)
        return x1, y1, x2, y2

    FONT       = cv2.FONT_HERSHEY_SIMPLEX
    FONT_SCALE = 0.45
    THICKNESS  = 1

    for res in resultats_zones:
        nom_zone  = res['zone']
        ini_coords = res['initial']['coords']
        opt_coords = res['optimal']['coords']
        score_ini  = res['initial']['score']
        score_opt  = res['optimal']['score']
        amel       = res['amelioration']

        # Zone initiale en rouge pointille
        x1i, y1i, x2i, y2i = coords_to_px(ini_coords, cw, ch, cx, cy)
        # Simuler pointille avec des petits rectangles
        for start in range(x1i, x2i, 10):
            end = min(start + 5, x2i)
            cv2.line(img, (start, y1i), (end, y1i), (0, 0, 200), 1)
            cv2.line(img, (start, y2i), (end, y2i), (0, 0, 200), 1)
        for start in range(y1i, y2i, 10):
            end = min(start + 5, y2i)
            cv2.line(img, (x1i, start), (x1i, end), (0, 0, 200), 1)
            cv2.line(img, (x2i, start), (x2i, end), (0, 0, 200), 1)

        # Zone optimale en vert plein
        x1o, y1o, x2o, y2o = coords_to_px(opt_coords, cw, ch, cx, cy)
        cv2.rectangle(img, (x1o, y1o), (x2o, y2o), (0, 200, 60), 2)

        # Etiquette: nom + score
        label = f"{nom_zone}  {score_opt:.0%}"
        if amel > 0.01:
            label += f" (+{amel:.0%})"
        (tw, th), _ = cv2.getTextSize(label, FONT, FONT_SCALE, THICKNESS)
        # Fond sombre derriere le texte
        tx, ty = x1o, max(y1o - 4, th + 4)
        cv2.rectangle(img, (tx, ty - th - 3), (tx + tw + 4, ty + 2), (20, 20, 20), -1)
        cv2.putText(img, label, (tx + 2, ty), FONT, FONT_SCALE, (0, 230, 80), THICKNESS)

        # Texte OCR optimal en bleu clair
        texte_ocr = res['optimal'].get('texte', '')[:30]
        if texte_ocr:
            cv2.putText(img, texte_ocr, (x1o + 2, y2o - 4),
                        FONT, FONT_SCALE, (255, 200, 50), THICKNESS)

    # Legende
    leg_y = h_img - 20
    cv2.rectangle(img, (8, leg_y - 14), (22, leg_y), (0, 200, 60), 2)
    cv2.putText(img, 'Zone optimale', (26, leg_y), FONT, 0.4, (0, 200, 60), 1)
    cv2.rectangle(img, (130, leg_y - 14), (144, leg_y), (0, 0, 200), 1)
    cv2.putText(img, 'Zone initiale', (148, leg_y), FONT, 0.4, (0, 0, 200), 1)

    cv2.imwrite(output_path, img)
    return output_path

def calculer_similarite(texte_ocr, texte_attendu):
    """Calcule la similarité entre le texte OCR et le texte attendu."""
    if not texte_ocr or not texte_attendu:
        return 0.0
    
    # Nettoyer les textes
    t1 = texte_ocr.strip()
    t2 = texte_attendu.strip()
    
    if not t1:
        return 0.0
    
    # Similarité de séquence
    sim = SequenceMatcher(None, t1, t2).ratio()
    
    # Bonus si le texte attendu est contenu dans le résultat OCR
    if t2 in t1:
        sim = max(sim, 0.95)
    
    return sim


def preparer_image_de_travail(image_path, entity):
    """
    Prépare l'image de travail en appliquant le rognage du cadre de référence,
    exactement comme le fait l'API réelle via analyser_hybride.

    Stratégie :
      1. Lance analyser_hybride sur une zone fictive → récupère cadre_detecte (x,y,w,h relatifs)
      2. Rogne manuellement l'image originale avec ces coordonnées → sauvegarde en fichier temporaire
      3. Retourne le chemin du crop + les infos du cadre

    Returns:
        tuple: (image_path_effective, cadre_info, crop_path_a_nettoyer)
          - image_path_effective : chemin du crop si ancres trouvées, sinon chemin original
          - cadre_info           : dict {x, y, width, height} relatifs, ou None
          - crop_path_a_nettoyer : chemin du fichier temporaire à supprimer après usage
    """
    cadre_reference = entity.get('cadre_reference')
    if not cadre_reference:
        logger.info("⚠️ Pas de cadre de référence → optimisation sur image brute")
        return image_path, None, None

    zones_fictives = {
        '_optimizer_probe': {
            'coords': [0.4, 0.4, 0.6, 0.6],
            'lang': 'ara',
            'preprocess': 'arabic_textured',
            'type': 'text'
        }
    }

    logger.info("✂️ Détection du cadre de référence via analyser_hybride...")
    try:
        _resultats, _alertes, cadre_detecte = analyser_hybride(
            image_path, zones_fictives, cadre_reference
        )
    except Exception as e:
        logger.warning(f"⚠️ analyser_hybride a échoué: {e} → image brute")
        return image_path, None, None

    if not cadre_detecte:
        logger.warning("⚠️ Cadre non détecté → optimisation sur image brute")
        return image_path, None, None

    # Reconstruire le crop manuellement depuis cadre_detecte (x, y, width, height relatifs)
    try:
        with Image.open(image_path) as img:
            orig_w, orig_h = img.size
            left   = int(cadre_detecte['x']      * orig_w)
            top    = int(cadre_detecte['y']       * orig_h)
            right  = int((cadre_detecte['x'] + cadre_detecte['width'])  * orig_w)
            bottom = int((cadre_detecte['y'] + cadre_detecte['height']) * orig_h)

            # Clamp
            left, top = max(0, left), max(0, top)
            right, bottom = min(orig_w, right), min(orig_h, bottom)

            if right <= left or bottom <= top:
                logger.warning("⚠️ Crop invalide → image brute")
                return image_path, cadre_detecte, None

            img_crop = img.crop((left, top, right, bottom))
            if img_crop.mode in ('RGBA', 'P', 'LA'):
                img_crop = img_crop.convert('RGB')

            import uuid
            crop_path = os.path.join(
                os.path.dirname(image_path),
                f"_optimizer_crop_{uuid.uuid4().hex[:8]}.jpg"
            )
            img_crop.save(crop_path)

            logger.info(
                f"✅ Image rognée pour l'optimisation : {crop_path} "
                f"({right-left}×{bottom-top}px, cadre={cadre_detecte})"
            )
            return crop_path, cadre_detecte, crop_path

    except Exception as e:
        logger.warning(f"⚠️ Erreur lors du rognage manuel: {e} → image brute")
        return image_path, None, None


def ocr_zone_unique(image_path, nom_zone, coords, lang='ara', preprocess='arabic_textured'):
    """
    Exécute l'OCR sur une seule zone et retourne le résultat.
    
    Returns:
        dict: {'texte': str, 'confiance': float, 'moteur': str}
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
    
    if USE_TESSERACT and TESSERACT_DISPONIBLE:
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
        except Exception as e:
            logger.debug(f"Tesseract error: {e}")
    
    if USE_EASYOCR and EASYOCR_DISPONIBLE:
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
        except Exception as e:
            logger.debug(f"EasyOCR error: {e}")
    
    return best_result


def generer_variations(coords_base, pas, plage):
    """
    Génère toutes les variations de coordonnées autour d'une base.
    
    Optimise chaque bord indépendamment: x1, y1, x2, y2
    
    Args:
        coords_base: [x1, y1, x2, y2] coordonnées de départ
        pas: incrément de variation
        plage: plage de variation ±
    
    Yields:
        tuple: (coords_variée, description)
    """
    x1, y1, x2, y2 = coords_base
    
    # Pour chaque bord, générer les variations
    for bord_idx, bord_nom in enumerate(['x1', 'y1', 'x2', 'y2']):
        val_base = coords_base[bord_idx]
        
        # Plage de variation
        val_min = max(0.0, val_base - plage)
        val_max = min(1.0, val_base + plage)
        
        # Générer les incréments
        n_steps = int((val_max - val_min) / pas) + 1
        for i in range(n_steps):
            val_new = val_min + i * pas
            
            # Construire les nouvelles coordonnées
            new_coords = list(coords_base)
            new_coords[bord_idx] = round(val_new, 6)
            
            # Vérifier la validité (x1 < x2, y1 < y2, taille minimale)
            if new_coords[0] >= new_coords[2] - 0.02:  # Largeur min 2%
                continue
            if new_coords[1] >= new_coords[3] - 0.02:  # Hauteur min 2%
                continue
            
            delta = round(val_new - val_base, 4)
            desc = f"{bord_nom}{'+' if delta >= 0 else ''}{delta:.4f}"
            
            yield new_coords, desc


def optimiser_zone(image_path, nom_zone, coords_base, texte_attendu, 
                   lang='ara', preprocess='arabic_textured'):
    """
    Optimise les coordonnées d'une zone pour maximiser le score OCR.
    
    Stratégie en 2 passes:
      1. Balayage grossier (pas=2%, plage=±15%)
      2. Affinement fin (pas=0.5%, plage=±3% autour du meilleur)
    
    Returns:
        dict avec les résultats d'optimisation
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"🎯 OPTIMISATION ZONE: {nom_zone}")
    logger.info(f"   Texte attendu: {texte_attendu}")
    logger.info(f"   Coords initiales: {coords_base}")
    logger.info(f"{'='*70}")
    
    # --- Score initial ---
    result_initial = ocr_zone_unique(image_path, nom_zone, coords_base, lang, preprocess)
    sim_initial = calculer_similarite(result_initial['texte'], texte_attendu)
    score_initial = result_initial['confiance'] * sim_initial
    
    logger.info(f"\n📊 Score initial:")
    logger.info(f"   Texte OCR: '{result_initial['texte']}'")
    logger.info(f"   Confiance: {result_initial['confiance']:.1%}")
    logger.info(f"   Similarité: {sim_initial:.1%}")
    logger.info(f"   Score composite: {score_initial:.1%}")
    
    all_results = []
    
    # =======================================================================
    # PASSE 1 : Optimisation bord par bord (grossière)
    # =======================================================================
    logger.info(f"\n{'─'*50}")
    logger.info(f"📐 PASSE 1 : Optimisation bord par bord (pas={PASSE1_PAS:.1%}, plage=±{PASSE1_RANGE:.0%})")
    logger.info(f"{'─'*50}")
    
    best_coords = list(coords_base)
    best_score = score_initial
    best_texte = result_initial['texte']
    best_confiance = result_initial['confiance']
    best_similarite = sim_initial
    
    bord_noms = ['x1 (gauche)', 'y1 (haut)', 'x2 (droite)', 'y2 (bas)']
    
    # Optimiser chaque bord séquentiellement (le résultat d'un bord alimente le suivant)
    for bord_idx in range(4):
        bord_nom = bord_noms[bord_idx]
        val_base = best_coords[bord_idx]
        val_min = max(0.0, val_base - PASSE1_RANGE)
        val_max = min(1.0, val_base + PASSE1_RANGE)
        
        n_steps = int((val_max - val_min) / PASSE1_PAS) + 1
        logger.info(f"\n   🔧 Bord {bord_nom}: {n_steps} variations [{val_min:.3f} → {val_max:.3f}]")
        
        meilleur_val_bord = best_coords[bord_idx]
        meilleur_score_bord = best_score
        
        for i in range(n_steps):
            val_new = round(val_min + i * PASSE1_PAS, 6)
            
            test_coords = list(best_coords)
            test_coords[bord_idx] = val_new
            
            # Validation
            if test_coords[0] >= test_coords[2] - 0.02:
                continue
            if test_coords[1] >= test_coords[3] - 0.02:
                continue
            
            result = ocr_zone_unique(image_path, nom_zone, test_coords, lang, preprocess)
            sim = calculer_similarite(result['texte'], texte_attendu)
            score = result['confiance'] * sim
            
            all_results.append({
                'coords': list(test_coords),
                'texte': result['texte'],
                'confiance': result['confiance'],
                'similarite': sim,
                'score': score,
                'bord': bord_nom,
                'passe': 1,
                'moteur': result['moteur']
            })
            
            if score > meilleur_score_bord:
                meilleur_score_bord = score
                meilleur_val_bord = val_new
                logger.info(f"      ✨ Nouveau meilleur: {bord_nom}={val_new:.4f} → "
                          f"score={score:.1%} (conf={result['confiance']:.1%}, "
                          f"sim={sim:.1%}) texte='{result['texte'][:30]}'")
        
        # Appliquer le meilleur pour ce bord
        old_val = best_coords[bord_idx]
        best_coords[bord_idx] = meilleur_val_bord
        
        if meilleur_score_bord > best_score:
            best_score = meilleur_score_bord
            # Récupérer le texte/confiance/sim du meilleur
            for r in reversed(all_results):
                if r['score'] == meilleur_score_bord:
                    best_texte = r['texte']
                    best_confiance = r['confiance']
                    best_similarite = r['similarite']
                    break
        
        delta = meilleur_val_bord - old_val
        logger.info(f"   ✅ Bord {bord_nom}: {old_val:.4f} → {meilleur_val_bord:.4f} (Δ={delta:+.4f})")
    
    logger.info(f"\n   📊 Résultat passe 1:")
    logger.info(f"      Score: {score_initial:.1%} → {best_score:.1%}")
    logger.info(f"      Coords: {[round(c,4) for c in coords_base]} → {[round(c,4) for c in best_coords]}")
    
    # =======================================================================
    # PASSE 2 : Affinement fin autour du meilleur
    # =======================================================================
    logger.info(f"\n{'─'*50}")
    logger.info(f"🔬 PASSE 2 : Affinement fin (pas={PASSE2_PAS:.2%}, plage=±{PASSE2_RANGE:.1%})")
    logger.info(f"{'─'*50}")
    
    coords_passe2_base = list(best_coords)
    
    for bord_idx in range(4):
        bord_nom = bord_noms[bord_idx]
        val_base = best_coords[bord_idx]
        val_min = max(0.0, val_base - PASSE2_RANGE)
        val_max = min(1.0, val_base + PASSE2_RANGE)
        
        n_steps = int((val_max - val_min) / PASSE2_PAS) + 1
        logger.info(f"\n   🔧 Bord {bord_nom}: {n_steps} variations [{val_min:.4f} → {val_max:.4f}]")
        
        meilleur_val_bord = best_coords[bord_idx]
        meilleur_score_bord = best_score
        
        for i in range(n_steps):
            val_new = round(val_min + i * PASSE2_PAS, 6)
            
            test_coords = list(best_coords)
            test_coords[bord_idx] = val_new
            
            if test_coords[0] >= test_coords[2] - 0.02:
                continue
            if test_coords[1] >= test_coords[3] - 0.02:
                continue
            
            result = ocr_zone_unique(image_path, nom_zone, test_coords, lang, preprocess)
            sim = calculer_similarite(result['texte'], texte_attendu)
            score = result['confiance'] * sim
            
            all_results.append({
                'coords': list(test_coords),
                'texte': result['texte'],
                'confiance': result['confiance'],
                'similarite': sim,
                'score': score,
                'bord': bord_nom,
                'passe': 2,
                'moteur': result['moteur']
            })
            
            if score > meilleur_score_bord:
                meilleur_score_bord = score
                meilleur_val_bord = val_new
                logger.info(f"      ✨ Affinement: {bord_nom}={val_new:.5f} → "
                          f"score={score:.1%} (conf={result['confiance']:.1%}, "
                          f"sim={sim:.1%})")
        
        old_val = best_coords[bord_idx]
        best_coords[bord_idx] = meilleur_val_bord
        
        if meilleur_score_bord > best_score:
            best_score = meilleur_score_bord
            for r in reversed(all_results):
                if r['score'] == meilleur_score_bord:
                    best_texte = r['texte']
                    best_confiance = r['confiance']
                    best_similarite = r['similarite']
                    break
        
        delta = meilleur_val_bord - old_val
        if abs(delta) > 0.0001:
            logger.info(f"   ✅ Bord {bord_nom}: {old_val:.5f} → {meilleur_val_bord:.5f} (Δ={delta:+.5f})")
    
    # =======================================================================
    # RÉSUMÉ FINAL
    # =======================================================================
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
        'nb_evaluations': len(all_results),
        'all_results': all_results,
    }


def generer_rapport_html(resultats_zones, output_path):
    """Génère un rapport HTML visuel avec les résultats d'optimisation."""
    
    html = """<!DOCTYPE html>
<html lang="fr" dir="ltr">
<head>
    <meta charset="UTF-8">
    <title>Rapport d'Optimisation des Zones OCR</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, sans-serif; 
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: #e0e0e0; 
            padding: 40px; 
            min-height: 100vh;
        }
        h1 { 
            text-align: center; 
            font-size: 2.2em; 
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d2ff, #3a7bd5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle { text-align: center; color: #888; margin-bottom: 40px; font-size: 0.95em; }
        .zone-card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 30px;
        }
        .zone-title {
            font-size: 1.5em;
            color: #00d2ff;
            margin-bottom: 5px;
        }
        .zone-truth { color: #aaa; margin-bottom: 20px; font-size: 1.1em; }
        .zone-truth span { color: #ffa726; font-weight: bold; font-size: 1.3em; }
        .comparison {
            display: grid;
            grid-template-columns: 1fr 60px 1fr;
            gap: 20px;
            align-items: center;
            margin-bottom: 25px;
        }
        .result-box {
            background: rgba(0,0,0,0.3);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.08);
        }
        .result-box.initial { border-left: 4px solid #ef5350; }
        .result-box.optimal { border-left: 4px solid #66bb6a; }
        .result-box h3 { margin-bottom: 12px; font-size: 1.1em; }
        .result-box.initial h3 { color: #ef5350; }
        .result-box.optimal h3 { color: #66bb6a; }
        .metric { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .metric-label { color: #aaa; }
        .metric-value { font-weight: bold; font-family: 'Consolas', monospace; }
        .arrow { 
            font-size: 2.5em; 
            text-align: center; 
            color: #66bb6a;
            animation: pulse 2s infinite;
        }
        @keyframes pulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
        .coords-box {
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            padding: 12px;
            margin-top: 10px;
            font-family: 'Consolas', monospace;
            font-size: 0.85em;
            color: #81d4fa;
        }
        .amelioration {
            text-align: center;
            padding: 15px;
            border-radius: 12px;
            font-size: 1.3em;
            font-weight: bold;
            margin-top: 10px;
        }
        .amelioration.positive { 
            background: rgba(102, 187, 106, 0.15); 
            color: #66bb6a;
            border: 1px solid rgba(102, 187, 106, 0.3);
        }
        .amelioration.negative { 
            background: rgba(239, 83, 80, 0.15); 
            color: #ef5350;
            border: 1px solid rgba(239, 83, 80, 0.3);
        }
        .amelioration.neutral { 
            background: rgba(255, 167, 38, 0.15); 
            color: #ffa726;
            border: 1px solid rgba(255, 167, 38, 0.3);
        }
        .score-bar {
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            margin-top: 4px;
            overflow: hidden;
        }
        .score-bar-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s;
        }
        .stats-footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #666;
            font-size: 0.85em;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        th { color: #81d4fa; font-size: 0.85em; text-transform: uppercase; }
        td { font-family: 'Consolas', monospace; font-size: 0.85em; }
        .delta-positive { color: #66bb6a; }
        .delta-negative { color: #ef5350; }
    </style>
</head>
<body>
    <h1>🎯 Optimisation des Zones OCR</h1>
    <p class="subtitle">Recherche de la taille optimale pour maximiser la confiance OCR</p>
"""
    
    total_evals = 0
    
    for res in resultats_zones:
        ini = res['initial']
        opt = res['optimal']
        total_evals += res['nb_evaluations']
        
        # Classe d'amélioration
        if res['amelioration'] > 0.01:
            amel_class = 'positive'
            amel_icon = '📈'
        elif res['amelioration'] < -0.01:
            amel_class = 'negative'
            amel_icon = '📉'
        else:
            amel_class = 'neutral'
            amel_icon = '↔️'
        
        # Couleurs des barres
        def bar_color(score):
            if score >= 0.8: return '#66bb6a'
            if score >= 0.5: return '#ffa726'
            return '#ef5350'
        
        # Différences de coordonnées
        coord_diffs = []
        labels = ['x1', 'y1', 'x2', 'y2']
        for i in range(4):
            d = opt['coords'][i] - ini['coords'][i]
            coord_diffs.append(f"Δ{labels[i]}={d:+.4f}")
        
        html += f"""
    <div class="zone-card">
        <h2 class="zone-title">Zone : {res['zone']}</h2>
        <p class="zone-truth">Texte attendu : <span>{res['texte_attendu']}</span></p>
        
        <div class="comparison">
            <div class="result-box initial">
                <h3>❌ Configuration Initiale</h3>
                <div class="metric">
                    <span class="metric-label">Texte OCR</span>
                    <span class="metric-value">{ini['texte'] or '(vide)'}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Confiance</span>
                    <span class="metric-value">{ini['confiance']:.1%}</span>
                </div>
                <div class="score-bar"><div class="score-bar-fill" style="width:{ini['confiance']*100:.0f}%;background:{bar_color(ini['confiance'])}"></div></div>
                <div class="metric">
                    <span class="metric-label">Similarité</span>
                    <span class="metric-value">{ini['similarite']:.1%}</span>
                </div>
                <div class="score-bar"><div class="score-bar-fill" style="width:{ini['similarite']*100:.0f}%;background:{bar_color(ini['similarite'])}"></div></div>
                <div class="metric">
                    <span class="metric-label">Score composite</span>
                    <span class="metric-value" style="color:{bar_color(ini['score'])}">{ini['score']:.1%}</span>
                </div>
                <div class="coords-box">
                    [{', '.join(f'{c:.4f}' for c in ini['coords'])}]
                </div>
            </div>
            
            <div class="arrow">→</div>
            
            <div class="result-box optimal">
                <h3>✅ Configuration Optimale</h3>
                <div class="metric">
                    <span class="metric-label">Texte OCR</span>
                    <span class="metric-value">{opt['texte'] or '(vide)'}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Confiance</span>
                    <span class="metric-value">{opt['confiance']:.1%}</span>
                </div>
                <div class="score-bar"><div class="score-bar-fill" style="width:{opt['confiance']*100:.0f}%;background:{bar_color(opt['confiance'])}"></div></div>
                <div class="metric">
                    <span class="metric-label">Similarité</span>
                    <span class="metric-value">{opt['similarite']:.1%}</span>
                </div>
                <div class="score-bar"><div class="score-bar-fill" style="width:{opt['similarite']*100:.0f}%;background:{bar_color(opt['similarite'])}"></div></div>
                <div class="metric">
                    <span class="metric-label">Score composite</span>
                    <span class="metric-value" style="color:{bar_color(opt['score'])}">{opt['score']:.1%}</span>
                </div>
                <div class="coords-box">
                    [{', '.join(f'{c:.4f}' for c in opt['coords'])}]
                </div>
            </div>
        </div>
        
        <div class="amelioration {amel_class}">
            {amel_icon} Amélioration du score : {res['amelioration']:+.1%} 
            ({res['nb_evaluations']} évaluations OCR)
        </div>
        
        <table>
            <tr><th>Bord</th><th>Avant</th><th>Après</th><th>Delta</th></tr>
"""
        for i, label in enumerate(labels):
            d = opt['coords'][i] - ini['coords'][i]
            css = 'delta-positive' if abs(d) > 0.001 else ''
            html += f"""            <tr>
                <td>{label}</td>
                <td>{ini['coords'][i]:.6f}</td>
                <td>{opt['coords'][i]:.6f}</td>
                <td class="{css}">{d:+.6f}</td>
            </tr>
"""
        
        html += """        </table>
    </div>
"""
    
    html += f"""
    <div class="stats-footer">
        Généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
        {total_evals} évaluations OCR au total |
        Moteurs : {'Tesseract' if USE_TESSERACT else ''} {'+ EasyOCR' if USE_EASYOCR else ''}
    </div>
</body>
</html>"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    logger.info(f"📄 Rapport HTML: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    # Parser les arguments CLI
    args = parse_args()
    ENTITY_NAME, ENTITY_FILE, IMAGE_FILE, GROUND_TRUTH, dry_run, visualize = resolve_config(args)
    
    print(f"\n{'='*70}")
    print(f"  🎯 TEST D'OPTIMISATION DES ZONES OCR")
    print(f"  Entité : {ENTITY_NAME}")
    print(f"  Image  : {IMAGE_FILE}")
    print(f"  Zones  : {list(GROUND_TRUTH.keys())}")
    if dry_run:
        print(f"  Mode   : 🔍 DRY-RUN (aucune modification)")
    if visualize:
        print(f"  Mode   : 🖼️ VISUALISATION (image annotée en sortie)")
    print(f"{'='*70}\n")
    
    # Vérifications
    if not os.path.exists(ENTITY_FILE):
        print(f"❌ Fichier entité introuvable: {ENTITY_FILE}")
        sys.exit(1)
    
    if not os.path.exists(IMAGE_FILE):
        print(f"❌ Image introuvable: {IMAGE_FILE}")
        sys.exit(1)
    
    if not TESSERACT_DISPONIBLE:
        print(f"⚠️ Tesseract non disponible!")
        if not EASYOCR_DISPONIBLE:
            print(f"❌ Aucun moteur OCR disponible!")
            sys.exit(1)
    
    # Charger l'entité
    with open(ENTITY_FILE, 'r', encoding='utf-8') as f:
        entity = json.load(f)
    
    print(f"📋 Entité chargée: {entity['nom']}")
    print(f"   {len(entity['zones'])} zone(s) configurée(s)")
    print(f"   Zones à optimiser: {list(GROUND_TRUTH.keys())}")
    print(f"   Moteurs: Tesseract={'✅' if TESSERACT_DISPONIBLE else '❌'}, EasyOCR={'✅' if EASYOCR_DISPONIBLE else '❌'}")
    
    # Vérifier les dimensions de l'image
    with Image.open(IMAGE_FILE) as img:
        img_w, img_h = img.size
        print(f"   Image: {img_w}x{img_h} px")
    
    # Créer le dossier de sortie
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # -----------------------------------------------------------------------
    # PRÉPARATION DE L'IMAGE DE TRAVAIL (même pipeline que l'API réelle)
    # -----------------------------------------------------------------------
    print(f"\n🔍 Préparation de l'image de travail...")
    image_de_travail, cadre_info, crop_a_nettoyer = preparer_image_de_travail(IMAGE_FILE, entity)
    
    if cadre_info:
        print(f"   ✅ Cadre de référence détecté → optimisation sur image rognée")
        print(f"      Cadre: x={cadre_info['x']:.3f}, y={cadre_info['y']:.3f}, "
              f"w={cadre_info['width']:.3f}, h={cadre_info['height']:.3f}")
        print(f"      Image de travail: {image_de_travail}")
    else:
        print(f"   ⚠️ Pas de cadre détecté → optimisation sur image originale")

    # Lancer l'optimisation pour chaque zone
    resultats_zones = []
    debut_total = time.time()
    
    try:
        for zone in entity['zones']:
            nom_zone = zone['nom']
            
            if nom_zone not in GROUND_TRUTH:
                print(f"\n   ⏭️ Zone '{nom_zone}' ignorée (pas de vérité terrain)")
                continue
            
            debut_zone = time.time()
            
            resultat = optimiser_zone(
                image_path=image_de_travail,   # ← image rognée si cadre détecté
                nom_zone=nom_zone,
                coords_base=zone['coords'],
                texte_attendu=GROUND_TRUTH[nom_zone],
                lang=zone.get('lang', 'ara'),
                preprocess=zone.get('preprocess', 'arabic_textured')
            )
            
            duree_zone = time.time() - debut_zone
            resultat['duree_secondes'] = round(duree_zone, 1)
            resultats_zones.append(resultat)
            
            # Affichage résumé
            ini = resultat['initial']
            opt = resultat['optimal']
            print(f"\n{'─'*60}")
            print(f"📊 RÉSULTAT ZONE '{nom_zone}' ({duree_zone:.0f}s, {resultat['nb_evaluations']} évals)")
            print(f"   Initial  : score={ini['score']:.1%} (conf={ini['confiance']:.1%}, sim={ini['similarite']:.1%})")
            print(f"              texte='{ini['texte']}'")
            print(f"              coords={[round(c,4) for c in ini['coords']]}")
            print(f"   Optimal  : score={opt['score']:.1%} (conf={opt['confiance']:.1%}, sim={opt['similarite']:.1%})")
            print(f"              texte='{opt['texte']}'")
            print(f"              coords={[round(c,4) for c in opt['coords']]}")
            print(f"   Δ score  : {resultat['amelioration']:+.1%}")
    
    finally:
        # Nettoyage du fichier crop temporaire créé par preparer_image_de_travail
        if crop_a_nettoyer and os.path.exists(crop_a_nettoyer):
            try:
                os.remove(crop_a_nettoyer)
                logger.info(f"🗑️ Crop temporaire supprimé: {crop_a_nettoyer}")
            except Exception:
                pass
    
    duree_totale = time.time() - debut_total
    
    # Sauvegarder le rapport JSON (sans all_results pour alléger)
    rapport_json = {
        'entity': ENTITY_NAME,
        'image': IMAGE_FILE,
        'date': datetime.now().isoformat(),
        'duree_totale_secondes': round(duree_totale, 1),
        'moteurs': {
            'tesseract': TESSERACT_DISPONIBLE and USE_TESSERACT,
            'easyocr': EASYOCR_DISPONIBLE and USE_EASYOCR,
        },
        'zones': [{
            'zone': r['zone'],
            'texte_attendu': r['texte_attendu'],
            'initial': r['initial'],
            'optimal': r['optimal'],
            'amelioration': r['amelioration'],
            'nb_evaluations': r['nb_evaluations'],
            'duree_secondes': r['duree_secondes'],
        } for r in resultats_zones]
    }
    
    json_path = os.path.join(OUTPUT_DIR, "zone_optimization_report.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(rapport_json, f, ensure_ascii=False, indent=2)
    print(f"\n📄 Rapport JSON: {json_path}")
    
    # Générer le rapport HTML
    html_path = os.path.join(OUTPUT_DIR, "zone_optimization_report.html")
    generer_rapport_html(resultats_zones, html_path)
    
    # Résumé final
    print(f"\n{'='*70}")
    print(f"  ✅ OPTIMISATION TERMINÉE en {duree_totale:.0f} secondes")
    print(f"  📄 Rapport JSON : {json_path}")
    print(f"  📄 Rapport HTML : {html_path}")

    # -----------------------------------------------------------------------
    # VISUALISATION : tracer les cadres optimaux sur l'image originale
    # -----------------------------------------------------------------------
    if visualize and resultats_zones:
        annot_path = os.path.join(OUTPUT_DIR, f"zones_annotees_{ENTITY_NAME}.jpg")
        try:
            generer_image_annotee(
                image_orig_path=IMAGE_FILE,
                resultats_zones=resultats_zones,
                cadre_info=cadre_info,
                output_path=annot_path
            )
            print(f"  🖼️ Image annotée : {annot_path}")
            # Ouvrir automatiquement l'image si possible
            try:
                import subprocess
                subprocess.Popen(['start', '', annot_path], shell=True)
            except Exception:
                pass
        except Exception as e:
            print(f"  ⚠️ Visualisation échouée: {e}")

    print(f"{'='*70}")
    
    # =======================================================================
    # APPLICATION AUTOMATIQUE DES COORDONNÉES OPTIMALES
    # =======================================================================
    zones_a_appliquer = [r for r in resultats_zones if r['amelioration'] > 0.01]
    
    if not zones_a_appliquer:
        print(f"\n✅ Aucune amélioration significative trouvée. L'entité reste inchangée.")
        return
    
    print(f"\n{'─'*60}")
    if dry_run:
        print(f"  🔍 MODE DRY-RUN (aucune modification appliquée)")
    else:
        print(f"  📝 APPLICATION AUTOMATIQUE DES COORDONNÉES OPTIMALES")
    print(f"{'─'*60}")
    
    for r in zones_a_appliquer:
        print(f"\n   Zone '{r['zone']}' (Δ score: {r['amelioration']:+.1%}):")
        print(f"   Avant : {[round(c,6) for c in r['initial']['coords']]}")
        print(f"   Après : {r['optimal']['coords']}")
    
    if dry_run:
        print(f"\n   💡 Relancez sans --dry-run pour appliquer les modifications.")
        return
    
    # 1. Créer une sauvegarde horodatée de l'entité
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = ENTITY_FILE.replace('.json', f'_backup_{timestamp}.json')
    
    import shutil
    shutil.copy2(ENTITY_FILE, backup_path)
    print(f"\n   💾 Sauvegarde créée: {backup_path}")
    
    # 2. Mettre à jour les coordonnées dans l'entité
    with open(ENTITY_FILE, 'r', encoding='utf-8') as f:
        entity_data = json.load(f)
    
    nb_mises_a_jour = 0
    for r in zones_a_appliquer:
        nom_zone = r['zone']
        new_coords = r['optimal']['coords']
        
        for zone in entity_data['zones']:
            if zone['nom'] == nom_zone:
                old_coords = zone['coords']
                zone['coords'] = new_coords
                nb_mises_a_jour += 1
                print(f"   ✅ Zone '{nom_zone}' mise à jour:")
                print(f"      {[round(c,4) for c in old_coords]} → {[round(c,4) for c in new_coords]}")
                break
    
    # 3. Sauvegarder l'entité modifiée
    with open(ENTITY_FILE, 'w', encoding='utf-8') as f:
        json.dump(entity_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n   📝 Entité '{ENTITY_NAME}' sauvegardée avec {nb_mises_a_jour} zone(s) optimisée(s)")
    print(f"   📂 Fichier : {ENTITY_FILE}")
    print(f"   💾 Backup  : {backup_path}")
    
    print(f"\n{'='*70}")
    print(f"  ✅ {nb_mises_a_jour} zone(s) corrigée(s) automatiquement !")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
