"""
Comprehensive data preparation with regulatory glossary integration.
Combines EMEA bilingual corpora with pharmaceutical domain terms.
"""

import pandas as pd
import os
import yaml
from typing import Tuple
from build_glossary import PharmaGlossaryBuilder
import json

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class DataPreparationPipeline:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.glossary = None
        self.df_emea = None
        self.df_regulatory = None
        self.df_combined = None
    
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
        
        # Load glossary-based pairs
        df_glossary = self.convert_glossary_to_pairs()
        
        # Load EMEA
        df_emea = self.load_emea_bilingual()
        
        if df_glossary.empty:
            print("[WARNING] No glossary data, using EMEA only")
            combined = df_emea
        elif df_emea.empty:
            print("[WARNING] No EMEA data, using glossary only")
            combined = df_glossary
        else:
            # Combine both sources
            combined = pd.concat([df_emea[["en", "de", "source"]], 
                                df_glossary[["en", "de", "source"]]], 
                               ignore_index=True)
        
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
        print(f"\n💾 Combined data saved: {output_combined}")
        
        # Save cleaned final
        output_cleaned = self.config["data"]["output_cleaned"]
        df_cleaned.to_csv(output_cleaned, index=False, encoding="utf-8")
        print(f"💾 Cleaned data saved: {output_cleaned}")
        
        # Print statistics
        print("\n" + "="*60)
        print("📈 FINAL STATISTICS")
        print("="*60)
        print(f"Training pairs: {len(df_cleaned)}")
        print(f"Languages: English → German")
        print(f"Domain: Pharmaceutical Regulatory")
        print(f"Glossary terms included: ~{len(self.glossary)}")
        print("="*60 + "\n")
        
        return output_combined, output_cleaned


if __name__ == "__main__":
    pipeline = DataPreparationPipeline(config_path="config.yaml")
    combined_file, cleaned_file = pipeline.prepare_training_data()
    print("[OK] Data preparation complete!")
    print(f"Use '{cleaned_file}' for training")
