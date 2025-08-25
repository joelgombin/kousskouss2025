from models import Restaurant, Plat, Date, Service
import dspy
from dotenv import load_dotenv
import os
import subprocess
from PIL import Image
import numpy as np
from pathlib import Path
import json
from tqdm import tqdm
import hashlib
from datetime import datetime
from enum import Enum
import mlflow
import mlflow.pyfunc
import time
from prompt_logger import setup_dspy_prompt_logging, log_final_prompt_statistics
from dspy_mlflow_integration import setup_enhanced_dspy_logging, log_extraction_context, analyze_dspy_usage


# read .env file
load_dotenv()

# Configuration MLflow
mlflow.set_experiment("kouskous2025_extraction")
mlflow.set_tracking_uri("file:./mlruns")

model = os.getenv("MODEL", "google/gemini-2.5-flash")

lm = dspy.LM("openrouter/"+ model, api_key=os.getenv("OPENROUTER_API_KEY"), cache=True, max_tokens=64000)
dspy.configure(lm=lm, track_usage=True)

# Activer le logging des prompts DSPy
setup_dspy_prompt_logging()
setup_enhanced_dspy_logging()

def detect_content_boundaries(full_img: Image.Image) -> tuple[int, int]:
    """Détecte automatiquement les vraies limites du contenu dans l'image sips"""
    
    try:
        img_array = np.array(full_img)
        
        # Convertir en niveaux de gris
        if len(img_array.shape) == 3:
            gray_array = np.mean(img_array, axis=2)
        elif len(img_array.shape) == 4:  # RGBA
            gray_array = np.mean(img_array[:, :, :3], axis=2)
        else:
            gray_array = img_array
        
        height = gray_array.shape[0]
        
        # Calculer la moyenne de chaque ligne horizontale
        horizontal_means = np.mean(gray_array, axis=1)
        
        # Détecter le début du contenu (après les marges/en-têtes)
        # Chercher la première zone avec beaucoup de variation
        content_start = 0
        for i in range(20, height // 10):  # Ignorer les 20 premières lignes, chercher dans le premier 10%
            window = horizontal_means[max(0, i-10):i+10]
            variance = np.var(window)
            
            if variance > 50:  # Seuil de variation pour détecter du contenu
                content_start = max(0, i - 10)
                break
        
        # Détecter la fin du contenu (avant les marges de fin)
        content_end = height
        for i in range(height - 20, max(content_start + 100, height * 9 // 10), -1):
            window = horizontal_means[max(0, i-10):min(height, i+10)]
            variance = np.var(window)
            
            if variance > 50:
                content_end = min(height, i + 10)
                break
        
        content_height = content_end - content_start
        
        # Validation et ajustements
        if content_height < height * 0.5:  # Si moins de 50% de l'image, probablement une erreur
            print(f"     ⚠️  Détection automatique douteuse, utilisation de l'image complète")
            content_start = 0
            content_height = height
        
        return content_start, content_height
        
    except Exception as e:
        print(f"     ❌ Erreur détection contenu: {e}")
        # Fallback: utiliser toute l'image
        return 0, full_img.size[1]

def convert_single_pdf_with_sips(pdf_path: Path) -> Image.Image:
    """Convertit un PDF d'une seule page avec sips direct"""
    temp_files = []
    
    try:
        print(f"     🔧 Conversion sips PDF individuel: {pdf_path.name}")
        
        # Utiliser sips directement sur le PDF individuel
        sips_output = f"temp_single_{pdf_path.stem}.png"
        temp_files.append(sips_output)
        
        cmd_sips = [
            'sips',
            '-s', 'format', 'png',
            '-s', 'dpiWidth', '200',
            '-s', 'dpiHeight', '200',
            '-Z', '1600',
            str(pdf_path),
            '--out', sips_output
        ]
        
        result_sips = subprocess.run(cmd_sips, capture_output=True, text=True, timeout=30)
        
        if result_sips.returncode != 0 or not Path(sips_output).exists():
            print(f"         ❌ Échec sips: {result_sips.stderr}")
            return None
        
        # Charger l'image
        image = Image.open(sips_output)
        img_array = np.array(image)
        unique_pixels = len(np.unique(img_array))
        
        print(f"         📊 Sips: {image.size}, {unique_pixels} pixels uniques")
        
        if unique_pixels <= 100:
            print(f"         ❌ Image quasi-vide")
            return None
        
        print(f"         ✅ Image valide extraite")
        return image.copy()
        
    except Exception as e:
        print(f"     ❌ Erreur conversion sips: {e}")
        return None
    
    finally:
        # Nettoyer les fichiers temporaires
        for temp_file in temp_files:
            try:
                Path(temp_file).unlink()
            except:
                pass

def create_complete_pdf_image(pdf_path: Path) -> Image.Image:
    """Crée une image complète du PDF avec toutes les pages - VRAIE SOLUTION"""
    temp_files = []
    
    try:
        # Obtenir le nombre de pages
        info_cmd = ['pdfinfo', str(pdf_path)]
        result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=10)
        
        num_pages = 3  # défaut
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    num_pages = int(line.split()[-1])
                    break
        
        print(f"     🔧 Création image complète de {num_pages} page(s)...")
        
        # Extraire et convertir chaque page individuellement
        page_images = []
        
        for page_num in range(1, num_pages + 1):
            try:
                # Étape 1: Extraire la page avec Ghostscript
                page_pdf = f"temp_page_{pdf_path.stem}_{page_num}.pdf"
                temp_files.append(page_pdf)
                
                cmd_gs = [
                    'gs',
                    '-dNOPAUSE',
                    '-dBATCH',
                    '-dSAFER',
                    '-sDEVICE=pdfwrite',
                    f'-dFirstPage={page_num}',
                    f'-dLastPage={page_num}',
                    f'-sOutputFile={page_pdf}',
                    str(pdf_path)
                ]
                
                result_gs = subprocess.run(cmd_gs, capture_output=True, text=True, timeout=30)
                
                if result_gs.returncode != 0 or not Path(page_pdf).exists():
                    print(f"         ❌ Échec extraction page {page_num}")
                    continue
                
                # Étape 2: Convertir avec sips (qui fonctionne sur page unique)
                page_png = f"temp_page_{pdf_path.stem}_{page_num}.png"
                temp_files.append(page_png)
                
                cmd_sips = [
                    'sips',
                    '-s', 'format', 'png',
                    '-s', 'dpiWidth', '200',
                    '-s', 'dpiHeight', '200',
                    '-Z', '1600',
                    page_pdf,
                    '--out', page_png
                ]
                
                result_sips = subprocess.run(cmd_sips, capture_output=True, text=True, timeout=30)
                
                if result_sips.returncode == 0 and Path(page_png).exists():
                    page_img = Image.open(page_png)
                    
                    # Vérifier que l'image a du contenu
                    page_array = np.array(page_img)
                    unique_pixels = len(np.unique(page_array))
                    
                    if unique_pixels > 100:
                        page_images.append(page_img.copy())
                        print(f"         ✅ Page {page_num}: {page_img.size}, {unique_pixels} pixels")
                    else:
                        print(f"         ⚠️  Page {page_num}: image vide ({unique_pixels} pixels)")
                else:
                    print(f"         ❌ Échec conversion sips page {page_num}")
                
            except Exception as e:
                print(f"         ❌ Erreur page {page_num}: {e}")
        
        if not page_images:
            print(f"     ❌ Aucune page convertie avec succès")
            return None
        
        # Étape 3: Concaténer toutes les pages verticalement
        print(f"     🔗 Concaténation de {len(page_images)} page(s)...")
        
        # Calculer les dimensions totales
        max_width = max(img.size[0] for img in page_images)
        total_height = sum(img.size[1] for img in page_images)
        
        # Créer l'image complète
        complete_image = Image.new('RGB', (max_width, total_height), (255, 255, 255))
        
        # Coller chaque page
        y_offset = 0
        for i, page_img in enumerate(page_images):
            # Convertir RGBA en RGB si nécessaire
            if page_img.mode == 'RGBA':
                rgb_img = Image.new('RGB', page_img.size, (255, 255, 255))
                rgb_img.paste(page_img, mask=page_img.split()[-1])
                page_img = rgb_img
            
            complete_image.paste(page_img, (0, y_offset))
            y_offset += page_img.size[1]
        
        print(f"     ✅ Image complète créée: {complete_image.size}")
        
        # Vérifier le contenu final
        complete_array = np.array(complete_image)
        complete_unique = len(np.unique(complete_array))
        print(f"     📊 Contenu final: {complete_unique} pixels uniques")
        
        if complete_unique > 200:
            return complete_image
        else:
            print(f"     ❌ Image complète semble vide")
            return None
        
    except Exception as e:
        print(f"     ❌ Erreur création image complète: {e}")
        return None
    
    finally:
        # Nettoyer les fichiers temporaires
        for temp_file in temp_files:
            try:
                Path(temp_file).unlink()
            except:
                pass

def convert_pdf_with_sips_multipage(pdf_path: Path) -> list[Image.Image]:
    """Convertit un PDF en images: sips pour le PDF complet puis division en pages - PRÉSERVE LES PROPORTIONS"""
    images = []
    temp_files = []
    
    try:
        # Obtenir les informations détaillées du PDF
        info_cmd = ['pdfinfo', str(pdf_path)]
        result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=10)
        
        num_pages = 3  # Valeur par défaut
        pdf_width_pts = 566.929  # Valeur par défaut
        pdf_height_pts = 396.85  # Valeur par défaut
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    num_pages = int(line.split()[-1])
                elif line.startswith('Page size:'):
                    # Extraire "566.929 x 396.85 pts"
                    parts = line.split()
                    if len(parts) >= 5:
                        pdf_width_pts = float(parts[2])
                        pdf_height_pts = float(parts[4])
        
        # Calculer les dimensions pour préserver les proportions
        # 1 point = 1/72 inch, donc à 200 DPI: 1 point = 200/72 ≈ 2.78 pixels
        pixels_per_point = 200 / 72
        pdf_width_px = int(pdf_width_pts * pixels_per_point)
        pdf_height_px = int(pdf_height_pts * pixels_per_point)
        
        # Taille totale pour toutes les pages (empilées verticalement)
        total_height_px = pdf_height_px * num_pages
        
        print(f"     📐 PDF: {pdf_width_pts:.1f}x{pdf_height_pts:.1f}pts → {pdf_width_px}x{pdf_height_px}px par page")
        print(f"     📊 Conversion sips multi-pages ({num_pages} page(s), total: {pdf_width_px}x{total_height_px}px)...")
        
        # Étape 1: Convertir avec sips en préservant les proportions exactes
        sips_output = f"temp_sips_full_{pdf_path.stem}.png"
        temp_files.append(sips_output)
        
        cmd = [
            'sips',
            '-s', 'format', 'png',
            '-s', 'dpiWidth', '200',
            '-s', 'dpiHeight', '200',
            '-s', 'pixelWidth', str(pdf_width_px),
            '-s', 'pixelHeight', str(total_height_px),
            str(pdf_path),
            '--out', sips_output
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"     ❌ Erreur sips: {result.stderr}")
            # Fallback: essayer sans forcer les dimensions exactes
            print(f"     🔄 Tentative fallback sans dimensions forcées...")
            
            cmd_fallback = [
                'sips',
                '-s', 'format', 'png',
                '-s', 'dpiWidth', '200',
                '-s', 'dpiHeight', '200',
                '-Z', str(max(pdf_width_px, 1500)),  # Largeur max adaptative
                str(pdf_path),
                '--out', sips_output
            ]
            
            result = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"     ❌ Échec complet sips: {result.stderr}")
                return []
        
        if not Path(sips_output).exists():
            print(f"     ❌ Fichier sips non créé")
            return []
        
        # Étape 2: Charger l'image complète et vérifier les dimensions
        full_img = Image.open(sips_output)
        full_array = np.array(full_img)
        full_unique_pixels = len(np.unique(full_array))
        
        actual_width, actual_height = full_img.size
        expected_page_height = actual_height // num_pages
        
        print(f"     📊 Image générée: {actual_width}x{actual_height}, {full_unique_pixels} pixels uniques")
        print(f"     📏 Hauteur par page: {expected_page_height}px")
        
        if full_unique_pixels <= 50:
            print(f"     ⚠️  Image complète semble vide")
            return []
        
        # Étape 3: Division manuelle optimisée basée sur analyse des PDFs
        # Les PDFs ont environ 5.4% de marge en haut d'après l'analyse
        margin_ratio = 0.054
        content_start = int(actual_height * margin_ratio)
        content_height = actual_height - content_start
        
        print(f"     🔍 Division manuelle: marge={content_start}px, contenu={content_height}px")
        
        # Diviser le contenu réel en pages avec buffer
        page_height = content_height // num_pages
        
        for page_num in range(num_pages):
            try:
                # Calculer les coordonnées dans la zone de contenu
                relative_top = page_num * page_height
                relative_bottom = min((page_num + 1) * page_height, content_height)
                
                # S'assurer que la dernière page prend tout l'espace restant
                if page_num == num_pages - 1:
                    relative_bottom = content_height
                
                # Convertir en coordonnées absolues avec buffer
                absolute_top = content_start + relative_top
                absolute_bottom = content_start + relative_bottom
                
                # Ajouter un buffer pour éviter la troncature
                margin_buffer = 10  # pixels de marge supplémentaire
                crop_top = max(0, absolute_top - margin_buffer)
                crop_bottom = min(actual_height, absolute_bottom + margin_buffer)
                
                # Extraire la page
                page_img = full_img.crop((0, crop_top, actual_width, crop_bottom))
                
                # Vérifier le contenu de la page
                page_array = np.array(page_img)
                page_unique_pixels = len(np.unique(page_array))
                
                page_width, page_height_actual = page_img.size
                print(f"     📄 Page {page_num + 1}: {page_width}x{page_height_actual}, {page_unique_pixels} pixels uniques")
                print(f"          Zone: {absolute_top}-{absolute_bottom} (contenu réel)")
                
                if page_unique_pixels > 20:
                    images.append(page_img.copy())
                    print(f"     ✅ Page {page_num + 1} ajoutée (hauteur réelle: {page_height_actual}px)")
                else:
                    print(f"     ⚠️  Page {page_num + 1} semble vide, ignorée")
                
            except Exception as e:
                print(f"     ❌ Erreur extraction page {page_num + 1}: {e}")
        
    except Exception as e:
        print(f"     ❌ Erreur conversion sips: {e}")
    
    finally:
        # Nettoyer les fichiers temporaires
        for temp_file in temp_files:
            try:
                Path(temp_file).unlink()
            except:
                pass
    
    return images

