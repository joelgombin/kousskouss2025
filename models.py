from pydantic import BaseModel, Field, validator
from typing import List, Optional
from enum import Enum
import re

class Date(BaseModel):
    """Une date de service. Le jour et le mois sont des entiers. Le festival dure du 22 août au 7 septembre 2025."""
    jour: int
    mois: int

class Service(Enum):
    MIDI = "midi"
    SOIR = "soir"

class Plat(BaseModel):
    nom: str = Field(description="Le nom du plat")
    prix: str = Field(description="Le prix du plat, garder le format original avec €, ça peut être aussi quelque chose comme '15-20 €' ou 'à partir de 15 €'")
    description: Optional[str] = Field(default="", description="La description du plat")
    vegetarien: Optional[bool] = Field(default=False, description="True si le plat est végétarien, False sinon. Si rien n'est indiqué, déduire de la description.")
    vegan: Optional[bool] = Field(default=False, description="True si le plat est vegan, False sinon. Si rien n'est indiqué, déduire de la description.")
    dates: Optional[List[Date]] = Field(default_factory=list, description="La liste des dates où le plat est disponible. Le festival dure du 22 août au 7 septembre 2025. S'il est indiqué 'Tous les jours', 'toute l'année' ou 'toute la durée du festival', cela signifie que le plat est disponible tous les jours du festival.")
    services: Optional[List[Service]] = Field(default_factory=list, description="La liste des services où le plat est disponible. Si rien n'est indiqué, cela signifie que le plat est disponible à tous les services, indique donc 'midi' et 'soir'.")
    
    @validator('nom', pre=True)
    def validate_nom(cls, v):
        if not v or not str(v).strip():
            return "Plat sans nom"
        return str(v).strip()
    
    @validator('prix', pre=True)
    def validate_prix(cls, v):
        if not v or not str(v).strip():
            return "Prix non spécifié"
        return str(v).strip()
    
    @validator('description', pre=True)
    def validate_description(cls, v):
        if not v:
            return ""
        return str(v).strip()

class Restaurant(BaseModel):
    nom: str = Field(description="Le nom du restaurant, il est écrit en blanc sur fond sombre")
    adresse: str = Field(description="L'adresse du restaurant")
    telephone: Optional[str] = Field(default=None, description="Le numéro de téléphone du restaurant")
    chef: Optional[str] = Field(default=None, description="Le nom du chef, de la cheffe ou des chefs du restaurant")
    plats: List[Plat] = Field(default_factory=list, description="La liste des plats proposés par ce restaurant. Attention il peut y avoir plusieurs plats par restaurant et ce n'est pas toujours très explicite. Par exemple 'Soupe de pois chiches au cumin, ail et harissa maison et ses garnitures au choix : oeufs thon, hargma. Couscous à l’agneau et ses légumes.' renvoie à deux plats, une soupe de pois chiches, et un couscous.")
    
    @validator('nom', pre=True)
    def validate_nom(cls, v):
        if not v or not str(v).strip():
            return "Restaurant sans nom"
        return str(v).strip()
    
    @validator('adresse', pre=True)
    def validate_adresse(cls, v):
        if not v or not str(v).strip():
            return "Adresse non spécifiée"
        return str(v).strip()
    
    @validator('telephone', pre=True)
    def validate_telephone(cls, v):
        if not v:
            return None
        
        # Nettoyer le numéro de téléphone
        phone_str = str(v).strip()
        if not phone_str:
            return None
            
        # Supprimer tous les caractères non numériques et espaces/tirets
        cleaned = re.sub(r'[^\d\+\-\s\(\)]', '', phone_str)
        
        # Si le numéro semble trop court ou trop long, retourner None plutôt qu'une erreur
        digits_only = re.sub(r'[^\d]', '', cleaned)
        if len(digits_only) < 6 or len(digits_only) > 15:
            return None
            
        return cleaned.strip() if cleaned.strip() else None
    
    @validator('chef', pre=True)
    def validate_chef(cls, v):
        if not v:
            return None
        return str(v).strip() if str(v).strip() else None
    
    @validator('plats', pre=True)
    def validate_plats(cls, v):
        if not v:
            return []
        
        # Si v n'est pas une liste, essayer de la convertir
        if not isinstance(v, list):
            return []
            
        # Filtrer les plats valides et créer une liste nettoyée
        valid_plats = []
        for plat_data in v:
            try:
                if isinstance(plat_data, dict):
                    # Essayer de créer un Plat, avec gestion d'erreur
                    if plat_data.get('nom'):  # Au minimum, un nom est requis
                        # Données avec valeurs par défaut sécurisées
                        safe_plat_data = {
                            'nom': plat_data.get('nom', 'Plat sans nom'),
                            'prix': plat_data.get('prix', 'Prix non spécifié'),
                            'description': plat_data.get('description', ''),
                            'vegetarien': plat_data.get('vegetarien', False),
                            'vegan': plat_data.get('vegan', False),
                            'dates': plat_data.get('dates', []),
                            'services': plat_data.get('services', [])
                        }
                        plat = Plat(**safe_plat_data)
                        valid_plats.append(plat)
                elif hasattr(plat_data, 'nom'):  # Déjà un objet Plat
                    valid_plats.append(plat_data)
            except Exception:
                # Ignorer silencieusement les plats invalides
                continue
                
        return valid_plats

