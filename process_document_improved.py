"""
Improved document processor with structure preservation and validation.
Handles complex regulatory documents with table and section preservation.
GPU optimized for RTX 4060.
"""

import os
import json
import random
import torch
import yaml
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict
from docx import Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.document import Document as DocumentClass
from docx.table import _Cell
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from peft import PeftModel
from collections import defaultdict

from validate_and_postprocess import GlossaryValidator, PostProcessingPipeline

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def check_gpu():
    """Verify GPU availability for document processing."""
    if not torch.cuda.is_available():
        print("[WARNING] CUDA not available. Document processing will run on CPU.")
        return False
    device = torch.cuda.current_device()
    props = torch.cuda.get_device_properties(device)
    print(f"[GPU] Using device: {props.name}")
    return True

class ImprovedDocumentProcessor:
    """Process pharmaceutical regulatory documents with validation."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.seed = self.config["data"].get("random_seed", self.config["validation"].get("seed", 42))
        self.set_seed()
        self.model = None
        self.tokenizer = None
        self.validator = GlossaryValidator(config_path=config_path)
        self.post_processor = PostProcessingPipeline(config_path=config_path)
        self.translation_log = defaultdict(list)
        self.stats = {
            "total_segments": 0,
            "successful_translations": 0,
            "failed_translations": 0,
            "glossary_matches": 0
        }

    def set_seed(self):
        os.environ["PYTHONHASHSEED"] = str(self.seed)
        random.seed(self.seed)
        np.random.seed(self.seed)
        torch.manual_seed(self.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.seed)
    
    def load_model(self, adapter_path: str = None):
        """Load model and tokenizer - GPU optimized."""
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
        
        self.model = PeftModel.from_pretrained(self.model, adapter_path)
        self.model.eval()
        
        print("[OK] Model loaded")
    
    def translate_text(self, text: str, max_retries: int = None) -> str:
        """
        Translate text with retry logic and validation.
        """
        if max_retries is None:
            max_retries = self.config["document_processing"]["max_retries"]
        
        text = text.strip()
        
        # Handle empty/short text
        if not text or len(text) < 2:
            return text
        
        # Try to translate with retries
        for attempt in range(max_retries):
            try:
                inputs = self.tokenizer(
                    text,
                    return_tensors="pt",
                    max_length=512,
                    truncation=True
                ).to(self.model.device)
                
                with torch.no_grad():
                    generated_tokens = self.model.generate(
                        **inputs,
                        forced_bos_token_id=self.tokenizer.convert_tokens_to_ids("deu_Latn"),
                        max_length=512,
                        num_beams=4,
                        early_stopping=True
                    )
                
                translation = self.tokenizer.batch_decode(
                    generated_tokens,
                    skip_special_tokens=True
                )[0]
                
                # Apply post-processing
                result = self.post_processor.process_translation(text, translation)
                final_translation = result["final_translation"]
                
                # Log translation for consistency checking
                self.translation_log[text.lower()].append(final_translation)
                
                self.stats["successful_translations"] += 1
                return final_translation
            
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"[WARNING] Translation failed after {max_retries} attempts: {str(e)[:50]}")
                    self.stats["failed_translations"] += 1
                    
                    # Fallback
                    fallback = self.config["document_processing"]["retry_fallback"]
                    if fallback == "glossary_only":
                        # Try glossary-only translation
                        return self._glossary_only_translate(text)
                    else:
                        return text  # Return original
        
        return text
    
    def _glossary_only_translate(self, text: str) -> str:
        """Fallback: translate using only glossary mappings."""
        result = text
        
        for en_term, translations in self.validator.term_map.items():
            if translations:
                import re
                pattern = re.compile(re.escape(en_term), re.IGNORECASE)
                result = pattern.sub(translations[0], result)
        
        return result
    
    def iter_block_items(self, parent):
        """Iterate over document blocks (paragraphs and tables)."""
        from docx.document import Document as _Document
        from docx.oxml.text.paragraph import CT_P
        from docx.oxml.table import CT_Tbl
        from docx.table import _Cell, Table
        from docx.text.paragraph import Paragraph
        
        if isinstance(parent, _Document):
            parent_elm = parent.element.body
        elif isinstance(parent, _Cell):
            parent_elm = parent._element
        else:
            parent_elm = parent._element
        
        for child in parent_elm:
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)
    
    def clean_inline_table(self, text: str) -> str:
        """
        Clean inline table content with repetitive headers.
        Detects and removes duplicate column headers (e.g., 'Einheitswert' repeated 50+ times).
        """
        # Check if text contains pipe-separated table markers
        if "|" not in text:
            return text
        
        # Split by pipes
        parts = text.split("|")
        
        # If repetitive columns detected, keep only first few unique headers and data
        if len(parts) > 15:  # Likely malformed table with many columns
            # Look for repeated tokens
            token_counts = defaultdict(int)
            for part in parts:
                stripped = part.strip()
                if stripped:
                    token_counts[stripped] += 1
            
            # If any token repeated >5 times, it's likely a mangled table header
            heavily_repeated = [t for t, count in token_counts.items() if count > 5]
            
            if heavily_repeated:
                print(f"[CLEAN] Detected malformed inline table with {len(parts)} columns")
                print(f"[CLEAN] Repeated tokens: {heavily_repeated}")
                
                # Reconstruct with unique parts only
                seen = set()
                cleaned_parts = []
                for part in parts:
                    stripped = part.strip()
                    if stripped and stripped not in seen and stripped not in heavily_repeated:
                        cleaned_parts.append(stripped)
                        seen.add(stripped)
                    elif stripped not in heavily_repeated:
                        cleaned_parts.append(stripped)
                
                text = " | ".join(cleaned_parts[:20])  # Limit to first 20 meaningful parts
                print(f"[CLEAN] Reduced to {len(cleaned_parts)} parts")
        
        return text
    
    def process_paragraph(self, paragraph) -> None:
        """Process and translate a paragraph."""
        text = paragraph.text
        
        if not text.strip() or len(text.strip()) < 2:
            return
        
        self.stats["total_segments"] += 1
        
        # Clean inline table content if malformed
        text = self.clean_inline_table(text)
        
        # Translate
        translated = self.translate_text(text)
        
        # Update paragraph runs
        for run in paragraph.runs:
            run.text = ""
        
        if paragraph.runs:
            paragraph.runs[0].text = translated
        else:
            paragraph.add_run(translated)
    
    def process_table(self, table) -> None:
        """Process and translate table cells."""
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    self.process_paragraph(paragraph)
    
    def process_document(self, input_path: str, output_path: str = None) -> Dict:
        """
        Process and translate entire document.
        Preserves structure and validates consistency.
        """
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_Translated_DE_v2{ext}"
        
        print("\n" + "="*70)
        print("[DOCUMENT] PROCESSING PHARMACEUTICAL REGULATORY DOCUMENT")
        print("="*70)
        print(f"Input:  {input_path}")
        print(f"Output: {output_path}")
        
        if not os.path.exists(input_path):
            print(f"[ERROR] Document not found: {input_path}")
            return {}
        
        # Load document
        print("\n[LOAD] Loading document...")
        doc = Document(input_path)
        
        # Process blocks
        print("[PROCESS] Translating content...")
        block_count = 0
        
        for block in self.iter_block_items(doc):
            try:
                from docx.text.paragraph import Paragraph
                from docx.table import Table
                
                if isinstance(block, Paragraph):
                    self.process_paragraph(block)
                    block_count += 1
                
                elif isinstance(block, Table):
                    self.process_table(block)
                    block_count += 1
            
            except Exception as e:
                print(f"[WARNING] Error processing block: {str(e)[:60]}")
        
        # Save document
        print(f"\n[SAVE] Saving translated document...")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        doc.save(output_path)
        
        # Check consistency
        consistency_issues = self._check_consistency()
        
        # Generate report
        report = self._generate_report(input_path, output_path, consistency_issues)
        
        print("\n" + "="*70)
        print("[OK] DOCUMENT PROCESSING COMPLETE")
        print("="*70)
        print(f"Blocks processed: {block_count}")
        print(f"Total segments: {self.stats['total_segments']}")
        print(f"Successful translations: {self.stats['successful_translations']}")
        print(f"Failed translations: {self.stats['failed_translations']}")
        if consistency_issues:
            print(f"Consistency issues found: {len(consistency_issues)}")
        print("="*70 + "\n")
        
        return report
    
    def _check_consistency(self) -> List[Dict]:
        """Check translation consistency across document."""
        issues = []
        
        for source_term, translations in self.translation_log.items():
            unique_translations = set(translations)
            
            if len(unique_translations) > 1:
                issues.append({
                    "source_term": source_term,
                    "translations": list(unique_translations),
                    "occurrences": len(translations)
                })
        
        return issues
    
    def _generate_report(self, input_path: str, output_path: str, 
                        consistency_issues: List[Dict]) -> Dict:
        """Generate processing report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "input_document": input_path,
            "output_document": output_path,
            "model_config": {
                "base_model": self.config["model"]["base_model"],
                "adapter": self.config["paths"]["adapter_final"]
            },
            "processing_stats": self.stats,
            "consistency_issues": consistency_issues,
            "quality_thresholds": {
                "bleu_minimum": self.config["validation"]["bleu_threshold"],
                "glossary_match_minimum": self.config["validation"]["glossary_match_threshold"]
            }
        }
        
        report_path = output_path.replace(
            output_path.split(".")[-1],
            "report.json"
        )
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"[REPORT] Report saved: {report_path}")
        
        return report


if __name__ == "__main__":
    import sys
    
    config_path = "config.yaml"
    
    if len(sys.argv) > 1:
        input_doc = sys.argv[1]
    else:
        input_doc = "xarelto_first_3_pages.docx"
    
    processor = ImprovedDocumentProcessor(config_path=config_path)
    processor.load_model()
    report = processor.process_document(input_doc)
    
    print("\n[SUCCESS] Processing complete!")
