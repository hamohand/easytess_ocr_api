import pypdfium2 as pdfium
from PIL import Image
import logging
import os

logger = logging.getLogger(__name__)

def convert_pdf_to_image(pdf_path, output_path=None, dpi=300):
    """
    Convertit la première page d'un PDF en image.
    Si output_path est fourni, sauvegarde l'image.
    Retourne le chemin de l'image sauvegardée.
    """
    try:
        pdf = pdfium.PdfDocument(pdf_path)
        if len(pdf) < 1:
            raise ValueError("Le PDF est vide")
            
        # Rendu de la première page
        page = pdf[0]
        # Scale = DPI / 72 (72 est la résolution par défaut PDF)
        scale = dpi / 72
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        
        if output_path:
            pil_image.save(output_path, format="JPEG", quality=95)
            return output_path
        else:
            # Si pas de chemin de sortie, on génère un nom basé sur le PDF
            base, _ = os.path.splitext(pdf_path)
            new_path = f"{base}_page1.jpg"
            pil_image.save(new_path, format="JPEG", quality=95)
            return new_path
            
    except Exception as e:
        logger.error(f"Erreur lors de la conversion PDF: {e}")
        raise e
