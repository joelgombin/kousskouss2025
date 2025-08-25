"""
Module pour logger les prompts et réponses DSPy dans MLflow
"""

import mlflow
import json
import time
from datetime import datetime
from typing import Any, Dict, List
import hashlib


class DSPyPromptLogger:
    """Logger pour capturer les prompts et réponses DSPy"""
    
    def __init__(self):
        self.call_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.prompts_log = []
    
    def log_llm_call(self, prompt: str, response: str, model: str = None, 
                     metadata: Dict[str, Any] = None):
        """Logger un appel au LLM avec prompt et réponse"""
        self.call_count += 1
        timestamp = datetime.now().isoformat()
        
        # Calculer les statistiques du prompt
        prompt_length = len(prompt)
        response_length = len(response)
        
        # Estimation grossière des tokens (à améliorer avec un tokenizer réel)
        estimated_prompt_tokens = len(prompt.split()) * 1.3
        estimated_response_tokens = len(response.split()) * 1.3
        total_tokens = estimated_prompt_tokens + estimated_response_tokens
        
        self.total_tokens += total_tokens
        
        # Créer un hash unique pour ce prompt
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        
        # Préparer les données du log
        log_entry = {
            "call_number": self.call_count,
            "timestamp": timestamp,
            "prompt_hash": prompt_hash,
            "prompt": prompt,
            "response": response,
            "model": model,
            "prompt_length": prompt_length,
            "response_length": response_length,
            "estimated_prompt_tokens": int(estimated_prompt_tokens),
            "estimated_response_tokens": int(estimated_response_tokens),
            "total_estimated_tokens": int(total_tokens),
            "metadata": metadata or {}
        }
        
        self.prompts_log.append(log_entry)
        
        # Logger dans MLflow
        try:
            # Métriques par appel (les métriques peuvent être loggées plusieurs fois)
            mlflow.log_metric(f"llm_call_{self.call_count}_prompt_length", prompt_length)
            mlflow.log_metric(f"llm_call_{self.call_count}_response_length", response_length)
            mlflow.log_metric(f"llm_call_{self.call_count}_tokens", total_tokens)
            
            # Métriques cumulatives (utiliser step pour éviter les collisions)
            mlflow.log_metric("total_llm_calls", self.call_count, step=self.call_count)
            mlflow.log_metric("total_estimated_tokens", self.total_tokens, step=self.call_count)
            
            # Logger le prompt complet comme paramètre (tronqué si trop long)
            # Utiliser un hash court pour éviter les conflisions de paramètres identiques
            if len(prompt) <= 500:
                try:
                    mlflow.log_param(f"prompt_{self.call_count}_full", prompt)
                except:
                    # Si le paramètre existe déjà, utiliser le hash
                    mlflow.log_param(f"prompt_{prompt_hash}", prompt[:500])
            else:
                try:
                    mlflow.log_param(f"prompt_{self.call_count}_preview", prompt[:500] + "...")
                except:
                    mlflow.log_param(f"prompt_preview_{prompt_hash}", prompt[:500] + "...")
            
            # Logger un échantillon de la réponse
            if len(response) <= 500:
                try:
                    mlflow.log_param(f"response_{self.call_count}_sample", response)
                except:
                    response_hash = hashlib.md5(response.encode()).hexdigest()[:8]
                    mlflow.log_param(f"response_{response_hash}", response[:500])
            else:
                try:
                    mlflow.log_param(f"response_{self.call_count}_sample", response[:500] + "...")
                except:
                    response_hash = hashlib.md5(response.encode()).hexdigest()[:8]
                    mlflow.log_param(f"response_sample_{response_hash}", response[:500] + "...")
                
        except Exception as e:
            print(f"⚠️  Erreur lors du logging MLflow: {e}")
    
    def save_full_prompts_artifact(self, filename: str = "prompts_log.json"):
        """Sauvegarder tous les prompts comme artefact MLflow"""
        try:
            import tempfile
            import os
            
            # Créer un fichier temporaire
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                json.dump(self.prompts_log, f, indent=2, ensure_ascii=False)
                temp_path = f.name
            
            # Logger comme artefact
            mlflow.log_artifact(temp_path, "prompts")
            
            # Nettoyer le fichier temporaire
            os.unlink(temp_path)
            
            print(f"📎 Prompts sauvegardés comme artefact: {filename}")
            
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde des prompts: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtenir les statistiques des appels LLM"""
        if not self.prompts_log:
            return {}
        
        total_prompt_chars = sum(entry["prompt_length"] for entry in self.prompts_log)
        total_response_chars = sum(entry["response_length"] for entry in self.prompts_log)
        avg_prompt_length = total_prompt_chars / len(self.prompts_log)
        avg_response_length = total_response_chars / len(self.prompts_log)
        
        return {
            "total_calls": self.call_count,
            "total_prompt_chars": total_prompt_chars,
            "total_response_chars": total_response_chars,
            "avg_prompt_length": avg_prompt_length,
            "avg_response_length": avg_response_length,
            "total_estimated_tokens": self.total_tokens,
            "unique_prompts": len(set(entry["prompt_hash"] for entry in self.prompts_log))
        }


# Instance globale du logger
prompt_logger = DSPyPromptLogger()


def wrap_dspy_lm_call(original_call_method):
    """Wrapper pour intercepter les appels DSPy LM"""
    def wrapped_call(self, *args, **kwargs):
        # Capturer les arguments avant l'appel
        prompt_data = None
        if args:
            # Le premier argument est généralement le prompt ou les messages
            prompt_data = args[0]
        
        # Faire l'appel original
        start_time = time.time()
        result = original_call_method(self, *args, **kwargs)
        call_duration = time.time() - start_time
        
        # Extraire le prompt et la réponse
        try:
            # Pour DSPy, le prompt peut être dans différents formats
            if isinstance(prompt_data, str):
                prompt_text = prompt_data
            elif isinstance(prompt_data, list):
                # Messages format
                prompt_text = "\n".join([
                    f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" 
                    for msg in prompt_data if isinstance(msg, dict)
                ])
            elif hasattr(prompt_data, 'messages'):
                prompt_text = str(prompt_data.messages)
            else:
                prompt_text = str(prompt_data)
            
            # Extraire la réponse
            if hasattr(result, 'choices') and result.choices:
                response_text = result.choices[0].get('message', {}).get('content', str(result))
            elif hasattr(result, 'content'):
                response_text = result.content
            elif isinstance(result, str):
                response_text = result
            else:
                response_text = str(result)
            
            # Logger l'appel
            metadata = {
                "call_duration": call_duration,
                "model_name": getattr(self, 'model', 'unknown'),
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            }
            
            prompt_logger.log_llm_call(
                prompt=prompt_text,
                response=response_text,
                model=getattr(self, 'model', 'unknown'),
                metadata=metadata
            )
            
        except Exception as e:
            print(f"⚠️  Erreur lors de l'interception du prompt: {e}")
        
        return result
    
    return wrapped_call


def setup_dspy_prompt_logging():
    """Configurer l'interception des prompts DSPy"""
    try:
        import dspy
        
        # Patcher la méthode d'appel du LM
        original_call = dspy.LM.__call__
        dspy.LM.__call__ = wrap_dspy_lm_call(original_call)
        
        print("✅ Logging des prompts DSPy activé")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la configuration du logging DSPy: {e}")
        return False


def log_final_prompt_statistics():
    """Logger les statistiques finales des prompts"""
    stats = prompt_logger.get_statistics()
    
    if stats:
        print(f"\n📊 STATISTIQUES DES PROMPTS:")
        print(f"   🔢 Appels LLM: {stats['total_calls']}")
        print(f"   📝 Caractères prompts: {stats['total_prompt_chars']:,}")
        print(f"   📋 Caractères réponses: {stats['total_response_chars']:,}")
        print(f"   📏 Longueur moyenne prompt: {stats['avg_prompt_length']:.0f}")
        print(f"   📊 Longueur moyenne réponse: {stats['avg_response_length']:.0f}")
        print(f"   🎯 Tokens estimés: {stats['total_estimated_tokens']:,.0f}")
        print(f"   🔄 Prompts uniques: {stats['unique_prompts']}")
        
        # Logger dans MLflow
        try:
            for key, value in stats.items():
                mlflow.log_metric(f"final_{key}", value)
        except Exception as e:
            print(f"⚠️  Erreur lors du logging des statistiques: {e}")
        
        # Sauvegarder les prompts complets
        prompt_logger.save_full_prompts_artifact()
