import json
import os
from datetime import datetime
from PIL import Image, ImageDraw
import base64
from io import BytesIO

class EntityManager:
    def __init__(self, entities_dir="entities"):
        self.entities_dir = entities_dir
        os.makedirs(entities_dir, exist_ok=True)
    
    def sauvegarder_entite(self, nom_entite, zones, image_path=None, description="", cadre_reference=None):
        """Sauvegarde une entité avec ses zones et cadre de référence optionnel"""
        entite_data = {
            'nom': nom_entite,
            'description': description,
            'date_creation': datetime.now().isoformat(),
            'image_reference': image_path,
            'zones': zones,
            'cadre_reference': cadre_reference,  # NOUVEAU: Cadre de référence à 3 étiquettes
            'metadata': {
                'nombre_zones': len(zones),
                'image_dimensions': self._get_image_dimensions(image_path) if image_path else None
            }
        }
        
        fichier_entite = os.path.join(self.entities_dir, f"{nom_entite}.json")
        
        with open(fichier_entite, 'w', encoding='utf-8') as f:
            json.dump(entite_data, f, ensure_ascii=False, indent=2)
        
        return fichier_entite
    
    def charger_entite(self, nom_entite):
        """Charge une entité"""
        fichier_entite = os.path.join(self.entities_dir, f"{nom_entite}.json")
        
        if os.path.exists(fichier_entite):
            with open(fichier_entite, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def lister_entites(self):
        """Liste toutes les entités disponibles"""
        entites = []
        if not os.path.exists(self.entities_dir):
            return []
            
        for fichier in os.listdir(self.entities_dir):
            if fichier.endswith('.json'):
                nom = fichier[:-5]  # Retirer .json
                entite_data = self.charger_entite(nom)
                if entite_data:
                    entites.append(entite_data)
        return entites
    
    def _get_image_dimensions(self, image_path):
        """Récupère les dimensions d'une image"""
        try:
            with Image.open(image_path) as img:
                return {'width': img.width, 'height': img.height}
        except:
            return None
    
    def generer_image_annotation(self, image_path, zones, output_path=None, cadre_reference=None):
        """Génère une image avec les zones annotées
        Args:
            image_path: Chemin image source
            zones: Liste des zones
            output_path: Chemin sortie (optonnel)
            cadre_reference: Dikto du cadre pour transformation des coords (ou None)
        """
        try:
            with Image.open(image_path) as img:
                draw = ImageDraw.Draw(img)
                img_w, img_h = img.size
                
                # Paramètres du cadre par défaut (Image entière)
                x_ref_min = 0.0
                y_ref_min = 0.0
                larg_cadre = 1.0
                haut_cadre = 1.0
                
                # Si cadre fourni, calculer les paramètres de transformation
                if cadre_reference and cadre_reference.get('haut') and cadre_reference.get('gauche_bas'):
                     # Récupérer les ancres (supposées normalisées 0-1 dans l'Image)
                     # Note: Ici on utilise les positions "théoriques" ou détectées stockées dans l'entité
                     # Si l'entité a été sauvegardée, position_base contient les coords dans l'IMAGE.
                     
                     # Attention: position_base dans le JSON est [x, y]
                     gb = cadre_reference['gauche_bas'].get('position_base', [0, 1])
                     h = cadre_reference['haut'].get('position_base', [0.5, 0])
                     d = cadre_reference['droite'].get('position_base', [1, 0])
                     
                     x_ref_min = gb[0]
                     y_ref_min = h[1]
                     larg_cadre = d[0] - gb[0]
                     haut_cadre = gb[1] - h[1]
                
                for i, zone in enumerate(zones):
                    coords = zone['coords']
                    # Coords sont [x1, y1, x2, y2] RELATIFS AU CADRE
                    
                    # 1. Transformer Relatif Cadre -> Relatif Image
                    rx1, ry1, rx2, ry2 = coords
                    gx1 = rx1 * larg_cadre + x_ref_min
                    gy1 = ry1 * haut_cadre + y_ref_min
                    gx2 = rx2 * larg_cadre + x_ref_min
                    gy2 = ry2 * haut_cadre + y_ref_min
                    
                    # 2. Transformer Relatif Image -> Absolu Pixels
                    x1 = int(gx1 * img_w)
                    y1 = int(gy1 * img_h)
                    x2 = int(gx2 * img_w)
                    y2 = int(gy2 * img_h)
                    
                    nom = zone.get('nom', f'Zone {i+1}')
                    
                    # Dessiner le rectangle
                    draw.rectangle([x1, y1, x2, y2], outline='red', width=3)
                    
                    # Ajouter le nom de la zone
                    draw.text((x1, y1-25), nom, fill='blue')
                    
                    # Ajouter un numéro
                    draw.ellipse([x1-15, y1-15, x1, y1], fill='green')
                    draw.text((x1-10, y1-12), str(i+1), fill='white')
                
                if output_path:
                    img.save(output_path)
                    return output_path
                else:
                    # Retourner en base64 pour l'affichage web
                    buffered = BytesIO()
                    img.save(buffered, format="JPEG", quality=85)
                    return base64.b64encode(buffered.getvalue()).decode()
                    
        except Exception as e:
            print(f"Erreur génération image: {e}")
            return None
