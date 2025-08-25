#!/usr/bin/env python3
"""
Script pour analyser et afficher les résultats des expériences MLflow
"""

import mlflow
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json

def setup_mlflow():
    """Configure MLflow pour l'analyse"""
    mlflow.set_tracking_uri("file:./mlruns")
    mlflow.set_experiment("kouskous2025_extraction")

def get_experiment_data():
    """Récupère les données des expériences"""
    setup_mlflow()
    
    # Obtenir l'expérience
    experiment = mlflow.get_experiment_by_name("kouskous2025_extraction")
    if not experiment:
        print("❌ Aucune expérience 'kouskous2025_extraction' trouvée")
        return None
    
    # Rechercher tous les runs
    runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
    return runs

def analyze_performance(runs_df):
    """Analyse les performances des extractions"""
    if runs_df.empty:
        print("❌ Aucun run trouvé dans l'expérience")
        return
    
    print("📊 ANALYSE DES PERFORMANCES")
    print("=" * 50)
    
    # Métriques de base
    if 'metrics.total_restaurants' in runs_df.columns:
        total_restaurants = runs_df['metrics.total_restaurants'].dropna()
        if not total_restaurants.empty:
            print(f"🍽️  Restaurants extraits:")
            print(f"   • Moyenne: {total_restaurants.mean():.1f}")
            print(f"   • Maximum: {total_restaurants.max():.0f}")
            print(f"   • Minimum: {total_restaurants.min():.0f}")
    
    if 'metrics.total_plats' in runs_df.columns:
        total_plats = runs_df['metrics.total_plats'].dropna()
        if not total_plats.empty:
            print(f"\n🍜 Plats extraits:")
            print(f"   • Moyenne: {total_plats.mean():.1f}")
            print(f"   • Maximum: {total_plats.max():.0f}")
            print(f"   • Minimum: {total_plats.min():.0f}")
    
    if 'metrics.total_run_time' in runs_df.columns:
        run_times = runs_df['metrics.total_run_time'].dropna()
        if not run_times.empty:
            print(f"\n⏱️  Temps d'exécution:")
            print(f"   • Moyenne: {run_times.mean():.1f}s")
            print(f"   • Maximum: {run_times.max():.1f}s")
            print(f"   • Minimum: {run_times.min():.1f}s")
    
    if 'metrics.success_rate' in runs_df.columns:
        success_rates = runs_df['metrics.success_rate'].dropna()
        if not success_rates.empty:
            print(f"\n✅ Taux de succès:")
            print(f"   • Moyenne: {success_rates.mean():.1%}")
            print(f"   • Maximum: {success_rates.max():.1%}")
            print(f"   • Minimum: {success_rates.min():.1%}")

def show_latest_run_details():
    """Affiche les détails du dernier run"""
    setup_mlflow()
    
    # Obtenir le dernier run
    runs = mlflow.search_runs(
        experiment_ids=[mlflow.get_experiment_by_name("kouskous2025_extraction").experiment_id],
        order_by=["start_time DESC"],
        max_results=1
    )
    
    if runs.empty:
        print("❌ Aucun run trouvé")
        return
    
    latest_run = runs.iloc[0]
    
    print("🔍 DERNIER RUN DÉTAILLÉ")
    print("=" * 50)
    print(f"🆔 Run ID: {latest_run['run_id']}")
    print(f"📅 Date: {latest_run['start_time']}")
    print(f"⏱️  Durée: {latest_run.get('metrics.total_run_time', 'N/A')}s")
    print(f"🏷️  Modèle: {latest_run.get('params.model', 'N/A')}")
    
    # Métriques principales
    metrics_to_show = [
        ('total_restaurants', '🍽️  Restaurants extraits'),
        ('total_plats', '🍜 Plats extraits'),
        ('vegetarian_plats', '🌱 Plats végétariens'),
        ('vegan_plats', '🌿 Plats vegan'),
        ('successful_files', '✅ Fichiers traités avec succès'),
        ('failed_files', '❌ Fichiers en erreur'),
        ('success_rate', '📈 Taux de succès')
    ]
    
    print("\n📊 Métriques:")
    for metric_key, description in metrics_to_show:
        value = latest_run.get(f'metrics.{metric_key}', None)
        if value is not None:
            if metric_key == 'success_rate':
                print(f"   {description}: {value:.1%}")
            else:
                print(f"   {description}: {value:.0f}")