# Note: DSPy.Image.from_file() gère automatiquement la conversion des images

class ExtractPlats(dspy.Signature):
    """Extraie les plats et restaurants du programme du festival Kouss Kouss 2025"""

    context: str = dspy.InputField(desc="Le contexte de l'extraction")
    page_image: dspy.Image = dspy.InputField(desc="Une page du programme festival")

    restaurants: list[Restaurant] = dspy.OutputField(desc="La liste des restaurants participants au festival")

def get_context_for_extraction():
    """Génère le contexte d'extraction simplifié sans quartiers"""
    
    return """
Le festival Kouss Kouss 2025 est un festival culinaire marseillais consacré au couscous. 
Cette image est une page du programme officiel du festival.

IMPORTANT: 
- Extrais TOUS les restaurants et leurs plats visibles sur cette page
- Les noms des restaurants sont généralement en BLANC sur FOND SOMBRE  
- Les adresses sont généralement indiquées sous les noms des restaurants
- Les plats avec leurs prix et descriptions suivent
- Lis attentivement le texte visible, ne pas inventer
- Si un élément n'est pas clairement visible, ne l'inclus pas

L'image contient :
- Les noms des restaurants (en blanc sur fond sombre)
- Les adresses des restaurants  
- Les plats proposés avec leurs prix
- Les descriptions des plats
- Les dates de disponibilité (22 août au 7 septembre 2025)

Parfois des éléments ne sont pas des plats ou des restaurants, par exemple les sections "KOUSS•ESSENTIELS CUISINE" 
concernent des ustensiles et doivent être ignorées.

Analyse cette page pour extraire tous les restaurants et leurs plats visibles.
"""

