# Guide du Logging des Prompts DSPy avec MLflow

Ce guide explique comment utiliser le système de logging des prompts intégré dans votre projet Kouskous 2025.

## 🎯 Fonctionnalités du Logging des Prompts

### ✅ Ce qui est automatiquement loggé

1. **Prompts complets** envoyés au LLM
2. **Réponses complètes** reçues du LLM  
3. **Métriques de performance** : 
   - Longueur des prompts/réponses
   - Estimation des tokens utilisés
   - Temps de traitement
   - Nombre d'appels total

4. **Contexte d'extraction** :
   - Contenu complet du contexte
   - Nombre de pages traitées
   - Mots-clés détectés

5. **Historique complet** sauvegardé comme artefacts MLflow

## 📊 Métriques disponibles dans MLflow

### Métriques par appel LLM
- `llm_call_{N}_prompt_length` : Longueur du prompt N
- `llm_call_{N}_response_length` : Longueur de la réponse N  
- `llm_call_{N}_tokens` : Tokens estimés pour l'appel N

### Métriques cumulatives
- `total_llm_calls` : Nombre total d'appels
- `total_estimated_tokens` : Total des tokens estimés
- `final_avg_prompt_length` : Longueur moyenne des prompts
- `final_unique_prompts` : Nombre de prompts uniques

### Métriques du contexte
- `extraction_context_length` : Longueur du contexte
- `extraction_context_lines` : Nombre de lignes
- `context_keyword_{mot}` : Occurrences de mots-clés

## 📂 Artefacts sauvegardés

### Dans l'onglet "Artifacts" de MLflow :

1. **`prompts/`** : Dossier contenant tous les prompts
   - `prompts_log.json` : Historique complet des appels

2. **`dspy_calls/`** : Dossier des appels DSPy  
   - `dspy_calls.json` : Détails des signatures DSPy

## 🔍 Comment consulter les prompts

### 1. Interface MLflow Web
```bash
uv run python launch_mlflow.py
# Ouvrir http://localhost:5000
```

Dans l'interface :
1. Sélectionner l'expérience "kouskous2025_extraction"
2. Cliquer sur un run
3. Aller dans l'onglet "Artifacts" 
4. Télécharger `prompts/prompts_log.json`

### 2. Dashboard programmatique
```bash
uv run python mlflow_dashboard.py
```

### 3. Accès direct aux artefacts
```python
import mlflow
import json

# Récupérer le dernier run
runs = mlflow.search_runs(experiment_ids=[experiment_id], max_results=1)
run_id = runs.iloc[0]['run_id']

# Télécharger l'artefact des prompts
mlflow.artifacts.download_artifacts(
    run_id=run_id, 
    artifact_path="prompts/prompts_log.json",
    dst_path="./downloaded_prompts/"
)

# Lire les prompts
with open("./downloaded_prompts/prompts_log.json", "r") as f:
    prompts_data = json.load(f)
    
for prompt_entry in prompts_data:
    print(f"Prompt {prompt_entry['call_number']}:")
    print(prompt_entry['prompt'])
    print(f"Réponse: {prompt_entry['response']}")
    print("-" * 50)
```

## 📋 Structure des données de prompts

### Format JSON des prompts loggés :
```json
{
  "call_number": 1,
  "timestamp": "2025-08-24T23:31:43.123456",
  "prompt_hash": "abc12345",
  "prompt": "Texte complet du prompt envoyé...",
  "response": "Réponse complète reçue...",
  "model": "google/gemini-2.5-flash",
  "prompt_length": 1234,
  "response_length": 5678,
  "estimated_prompt_tokens": 300,
  "estimated_response_tokens": 1200,
  "total_estimated_tokens": 1500,
  "metadata": {
    "call_duration": 2.5,
    "model_name": "openrouter/google/gemini-2.5-flash",
    "args_count": 2,
    "kwargs_keys": ["temperature", "max_tokens"]
  }
}
```

## 🔧 Configuration avancée

### Personnaliser le logging
```python
# Dans votre script
from prompt_logger import prompt_logger

# Logger manuellement un appel
prompt_logger.log_llm_call(
    prompt="Mon prompt personnalisé",
    response="La réponse obtenue", 
    model="mon-modele",
    metadata={"custom": "data"}
)

# Obtenir les statistiques
stats = prompt_logger.get_statistics()
print(f"Appels total: {stats['total_calls']}")
```

### Désactiver le logging
```python
# Pour désactiver temporairement
# Commentez cette ligne dans main.py :
# setup_dspy_prompt_logging()
```

## 📈 Analyser les coûts

### Estimation des coûts par modèle :
```python
def estimate_cost(tokens, model_name):
    # Prix approximatifs (à ajuster selon votre fournisseur)
    prices = {
        "google/gemini-2.5-flash": 0.0001,  # par 1000 tokens
        "anthropic/claude-3": 0.0015,
        "openai/gpt-4": 0.003
    }
    
    price_per_1k = prices.get(model_name, 0.0001)
    return (tokens / 1000) * price_per_1k

# Dans vos analyses MLflow
total_tokens = runs['metrics.total_estimated_tokens'].sum()
estimated_cost = estimate_cost(total_tokens, "google/gemini-2.5-flash")
print(f"Coût estimé: ${estimated_cost:.4f}")
```

## 🚨 Bonnes pratiques

### ✅ À faire :
- Consultez régulièrement les prompts pour optimiser leur efficacité
- Surveillez la longueur des prompts pour contrôler les coûts
- Analysez les patterns de réponses pour améliorer les signatures DSPy
- Comparez les performances entre différents modèles

### ❌ À éviter :
- Ne pas inclure de données sensibles dans les prompts
- Ne pas laisser les prompts devenir trop longs inutilement
- Ne pas oublier de nettoyer les anciens runs MLflow périodiquement

## 📊 Métriques recommandées à surveiller

1. **Efficacité** : tokens/restaurant extrait
2. **Cohérence** : nombre de prompts uniques vs total
3. **Performance** : temps moyen par appel LLM
4. **Qualité** : taux de succès d'extraction vs longueur prompts

## 🔍 Dépannage

### Prompts non sauvegardés
```bash
# Vérifier que MLflow est configuré
uv run python test_prompt_logging.py

# Vérifier les permissions du dossier mlruns
ls -la mlruns/
```

### Métriques manquantes
```python
# Vérifier que le logging est activé
from prompt_logger import prompt_logger
print(f"Appels loggés: {len(prompt_logger.prompts_log)}")
```

### Artefacts corrompus
```bash
# Supprimer et relancer
rm -rf mlruns/
uv run python main.py
```

## 💡 Optimisations suggérées

### Réduire les coûts
1. Analyser les prompts redondants
2. Optimiser le contexte d'extraction
3. Utiliser le cache DSPy efficacement
4. Ajuster max_tokens selon les besoins

### Améliorer la qualité
1. Analyser les échecs d'extraction
2. Comparer les prompts efficaces vs inefficaces  
3. Ajuster les signatures DSPy selon les patterns observés
4. Tester différentes formulations de prompts

Ce système vous donne une visibilité complète sur l'utilisation de votre LLM et vous permet d'optimiser continuellement vos extractions ! 🚀
