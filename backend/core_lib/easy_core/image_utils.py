from PIL import Image, ImageOps
import numpy as np
import os
import logging

logger = logging.getLogger(__name__)


def apply_pillow_patch():
    """Fix for Pillow 10+ where ANTIALIAS was removed"""
    if not hasattr(Image, 'ANTIALIAS'):
        try:
            Image.ANTIALIAS = Image.Resampling.LANCZOS
        except AttributeError:
            Image.ANTIALIAS = 1


def get_image_dimensions(image_path):
    """Récupère les dimensions d'une image"""
    try:
        with Image.open(image_path) as img:
            return {'width': img.width, 'height': img.height}
    except:
        return {'width': 0, 'height': 0}


def crop_image(source, x, y, width, height, output_path=None):
    """Rogne une partie rectangulaire d'une image.

    Extrait exactement la zone définie par le sommet haut-gauche (x, y)
    et les dimensions (width, height), toutes en pixels.
    Utilise le slicing numpy pour garantir qu'aucun pixel n'est inventé :
    seuls les pixels existants dans l'image sont retournés.

    Args:
        source (str | PIL.Image.Image): Chemin vers l'image ou objet PIL Image.
        x (int): Coordonnée X du sommet haut-gauche du cadre (pixels).
        y (int): Coordonnée Y du sommet haut-gauche du cadre (pixels).
        width (int): Largeur du cadre à extraire (pixels).
        height (int): Hauteur du cadre à extraire (pixels).
        output_path (str, optional): Si fourni, sauvegarde l'image rognée
            à ce chemin. Le format est déduit de l'extension.

    Returns:
        PIL.Image.Image: L'image rognée.

    Raises:
        FileNotFoundError: Si source est un chemin et le fichier n'existe pas.
        ValueError: Si les coordonnées ou dimensions sont invalides.

    Exemple:
        >>> from easy_core.image_utils import crop_image
        >>> cropped = crop_image("scan.jpg", x=100, y=50, width=400, height=200)
        >>> cropped.save("extrait.jpg")

        >>> # Ou directement avec output_path
        >>> crop_image("scan.jpg", 100, 50, 400, 200, output_path="extrait.jpg")
    """
    # --- Ouvrir l'image ---
    if isinstance(source, str):
        if not os.path.exists(source):
            raise FileNotFoundError(f"Image introuvable : {source}")
        img = Image.open(source)
    elif isinstance(source, Image.Image):
        img = source.copy()
    else:
        raise TypeError(
            f"source doit être un chemin (str) ou un PIL.Image.Image, "
            f"reçu : {type(source).__name__}"
        )

    # Appliquer l'orientation EXIF pour que les coordonnées correspondent
    # à ce que l'utilisateur voit (comme dans Paint)
    img = ImageOps.exif_transpose(img)

    img_width, img_height = img.size

    # --- Validation des paramètres ---
    if width <= 0 or height <= 0:
        raise ValueError(
            f"Les dimensions doivent être positives (reçu : {width}×{height})"
        )
    if x < 0 or y < 0:
        raise ValueError(
            f"Les coordonnées doivent être positives ou nulles (reçu : x={x}, y={y})"
        )
    if x >= img_width or y >= img_height:
        raise ValueError(
            f"Le point de départ ({x}, {y}) est hors de l'image "
            f"({img_width}×{img_height})"
        )

    # Borner strictement aux limites de l'image
    right = min(x + width, img_width)
    bottom = min(y + height, img_height)

    actual_w = right - x
    actual_h = bottom - y

    if actual_w != width or actual_h != height:
        logger.warning(
            f"⚠️ Cadre tronqué aux limites de l'image : "
            f"demandé ({x},{y})+({width}×{height}), "
            f"effectif ({x},{y})+({actual_w}×{actual_h})"
        )

    # --- Rognage par slicing numpy (jamais de padding) ---
    arr = np.array(img)
    cropped_arr = arr[y:bottom, x:right]
    cropped = Image.fromarray(cropped_arr)

    logger.info(
        f"Rognage: ({x},{y})+({actual_w}×{actual_h}) "
        f"depuis image {img_width}×{img_height} → résultat {cropped.size[0]}×{cropped.size[1]}"
    )

    # Conversion RGBA → RGB si nécessaire (pour sauvegarde JPEG)
    if output_path and output_path.lower().endswith(('.jpg', '.jpeg')):
        if cropped.mode in ('RGBA', 'P', 'LA'):
            cropped = cropped.convert('RGB')

    # --- Sauvegarde optionnelle ---
    if output_path:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        cropped.save(output_path)
        logger.info(f"✅ Image rognée sauvegardée : {output_path} ({cropped.size[0]}×{cropped.size[1]})")

    return cropped