extract = dspy.Predict(ExtractPlats)

def format_restaurants(restaurants_result):
    """Formate joliment la liste des restaurants"""
    if hasattr(restaurants_result, 'restaurants'):
        restaurants_list = restaurants_result.restaurants
    else:
        restaurants_list = restaurants_result
        
    print("🍽️  RESTAURANTS DU FESTIVAL KOUSS•KOUSS 2025 🍽️")
    print("=" * 60)
    
    for i, restaurant in enumerate(restaurants_list, 1):
        print(f"\n📍 {i}. {restaurant.nom}")
        print(f"   📍 Adresse: {restaurant.adresse}")
        
        if restaurant.chef:
            print(f"   👨‍🍳 Chef: {restaurant.chef}")
        
        if restaurant.telephone:
            print(f"   📞 Téléphone: {restaurant.telephone}")
        
        print(f"   🍽️  Plats ({len(restaurant.plats)}):")
        
        for j, plat in enumerate(restaurant.plats, 1):
            vegetarien_icon = "🌱" if plat.vegetarien else ""
            vegan_icon = "🌿" if plat.vegan else ""
            
            print(f"      {j}. {plat.nom} {vegetarien_icon}{vegan_icon}")
            print(f"         💰 {plat.prix}")
            print(f"         📝 {plat.description}")
            
            if plat.dates:
                dates_str = ", ".join([f"{date.jour}/{date.mois}" for date in plat.dates])
                print(f"         📅 Dates: {dates_str}")
            
            if plat.services:
                services_str = ", ".join([service.value for service in plat.services])
                print(f"         ⏰ Services: {services_str}")
            
            if j < len(restaurant.plats):
                print()
        
        print("-" * 50)
    

