"""
Improved training script with enhanced LoRA configuration and evaluation metrics.
Follows configuration from config.yaml for reproducibility.
Optimized for RTX 4060 GPU execution.
"""

import torch
import yaml
import time
import os
from datetime import timedelta
from datasets import load_dataset
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    DataCollatorForSeq2Seq,
    TrainerCallback,
    EarlyStoppingCallback
)
from peft import LoraConfig, get_peft_model, TaskType
import json

def check_gpu():
    """Verify CUDA/GPU availability and log GPU info."""
    if not torch.cuda.is_available():
        print("[ERROR] CUDA is not available. Please ensure PyTorch with CUDA support is installed.")
        raise RuntimeError("CUDA not available")
    
    cuda_version = torch.version.cuda
    cudnn_version = torch.backends.cudnn.version()
    device_count = torch.cuda.device_count()
    
    print("\n" + "="*70)
    print("[GPU] CUDA/GPU Configuration")
    print("="*70)
    print(f"CUDA Available: True")
    print(f"CUDA Version: {cuda_version}")
    print(f"cuDNN Version: {cudnn_version}")
    print(f"Number of GPUs: {device_count}")
    
    for i in range(device_count):
        props = torch.cuda.get_device_properties(i)
        print(f"\nGPU {i}: {props.name}")
        print(f"  Memory: {props.total_memory / 1e9:.2f} GB")
        print(f"  Compute Capability: {props.major}.{props.minor}")
    
    current_device = torch.cuda.current_device()
    print(f"\nDefault Device: GPU {current_device}")
    
    allocated = torch.cuda.memory_allocated() / 1e9
    reserved = torch.cuda.memory_reserved() / 1e9
    print(f"Memory Allocated: {allocated:.2f} GB")
    print(f"Memory Reserved: {reserved:.2f} GB")
    print("="*70 + "\n")

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class TimerCallback(TrainerCallback):
    """Track training time."""
    def on_train_begin(self, args, state, control, **kwargs):
        self.start_time = time.time()
        print(f"\n⏱️ Training started at: {time.strftime('%H:%M:%S')}")

    def on_train_end(self, args, state, control, **kwargs):
        total_time = time.time() - self.start_time
        print(f"\n⏱️ TOTAL TRAINING TIME: {str(timedelta(seconds=int(total_time)))}")

