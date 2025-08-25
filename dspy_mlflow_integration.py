"""
Intégration avancée entre DSPy et MLflow pour le logging des prompts
"""

import mlflow
import dspy
import json
import time
from datetime import datetime
from typing import Any, Dict, List
import hashlib


class DSPyMLflowTracker:
    """Tracker pour intégrer DSPy avec MLflow"""
    
    def __init__(self):
        self.call_history = []
        self.current_run_id = None
    
    def start_tracking(self):
        """Démarre le tracking DSPy-MLflow"""
        # Si on est dans un run MLflow, récupérer son ID
        try:
            run = mlflow.active_run()
            if run:
                self.current_run_id = run.info.run_id
                print("🔗 Tracking DSPy activé pour le run MLflow")
            else:
                print("⚠️  Aucun run MLflow actif détecté")
        except Exception as e:
            print(f"⚠️  Erreur lors de l'initialisation du tracking: {e}")
    
    def log_dspy_call(self, signature_name: str, inputs: Dict, outputs: Dict, 
                      metadata: Dict = None):
        """Logger un appel DSPy complet"""
        timestamp = datetime.now().isoformat()
        call_id = len(self.call_history) + 1
        
        # Préparer les données
        call_data = {
            "call_id": call_id,
            "timestamp": timestamp,
            "signature_name": signature_name,
            "inputs": inputs,
            "outputs": outputs,
            "metadata": metadata or {}
        }
        
        self.call_history.append(call_data)
        
        try:
            # Logger dans MLflow
            mlflow.log_param(f"dspy_call_{call_id}_signature", signature_name)
            
            # Logger les inputs (tronqués si nécessaire)
            for key, value in inputs.items():
                value_str = str(value)
                if len(value_str) <= 500:
                    mlflow.log_param(f"dspy_call_{call_id}_input_{key}", value_str)
                else:
                    mlflow.log_param(f"dspy_call_{call_id}_input_{key}_preview", value_str[:500] + "...")
                    mlflow.log_metric(f"dspy_call_{call_id}_input_{key}_length", len(value_str))
            
            # Logger les outputs
            for key, value in outputs.items():
                value_str = str(value)
                if len(value_str) <= 500:
                    mlflow.log_param(f"dspy_call_{call_id}_output_{key}", value_str)
                else:
                    mlflow.log_param(f"dspy_call_{call_id}_output_{key}_preview", value_str[:500] + "...")
                    mlflow.log_metric(f"dspy_call_{call_id}_output_{key}_length", len(value_str))
            
            # Métriques générales
            mlflow.log_metric("dspy_total_calls", call_id)
            
        except Exception as e:
            print(f"⚠️  Erreur lors du logging MLflow: {e}")
    
    def save_call_history(self, filename: str = "dspy_calls.json"):
        """Sauvegarder l'historique complet des appels DSPy"""
        if not self.call_history:
            return
        
        try:
            import tempfile
            import os
            
            # Créer un fichier temporaire
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                json.dump(self.call_history, f, indent=2, ensure_ascii=False, default=str)
                temp_path = f.name
            
            # Logger comme artefact
            mlflow.log_artifact(temp_path, "dspy_calls")
            
            # Nettoyer le fichier temporaire
            os.unlink(temp_path)
            
            print(f"📎 Historique DSPy sauvegardé: {len(self.call_history)} appels")
            
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde DSPy: {e}")


# Instance globale du tracker
dspy_tracker = DSPyMLflowTracker()


def create_logged_predictor(signature_class, predictor_name: str = None):
    """Créer un Predict avec logging automatique"""
    
    class LoggedPredict(dspy.Predict):
        def __init__(self, signature, **config):
            super().__init__(signature, **config)
            self.signature_name = predictor_name or signature.__name__
        
        def forward(self, **kwargs):
            # Capturer les inputs
            inputs = {k: v for k, v in kwargs.items()}
            
            # Faire l'appel original
            result = super().forward(**kwargs)
            
            # Capturer les outputs
            if hasattr(result, '__dict__'):
                outputs = {k: v for k, v in result.__dict__.items() if not k.startswith('_')}
            else:
                outputs = {"result": str(result)}
            
            # Logger l'appel
            dspy_tracker.log_dspy_call(
                signature_name=self.signature_name,
                inputs=inputs,
                outputs=outputs,
                metadata={"predictor_type": "Predict"}
            )
            
            return result
    
    return LoggedPredict(signature_class)


