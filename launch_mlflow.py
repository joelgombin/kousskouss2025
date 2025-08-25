#!/usr/bin/env python3
"""
Script pour lancer l'interface MLflow UI
"""

import subprocess
import sys
import os
from pathlib import Path

def launch_mlflow_ui():
    """Lance l'interface MLflow UI"""
    
    # S'assurer que nous sommes dans le bon répertoire
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Vérifier que le dossier mlruns existe
    mlruns_path = project_root / "mlruns"
    if not mlruns_path.exists():
        print("⚠️  Le dossier 'mlruns' n'existe pas encore.")
        print("   Lancez d'abord le script principal pour créer des expériences.")
        print("   Création du dossier mlruns...")
        mlruns_path.mkdir(exist_ok=True)
    
    print("🚀 Lancement de l'interface MLflow UI...")
    print("📍 Tracking URI: file:./mlruns")
    print("🌐 L'interface sera disponible sur: http://localhost:5000")
    print("⏹️  Appuyez sur Ctrl+C pour arrêter l'interface")
    print("=" * 60)
    
    try:
        # Lancer MLflow UI
        cmd = [
            sys.executable, "-m", "mlflow", "ui",
            "--backend-store-uri", "file:./mlruns",
            "--host", "0.0.0.0",
            "--port", "5000"
        ]
        
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n⏹️  Interface MLflow arrêtée.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors du lancement de MLflow UI: {e}")
        print("💡 Assurez-vous que MLflow est installé: pip install mlflow")
    except FileNotFoundError:
        print("❌ MLflow n'est pas installé ou non trouvé dans le PATH")
        print("💡 Installez MLflow: pip install mlflow")

if __name__ == "__main__":
    launch_mlflow_ui()
