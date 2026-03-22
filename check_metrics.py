"""
Comprehensive metrics checker and reporter.
Validates all required metrics and prints detailed report.
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

class MetricsChecker:
    """Check and report all translation quality metrics."""
    
    # Target metrics thresholds
    TARGETS = {
        "bleu": 20,
        "meteor": 35,
        "chrf": 60,
        "ter": 60,  # TER should be LOWER than this
        "glossary_match": 85,
        "consistency": 90
    }
    
    def __init__(self):
        self.metrics = {}
        self.status = {}
        self.issues = []
    
    def load_evaluation_report(self, report_path: str = "outputs/evaluation_report.json") -> bool:
        """Load evaluation report from file."""
        if not os.path.exists(report_path):
            self.issues.append(f"Evaluation report not found: {report_path}")
            print(f"[ERROR] Report not found: {report_path}")
            return False
        
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.metrics.update(data)
                print(f"[OK] Loaded evaluation report")
                return True
        except Exception as e:
            self.issues.append(f"Failed to load report: {e}")
            print(f"[ERROR] Failed to load report: {e}")
            return False
    
    def check_metrics(self) -> Dict:
        """Validate all metrics against targets."""
        print("\n" + "="*70)
        print("METRICS VALIDATION REPORT")
        print("="*70)
        
        results = {
            "total_metrics": 0,
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        # Check BLEU Score
        if "bleu" in self.metrics:
            bleu = self.metrics["bleu"]
            passed = bleu is not None and bleu >= self.TARGETS["bleu"]
            results["details"].append(self._format_metric("BLEU Score", bleu, self.TARGETS["bleu"], passed))
            results["total_metrics"] += 1
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
        else:
            results["details"].append(self._format_metric("BLEU Score", "N/A", self.TARGETS["bleu"], False))
            results["total_metrics"] += 1
            results["failed"] += 1
        
        # Check METEOR
        if "meteor" in self.metrics:
            meteor = self.metrics["meteor"]
            passed = meteor is not None and meteor >= self.TARGETS["meteor"]
            results["details"].append(self._format_metric("METEOR", meteor, self.TARGETS["meteor"], passed))
            results["total_metrics"] += 1
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
        else:
            results["details"].append(self._format_metric("METEOR", "N/A", self.TARGETS["meteor"], False))
            results["total_metrics"] += 1
            results["failed"] += 1
        
        # Check ChrF
        if "chrf" in self.metrics:
            chrf = self.metrics["chrf"]
            passed = chrf is not None and chrf >= self.TARGETS["chrf"]
            results["details"].append(self._format_metric("ChrF", chrf, self.TARGETS["chrf"], passed))
            results["total_metrics"] += 1
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
        else:
            results["details"].append(self._format_metric("ChrF", "N/A", self.TARGETS["chrf"], False))
            results["total_metrics"] += 1
            results["failed"] += 1
        
        # Check TER (lower is better)
        if "ter" in self.metrics:
            ter = self.metrics["ter"]
            passed = ter is not None and ter <= self.TARGETS["ter"]
            results["details"].append(self._format_metric(
                "TER (lower better)", 
                ter, 
                f"< {self.TARGETS['ter']}", 
                passed
            ))
            results["total_metrics"] += 1
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
        else:
            results["details"].append(self._format_metric("TER", "N/A", f"< {self.TARGETS['ter']}", False))
            results["total_metrics"] += 1
            results["failed"] += 1
        
        # Check Glossary Match Rate
        if "glossary_match_rate" in self.metrics:
            glossary = self.metrics["glossary_match_rate"]
            passed = glossary is not None and glossary >= self.TARGETS["glossary_match"]
            results["details"].append(self._format_metric(
                "Glossary Match Rate", 
                f"{glossary}%", 
                f">= {self.TARGETS['glossary_match']}%", 
                passed
            ))
            results["total_metrics"] += 1
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
        else:
            results["details"].append(self._format_metric(
                "Glossary Match Rate", 
                "N/A", 
                f">= {self.TARGETS['glossary_match']}%", 
                False
            ))
            results["total_metrics"] += 1
            results["failed"] += 1
        
        # Check Term Consistency
        if "consistency_rate" in self.metrics:
            consistency = self.metrics["consistency_rate"]
            passed = consistency is not None and consistency >= self.TARGETS["consistency"]
            results["details"].append(self._format_metric(
                "Term Consistency", 
                f"{consistency}%", 
                f">= {self.TARGETS['consistency']}%", 
                passed
            ))
            results["total_metrics"] += 1
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
        else:
            results["details"].append(self._format_metric(
                "Term Consistency", 
                "N/A", 
                f">= {self.TARGETS['consistency']}%", 
                False
            ))
            results["total_metrics"] += 1
            results["failed"] += 1
        
        return results
    
    def _format_metric(self, name: str, value, target, passed: bool) -> str:
        """Format metric for display."""
        status = "[PASS]" if passed else "[FAIL]"
        
        if value == "N/A":
            return f"{status} {name:<25} Value: {value:<15} Target: {target}"
        
        if isinstance(value, (int, float)):
            return f"{status} {name:<25} Value: {value:>10.2f}  Target: {target}"
        else:
            return f"{status} {name:<25} Value: {value:<15} Target: {target}"
    
    def print_report(self, results: Dict):
        """Print formatted metrics report."""
        print("\nMetrics Validation Status:")
        print("-" * 70)
        
        for detail in results["details"]:
            print(detail)
        
        print("-" * 70)
        print(f"Overall: {results['passed']}/{results['total_metrics']} metrics passed")
        
        if results["failed"] > 0:
            print(f"[WARNING] {results['failed']} metric(s) below target")
        else:
            print("[SUCCESS] All metrics meet or exceed targets!")
        
        print("="*70)
    
    def print_detailed_metrics(self):
        """Print all detailed metrics from report."""
        print("\nDetailed Metrics Information:")
        print("-" * 70)
        
        for key, value in self.metrics.items():
            if key not in ["bleu", "meteor", "chrf", "ter", "glossary_match_rate", "consistency_rate"]:
                print(f"{key:<35} : {value}")
        
        print("="*70)
    
    def check_sample_translations(self, samples_path: str = "outputs/evaluation_samples.csv") -> bool:
        """Check if sample translations exist."""
        if os.path.exists(samples_path):
            try:
                import pandas as pd
                df = pd.read_csv(samples_path)
                print(f"\n[OK] Found {len(df)} sample translations")
                return True
            except Exception as e:
                print(f"[WARNING] Could not read samples: {e}")
                return False
        else:
            print(f"\n[WARNING] Sample translations not found: {samples_path}")
            return False
    
    def check_model_adapter(self, adapter_path: str = "medical_adapter_final") -> bool:
        """Check if trained adapter exists."""
        if os.path.isdir(adapter_path):
            required_files = [
                "adapter_config.json",
                "adapter_model.safetensors"
            ]
            
            missing = []
            for file in required_files:
                if not os.path.exists(os.path.join(adapter_path, file)):
                    missing.append(file)
            
            if not missing:
                print(f"[OK] Adapter found: {adapter_path}")
                return True
            else:
                print(f"[WARNING] Missing files in adapter: {missing}")
                return False
        else:
            print(f"[ERROR] Adapter not found: {adapter_path}")
            return False
    
    def check_training_data(self, data_path: str = "medical_training_final_cleaned.csv") -> bool:
        """Check if training data exists."""
        if os.path.exists(data_path):
            try:
                import pandas as pd
                df = pd.read_csv(data_path)
                print(f"[OK] Training data found: {len(df)} samples")
                return True
            except Exception as e:
                print(f"[ERROR] Could not read training data: {e}")
                return False
        else:
            print(f"[ERROR] Training data not found: {data_path}")
            return False
    
    def generate_summary(self) -> Dict:
        """Generate complete system summary."""
        summary = {
            "timestamp": None,
            "model_adapter": self.check_model_adapter(),
            "training_data": self.check_training_data(),
            "evaluation_report": os.path.exists("outputs/evaluation_report.json"),
            "sample_translations": self.check_sample_translations(),
            "issues": self.issues
        }
        
        return summary


def main():
    """Main execution."""
    print("\n")
    print("=" * 70)
    print("PHARMACEUTICAL TRANSLATOR - METRICS CHECKER")
    print("=" * 70)
    
    checker = MetricsChecker()
    
    # Check system health
    print("\n[CHECK] System Health Status:")
    print("-" * 70)
    checker.check_model_adapter()
    checker.check_training_data()
    checker.check_sample_translations()
    
    # Load and validate metrics
    print("\n[CHECK] Loading evaluation metrics...")
    if checker.load_evaluation_report():
        results = checker.check_metrics()
        checker.print_report(results)
        checker.print_detailed_metrics()
        
        # Print summary
        summary = checker.generate_summary()
        print("\nSystem Status Summary:")
        print(f"  Model Adapter:        {'[OK]' if summary['model_adapter'] else '[MISSING]'}")
        print(f"  Training Data:        {'[OK]' if summary['training_data'] else '[MISSING]'}")
        print(f"  Evaluation Report:    {'[OK]' if summary['evaluation_report'] else '[MISSING]'}")
        print(f"  Sample Translations:  {'[OK]' if summary['sample_translations'] else '[MISSING]'}")
        
        if checker.issues:
            print(f"\nIssues Found:")
            for issue in checker.issues:
                print(f"  - {issue}")
        else:
            print("\n[SUCCESS] No issues detected!")
    else:
        print("[ERROR] Could not load evaluation report")
        print("Run evaluation first: .\venv\Scripts\python.exe evaluate_model.py")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
