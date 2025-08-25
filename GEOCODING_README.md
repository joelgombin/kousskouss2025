# Géolocalisation des Restaurants - Kouskous 2025

Ce script utilise l'API de géocodage de l'IGN Géoplateforme pour géolocaliser automatiquement les adresses des restaurants participant au festival Kouskous 2025.

## 🌍 Fonctionnalités

- **Géocodage automatique** : Convertit les adresses textuelles en coordonnées GPS (latitude/longitude)
- **API IGN Géoplateforme** : Utilise l'API officielle française de haute qualité
- **Gestion d'erreurs robuste** : Traite les échecs de géocodage et les erreurs réseau
- **Logging détaillé** : Enregistre toutes les opérations dans un fichier de log
- **Statistiques** : Affiche un résumé des résultats de géolocalisation
- **Respect des limites** : Inclut des délais pour respecter les quotas de l'API

## 📁 Fichiers

- `geolocalize_restaurants.py` - Script principal
- `output/restaurants.json` - Fichier d'entrée (restaurants originaux)
- `output/restaurants_geolocalized.json` - Fichier de sortie (avec coordonnées)
- `geolocalization.log` - Journal des opérations

## 🚀 Utilisation

### Exécution simple

```bash
python geolocalize_restaurants.py
```

### Avec UV (recommandé)

```bash
uv run geolocalize_restaurants.py
```

## 📊 Format des données

### Données d'entrée
Chaque restaurant doit avoir au minimum :
```json
{
  "nom": "Nom du restaurant",
  "adresse": "12 rue de la Paix - 13001 Marseille",
  // ... autres champs
}
```

### Données de sortie
Le script ajoute les champs suivants :
```json
{
  "nom": "Nom du restaurant",
  "adresse": "12 rue de la Paix - 13001 Marseille",
  "longitude": 5.376954,
  "latitude": 43.297041,
  "geocoding_status": "success",
  // ... autres champs originaux
}
```

## 📈 Statuts de géocodage

- `success` : Adresse géolocalisée avec succès
- `failed` : Échec de la géolocalisation (adresse non trouvée)
- `no_address` : Restaurant sans adresse renseignée

## 🔧 Configuration

### Délai entre requêtes
Par défaut : 100ms entre chaque requête pour respecter les limites de l'API.
Modifiable dans la classe `IGNGeocoder` :

```python
self.delay = 0.1  # en secondes
```

### Timeout des requêtes
Par défaut : 10 secondes. Modifiable dans la méthode `geocode_address` :

```python
response = self.session.get(self.base_url, params=params, timeout=10)
```

## 📋 Exemple de log

```
2024-01-20 14:30:15 - INFO - Chargement réussi de 150 restaurants depuis output/restaurants.json
2024-01-20 14:30:15 - INFO - Début de la géolocalisation de 150 restaurants...
2024-01-20 14:30:15 - INFO - Traitement 1/150: L'ECOMOTIVE
2024-01-20 14:30:16 - INFO - Adresse géolocalisée: 2 Pl. des Marseillaises - 13001 -> (5.376954, 43.297041)
...
2024-01-20 14:35:20 - INFO - === STATISTIQUES DE GÉOLOCALISATION ===
2024-01-20 14:35:20 - INFO - Total des restaurants: 150
2024-01-20 14:35:20 - INFO - Géolocalisés avec succès: 142 (94.7%)
2024-01-20 14:35:20 - INFO - Échecs de géolocalisation: 6 (4.0%)
2024-01-20 14:35:20 - INFO - Sans adresse: 2 (1.3%)
```

## 🚨 Gestion d'erreurs

Le script gère automatiquement :
- **Erreurs réseau** : Timeout, connexion fermée, etc.
- **Adresses introuvables** : L'API ne trouve pas de correspondance
- **Restaurants sans adresse** : Champ adresse vide ou manquant
- **Erreurs de parsing JSON** : Réponse API malformée

## 📡 À propos de l'API IGN

L'API de géocodage de l'IGN Géoplateforme :
- **Gratuite** pour un usage raisonnable
- **Données officielles françaises** de haute qualité
- **Couverture nationale** complète
- **Documentation** : [https://geoservices.ign.fr/documentation/services/services-geoplateforme/geocodage](https://geoservices.ign.fr/documentation/services/services-geoplateforme/geocodage)

## 🛠️ Dépendances

- `requests>=2.31.0` - Pour les requêtes HTTP
- `python>=3.12.0` - Version Python minimale

Toutes les dépendances sont déjà définies dans `pyproject.toml`.