class ImprovedPharmaTrainer:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.model = None
        self.tokenizer = None
        self.trainer = None
    
    def setup_model_and_tokenizer(self):
        """Initialize base model and tokenizer."""
        print("🧠 Initializing model and tokenizer...")
        
        model_id = self.config["model"]["base_model"]
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            src_lang=self.config["model"]["src_lang"],
            tgt_lang=self.config["model"]["tgt_lang"]
        )
        
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            model_id,
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )
        
        print(f"[OK] Model: {model_id}")
        return self.model, self.tokenizer
    
    def setup_lora(self):
        """Configure LoRA with enhanced settings."""
        print("🔧 Configuring LoRA adapters...")
        
        lora_config_dict = self.config["training"]["lora"]
        
        peft_config = LoraConfig(
            task_type=TaskType.SEQ_2_SEQ_LM,
            r=lora_config_dict["r"],
            lora_alpha=lora_config_dict["lora_alpha"],
            lora_dropout=lora_config_dict["lora_dropout"],
            target_modules=lora_config_dict["target_modules"],
            bias=lora_config_dict["bias"]
        )
        
        self.model = get_peft_model(self.model, peft_config)
        self.model.print_trainable_parameters()
        
        print(f"[OK] LoRA configured:")
        print(f"   Rank (r): {lora_config_dict['r']}")
        print(f"   Alpha: {lora_config_dict['lora_alpha']}")
        print(f"   Dropout: {lora_config_dict['lora_dropout']}")
        print(f"   Target modules: {lora_config_dict['target_modules']}")
        
        return self.model
    
    def load_and_preprocess_data(self):
        """Load and preprocess training data."""
        print("\n📦 Loading dataset...")
        
        csv_path = self.config["data"]["output_cleaned"]
        
        if not os.path.exists(csv_path):
            print(f"[WARNING] File not found: {csv_path}")
            print(f"   Run prepare_data.py first")
            return None, None
        
        dataset = load_dataset("csv", data_files=csv_path)["train"]
        
        # Split into train/test/val
        train_test = dataset.train_test_split(
            test_size=self.config["validation"]["test_size"],
            seed=self.config["validation"]["seed"]
        )
        
        train_val = train_test["train"].train_test_split(
            test_size=self.config["validation"]["val_size"],
            seed=self.config["validation"]["seed"]
        )
        
        dataset_dict = {
            "train": train_val["train"],
            "val": train_val["test"],
            "test": train_test["test"]
        }
        
        print(f"[OK] Dataset sizes:")
        print(f"   Train: {len(dataset_dict['train'])}")
        print(f"   Val: {len(dataset_dict['val'])}")
        print(f"   Test: {len(dataset_dict['test'])}")
        
        # Tokenization
        print("🛠️ Tokenizing data...")
        
        def preprocess_function(examples):
            max_input_length = self.config["training"]["max_seq_length"]
            
            model_inputs = self.tokenizer(
                examples["en"],
                max_length=max_input_length,
                truncation=True,
                padding="max_length"
            )
            
            labels = self.tokenizer(
                text_target=examples["de"],
                max_length=max_input_length,
                truncation=True,
                padding="max_length"
            )
            
            model_inputs["labels"] = labels["input_ids"]
            return model_inputs
        
        tokenized = {}
        for split, data in dataset_dict.items():
            tokenized[split] = data.map(
                preprocess_function,
                batched=True,
                remove_columns=data.column_names,
                desc=f"Tokenizing {split}"
            )
        
        print("[OK] Tokenization complete")
        return tokenized, dataset_dict
    
    def setup_training_args(self):
        """Configure training arguments from config - GPU optimized."""
        print("\n[CONFIG] Setting up training arguments...")
        
        training_config = self.config["training"]
        
        args = Seq2SeqTrainingArguments(
            output_dir=training_config["output_dir"],
            num_train_epochs=training_config["num_epochs"],
            per_device_train_batch_size=training_config["per_device_train_batch_size"],
            per_device_eval_batch_size=training_config["per_device_eval_batch_size"],
            gradient_accumulation_steps=training_config["gradient_accumulation_steps"],
            learning_rate=training_config["learning_rate"],
            warmup_steps=int(1000 * training_config.get("warmup_ratio", 0.1)),
            weight_decay=training_config.get("weight_decay", 0.01),
            bf16=True,
            logging_steps=training_config["logging_steps"],
            eval_strategy=training_config["eval_strategy"],
            save_strategy=training_config["save_strategy"],
            save_total_limit=training_config["save_total_limit"],
            predict_with_generate=True,
            report_to="none",
            seed=self.config["validation"]["seed"],
            optim="paged_adamw_8bit",
            # GPU optimizations
            gradient_checkpointing=training_config.get("gradient_checkpointing", True),
            max_grad_norm=training_config.get("max_grad_norm", 1.0),
            fp16=False,  # Using bfloat16 instead
            remove_unused_columns=False
        )
        
        print("[OK] Training arguments configured")
        return args
    
    def train(self):
        """Execute training pipeline - GPU optimized."""
        # Check GPU availability first
        check_gpu()
        
        print("\n" + "="*70)
        print("[START] PHARMACEUTICAL TRANSLATOR - TRAINING PIPELINE")
        print("="*70)
        
        # Setup
        self.setup_model_and_tokenizer()
        self.setup_lora()
        
        # Enable gradient checkpointing for memory efficiency
        if hasattr(self.model, 'gradient_checkpointing_enable'):
            self.model.gradient_checkpointing_enable()
            print("[OK] Gradient checkpointing enabled")
        
        # Data
        tokenized_data, raw_dataset = self.load_and_preprocess_data()
        if tokenized_data is None:
            return False
        
        # Training config
        training_args = self.setup_training_args()
        
        # Trainer
        print("\n🏋️ Initializing trainer...")
        
        self.trainer = Seq2SeqTrainer(
            model=self.model,
            args=training_args,
            train_dataset=tokenized_data["train"],
            eval_dataset=tokenized_data["val"],
            tokenizer=self.tokenizer,
            data_collator=DataCollatorForSeq2Seq(self.tokenizer, model=self.model),
            callbacks=[
                TimerCallback(),
                EarlyStoppingCallback(
                    early_stopping_patience=self.config["training"]["early_stopping_patience"],
                    early_stopping_threshold=self.config["training"]["early_stopping_threshold"]
                )
            ]
        )
        
        # Train
        print("🏋️ Starting training...\n")
        try:
            train_result = self.trainer.train()
            
            # Evaluate on test set
            print("\n📊 Evaluating on test set...")
            test_results = self.trainer.evaluate(
                eval_dataset=tokenized_data["test"],
                metric_key_prefix="test"
            )
            
            # Save final model
            adapter_path = self.config["paths"]["adapter_final"]
            print(f"\n💾 Saving model to {adapter_path}...")
            self.model.save_pretrained(adapter_path)
            self.tokenizer.save_pretrained(adapter_path)
            
            # Save results
            results = {
                "training": train_result.to_dict() if hasattr(train_result, 'to_dict') else str(train_result),
                "test_evaluation": test_results,
                "model_config": self.config
            }
            
            results_path = os.path.join(self.config["training"]["output_dir"], "training_results.json")
            with open(results_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, default=str)
            
            print("\n" + "="*70)
            print("[OK] TRAINING COMPLETE")
            print("="*70)
            print(f"Model saved: {adapter_path}")
            print(f"Results saved: {results_path}")
            print("="*70 + "\n")
            
            return True
        
        except Exception as e:
            print(f"\n[ERROR] Training failed: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    trainer = ImprovedPharmaTrainer(config_path="config.yaml")
    success = trainer.train()
    exit(0 if success else 1)
