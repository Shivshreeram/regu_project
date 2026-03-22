"""
Evaluation module with BLEU, METEOR, ChrF, and TER metrics.
Computes pharmaceutical translation quality scores.
GPU optimized for RTX 4060.
"""

import os
import json
import torch
import numpy as np
import pandas as pd
import yaml
from typing import Dict, List, Tuple
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from peft import PeftModel
from datasets import load_dataset

try:
    from sacrebleu import BLEU, CHRF, TER
    HAS_SACREBLEU = True
    
    # Try to import METEOR (not available in newer versions)
    try:
        from sacrebleu import METEOR
        HAS_METEOR = True
    except ImportError:
        HAS_METEOR = False
        print("[WARNING] METEOR not available in this sacrebleu version. Will use alternative metrics.")
        
except ImportError:
    print("[WARNING] sacrebleu not installed. Install with: pip install sacrebleu")
    HAS_SACREBLEU = False
    HAS_METEOR = False

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def check_gpu():
    """Verify GPU availability for evaluation."""
    if not torch.cuda.is_available():
        print("[WARNING] CUDA not available. Evaluation will run on CPU.")
        return False
    device = torch.cuda.current_device()
    props = torch.cuda.get_device_properties(device)
    print(f"[GPU] Using device: {props.name}")
    return True

