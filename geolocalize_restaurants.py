#!/usr/bin/env python3
"""
Script de géolocalisation des restaurants du Kouskous 2025
Utilise l'API de géocodage de l'IGN Géoplateforme
"""

import json
import requests
import time
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('geolocalization.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IGNGeocoder:
    """Classe pour géolocaliser les adresses avec l'API IGN"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise le géocodeur IGN
        
        Args:
            api_key: Clé API IGN (optionnelle, certains services sont libres)
        """
        # URL de l'API de géocodage IGN Géoplateforme
        self.base_url = "https://data.geopf.fr/geocodage/search"
        self.api_key = api_key
        self.delay = 0.1  # Délai entre les requêtes (100ms)
        self.session = requests.Session()
        
        # Headers pour les requêtes
        self.session.headers.update({
            'User-Agent': 'Kouskous2025-Geocoder/1.0',
            'Accept': 'application/json'
        })
    
    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Géolocalise une adresse
        
        Args:
            address: L'adresse à géolocaliser
            
        Returns:
            Tuple (longitude, latitude) si trouvé, None sinon
        """
        params = {
            'q': address,
            'limit': 1,
            'returntruegeometry': 'true'
        }
        
        try:
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('features') and len(data['features']) > 0:
                feature = data['features'][0]
                geometry = feature.get('geometry', {})
                coordinates = geometry.get('coordinates')
                
                if coordinates and len(coordinates) >= 2:
                    longitude, latitude = coordinates[0], coordinates[1]
                    logger.info(f"Adresse géolocalisée: {address} -> ({longitude:.6f}, {latitude:.6f})")
                    return longitude, latitude
                    
            logger.warning(f"Aucun résultat trouvé pour l'adresse: {address}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la requête pour '{address}': {e}")
            return None
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Erreur lors du parsing de la réponse pour '{address}': {e}")
            return None
    
    def geocode_restaurants(self, restaurants: List[Dict]) -> List[Dict]:
        """
        Géolocalise une liste de restaurants
        
        Args:
            restaurants: Liste des restaurants à géolocaliser
            
        Returns:
            Liste des restaurants avec coordonnées ajoutées
        """
        geolocated_restaurants = []
        total = len(restaurants)
        
        logger.info(f"Début de la géolocalisation de {total} restaurants...")
        
        for i, restaurant in enumerate(restaurants, 1):
            logger.info(f"Traitement {i}/{total}: {restaurant.get('nom', 'Sans nom')}")
            
            # Copie du restaurant pour éviter de modifier l'original
            geo_restaurant = restaurant.copy()
            
            address = restaurant.get('adresse')
            if not address:
                logger.warning(f"Restaurant {restaurant.get('nom', 'Sans nom')} sans adresse")
                geo_restaurant['longitude'] = None
                geo_restaurant['latitude'] = None
                geo_restaurant['geocoding_status'] = 'no_address'
            else:
                coordinates = self.geocode_address(address)
                if coordinates:
                    geo_restaurant['longitude'] = coordinates[0]
                    geo_restaurant['latitude'] = coordinates[1]
                    geo_restaurant['geocoding_status'] = 'success'
                else:
                    geo_restaurant['longitude'] = None
                    geo_restaurant['latitude'] = None
                    geo_restaurant['geocoding_status'] = 'failed'
            
            geolocated_restaurants.append(geo_restaurant)
            
            # Respect du délai entre les requêtes
            if i < total:  # Pas de délai après la dernière requête
                time.sleep(self.delay)
        
        logger.info(f"Géolocalisation terminée: {total} restaurants traités")
        return geolocated_restaurants

def load_restaurants(filepath: str) -> List[Dict]:
    """Charge les restaurants depuis un fichier JSON"""
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            restaurants = json.load(file)
            logger.info(f"Chargement réussi de {len(restaurants)} restaurants depuis {filepath}")
            return restaurants
    except FileNotFoundError:
        logger.error(f"Fichier non trouvé: {filepath}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de parsing JSON: {e}")
        raise

def save_restaurants(restaurants: List[Dict], output_filepath: str) -> None:
    """Sauvegarde les restaurants géolocalisés"""
    try:
        with open(output_filepath, 'w', encoding='utf-8') as file:
            json.dump(restaurants, file, ensure_ascii=False, indent=2)
        logger.info(f"Sauvegarde réussie de {len(restaurants)} restaurants dans {output_filepath}")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde: {e}")
        raise

def print_statistics(restaurants: List[Dict]) -> None:
    """Affiche les statistiques de géolocalisation"""
    total = len(restaurants)
    success = sum(1 for r in restaurants if r.get('geocoding_status') == 'success')
    failed = sum(1 for r in restaurants if r.get('geocoding_status') == 'failed')
    no_address = sum(1 for r in restaurants if r.get('geocoding_status') == 'no_address')
    
    logger.info("=== STATISTIQUES DE GÉOLOCALISATION ===")
    logger.info(f"Total des restaurants: {total}")
    logger.info(f"Géolocalisés avec succès: {success} ({success/total*100:.1f}%)")
    logger.info(f"Échecs de géolocalisation: {failed} ({failed/total*100:.1f}%)")
    logger.info(f"Sans adresse: {no_address} ({no_address/total*100:.1f}%)")

def main():
    """Fonction principale"""
    # Chemins des fichiers
    input_file = "output/restaurants.json"
    output_file = "output/restaurants_geolocalized.json"
    
    try:
        # Chargement des données
        restaurants = load_restaurants(input_file)
        
        # Initialisation du géocodeur
        geocoder = IGNGeocoder()
        
        # Géolocalisation
        geolocated_restaurants = geocoder.geocode_restaurants(restaurants)
        
        # Sauvegarde
        save_restaurants(geolocated_restaurants, output_file)
        
        # Statistiques
        print_statistics(geolocated_restaurants)
        
        logger.info("Script terminé avec succès!")
        
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        raise

if __name__ == "__main__":
    main()
