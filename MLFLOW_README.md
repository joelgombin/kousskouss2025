# Monitoring MLflow pour Kouskous 2025

Ce projet utilise MLflow pour monitorer et analyser les performances du système d'extraction des données du festival Kouskous 2025.

## 🚀 Fonctionnalités MLflow intégrées

### Métriques suivies
- **Performances d'extraction** : nombre de restaurants et plats extraits
- **Temps de traitement** : temps par fichier PDF et temps total
- **Taux de succès** : pourcentage de fichiers traités avec succès
- **Distribution géographique** : répartition des restaurants par quartier
- **Analyse nutritionnelle** : comptage des plats végétariens et vegan
- **Métriques par fichier** : suivi détaillé de chaque PDF traité

### Paramètres loggés
- Modèle utilisé (DSPy/OpenRouter)
- Configuration des tokens
- Horodatage des exécutions
- Paramètres de cache

### Artefacts sauvegardés
- Fichier de résultats JSON (`output/restaurants.json`)
- Fichier de progression (`output/extraction_progress.json`)

## 📊 Utilisation

### 1. Exécution normale avec monitoring
```bash
python main.py
```
Chaque exécution créera automatiquement un nouveau run MLflow avec toutes les métriques.

### 2. Lancement de l'interface MLflow
```bash
python launch_mlflow.py
```
Ouvre l'interface web MLflow sur http://localhost:5000

### 3. Dashboard d'analyse
```bash
python mlflow_dashboard.py
```
Affiche un résumé des performances et génère des graphiques d'analyse.

## 📈 Métriques principales

### Métriques globales
- `total_restaurants` : Nombre total de restaurants extraits
- `total_plats` : Nombre total de plats extraits
- `total_run_time` : Temps total d'exécution en secondes
- `success_rate` : Taux de succès (0.0 à 1.0)

### Métriques par fichier
- `restaurants_extracted_{filename}` : Restaurants extraits par fichier
- `plats_extracted_{filename}` : Plats extraits par fichier
- `processing_time_{filename}` : Temps de traitement par fichier
- `pdf_pages_{filename}` : Nombre de pages par PDF

### Métriques de qualité
- `vegetarian_plats` : Nombre de plats végétariens
- `vegan_plats` : Nombre de plats vegan
- `unique_quartiers` : Nombre de quartiers différents

### Métriques par quartier
- `restaurants_in_{quartier}` : Nombre de restaurants par quartier

## 🔍 Analyse des performances

L'interface MLflow permet de :
- Comparer les performances entre différentes exécutions
- Identifier les fichiers PDF problématiques
- Suivre l'évolution des extractions dans le temps
- Analyser la distribution géographique des restaurants
- Détecter les régressions de performance

## 📂 Structure des données MLflow

```
mlruns/
├── 0/                          # Expérience par défaut
└── {experiment_id}/            # Expérience kouskous2025_extraction
    ├── meta.yaml              # Métadonnées de l'expérience
    └── {run_id}/              # Dossier pour chaque run
        ├── meta.yaml          # Métadonnées du run
        ├── metrics/           # Fichiers de métriques
        ├── params/            # Paramètres du run
        ├── tags/              # Tags du run
        └── artifacts/         # Artefacts sauvegardés
            ├── results/       # Fichiers de résultats
            └── progress/      # Fichiers de progression
```

## 🛠️ Configuration avancée

### Variables d'environnement MLflow (optionnelles)
```bash
export MLFLOW_TRACKING_URI="file:./mlruns"     # URI de tracking
export MLFLOW_EXPERIMENT_NAME="kouskous2025_extraction"  # Nom de l'expérience
```

### Utilisation avec un serveur MLflow distant
Pour utiliser un serveur MLflow distant, modifiez la ligne dans `main.py` :
```python
mlflow.set_tracking_uri("http://your-mlflow-server:5000")
```

## 📋 Checklist de monitoring

- [ ] Vérifier que les métriques sont bien loggées après chaque exécution
- [ ] Consulter régulièrement l'interface MLflow pour détecter les anomalies
- [ ] Comparer les performances entre les différents modèles
- [ ] Analyser les fichiers en échec pour améliorer l'extraction
- [ ] Surveiller les temps de traitement pour optimiser les performances

## 🚨 Dépannage

### Problème : Interface MLflow ne se lance pas
```bash
pip install mlflow>=2.8.0
```

### Problème : Graphiques non générés
```bash
pip install matplotlib seaborn pandas
```

### Problème : Métriques manquantes
Vérifiez que le dossier `mlruns` existe et que les permissions sont correctes.

### Problème : Runs non visibles
Assurez-vous que l'expérience "kouskous2025_extraction" est bien créée et sélectionnée dans l'interface.
