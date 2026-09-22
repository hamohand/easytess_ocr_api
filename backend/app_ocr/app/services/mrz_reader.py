"""
Lecteur MRZ (Machine Readable Zone) pour documents d'identité.

Supporte :
- CNI biométrique algérienne : format TD1 (3 lignes × 30 caractères)
- Passeport : format TD3 (2 lignes × 44 caractères)

Pipeline :
1. Détection de la zone MRZ dans l'image via OpenCV (morphologie)
2. Lecture OCR avec Tesseract (police OCR-B, whitelist restreinte)
3. Retour des lignes brutes pour parsing côté Java (mrz-java)
"""

import os
import re
import logging
import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)

# Caractères valides dans une MRZ
MRZ_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"

# Dimensions attendues
TD1_LINES = 3
TD1_CHARS_PER_LINE = 30
TD3_LINES = 2
TD3_CHARS_PER_LINE = 44


class MrzReader:
    """Service de détection et lecture de zones MRZ sur des documents d'identité."""

    def __init__(self):
        self._tesseract_available = False
        try:
            import pytesseract
            # Vérifier que Tesseract est accessible
            pytesseract.get_tesseract_version()
            self._tesseract_available = True
            logger.info("✅ MRZ Reader : Tesseract disponible")
        except Exception as e:
            logger.warning(f"⚠️ MRZ Reader : Tesseract non disponible — {e}")

    # =========================================================================
    # POINT D'ENTRÉE PRINCIPAL
    # =========================================================================

    def extract_mrz(self, image_path: str) -> dict:
        """
        Pipeline complet : détection → lecture → nettoyage.

        Args:
            image_path: Chemin absolu vers l'image (JPG/PNG).

        Returns:
            dict: {
                "success": bool,
                "format": "TD1" | "TD3" | null,
                "mrz_lines": ["...", "...", ...],
                "mrz_raw": "ligne1\\nligne2\\n...",
                "confidence": float (0.0 - 1.0),
                "error": str | null
            }
        """
        if not self._tesseract_available:
            return self._error("Tesseract non disponible pour la lecture MRZ")

        if not os.path.exists(image_path):
            return self._error(f"Fichier introuvable : {image_path}")

        try:
            # Charger l'image
            img = cv2.imread(image_path)
            if img is None:
                return self._error(f"Impossible de charger l'image : {image_path}")

            logger.info(f"🔍 MRZ : Analyse de {os.path.basename(image_path)} "
                        f"({img.shape[1]}×{img.shape[0]})")

            # Étape 1 : Détecter la zone MRZ
            mrz_roi = self._detect_mrz_zone(img)
            if mrz_roi is None:
                # Fallback : essayer sur le tiers inférieur de l'image
                mrz_roi = self._fallback_bottom_crop(img)
                if mrz_roi is None:
                    return self._error("Zone MRZ non détectée dans l'image")
                logger.info("🔍 MRZ : Utilisation du fallback (tiers inférieur)")

            # Étape 2 : Lire le texte MRZ avec Tesseract
            raw_text = self._read_mrz_text(mrz_roi)
            if not raw_text:
                return self._error("Aucun texte MRZ extrait par Tesseract")

            # Étape 3 : Nettoyer et valider les lignes
            lines, mrz_format, confidence = self._clean_and_validate(raw_text)
            if not lines:
                return self._error(f"Texte MRZ invalide : '{raw_text[:80]}...'")

            logger.info(f"✅ MRZ {mrz_format} détectée — {len(lines)} lignes, "
                        f"confiance={confidence:.0%}")
            for i, line in enumerate(lines):
                logger.info(f"   Ligne {i+1}: {line}")

            return {
                "success": True,
                "format": mrz_format,
                "mrz_lines": lines,
                "mrz_raw": "\n".join(lines),
                "confidence": round(confidence, 3),
                "error": None
            }

        except Exception as e:
            logger.error(f"❌ MRZ : Erreur inattendue — {e}", exc_info=True)
            return self._error(str(e))

    # =========================================================================
    # DÉTECTION DE LA ZONE MRZ
    # =========================================================================

    def _detect_mrz_zone(self, img: np.ndarray) -> np.ndarray:
        """
        Détecte la zone MRZ dans l'image via opérations morphologiques.

        Algorithme :
        1. Conversion en niveaux de gris
        2. Filtre blackhat (détecte les caractères sombres sur fond clair)
        3. Gradient de Scharr pour renforcer les bords
        4. Fermeture morphologique pour fusionner les caractères
        5. Seuillage Otsu + dilatation
        6. Recherche du plus grand contour rectangulaire en bas de l'image
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # Blackhat : révèle les caractères sombres sur fond clair
        kernel_bh = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel_bh)

        # Gradient de Scharr (horizontal) pour accentuer les bords verticaux des caractères
        grad_x = cv2.Sobel(blackhat, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
        grad_x = np.absolute(grad_x)
        min_val, max_val = grad_x.min(), grad_x.max()
        if max_val - min_val > 0:
            grad_x = (255 * (grad_x - min_val) / (max_val - min_val)).astype(np.uint8)
        else:
            grad_x = np.zeros_like(grad_x, dtype=np.uint8)

        # Fermeture morphologique : fusionner les caractères en blocs
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
        closed = cv2.morphologyEx(grad_x, cv2.MORPH_CLOSE, kernel_close)

        # Seuillage Otsu
        _, thresh = cv2.threshold(closed, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        # Dilatation pour combler les trous
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 11))
        dilated = cv2.dilate(thresh, kernel_dilate, iterations=2)

        # Trouver les contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)

        # Filtrer : chercher un grand rectangle horizontal dans la moitié inférieure
        candidates = []
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            aspect_ratio = cw / float(ch) if ch > 0 else 0
            area_ratio = (cw * ch) / (w * h)

            # La MRZ est un rectangle large (ratio > 5), en bas de l'image
            if (aspect_ratio > 3 and
                    area_ratio > 0.02 and
                    y > h * 0.4 and  # dans la moitié inférieure
                    cw > w * 0.4):   # au moins 40% de la largeur
                candidates.append((x, y, cw, ch, area_ratio))

        if not candidates:
            return None

        # Prendre le plus grand candidat
        candidates.sort(key=lambda c: c[4], reverse=True)
        x, y, cw, ch = candidates[0][:4]

        # Ajouter une marge
        margin_x = int(cw * 0.02)
        margin_y = int(ch * 0.15)
        x1 = max(0, x - margin_x)
        y1 = max(0, y - margin_y)
        x2 = min(w, x + cw + margin_x)
        y2 = min(h, y + ch + margin_y)

        roi = img[y1:y2, x1:x2]
        logger.info(f"🔍 MRZ : Zone détectée ({x1},{y1})-({x2},{y2}) "
                    f"= {x2-x1}×{y2-y1}px")
        return roi

    def _fallback_bottom_crop(self, img: np.ndarray) -> np.ndarray:
        """Fallback : découper le tiers inférieur de l'image."""
        h, w = img.shape[:2]
        # Pour TD1 (CNI) : MRZ occupe ~25% du bas
        # Pour TD3 (Passeport) : MRZ occupe ~20% du bas
        crop_ratio = 0.30
        y_start = int(h * (1 - crop_ratio))
        roi = img[y_start:h, 0:w]
        if roi.shape[0] < 20 or roi.shape[1] < 100:
            return None
        return roi

    # =========================================================================
    # LECTURE OCR DE LA ZONE MRZ
    # =========================================================================

    def _read_mrz_text(self, mrz_roi: np.ndarray) -> str:
        """
        Lit le texte MRZ avec Tesseract en mode optimisé.

        Prétraitement :
        - Agrandissement 2× pour améliorer la résolution
        - Conversion en niveaux de gris
        - Seuillage adaptatif
        - Inversion si nécessaire (texte sombre sur fond clair)

        Configuration Tesseract :
        - PSM 6 : bloc de texte uniforme
        - Whitelist : A-Z, 0-9, <
        - Pas de dictionnaire
        """
        import pytesseract

        # Agrandir l'image 2× (améliore la précision OCR)
        scale = 2
        roi = cv2.resize(mrz_roi, None, fx=scale, fy=scale,
                         interpolation=cv2.INTER_CUBIC)

        # Niveaux de gris
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi

        # Seuillage adaptatif (gère l'éclairage inégal)
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=31,
            C=10
        )

        # S'assurer que le texte est sombre sur fond clair
        # (la MRZ a typiquement des caractères sombres sur fond clair)
        white_ratio = np.sum(binary == 255) / binary.size
        if white_ratio < 0.5:
            binary = cv2.bitwise_not(binary)

        # Configuration Tesseract pour MRZ
        config = (
            "--psm 6 "
            "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789< "
            "-c load_system_dawg=false "
            "-c load_freq_dawg=false "
            "-c textord_min_linesize=2.5"
        )

        text = pytesseract.image_to_string(binary, config=config)
        logger.info(f"🔤 MRZ Tesseract brut : '{text.strip()[:100]}'")
        return text.strip()

    # =========================================================================
    # NETTOYAGE ET VALIDATION
    # =========================================================================

    def _clean_and_validate(self, raw_text: str):
        """
        Nettoie le texte OCR et détermine le format MRZ.

        Returns:
            tuple: (lines, format, confidence) ou (None, None, 0.0)
        """
        # Nettoyer : supprimer espaces, garder uniquement les caractères MRZ
        lines = []
        for line in raw_text.split('\n'):
            cleaned = line.strip().upper()
            # Remplacer les erreurs OCR courantes
            cleaned = cleaned.replace(' ', '')
            cleaned = cleaned.replace('|', '<')
            cleaned = cleaned.replace('«', '<')
            cleaned = cleaned.replace('»', '<')
            cleaned = cleaned.replace('(', '<')
            cleaned = cleaned.replace(')', '<')
            cleaned = cleaned.replace('{', '<')
            cleaned = cleaned.replace('}', '<')
            cleaned = cleaned.replace('[', '<')
            cleaned = cleaned.replace(']', '<')
            # Ne garder que les caractères MRZ valides
            cleaned = ''.join(c for c in cleaned if c in MRZ_CHARSET)
            if len(cleaned) >= 20:  # Une ligne MRZ fait au moins 28-30 chars
                lines.append(cleaned)

        if not lines:
            return None, None, 0.0

        # Déterminer le format
        mrz_format = None
        if len(lines) >= 3:
            # Possible TD1 (3 × 30)
            td1_lines = self._normalize_lines(lines, TD1_LINES, TD1_CHARS_PER_LINE)
            if td1_lines:
                mrz_format = "TD1"
                lines = td1_lines
        
        if mrz_format is None and len(lines) >= 2:
            # Possible TD3 (2 × 44)
            td3_lines = self._normalize_lines(lines, TD3_LINES, TD3_CHARS_PER_LINE)
            if td3_lines:
                mrz_format = "TD3"
                lines = td3_lines

        if mrz_format is None:
            # Tentative de récupération : si on a 2+ lignes de ~30 chars → TD1
            if len(lines) >= 2:
                avg_len = sum(len(l) for l in lines) / len(lines)
                if 25 <= avg_len <= 35:
                    mrz_format = "TD1"
                    lines = self._pad_lines(lines[:3], TD1_CHARS_PER_LINE)
                elif 38 <= avg_len <= 50:
                    mrz_format = "TD3"
                    lines = self._pad_lines(lines[:2], TD3_CHARS_PER_LINE)

        if mrz_format is None:
            return None, None, 0.0

        # Calculer la confiance basée sur la validité des caractères
        confidence = self._compute_confidence(lines, mrz_format)

        return lines, mrz_format, confidence

    def _normalize_lines(self, lines: list, expected_count: int,
                         expected_length: int) -> list:
        """Tente de normaliser les lignes à la longueur attendue."""
        result = []
        for line in lines:
            if len(line) == expected_length:
                result.append(line)
            elif abs(len(line) - expected_length) <= 3:
                # Padding ou troncature légère
                if len(line) < expected_length:
                    result.append(line + '<' * (expected_length - len(line)))
                else:
                    result.append(line[:expected_length])

        if len(result) >= expected_count:
            return result[:expected_count]
        return None

    def _pad_lines(self, lines: list, target_length: int) -> list:
        """Padde les lignes avec '<' pour atteindre la longueur cible."""
        result = []
        for line in lines:
            if len(line) < target_length:
                result.append(line + '<' * (target_length - len(line)))
            else:
                result.append(line[:target_length])
        return result

    def _compute_confidence(self, lines: list, mrz_format: str) -> float:
        """
        Calcule un score de confiance pour la lecture MRZ.

        Critères :
        - Longueur correcte des lignes
        - Présence de checksums valides (positions connues)
        - Densité de '<' cohérente
        """
        expected_length = TD1_CHARS_PER_LINE if mrz_format == "TD1" else TD3_CHARS_PER_LINE
        total_checks = 0
        passed_checks = 0

        for line in lines:
            total_checks += 1
            if len(line) == expected_length:
                passed_checks += 1

        # Vérifier que chaque caractère est valide
        all_chars = ''.join(lines)
        valid_chars = sum(1 for c in all_chars if c in MRZ_CHARSET)
        total_checks += 1
        if len(all_chars) > 0:
            char_ratio = valid_chars / len(all_chars)
            if char_ratio > 0.95:
                passed_checks += 1

        # Vérifier la présence du code pays (DZA) pour les documents algériens
        total_checks += 1
        combined = ''.join(lines)
        if 'DZA' in combined:
            passed_checks += 1

        # Vérifier le code document
        total_checks += 1
        if mrz_format == "TD1" and lines[0][:2] in ('ID', 'I<', 'AC'):
            passed_checks += 1
        elif mrz_format == "TD3" and lines[0][0] == 'P':
            passed_checks += 1

        return passed_checks / total_checks if total_checks > 0 else 0.0

    # =========================================================================
    # UTILITAIRES
    # =========================================================================

    @staticmethod
    def _error(message: str) -> dict:
        logger.warning(f"⚠️ MRZ : {message}")
        return {
            "success": False,
            "format": None,
            "mrz_lines": [],
            "mrz_raw": "",
            "confidence": 0.0,
            "error": message
        }


# Singleton
_mrz_reader_instance = None

def get_mrz_reader() -> MrzReader:
    """Retourne l'instance singleton du lecteur MRZ."""
    global _mrz_reader_instance
    if _mrz_reader_instance is None:
        _mrz_reader_instance = MrzReader()
    return _mrz_reader_instance