class PharmaTranslationEvaluator:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.model = None
        self.tokenizer = None
        self.results = {}
    
    def load_model(self, adapter_path: str = None):
        """Load trained model with adapter - GPU optimized."""
        check_gpu()
        
        if adapter_path is None:
            adapter_path = self.config["paths"]["adapter_final"]
        
        print(f"[LOAD] Loading model from {adapter_path}...")
        
        base_model = self.config["model"]["base_model"]
        
        self.tokenizer = AutoTokenizer.from_pretrained(base_model)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            base_model,
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )
        
        # Load adapter
        self.model = PeftModel.from_pretrained(self.model, adapter_path)
        self.model.eval()
        
        print("[OK] Model loaded")
    
    def translate_batch(self, texts: List[str], batch_size: int = 8) -> List[str]:
        """Translate batch of texts."""
        translations = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            
            inputs = self.tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=128
            ).to(self.model.device)
            
            with torch.no_grad():
                generated_tokens = self.model.generate(
                    **inputs,
                    forced_bos_token_id=self.tokenizer.convert_tokens_to_ids("deu_Latn"),
                    max_length=128,
                    num_beams=4
                )
            
            batch_translations = self.tokenizer.batch_decode(
                generated_tokens,
                skip_special_tokens=True
            )
            translations.extend(batch_translations)
        
        return translations
    
    def compute_metrics(self, predictions: List[str], references: List[str]) -> Dict:
        """Compute BLEU, METEOR, ChrF, TER scores."""
        print("\n[STATS] Computing translation metrics...")
        
        metrics = {}
        
        if HAS_SACREBLEU:
            try:
                # BLEU
                bleu = BLEU()
                bleu_score = bleu.corpus_score(predictions, [references])
                metrics["bleu"] = float(bleu_score.score)
                print(f"   BLEU: {metrics['bleu']:.2f}")
            except Exception as e:
                print(f"   BLEU: Error - {e}")
            
            try:
                # METEOR (if available)
                if HAS_METEOR:
                    meteor = METEOR()
                    meteor_score = meteor.corpus_score(predictions, [references])
                    metrics["meteor"] = float(meteor_score.score)
                    print(f"   METEOR: {metrics['meteor']:.2f}")
                else:
                    print("   METEOR: Not available in this sacrebleu version")
            except Exception as e:
                print(f"   METEOR: Error - {e}")
            
            try:
                # ChrF
                chrf = CHRF()
                chrf_score = chrf.corpus_score(predictions, [references])
                metrics["chrf"] = float(chrf_score.score)
                print(f"   ChrF: {metrics['chrf']:.2f}")
            except Exception as e:
                print(f"   ChrF: Error - {e}")
            
            try:
                # TER
                ter = TER()
                ter_score = ter.corpus_score(predictions, [references])
                metrics["ter"] = float(ter_score.score)
                print(f"   TER: {metrics['ter']:.2f}")
            except Exception as e:
                print(f"   TER: Error - {e}")
        else:
            print("   [WARNING] sacrebleu not available. Install for full metrics.")
        
        return metrics
    
    def evaluate_dataset(self, csv_path: str = None, max_samples: int = None) -> Dict:
        """Evaluate on dataset."""
        if csv_path is None:
            csv_path = self.config["data"]["output_cleaned"]
        
        print(f"\n[LOAD] Loading test data from {csv_path}...")
        
        if not os.path.exists(csv_path):
            print(f"[ERROR] File not found: {csv_path}")
            return {}
        
        df = pd.read_csv(csv_path)
        
        if max_samples:
            df = df.sample(n=min(max_samples, len(df)), random_state=42)
        
        print(f"[STATS] Evaluating on {len(df)} samples...")
        
        en_texts = df["en"].tolist()
        de_references = df["de"].tolist()
        
        # Translate
        de_predictions = self.translate_batch(en_texts)
        
        # Compute metrics
        metrics = self.compute_metrics(de_predictions, de_references)
        
        # Save sample outputs
        sample_df = pd.DataFrame({
            "english": en_texts[:10],
            "reference_german": de_references[:10],
            "predicted_german": de_predictions[:10]
        })
        
        sample_path = os.path.join(
            self.config["paths"]["outputs"],
            "evaluation_samples.csv"
        )
        os.makedirs(os.path.dirname(sample_path), exist_ok=True)
        sample_df.to_csv(sample_path, index=False, encoding="utf-8")
        
        self.results = {
            "metrics": metrics,
            "dataset_size": len(df),
            "sample_outputs_path": sample_path
        }
        
        return self.results
    
    def manual_quality_check(self, num_samples: int = 10) -> None:
        """Perform manual quality check on sample translations."""
        print(f"\n[CHECK] Manual quality check on {num_samples} samples...")
        print("="*70)
        
        csv_path = self.config["data"]["output_cleaned"]
        df = pd.read_csv(csv_path)
        df_sample = df.sample(n=min(num_samples, len(df)), random_state=42)
        
        for idx, row in df_sample.iterrows():
            en_text = row["en"]
            de_ref = row["de"]
            
            de_pred = self.translate_batch([en_text])[0]
            
            print(f"\n[Sample {idx+1}]")
            print(f"English:         {en_text}")
            print(f"Reference DE:    {de_ref}")
            print(f"Predicted DE:    {de_pred}")
            print("-"*70)
    
    def generate_report(self, output_path: str = None) -> str:
        """Generate evaluation report."""
        if output_path is None:
            output_path = os.path.join(
                self.config["paths"]["outputs"],
                "evaluation_report.json"
            )
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        report = {
            "model_config": {
                "base_model": self.config["model"]["base_model"],
                "adapter": self.config["paths"]["adapter_final"],
                "lora_config": self.config["training"]["lora"]
            },
            "evaluation_results": self.results,
            "thresholds": {
                "bleu_minimum": self.config["validation"]["bleu_threshold"],
                "glossary_match_minimum": self.config["validation"]["glossary_match_threshold"]
            }
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n[SAVE] Report saved: {output_path}")
        return output_path
    
    def evaluate(self):
        """Full evaluation pipeline."""
        print("\n" + "="*70)
        print("[STATS] PHARMACEUTICAL TRANSLATOR - EVALUATION PIPELINE")
        print("="*70)
        
        self.load_model()
        self.evaluate_dataset(max_samples=100)  # Evaluation on 100 samples
        self.manual_quality_check(num_samples=10)
        self.generate_report()
        
        print("\n" + "="*70)
        print("[OK] EVALUATION COMPLETE")
        print("="*70)


if __name__ == "__main__":
    evaluator = PharmaTranslationEvaluator(config_path="config.yaml")
    evaluator.evaluate()
