# Stratégie de Portabilité Mobile (Android)

Ce document décrit les options et la stratégie recommandée pour porter l'application EasyTess (Angular + Python) sur mobile, spécifiquement Android.

## Contexte Technique
*   **Frontend** : Angular
*   **Backend** : Python (Flask + EasyOCR/PyTorch)
*   **Contrainte** : Le moteur OCR est lourd et nécessite des ressources importantes, rendant une exécution locale sur mobile complexe.

**Architecture Recommandée** : Application Mobile (Client) ↔ API Python (Serveur Distant).

---

## Options de Développement

### 1. Ionic + Capacitor (Recommandé 🏆)
C'est la méthode idéale car elle **réutilise le code Angular existant**.
*   **Principe** : Capacitor "emballe" le site Angular dans une coquille native Android.
*   **Avantages** :
    *   **90% de réutilisation de code** : Conservation des composants, services et logique Angular.
    *   **Fonctionnalités natives** : Accès facile à l'appareil photo, à la galerie, et aux notifications via plugins.
    *   **Développement rapide** : Une seule commande (`npx cap add android`) suffit pour initialiser le projet Android Studio.
*   **Inconvénients** : Nécessite une connexion internet pour l'analyse OCR (API Python distante).

### 2. PWA (Progressive Web App) (Le plus rapide ⚡)
L'application Angular devient une PWA installable.
*   **Principe** : L'utilisateur installe l'application depuis le navigateur (Chrome Mobile).
*   **Avantages** :
    *   **Zéro code natif** : Configuration purement Angular (`ng add @angular/pwa`).
    *   **Mises à jour instantanées** : Pas de passage par le Play Store.
*   **Inconvénients** : Accès au matériel moins fluide que le natif, bien que la capture caméra fonctionne via l'input file.

### 3. Flutter ou Native Android (Kotlin) (Le plus performant 🚀)
Réécriture complète du frontend.
*   **Principe** : Création d'une interface mobile spécifique de zéro.
*   **Avantages** : Performance fluide maximale, UX 100% native.
*   **Inconvénients** : Maintenance de deux bases de code frontend distinctes (Angular Web + Mobile).

---

## Recommandation Stratégique
**Adopter l'option 1 : Ionic/Capacitor.**
Cette approche permet de générer rapidement un fichier `.apk` installable en capitalisant sur le développement Angular déjà réalisé, tout en offrant une expérience utilisateur proche du natif pour la capture de documents.
