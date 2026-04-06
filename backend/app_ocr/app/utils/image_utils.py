from PIL import Image
import os

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