def show_quartiers_distribution():
    """Affiche la distribution des restaurants par quartier"""
    setup_mlflow()
    
    # Obtenir le dernier run
    runs = mlflow.search_runs(
        experiment_ids=[mlflow.get_experiment_by_name("kouskous2025_extraction").experiment_id],
        order_by=["start_time DESC"],
        max_results=1
    )
    
    if runs.empty:
        return
    
    latest_run = runs.iloc[0]
    
    print("\n🗺️  DISTRIBUTION PAR QUARTIER")
    print("=" * 50)
    
    # Chercher les métriques de quartier
    quartier_metrics = []
    for col in latest_run.index:
        if col.startswith('metrics.restaurants_in_'):
            quartier = col.replace('metrics.restaurants_in_', '').replace('_', ' ').title()
            count = latest_run[col]
            if pd.notna(count) and count > 0:
                quartier_metrics.append((quartier, int(count)))
    
    # Trier par nombre de restaurants
    quartier_metrics.sort(key=lambda x: x[1], reverse=True)
    
    for quartier, count in quartier_metrics:
        print(f"   📍 {quartier}: {count} restaurant(s)")

def create_performance_chart():
    """Crée un graphique des performances au fil du temps"""
    runs_df = get_experiment_data()
    if runs_df is None or runs_df.empty:
        return
    
    # Préparer les données pour le graphique
    if 'metrics.total_restaurants' in runs_df.columns and 'start_time' in runs_df.columns:
        plt.figure(figsize=(12, 6))
        
        # Convertir les timestamps
        runs_df['start_time'] = pd.to_datetime(runs_df['start_time'])
        runs_df = runs_df.sort_values('start_time')
        
        # Graphique 1: Évolution du nombre de restaurants
        plt.subplot(1, 2, 1)
        plt.plot(runs_df['start_time'], runs_df['metrics.total_restaurants'], 'bo-')
        plt.title('Évolution du nombre de restaurants extraits')
        plt.xlabel('Date')
        plt.ylabel('Nombre de restaurants')
        plt.xticks(rotation=45)
        
        # Graphique 2: Temps d'exécution
        if 'metrics.total_run_time' in runs_df.columns:
            plt.subplot(1, 2, 2)
            plt.plot(runs_df['start_time'], runs_df['metrics.total_run_time'], 'ro-')
            plt.title('Évolution du temps d\'exécution')
            plt.xlabel('Date')
            plt.ylabel('Temps (secondes)')
            plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # Sauvegarder le graphique
        chart_path = Path("output/mlflow_performance_chart.png")
        chart_path.parent.mkdir(exist_ok=True)
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        print(f"\n📈 Graphique sauvegardé: {chart_path}")
        
        # Afficher le graphique si possible
        try:
            plt.show()
        except:
            print("   (Affichage graphique non disponible en mode headless)")

def main():
    """Fonction principale du dashboard"""
    print("🔬 DASHBOARD MLFLOW - KOUSKOUS 2025")
    print("=" * 60)
    
    # Vérifier que MLflow est configuré
    if not Path("mlruns").exists():
        print("❌ Dossier 'mlruns' non trouvé.")
        print("   Lancez d'abord le script principal pour créer des expériences.")
        return
    
    try:
        # Analyser les données
        runs_df = get_experiment_data()
        
        if runs_df is not None and not runs_df.empty:
            print(f"📊 {len(runs_df)} run(s) trouvé(s) dans l'expérience")
            
            # Analyses
            analyze_performance(runs_df)
            show_latest_run_details()
            show_quartiers_distribution()
            
            # Créer les graphiques
            print("\n📈 Génération des graphiques...")
            create_performance_chart()
            
        else:
            print("❌ Aucune donnée d'expérience trouvée")
            print("   Lancez d'abord le script principal pour créer des expériences.")
    
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")
    
    print(f"\n💡 Pour voir l'interface MLflow web, lancez: python launch_mlflow.py")

if __name__ == "__main__":
    # Installer les dépendances si nécessaire
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError:
        print("⚠️  Dépendances graphiques non installées.")
        print("   Pour les graphiques, installez: pip install matplotlib seaborn")
    
    main()