def get_file_hash(file_path: Path) -> str:
    """Calcule le hash MD5 d'un fichier PDF"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def load_progress() -> dict:
    """Charge l'état d'avancement depuis le fichier de sauvegarde"""
    progress_file = Path("output/extraction_progress.json")
    if progress_file.exists():
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            print("⚠️  Fichier de progression corrompu, recommencement depuis le début")
    return {"processed_files": {}, "restaurants": [], "last_update": None}

class EnumEncoder(json.JSONEncoder):
    """Encodeur JSON personnalisé pour gérer les Enum"""
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

def save_progress(progress: dict):
    """Sauvegarde l'état d'avancement"""
    progress["last_update"] = datetime.now().isoformat()
    progress_file = Path("output/extraction_progress.json")
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False, cls=EnumEncoder)

def extract_from_single_pdf(pdf_path: Path, progress: dict) -> list[Restaurant]:
    """Extract restaurants from a single-page PDF file"""
    file_hash = get_file_hash(pdf_path)
    
    # Vérifier si ce fichier a déjà été traité avec la même version
    if pdf_path.name in progress["processed_files"]:
        stored_hash = progress["processed_files"][pdf_path.name].get("hash")
        if stored_hash == file_hash:
            print(f"⏭️  Fichier déjà traité: {pdf_path.name} (ignoré)")
            # Logger dans MLflow que le fichier a été ignoré
            mlflow.log_metric(f"skipped_file_{pdf_path.stem}", 1)
            return progress["processed_files"][pdf_path.name].get("restaurants", [])
    
    print(f"📄 Traitement PDF individuel: {pdf_path.name}")
    
    # Commencer le tracking du temps de traitement
    start_time = time.time()
    
    try:
        # NOUVELLE APPROCHE: Convertir le PDF individuel avec sips
        image = convert_single_pdf_with_sips(pdf_path)
        conversion_time = time.time() - start_time
        
        # Logger les métriques de conversion PDF
        mlflow.log_metric(f"pdf_conversion_time_{pdf_path.stem}", conversion_time)
        
        # Vérifier si le PDF a été converti
        if image is None:
            print(f"   ⚠️  PDF non converti ou vide")
            mlflow.log_metric(f"empty_pdf_{pdf_path.stem}", 1)
            return []
        
        print(f"   📊 Image extraite: {image.size}")
        
        # Traitement de l'image unique
        temp_path = f"temp_single_{pdf_path.stem}.jpg"
        
        try:
            # Convertir RGBA en RGB si nécessaire pour JPEG
            if image.mode == 'RGBA':
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[-1])
                image = rgb_image
            
            image.save(temp_path, "JPEG", quality=95)
            
            # Créer l'objet dspy.Image
            dspy_image = dspy.Image.from_file(temp_path)
            
            # Générer le contexte simplifié
            context = get_context_for_extraction()
            
            # Extraction sur cette page avec gestion d'erreur gracieuse
            extraction_start = time.time()
            result = extract(context=context, page_image=dspy_image)
            extraction_time = time.time() - extraction_start
            
            # Récupérer les restaurants avec validation tolérante
            raw_restaurants = result.restaurants if hasattr(result, 'restaurants') else (result if isinstance(result, list) else [])
            
            # Appliquer une validation tolérante aux erreurs
            restaurants = []
            for restaurant_data in raw_restaurants:
                try:
                    # Si c'est déjà un objet Restaurant validé
                    if hasattr(restaurant_data, 'nom'):
                        restaurants.append(restaurant_data)
                    # Si c'est un dictionnaire, essayer de créer un Restaurant
                    elif isinstance(restaurant_data, dict):
                        # Créer le restaurant avec validation tolérante
                        restaurant = Restaurant(**restaurant_data)
                        restaurants.append(restaurant)
                except Exception as validation_error:
                    # En cas d'erreur de validation, essayer de sauver ce qu'on peut
                    print(f"           ⚠️  Erreur validation restaurant: {validation_error}")
                    try:
                        # Créer un restaurant minimal avec les données disponibles
                        safe_data = {
                            'nom': restaurant_data.get('nom', 'Restaurant sans nom'),
                            'adresse': restaurant_data.get('adresse', 'Adresse non spécifiée'),
                            'telephone': None,  # En cas de problème, on met None
                            'plats': []  # En cas de problème avec les plats, liste vide
                        }
                        
                        # Essayer d'ajouter les plats valides un par un
                        if 'plats' in restaurant_data and isinstance(restaurant_data['plats'], list):
                            valid_plats = []
                            for plat_data in restaurant_data['plats']:
                                try:
                                    if isinstance(plat_data, dict) and plat_data.get('nom'):
                                        plat = Plat(
                                            nom=plat_data.get('nom', 'Plat sans nom'),
                                            prix=plat_data.get('prix', 'Prix non spécifié'),
                                            description=plat_data.get('description')
                                        )
                                        valid_plats.append(plat)
                                except:
                                    continue  # Ignorer les plats problématiques
                            safe_data['plats'] = valid_plats
                        
                        restaurant = Restaurant(**safe_data)
                        restaurants.append(restaurant)
                        print(f"           ✅ Restaurant sauvé avec données partielles: {safe_data['nom']}")
                        
                    except Exception as final_error:
                        print(f"           ❌ Impossible de sauver le restaurant: {final_error}")
                        continue
            
            if restaurants:
                print(f"   ✅ {len(restaurants)} restaurant(s) trouvé(s) (temps: {extraction_time:.1f}s)")
            else:
                print(f"   ⚠️  Aucun restaurant trouvé")
            
            # Logger les métriques
            mlflow.log_metric(f"restaurants_{pdf_path.stem}", len(restaurants))
            mlflow.log_metric(f"extraction_time_{pdf_path.stem}", extraction_time)
            
        finally:
            # Nettoyer le fichier temporaire
            try:
                Path(temp_path).unlink()
            except:
                pass
        
        # Vérifier si l'extraction a retourné des résultats
        if restaurants is None:
            print(f"   ⚠️  Aucun restaurant trouvé dans ce PDF")
            restaurants = []
        
        # Logger les métriques d'extraction
        total_time = time.time() - start_time
        restaurant_count = len(restaurants)
        
        mlflow.log_metric(f"total_processing_time_{pdf_path.stem}", total_time)
        
        # Calculer le nombre total de plats
        total_plats = sum(len(restaurant.plats) if hasattr(restaurant, 'plats') else 0 for restaurant in restaurants)
        mlflow.log_metric(f"plats_extracted_{pdf_path.stem}", total_plats)
        
        print(f"   ✅ {restaurant_count} restaurant(s) extrait(s) en {total_time:.2f}s")
        
        # Sauvegarder le progrès pour ce fichier
        # Convertir les objets Restaurant en dictionnaires avec gestion des Enum
        restaurants_data = []
        for restaurant in restaurants:
            if hasattr(restaurant, 'dict'):
                restaurant_dict = restaurant.dict()
            else:
                restaurant_dict = restaurant.__dict__.copy()
                
            restaurants_data.append(restaurant_dict)
        
        file_data = {
            "hash": file_hash,
            "restaurants": restaurants_data,
            "processed_at": datetime.now().isoformat(),
            "restaurant_count": len(restaurants),
            "processing_time": total_time,
            "pages_count": 1  # PDF individuel = 1 page
        }
        progress["processed_files"][pdf_path.name] = file_data
        save_progress(progress)
        print(f"   💾 Progrès sauvegardé pour {pdf_path.name}")
        
        return restaurants
        
    except Exception as e:
        error_time = time.time() - start_time
        print(f"   ❌ Erreur lors du traitement de {pdf_path.name}: {e}")
        
        # Logger l'erreur dans MLflow
        mlflow.log_metric(f"error_{pdf_path.stem}", 1)
        mlflow.log_metric(f"error_time_{pdf_path.stem}", error_time)
        mlflow.log_param(f"error_message_{pdf_path.stem}", str(e))
        
        # Sauvegarder l'erreur dans le progrès
        progress["processed_files"][pdf_path.name] = {
            "hash": file_hash,
            "error": str(e),
            "processed_at": datetime.now().isoformat(),
            "restaurants": [],
            "processing_time": error_time
        }
        save_progress(progress)
        return []

def main():
    # Commencer un run MLflow pour l'ensemble du processus
    with mlflow.start_run(run_name=f"kouskous_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}") as run:
        run_start_time = time.time()
        
        # Logger les paramètres de configuration
        mlflow.log_param("model", model)
        mlflow.log_param("max_tokens", 32000)
        mlflow.log_param("cache_enabled", True)
        mlflow.log_param("run_timestamp", datetime.now().isoformat())
        
        # Création du dossier output s'il n'existe pas
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # Charger l'état d'avancement
        progress = load_progress()
        
        # Collecte tous les PDFs individuels à traiter  
        pdf_files = list(Path("programme_bursted").glob("*.pdf"))
        
        if not pdf_files:
            print("❌ Aucun fichier PDF trouvé dans le dossier 'programme_bursted'")
            mlflow.log_metric("total_pdf_files", 0)
            mlflow.log_metric("status", 0)  # 0 = échec
            return
        
        # Logger les métriques générales
        mlflow.log_metric("total_pdf_files", len(pdf_files))
        
        # Analyser le progrès existant
        already_processed = len([f for f in progress["processed_files"].keys() if f in [p.name for p in pdf_files]])
        remaining_files = [f for f in pdf_files if f.name not in progress["processed_files"] or "error" in progress["processed_files"][f.name]]
        
        mlflow.log_metric("already_processed_files", already_processed)
        mlflow.log_metric("remaining_files", len(remaining_files))
        
        print(f"🍽️  Extraction des restaurants du festival Kouss•Kouss 2025")
        print(f"📁 {len(pdf_files)} fichier(s) PDF au total")
        print(f"✅ {already_processed} fichier(s) déjà traité(s)")
        print(f"🔄 {len(remaining_files)} fichier(s) à traiter")
        
        if progress["last_update"]:
            print(f"📅 Dernière mise à jour: {progress['last_update']}")
            mlflow.log_param("last_update", progress["last_update"])
        
        print("=" * 60)
        
        all_restaurants = []
        
        # Récupérer les restaurants déjà extraits
        for file_name, file_data in progress["processed_files"].items():
            if "restaurants" in file_data and "error" not in file_data:
                # Reconstituer les objets Restaurant depuis les données JSON
                for restaurant_data in file_data["restaurants"]:
                    all_restaurants.append(restaurant_data)  # Garde les données en dict pour la compatibilité
        
        print(f"📋 {len(all_restaurants)} restaurant(s) déjà en mémoire")
        mlflow.log_metric("restaurants_from_cache", len(all_restaurants))
        
        # Traiter les fichiers restants
        new_restaurants_count = 0
        processing_start_time = time.time()
        
        if remaining_files:
            print(f"\n🔄 Traitement des PDFs individuels...")
            for pdf_path in tqdm(remaining_files, desc="PDFs individuels", unit="fichier"):
                restaurants_list = extract_from_single_pdf(pdf_path, progress)
                
                # Convertir en dictionnaires pour la cohérence
                restaurants_dicts = [restaurant.dict() if hasattr(restaurant, 'dict') else restaurant.__dict__ for restaurant in restaurants_list]
                all_restaurants.extend(restaurants_dicts)
                new_restaurants_count += len(restaurants_dicts)
        else:
            print("\n✅ Tous les fichiers ont déjà été traités!")
        
        processing_time = time.time() - processing_start_time
        mlflow.log_metric("new_restaurants_extracted", new_restaurants_count)
        mlflow.log_metric("new_files_processing_time", processing_time)
        
        print(f"\n✅ Extraction terminée! {len(all_restaurants)} restaurants au total")
        
        # Calculer des statistiques globales
        total_plats = 0
        vegetarian_plats = 0
        vegan_plats = 0
        
        for restaurant in all_restaurants:
            if 'plats' in restaurant:
                total_plats += len(restaurant['plats'])
                for plat in restaurant['plats']:
                    if plat.get('vegetarien', False):
                        vegetarian_plats += 1
                    if plat.get('vegan', False):
                        vegan_plats += 1
           
        
        # Logger les métriques finales
        mlflow.log_metric("total_restaurants", len(all_restaurants))
        mlflow.log_metric("total_plats", total_plats)
        mlflow.log_metric("vegetarian_plats", vegetarian_plats)
        mlflow.log_metric("vegan_plats", vegan_plats)
        
        
        # Sauvegarde finale consolidée
        print("💾 Sauvegarde finale des données...")
        output_file = "output/restaurants.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_restaurants, f, indent=2, ensure_ascii=False, cls=EnumEncoder)
        
        print("✅ Données sauvegardées dans 'output/restaurants.json'")
        
        # Logger le fichier de sortie comme artefact
        mlflow.log_artifact(output_file, "results")
        mlflow.log_artifact("output/extraction_progress.json", "progress")
        
        # Afficher un résumé du traitement
        print(f"\n📊 Résumé du traitement:")
        success_count = len([f for f in progress["processed_files"].values() if "error" not in f])
        error_count = len([f for f in progress["processed_files"].values() if "error" in f])
        print(f"   ✅ {success_count} fichier(s) traité(s) avec succès")
        if error_count > 0:
            print(f"   ❌ {error_count} fichier(s) en erreur")
            print("   🔍 Vérifiez le fichier 'output/extraction_progress.json' pour plus de détails")
        
        # Logger les métriques de succès/erreur
        mlflow.log_metric("successful_files", success_count)
        mlflow.log_metric("failed_files", error_count)
        mlflow.log_metric("success_rate", success_count / len(pdf_files) if pdf_files else 0)
        
        # Temps total de traitement
        total_run_time = time.time() - run_start_time
        mlflow.log_metric("total_run_time", total_run_time)
        mlflow.log_metric("status", 1 if error_count == 0 else 0.5)  # 1 = succès complet, 0.5 = succès partiel
        
        # Logger les statistiques des prompts et DSPy
        log_final_prompt_statistics()
        analyze_dspy_usage()
        
        print(f"\n🔬 Run MLflow ID: {run.info.run_id}")
        print(f"⏱️  Temps total d'exécution: {total_run_time:.2f}s")




if __name__ == "__main__":
    main()
