from pydantic import BaseModel, Field
from typing import List
from enum import Enum

class Quartier(Enum):
    NOAILLES_BELSUNCE = "NOAILLES BELSUNCE"
    OPERA = "OPERA, HAXO, SAINTE, ESTIENNE D'ORVES"
    PREFECTURE = "PALAIS DE JUSTICE, PRÉFECTURE, GRIGNAN, ROSTAND, BRETEUIL, CASTELLANE, VAUBAN"
    VIEUX_PORT = "VIEUX PORT, PANIER, REPUBLIQUE, JOLIETTE"
    SAINT_VICTOR = "SAINT-VICTOR, CATALANS, CORNICHE, CHATEAU D'IF, PRADO"
    CANEBIERE = "CANEBIÈRE, RÉFORMÉS-CONSOLAT, LIBÉRATION, LONGCHAMP, SAINT-CHARLES"
    COURS_JULIEN = "COURS JULIEN, NOTRE-DAME-DU-MONT, CAMAS, SAINT-PIERRE, CHAVE"
    BELLE_DE_MAI = "BELLE DE MAI, CHUTES-LAVIE"
    SAINTE_MARTHE = "PLAN D'AOU, SAINTE-MARTHE, LA CABUCELLE, LA ROSE"
    ESTAQUE = "L'ESTAQUE, NIOLON, LE ROVE"

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
    description: str = Field(description="La description du plat")
    vegetarien: bool = Field(description="True si le plat est végétarien, False sinon. Si rien n'est indiqué, déduire de la description.")
    vegan: bool = Field(description="True si le plat est vegan, False sinon. Si rien n'est indiqué, déduire de la description.")
    dates: List[Date] = Field(description="La liste des dates où le plat est disponible. Le festival dure du 22 août au 7 septembre 2025. S'il est indiqué 'Tous les jours', 'toute l'année' ou 'toute la durée du festival', cela signifie que le plat est disponible tous les jours du festival.")
    services: List[Service] = Field(description="La liste des services où le plat est disponible. Si rien n'est indiqué, cela signifie que le plat est disponible à tous les services.")

class Restaurant(BaseModel):
    nom: str = Field(description="Le nom du restaurant, il est écrit en blanc sur fond sombre")
    adresse: str = Field(description="L'adresse du restaurant")
    telephone: str | None = Field(default=None, pattern=r'^(?:(?:\+|00)33|0)\s*[1-9](?:[\s.-]*\d{2}){4}$', description="Le numéro de téléphone du restaurant")
    chef: str | None = Field(default=None, description="Le nom du chef, de la cheffe ou des chefs du restaurant")
    quartier: Quartier = Field(description="Le quartier du restaurant")
    plats: List[Plat] = Field(description="La liste des plats proposés par ce restaurant")

