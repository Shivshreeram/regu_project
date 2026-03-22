"""
Comprehensive data preparation with regulatory glossary integration.
Combines EMEA bilingual corpora with pharmaceutical domain terms.
"""

import os
import re
import json
import random
import numpy as np
import pandas as pd
import yaml
from typing import Tuple, List
from build_glossary import PharmaGlossaryBuilder

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class DataPreparationPipeline:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.seed = self.config["data"].get("random_seed", 42)
        self.set_seed()
        self.glossary = None
        self.df_emea = None
        self.df_regulatory = None
        self.df_combined = None
    
    def set_seed(self):
        """Set deterministic seed for reproducible sampling and text generation."""
        os.environ["PYTHONHASHSEED"] = str(self.seed)
        random.seed(self.seed)
        np.random.seed(self.seed)

    def build_regulatory_glossary(self) -> None:
        """Build pharmaceutical regulatory glossary from CSVs."""
        print("[BUILD] Building regulatory glossary...")
        csv_files = self.config["data"]["regulatory_csvs"]
        
        builder = PharmaGlossaryBuilder(self.config["data"]["glossary_output"])
        builder.build_glossary(csv_files)
        builder.print_statistics()
        builder.save_glossary()
        
        self.glossary = builder.glossary
    
    def convert_glossary_to_pairs(self) -> pd.DataFrame:
        """Convert glossary dictionary to training pairs DataFrame."""
        print("[CONVERT] Converting glossary to training pairs...")
        
        glossary_pairs = []
        
        for en_term, data in self.glossary.items():
            if data["translations"]:
                # Use first translation as primary
                de_term = data["translations"][0]
                original_en = data.get("original_en", en_term)
                
                glossary_pairs.append({
                    "en": original_en,
                    "de": de_term,
                    "source": "glossary",
                    "category": data.get("category", "Unknown")
                })
        
        df_glossary = pd.DataFrame(glossary_pairs)
        print(f"[OK] Converted {len(df_glossary)} glossary entries to training pairs")
        return df_glossary
    
    def load_emea_bilingual(self) -> pd.DataFrame:
        """Load EMEA bilingual corpus."""
        print("\n[LOAD] Loading EMEA bilingual corpus...")
        
        en_file = self.config["data"]["raw_sources"][0]
        de_file = self.config["data"]["raw_sources"][1]
        
        if not (os.path.exists(en_file) and os.path.exists(de_file)):
            print(f"[WARNING] Could not find EMEA files")
            return pd.DataFrame()
        
        try:
            with open(en_file, "r", encoding="utf-8") as f:
                en_sentences = f.read().splitlines()
            
            with open(de_file, "r", encoding="utf-8") as f:
                de_sentences = f.read().splitlines()
            
            df_emea = pd.DataFrame({
                "en": en_sentences,
                "de": de_sentences,
                "source": "emea"
            })
            
            print(f"[OK] Loaded {len(df_emea)} EMEA pairs")
            return df_emea
        
        except Exception as e:
            print(f"[ERROR] Error loading EMEA: {e}")
            return pd.DataFrame()

    def generate_glossary_templates(self, en_term: str, de_term: str, count: int) -> List[dict]:
        """Generate fallback glossary sentence pairs when no corpus context is found."""
        templates = [
            "The patient was given {term}.",
            "Treatment included {term} administered daily.",
            "{term} is used in the treatment of the condition.",
            "Discontinue {term} if adverse effects occur.",
            "The physician prescribed {term} for the patient.",
            "Administration of {term} improved symptoms.",
            "Use {term} with caution in elderly patients.",
            "Monitor the patient while using {term}."
        ]
        selected = templates[:count]
        return [
            {
                "en": template.format(term=en_term),
                "de": template.format(term=de_term),
                "source": "glossary_template",
                "term": en_term
            }
            for template in selected
        ]

    def build_glossary_context_pairs(self) -> pd.DataFrame:
        """Build glossary examples by mining EMEA sentence contexts."""
        print("\n[BUILD] Mining glossary context pairs from EMEA corpus...")
        df_emea = self.load_emea_bilingual()
        if df_emea.empty:
            print("[WARNING] No EMEA corpus available for glossary context mining.")
            return pd.DataFrame()

        en_lines = df_emea["en"].tolist()
        de_lines = df_emea["de"].tolist()
        max_contexts = self.config["data"].get("glossary_max_contexts_per_term", 10)
        fallback_count = self.config["data"].get("glossary_template_count_per_term", 4)

        glossary_context_pairs = []
        missing_context_terms = []

        for en_term, data in self.glossary.items():
            translations = data.get("translations", [])
            if not translations:
                continue
            de_term = translations[0]
            pattern = re.compile(r"\b" + re.escape(en_term) + r"\b", flags=re.IGNORECASE)
            found = 0

            for idx, en_text in enumerate(en_lines):
                if pattern.search(en_text):
                    glossary_context_pairs.append({
                        "en": en_text,
                        "de": de_lines[idx],
                        "source": "glossary_context",
                        "term": en_term
                    })
                    found += 1
                    if found >= max_contexts:
                        break

            if found == 0:
                missing_context_terms.append(en_term)
                glossary_context_pairs.extend(
                    self.generate_glossary_templates(en_term, de_term, fallback_count)
                )

        if not glossary_context_pairs:
            print("[WARNING] No glossary context pairs were generated.")
            return pd.DataFrame()

        df_context = pd.DataFrame(glossary_context_pairs)
        df_context = df_context.drop_duplicates(subset=["en", "de"])

        output_path = self.config["data"].get(
            "glossary_context_pairs_output",
            "glossary_context_pairs.csv"
        )
        df_context.to_csv(output_path, index=False, encoding="utf-8")
        print(f"[SAVE] Glossary context/template pairs saved: {output_path}")
        print(f"[STATS] Total glossary context/template pairs: {len(df_context)}")
        print(f"[STATS] Terms without EMEA context: {len(missing_context_terms)}")

        return df_context
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply comprehensive data cleaning."""
        print("\n[CLEAN] Cleaning data...")
        
        initial_count = len(df)
        config_data = self.config["data"]
        
        # 1. Remove NaN/empty
        df = df.dropna(subset=["en", "de"])
        
        # 2. Convert to string and strip whitespace
        df["en"] = df["en"].astype(str).str.strip()
        df["de"] = df["de"].astype(str).str.strip()
        
        # 3. Remove empty after strip
        df = df[(df["en"] != "") & (df["de"] != "") & (df["en"] != "nan") & (df["de"] != "nan")]
        
        # 4. Filter by length constraints
        min_words = config_data["min_length"]
        max_length = config_data["max_length"]
        
        df["en_words"] = df["en"].str.split().str.len()
        df["de_words"] = df["de"].str.split().str.len()
        
        df = df[(df["en_words"] >= min_words) & (df["de_words"] >= min_words)]
        df = df[(df["en"].str.len() <= max_length) & (df["de"].str.len() <= max_length)]
        
        # 5. Remove duplicates
        if config_data["remove_duplicates"]:
            df = df.drop_duplicates(subset=["en", "de"])
        
        # 6. Remove near-duplicates (>95% similar)
        if config_data["remove_near_duplicates"]:
            df = df.drop_duplicates(subset=["en"], keep="first")
        
        # Clean up helper columns
        df = df.drop(columns=["en_words", "de_words"])
        
        removed = initial_count - len(df)
        print(f"[STATS] Original: {initial_count} pairs")
        print(f"[STATS] Removed: {removed} pairs")
        print(f"[OK] Final: {len(df)} pairs")
        
        return df
    
    def combine_data_sources(self) -> pd.DataFrame:
        """Combine EMEA and glossary-derived data."""
        print("\n[COMBINE] Combining data sources...")
        
        # Load glossary-based context pairs
        df_glossary = self.build_glossary_context_pairs()
        
        # Load EMEA
        df_emea = self.load_emea_bilingual()
        
        if df_emea.empty and df_glossary.empty:
            print("[ERROR] No training data available.")
            return pd.DataFrame()

        if not df_glossary.empty and not df_emea.empty:
            oversample_pct = self.config["data"].get("glossary_context_oversample_pct", 0.10)
            target_glossary_count = int(len(df_emea) * oversample_pct)

            if len(df_glossary) > target_glossary_count and target_glossary_count > 0:
                df_glossary = df_glossary.sample(
                    n=target_glossary_count,
                    random_state=self.seed
                ).reset_index(drop=True)
                print(f"[SAMPLE] Reduced glossary context pairs to {len(df_glossary)} ({oversample_pct*100:.0f}% of EMEA data)")
            else:
                print(f"[SAMPLE] Using {len(df_glossary)} glossary context/template pairs")

        if df_glossary.empty:
            print("[WARNING] No glossary context data, using EMEA only")
            combined = df_emea
        elif df_emea.empty:
            print("[WARNING] No EMEA data, using glossary only")
            combined = df_glossary
        else:
            combined = pd.concat([
                df_emea[["en", "de", "source"]],
                df_glossary[["en", "de", "source"]]
            ], ignore_index=True)

        print(f"[STATS] Combined dataset size: {len(combined)} pairs")
        return combined
    
    def prepare_training_data(self) -> Tuple[str, str]:
        """Execute full data preparation pipeline."""
        print("="*60)
        print("[START] PHARMACEUTICAL DATA PREPARATION PIPELINE")
        print("="*60)
        
        # Build glossary
        self.build_regulatory_glossary()
        
        # Combine sources
        df_combined = self.combine_data_sources()
        
        # Clean
        df_cleaned = self.clean_data(df_combined)
        
        # Save raw combined (before splitting)
        output_combined = self.config["data"]["output_training"]
        df_combined.to_csv(output_combined, index=False, encoding="utf-8")
        print(f"\n[SAVE] Combined data saved: {output_combined}")
        
        # Save cleaned final
        output_cleaned = self.config["data"]["output_cleaned"]
        df_cleaned.to_csv(output_cleaned, index=False, encoding="utf-8")
        print(f"[SAVE] Cleaned data saved: {output_cleaned}")
        
        # Print statistics
        print("\n" + "="*60)
        print("[STATS] FINAL STATISTICS")
        print("="*60)
        print(f"Training pairs: {len(df_cleaned)}")
        print(f"Languages: English -> German")
        print(f"Domain: Pharmaceutical Regulatory")
        print(f"Glossary terms included: ~{len(self.glossary)}")
        print("="*60 + "\n")
        
        return output_combined, output_cleaned


if __name__ == "__main__":
    pipeline = DataPreparationPipeline(config_path="config.yaml")
    combined_file, cleaned_file = pipeline.prepare_training_data()
    print("[OK] Data preparation complete!")
    print(f"Use '{cleaned_file}' for training")
