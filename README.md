# Plus de data dans mon couscous ! 🍽️

## Qu'est-ce que Kouskous2025 ?

**Kouss•kouss** est un festival culinaire marseillais entièrement consacré au couscous qui se déroule chaque année (cette année du 22 août au 7 septembre). Le programme officiel du festival, disponible sur [kousskouss.com](https://kousskouss.com/), liste tous les restaurants participants avec leurs plats, prix et adresses.

**Le problème :** Ce programme n'existe qu'en format PDF, ce qui le rend difficile à consulter sur mobile et impossible à filtrer ou rechercher efficacement.

**Notre solution :** Ce projet utilise la puissance des VLM (Vision Language Models) pour extraire automatiquement toutes les informations du PDF et les transformer en données structurées exploitables.

## Comment ça marche ? 🤖

### L'architecture en 4 étapes

1. **📄 PDF Processing Pipeline**
   - **Stirling PDF** : Éclatement du PDF multipages en pages individuelles
   - **sips/pdfinfo** : Conversion optimisée PDF→PNG avec détection automatique des dimensions
   - **Content boundary detection** : Algorithme de détection des marges basé sur l'analyse de variance des pixels
   - **Caching via MD5** : Évite le retraitement des fichiers non modifiés

2. **🧠 LLM-based Structured Extraction**
   - **DSPy Framework** : Pipeline reproductible avec signatures typées (`ExtractPlats`)
   - **OpenRouter API** : Abstraction multi-modèles (défaut: `google/gemini-2.5-flash`)
   - **Vision + Text processing** : Traitement d'images avec contexte métier spécifique
   - **Pydantic models** : Validation stricte avec fallback gracieux sur erreurs de parsing

3. **📍 Geocoding Service**
   - **IGN Géoplateforme API** : Service officiel français pour adresses françaises
   - **Rate limiting** : 100ms entre requêtes, timeout 10s, retry logic
   - **Batch processing** : Géolocalisation différée pour éviter la latence sur l'extraction

4. **📊 MLOps & Monitoring**
   - **MLflow tracking** : Métriques temps réel, coûts tokens, taux d'erreur
   - **Prompt logging** : Historique complet des appels LLM pour debugging
   - **Artifact versioning** : Sauvegarde automatique des outputs et modèles

### Stack technique

- **Python 3.12+** avec **uv** (dependency resolver ultra-rapide + virtualenv)
- **DSPy 3.0+** : Framework LLM structuré avec caching automatique
- **OpenRouter** : Gateway unifié vers les différents modèles LLM/VLM
- **MLflow 2.8+** : Experiment tracking et model registry
- **Pydantic 2.0** : Validation de données avec coercion automatique
- **stirling pdf/sips/pdfinfo** : Stack de traitement PDF/images

### Patterns d'implémentation

#### Resilience & Error Handling
```python
# Validation tolérante aux erreurs d'extraction LLM
@validator('plats', pre=True)
def validate_plats(cls, v):
    # Récupération gracieuse des plats même si certains échouent
    valid_plats = []
    for plat_data in v:
        try:
            plat = Plat(**plat_data)
            valid_plats.append(plat)
        except ValidationError:
            # Fallback avec données minimales
            continue
    return valid_plats
```

#### Progressive Processing avec State Recovery
```python
# Système de cache basé sur hash MD5 des fichiers
file_hash = get_file_hash(pdf_path)
if pdf_path.name in progress["processed_files"]:
    stored_hash = progress["processed_files"][pdf_path.name].get("hash")
    if stored_hash == file_hash:
        return cached_results  # Skip reprocessing
```


## Installation et utilisation 🚀

### Prérequis

```bash
# Installer UV (gestionnaire de paquets Python moderne)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Ou avec pip
pip install uv
```

### Configuration

1. **Cloner le projet**
```bash
git clone [repository-url]https://github.com/joelgombin/kousskouss2025.git
cd kouskous2025
```

2. **Installer les dépendances**
```bash
uv sync
```

3. **Configurer l'API IA**
```bash
# Créer un fichier .env
echo "OPENROUTER_API_KEY=your_api_key_here" > .env
echo "MODEL=google/gemini-2.5-flash" >> .env
```

4. **Placer le PDF du programme**
   - Télécharger le programme depuis [kousskouss.com](https://kousskouss.com/)
   - utiliser Stirling PDF pour le découper en pages individuelles
   - placer les pages individuelles des restaurants participants dans le dossier `programme_bursted`

### Lancer l'extraction

```bash
# Extraction complète des données
uv run python main.py

# Géolocalisation des adresses
uv run python geolocalize_restaurants.py

# Interface de monitoring
uv run python launch_mlflow.py
```

## Résultats obtenus 📈

Le système extrait automatiquement :

- **230+ restaurants** participant au festival
- **290+ plats** avec leurs prix et descriptions
- **Coordonnées GPS** de chaque restaurant
- **Informations détaillées** : chefs, téléphones, horaires, plats, prix, descriptions, etc.

### Format des données

```json
{
    "nom": "L'ECOMOTIVE",
    "adresse": "2 Pl. des Marseillaises - 13001",
    "telephone": "07 83 09 70 36",
    "chef": null,
    "plats": [
      {
        "nom": "KOUSS-LECO",
        "prix": "15 €",
        "description": "Couscous boulettes meati aux deux pois (pois chiches et cassés) parfumés avec des champignons, des noix, servi avec un bouillon épicé de tomates rôties et herbes fraîches.",
        "vegetarien": false,
        "vegan": false,
        "dates": [
          {
            "jour": 23,
            "mois": 8
          },
          {
            "jour": 24,
            "mois": 8
          }
        ],
        "services": [
          "midi"
        ]
      },
      {
        "nom": "Aubergines confites",
        "prix": "15 €",
        "description": "Aubergines confites fondantes et harissa aux abricots.",
        "vegetarien": true,
        "vegan": true,
        "dates": [
          {
            "jour": 23,
            "mois": 8
          },
          {
            "jour": 24,
            "mois": 8
          }
        ],
        "services": [
          "midi"
        ]
      },
      {
        "nom": "Pavlova",
        "prix": "15 €",
        "description": "Pavlova à la meringue d'aquafaba et son fruit de saison.",
        "vegetarien": true,
        "vegan": true,
        "dates": [
          {
            "jour": 23,
            "mois": 8
          },
          {
            "jour": 24,
            "mois": 8
          }
        ],
        "services": [
          "midi"
        ]
      }
    ]
  }
```


## Structure du projet 🗂️

```
kouskous2025/
├── main.py                    # Script principal d'extraction
├── models.py                  # Modèles de données (Restaurant, Plat)
├── geolocalize_restaurants.py # Service de géolocalisation
├── programme_bursted/         # pages pdf individuelles
├── output/                    # Fichiers de résultats
│   ├── restaurants.json       # Données extraites
│   └── restaurants_geolocalized.json # Avec coordonnées GPS
└── mlruns/                    # Données de monitoring MLflow
```

## Fonctionnalités avancées 🔧

### Reprise sur erreur
- Le système sauvegarde automatiquement son avancement
- En cas d'interruption, il reprend où il s'était arrêté
- Chaque fichier PDF est identifié par son empreinte MD5

### Validation robuste
- Les données extraites sont automatiquement vérifiées
- Les erreurs de format sont corrigées quand possible
- Les restaurants incomplets sont sauvegardés avec les données disponibles

### Cache intelligent
- Les appels à l'IA sont mis en cache pour éviter les doublons
- Accélère les exécutions suivantes
- Réduit les coûts d'utilisation

## Feuille de route 🎯

- [X] Extraction automatique des données du programme PDF
- [X] Géolocalisation des restaurants
- [X] Monitoring et suivi de qualité avec MLflow
- [X] Validation et nettoyage automatique des données

