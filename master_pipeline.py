"""
Master Pipeline: Complete pharmaceutical translator workflow.
Orchestrates: data prep → glossary building → training → evaluation → document processing.
"""

import os
import sys
import yaml
import argparse
from datetime import datetime

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class MasterPipeline:
    """Orchestrate complete translation pipeline."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.log = []
    
    def print_header(self, title: str):
        """Print section header."""
        print("\n" + "="*80)
        print(f"[>] {title}")
        print("="*80 + "\n")
    
    def step_1_build_glossary(self):
        """Step 1: Build regulatory glossary from CSVs."""
        self.print_header("STEP 1: Building Pharmaceutical Glossary")
        
        try:
            from build_glossary import PharmaGlossaryBuilder
            
            csv_files = self.config["data"]["regulatory_csvs"]
            builder = PharmaGlossaryBuilder(self.config["data"]["glossary_output"])
            builder.build_glossary(csv_files)
            builder.print_statistics()
            builder.save_glossary()
            
            self.log.append("[OK] Glossary built successfully")
            return True
        except Exception as e:
            print(f"[ERROR] Glossary building failed: {e}")
            self.log.append(f"[ERROR] Glossary building failed: {e}")
            return False
    
    def step_2_prepare_data(self):
        """Step 2: Prepare and clean training data."""
        self.print_header("STEP 2: Preparing Training Data")
        
        try:
            from prepare_data import DataPreparationPipeline
            
            pipeline = DataPreparationPipeline(config_path="config.yaml")
            combined_file, cleaned_file = pipeline.prepare_training_data()
            
            self.log.append("[OK] Data preparation complete")
            return True
        except Exception as e:
            print(f"[ERROR] Data preparation failed: {e}")
            self.log.append(f"[ERROR] Data preparation failed: {e}")
            return False
    
    def step_3_train_model(self):
        """Step 3: Train model with improved LoRA configuration."""
        self.print_header("STEP 3: Training Translation Model")
        
        try:
            from train_improved import ImprovedPharmaTrainer
            
            trainer = ImprovedPharmaTrainer(config_path="config.yaml")
            success = trainer.train()
            
            if success:
                self.log.append("[OK] Model training complete")
                return True
            else:
                self.log.append("[ERROR] Model training failed")
                return False
        except Exception as e:
            print(f"[ERROR] Training failed: {e}")
            self.log.append(f"[ERROR] Training failed: {e}")
            return False
    
    def step_4_evaluate_model(self):
        """Step 4: Evaluate model with BLEU, METEOR, ChrF metrics."""
        self.print_header("STEP 4: Evaluating Model")
        
        try:
            from evaluate_model import PharmaTranslationEvaluator
            
            evaluator = PharmaTranslationEvaluator(config_path="config.yaml")
            evaluator.load_model()
            evaluator.evaluate_dataset(max_samples=100)
            evaluator.manual_quality_check(num_samples=10)
            evaluator.generate_report()
            
            self.log.append("[OK] Model evaluation complete")
            return True
        except Exception as e:
            print(f"[ERROR] Evaluation failed: {e}")
            self.log.append(f"[ERROR] Evaluation failed: {e}")
            return False
    
    def step_5_process_document(self, input_doc: str = None):
        """Step 5: Process regulatory document with validation."""
        self.print_header("STEP 5: Processing Regulatory Document")
        
        if input_doc is None:
            input_doc = "xarelto_first_3_pages.docx"
        
        try:
            from process_document_improved import ImprovedDocumentProcessor
            
            processor = ImprovedDocumentProcessor(config_path="config.yaml")
            processor.load_model()
            report = processor.process_document(input_doc)
            
            self.log.append("[OK] Document processing complete")
            return True
        except Exception as e:
            print(f"[ERROR] Document processing failed: {e}")
            self.log.append(f"[ERROR] Document processing failed: {e}")
            return False
    
    def run_full_pipeline(self, skip_steps: list = None, input_doc: str = None):
        """Run complete pipeline with error handling."""
        if skip_steps is None:
            skip_steps = []
        
        print("\n" + "="*80)
        print("[MASTER] PHARMACEUTICAL REGULATORY TRANSLATOR - MASTER PIPELINE")
        print("="*80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        steps = [
            ("1", "Build Glossary", self.step_1_build_glossary, True),
            ("2", "Prepare Data", self.step_2_prepare_data, True),
            ("3", "Train Model", self.step_3_train_model, "train" not in skip_steps),
            ("4", "Evaluate Model", self.step_4_evaluate_model, "eval" not in skip_steps),
            ("5", "Process Document", lambda: self.step_5_process_document(input_doc), "process" not in skip_steps)
        ]
        
        results = {}
        
        for step_num, step_name, step_func, should_run in steps:
            if not should_run:
                print(f"\n[SKIP] Skipping Step {step_num}: {step_name}")
                results[step_num] = "skipped"
                continue
            
            try:
                if step_func():
                    results[step_num] = "success"
                else:
                    results[step_num] = "failed"
                    if step_num in ["1", "2"]:  # Critical steps
                        print(f"\n[ERROR] Pipeline halted at Step {step_num}")
                        break
            except Exception as e:
                print(f"\n[ERROR] Error in Step {step_num}: {e}")
                results[step_num] = "error"
                if step_num in ["1", "2"]:  # Critical steps
                    break
        
        # Final summary
        self.print_summary(results)
    
    def print_summary(self, results: dict):
        """Print pipeline summary."""
        print("\n" + "="*80)
        print("[SUMMARY] PIPELINE RESULTS")
        print("="*80)
        
        for step, status in results.items():
            status_icon = {
                "success": "[OK]",
                "failed": "[FAIL]",
                "error": "[ERROR]",
                "skipped": "[SKIP]"
            }.get(status, "[?]")
            
            step_names = {
                "1": "Build Glossary",
                "2": "Prepare Data",
                "3": "Train Model",
                "4": "Evaluate Model",
                "5": "Process Document"
            }
            
            print(f"{status_icon} Step {step}: {step_names.get(step, 'Unknown')}: {status.upper()}")
        
        print("\n" + "="*80)
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
        # Log
        for entry in self.log:
            print(entry)


def main():
    parser = argparse.ArgumentParser(
        description="Pharmaceutical Regulatory Document Translator - Master Pipeline"
    )
    
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    
    parser.add_argument(
        "--skip",
        choices=["train", "eval", "process"],
        nargs="+",
        default=[],
        help="Steps to skip"
    )
    
    parser.add_argument(
        "--document",
        default="xarelto_first_3_pages.docx",
        help="Input document to process"
    )
    
    parser.add_argument(
        "--steps",
        choices=["all", "data-prep", "train", "eval", "process"],
        default="all",
        help="Pipeline scope to run"
    )
    
    args = parser.parse_args()
    
    # Create output directories
    config = load_config(args.config)
    os.makedirs(config["paths"]["outputs"], exist_ok=True)
    os.makedirs(config["training"]["output_dir"], exist_ok=True)
    
    # Run pipeline
    pipeline = MasterPipeline(config_path=args.config)
    
    if args.steps == "all":
        pipeline.run_full_pipeline(skip_steps=args.skip, input_doc=args.document)
    elif args.steps == "data-prep":
        pipeline.step_1_build_glossary()
        pipeline.step_2_prepare_data()
    elif args.steps == "train":
        pipeline.step_3_train_model()
    elif args.steps == "eval":
        pipeline.step_4_evaluate_model()
    elif args.steps == "process":
        pipeline.step_5_process_document(args.document)


if __name__ == "__main__":
    main()
