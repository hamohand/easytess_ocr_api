# Documentation Projet API OCR - Déploiement en Ligne

## 1. Objectif
Le but est d'exposer les fonctionnalités d'OCR (comme l'extraction de CNI `cni_01`) via une API autonome, accessible depuis l'extérieur (applications tierces, mobile, web) tout en garantissant la stabilité du serveur et la sécurité des accès.

## 2. L'Endpoint d'Extraction Directe
Une route dédiée a été créée pour effectuer l'upload et l'analyse en une seule étape fluide pour le client final :
- **Route** : `POST /api/v1/extract/cni`
- **Body (form-data)** :
  - `image` : (Fichier) L'image ou le PDF de la carte d'identité.
  - `entite` : (Optionnel) Identifiant de l'entité, par défaut `cni_01`.
  - `mode` : (Optionnel) Mode d'analyse, par défaut `approfondi`.

**Exemple de retour JSON :**
```json
{
  "success": true,
  "document_type": "CNI",
  "entite_utilisee": "cni_01",
  "data": {
    "nom": "DUPONT",
    "prenom": "JEAN",
    "numero_cni": "123456789"
  },
  "alertes": []
}
```

## 3. Prérequis Matériels (Hébergement)
L'utilisation de modèles de Deep Learning (PaddleOCR, Tesseract) pour l'analyse d'images est extrêmement gourmande en ressources.
- **RAM Minimale** : **4 Go de RAM**. (Un serveur avec moins risque de crasher via "OOM Kill" - Out of Memory).
- **CPU** : **2 vCPUs** au minimum pour assurer un temps de réponse acceptable (2 à 5 secondes par requête image).

## 4. Stratégies d'Optimisation & Stabilité
Pour éviter que le serveur ne plante lors de pics de charge (plusieurs envois simultanés) :
1. **Gestion de la concurrence (Gunicorn)** : Lors du déploiement, il faudra configurer le serveur (via Gunicorn) pour n'utiliser qu'**un seul "worker"** (processus actif). Ainsi, les requêtes simultanées seront mises dans une file d'attente saine plutôt que d'être traitées en même temps (ce qui épuiserait la RAM instantanément).
2. **Cache des modèles (Déjà implémenté)** : Les modèles PaddleOCR et EasyOCR sont chargés une seule fois en mémoire au démarrage de l'API (Lazy Loading), ce qui accélère drastiquement les appels suivants.
3. **Optimisation Frontend (Recommandation Forte)** : Le client (site web ou app mobile) **doit compresser et redimensionner** l'image (ex: max 1500px - 1920px de large) *avant* l'envoi HTTP. Cela diminue le temps de traitement OCR et la consommation mémoire par 3.

## 5. Sécurisation de l'API
Étant donné le coût en calcul de chaque requête, l'API ne doit absolument pas être laissée publique (ouverte à tous sur internet).
- **Action requise avant déploiement** : Mettre en place un système de **Clé d'API**. Chaque client devra envoyer un token valide dans le header (ex: `X-API-Key: xxxxx`) pour prouver son identité.
- Les règles CORS (Cross-Origin Resource Sharing) actuelles devront être restreintes aux noms de domaines autorisés si appelée depuis un navigateur web.

## 6. Intégration Docker (Exemple de Déploiement)
L'image Docker (`backend/Dockerfile`) est fonctionnelle. Voici comment l'intégrer facilement dans votre stack `docker-compose-prod.yml` de production :

```yaml
version: '3.8'
services:
  easytess-api:
    build: 
      context: ./backend
    container_name: easytess_ocr_api
    restart: always
    ports:
      - "8082:8082"
    # Configuration recommandée en prod : 1 worker pour économiser la RAM, timeout élevé
    command: gunicorn -w 1 --timeout 120 -b 0.0.0.0:8082 app.main:app
    deploy:
      resources:
        limits:
          memory: 3.5G # Protection: Empêche le conteneur de prendre toute la RAM du serveur host
```