def log_extraction_context(context: str, pages_count: int, file_name: str = None):
    """Logger le contexte d'extraction spécifiquement"""
    try:
        # Utiliser un suffixe unique si le nom de fichier est fourni
        suffix = f"_{file_name}" if file_name else f"_{int(time.time())}"
        
        # Logger les paramètres avec un identifiant unique
        mlflow.log_param(f"extraction_context_length{suffix}", len(context))
        mlflow.log_param(f"extraction_pages_count{suffix}", pages_count)
        
        # Logger un extrait du contexte (tronqué si nécessaire)
        context_preview = context[:500] + "..." if len(context) > 500 else context
        mlflow.log_param(f"extraction_context_preview{suffix}", context_preview)
        
        # Analyser le contexte
        context_lines = context.split('\n')
        mlflow.log_metric(f"extraction_context_lines{suffix}", len(context_lines))
        
        # Compter les mots-clés importants
        keywords = ["restaurant", "plat", "couscous", "quartier", "festival"]
        keyword_counts = {}
        context_lower = context.lower()
        
        for keyword in keywords:
            count = context_lower.count(keyword)
            keyword_counts[keyword] = count
            mlflow.log_metric(f"context_keyword_{keyword}{suffix}", count)
        
        print(f"📝 Contexte d'extraction loggé: {len(context)} caractères, {len(context_lines)} lignes")
        
    except Exception as e:
        print(f"⚠️  Erreur lors du logging du contexte: {e}")


def analyze_dspy_usage():
    """Analyser l'utilisation de DSPy pour ce run"""
    try:
        # Obtenir les stats d'usage DSPy si disponibles
        if hasattr(dspy, 'usage_tracking') and dspy.usage_tracking:
            usage_data = dspy.usage_tracking.get_usage()
            
            if usage_data:
                for key, value in usage_data.items():
                    mlflow.log_metric(f"dspy_usage_{key}", value)
                
                print(f"📊 Stats d'usage DSPy loggées: {len(usage_data)} métriques")
        
        # Logger les informations de configuration DSPy
        if hasattr(dspy, 'settings') and dspy.settings:
            config = dspy.settings
            
            if hasattr(config, 'lm') and config.lm:
                mlflow.log_param("dspy_model_name", getattr(config.lm, 'model', 'unknown'))
                mlflow.log_param("dspy_cache_enabled", getattr(config.lm, 'cache', False))
                
                if hasattr(config.lm, 'kwargs'):
                    for key, value in config.lm.kwargs.items():
                        mlflow.log_param(f"dspy_lm_{key}", str(value))
        
        # Logger l'historique des appels
        dspy_tracker.save_call_history()
        
    except Exception as e:
        print(f"⚠️  Erreur lors de l'analyse DSPy: {e}")


def setup_enhanced_dspy_logging():
    """Configuration complète du logging DSPy"""
    try:
        # Démarrer le tracking
        dspy_tracker.start_tracking()
        
        # Hook pour capturer automatiquement tous les appels DSPy
        original_forward = dspy.Predict.forward
        
        def logged_forward(self, **kwargs):
            # Capturer le nom de la signature
            signature_name = getattr(self.signature, '__name__', 'UnknownSignature')
            
            # Inputs
            inputs = {k: v for k, v in kwargs.items()}
            
            # Appel original
            result = original_forward(self, **kwargs)
            
            # Outputs
            if hasattr(result, '__dict__'):
                outputs = {k: v for k, v in result.__dict__.items() if not k.startswith('_')}
            else:
                outputs = {"result": str(result)}
            
            # Logger
            dspy_tracker.log_dspy_call(
                signature_name=signature_name,
                inputs=inputs,
                outputs=outputs,
                metadata={"auto_captured": True}
            )
            
            return result
        
        # Appliquer le patch
        dspy.Predict.forward = logged_forward
        
        print("✅ Logging DSPy avancé activé")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la configuration DSPy avancée: {e}")
        return False
