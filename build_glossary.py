"""
Build pharmaceutical regulatory glossary from CSV files.
Integrates domain terminology for high-precision translation validation.
"""

import pandas as pd
import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple

class PharmaGlossaryBuilder:
    def __init__(self, output_path: str = "pharma_glossary.json"):
        self.glossary = defaultdict(lambda: {"translations": [], "frequency": 0, "category": ""})
        self.frequency_map = defaultdict(int)
        self.output_path = output_path
        self.category_mapping = {
            "100000073345_routes_of_admin": "Route of Administration",
            "100000110633_units_of_mesu": "Unit of Measurement",
            "200000000004_pharma_dose_form": "Pharmaceutical Dose Form",
            "200000000007_combined_terms": "Combined / General Terms",
            "200000000014_units_of_presen": "Unit of Presentation"
        }
    
    def load_csv_pharma_terms(self, csv_files: List[str]) -> None:
        """Load regulatory terms from CSV files.

        The source data is not organized as a direct en/de column pair. Instead,
        each record is identified by a `Term ID` and contains one or more language
        rows (for example `en`, `de`, `es`, `pt`, etc.) in the `Language` column.
        This method groups the rows by `Term ID` and pairs the English and German
        term names found in those grouped records.
        """
        print("[LOAD] Loading pharmaceutical regulatory terminology...")
        
        for csv_file in csv_files:
            if not os.path.exists(csv_file):
                print(f"[WARNING] Skipping {csv_file} - not found")
                continue
            
            try:
                df = pd.read_csv(csv_file, low_memory=False)
                category = None
                
                # Identify category from filename
                for key, cat in self.category_mapping.items():
                    if key in csv_file:
                        category = cat
                        break
                
                category = category or "Uncategorized"

                # Support both the current multilingual schema and any legacy
                # `en`/`de` column layout that may exist in older data files.
                language_col = next((col for col in df.columns if str(col).strip().lower() == "language"), None)
                term_id_col = next((col for col in df.columns if str(col).strip().lower() == "term id"), None)
                term_name_col = next((col for col in df.columns if str(col).strip().lower() == "term name"), None)

                legacy_en_col = None
                legacy_de_col = None
                
                if language_col is None or term_id_col is None or term_name_col is None:
                    for col in df.columns:
                        if 'en' in col.lower() or 'english' in col.lower() or 'eng' in col.lower():
                            legacy_en_col = col
                            break
                    
                    for col in df.columns:
                        if 'de' in col.lower() or 'deutsch' in col.lower() or 'ger' in col.lower():
                            legacy_de_col = col
                            break

                    if legacy_en_col is None or legacy_de_col is None:
                        print(
                            f"[WARNING] {csv_file}: Could not find supported en/de columns. "
                            f"Columns: {df.columns.tolist()}"
                        )
                        continue

                loaded_term_pairs = 0

                if language_col and term_id_col and term_name_col:
                    df = df.copy()
                    df[language_col] = df[language_col].astype(str).str.strip().str.lower()
                    df[term_name_col] = df[term_name_col].astype(str).str.strip()
                    df[term_id_col] = df[term_id_col].astype(str).str.strip()

                    term_groups = []
                    for term_id, group in df.groupby(term_id_col):
                        if not term_id or term_id == "nan":
                            continue

                        en_terms = group[group[language_col] == "en"][term_name_col].dropna().astype(str)
                        de_terms = group[group[language_col] == "de"][term_name_col].dropna().astype(str)

                        if en_terms.empty or de_terms.empty:
                            continue

                        en_term = en_terms.iloc[0]
                        de_term = de_terms.iloc[0]

                        if len(en_term) > 2 and len(de_term) > 2:
                            en_key = en_term.lower()
                            if de_term not in self.glossary[en_key]["translations"]:
                                self.glossary[en_key]["translations"].append(de_term)
                                self.glossary[en_key]["original_en"] = en_term

                            self.glossary[en_key]["frequency"] += 1
                            self.glossary[en_key]["category"] = category
                            self.frequency_map[en_key] += 1
                            loaded_term_pairs += 1

                    print(f"[OK] {csv_file}: Loaded {loaded_term_pairs} English/German term pairs")
                    continue

                # Legacy fallback for older column layouts
                for idx, row in df.iterrows():
                    en_term = str(row[legacy_en_col]).strip()
                    de_term = str(row[legacy_de_col]).strip()
                    
                    if len(en_term) > 2 and len(de_term) > 2 and en_term != "nan" and de_term != "nan":
                        en_key = en_term.lower()
                        
                        if de_term not in self.glossary[en_key]["translations"]:
                            self.glossary[en_key]["translations"].append(de_term)
                            self.glossary[en_key]["original_en"] = en_term
                        
                        self.glossary[en_key]["frequency"] += 1
                        self.glossary[en_key]["category"] = category
                        self.frequency_map[en_key] += 1
                
                print(f"[OK] {csv_file}: Loaded {len(df)} legacy terms")
            
            except Exception as e:
                print(f"[ERROR] Error loading {csv_file}: {e}")
    
    def add_hardcoded_regulatory_terms(self) -> None:
        """Add critical SmPC (Summary of Product Characteristics) terms."""
        print("[ADD] Adding hardcoded SmPC regulatory standards...")
        
        smpc_terms = {
            "Summary of Product Characteristics".lower(): {
                "translations": ["Zusammenfassung der Merkmale des Arzneimittels"],
                "original_en": "Summary of Product Characteristics",
                "frequency": 1000,
                "category": "SmPC Section"
            },
            "QUALITATIVE AND QUANTITATIVE COMPOSITION".lower(): {
                "translations": ["QUALITATIVE UND QUANTITATIVE ZUSAMMENSETZUNG"],
                "original_en": "QUALITATIVE AND QUANTITATIVE COMPOSITION",
                "frequency": 1000,
                "category": "SmPC Section"
            },
            "Pharmaceutical Form".lower(): {
                "translations": ["Darreichungsform"],
                "original_en": "Pharmaceutical Form",
                "frequency": 1000,
                "category": "SmPC Section"
            },
            "Active Ingredient".lower(): {
                "translations": ["Wirkstoff", "Wirkstoffe"],
                "original_en": "Active Ingredient",
                "frequency": 1000,
                "category": "SmPC Section"
            },
            "Excipient".lower(): {
                "translations": ["Sonstiger Bestandteil", "Sonstige Bestandteile"],
                "original_en": "Excipient",
                "frequency": 1000,
                "category": "SmPC Section"
            },
            "Special Warnings and Precautions for Use".lower(): {
                "translations": ["Besondere Warnhinweise und Vorsichtsmaßnahmen für die Anwendung"],
                "original_en": "Special Warnings and Precautions for Use",
                "frequency": 1000,
                "category": "SmPC Section"
            },
            "Pharmacokinetic Properties".lower(): {
                "translations": ["Pharmakokinetische Eigenschaften"],
                "original_en": "Pharmacokinetic Properties",
                "frequency": 1000,
                "category": "SmPC Section"
            },
            "Shelf Life".lower(): {
                "translations": ["Haltbarkeit"],
                "original_en": "Shelf Life",
                "frequency": 1000,
                "category": "SmPC Section"
            },
            "Storage Conditions".lower(): {
                "translations": ["Lagerbedingungen"],
                "original_en": "Storage Conditions",
                "frequency": 1000,
                "category": "SmPC Section"
            },
            "Haemorrhagic Risk".lower(): {
                "translations": ["Blutungsrisiko"],
                "original_en": "Haemorrhagic Risk",
                "frequency": 500,
                "category": "Medical Term"
            }
        }
        
        for en_key, data in smpc_terms.items():
            self.glossary[en_key] = data
        
        print(f"[OK] Added {len(smpc_terms)} SmPC critical terms")
    
    def build_glossary(self, csv_files: List[str]) -> Dict:
        """Build complete glossary from all sources."""
        self.load_csv_pharma_terms(csv_files)
        self.add_hardcoded_regulatory_terms()
        
        return self.glossary
    
    def save_glossary(self, output_format: str = "json") -> str:
        """Save glossary to file."""
        print(f"[SAVE] Saving glossary to {self.output_path}...")
        
        # Convert defaultdict to regular dict for JSON serialization
        glossary_dict = {}
        for key, value in self.glossary.items():
            glossary_dict[key] = dict(value)
            glossary_dict[key]["translations"] = list(glossary_dict[key]["translations"])
        
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(glossary_dict, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] Glossary saved: {len(self.glossary)} terms")
        return self.output_path
    
    def get_statistics(self) -> Dict:
        """Get glossary statistics."""
        stats = {
            "total_terms": len(self.glossary),
            "categories": defaultdict(int),
            "avg_translations_per_term": 0,
            "total_translations": 0,
            "high_frequency_terms": []
        }
        
        for term, data in self.glossary.items():
            category = data.get("category", "Unknown")
            stats["categories"][category] += 1
            stats["total_translations"] += len(data["translations"])
        
        if stats["total_terms"] > 0:
            stats["avg_translations_per_term"] = stats["total_translations"] / stats["total_terms"]
        
        # Top 10 frequent terms
        sorted_terms = sorted(self.frequency_map.items(), key=lambda x: x[1], reverse=True)
        stats["high_frequency_terms"] = sorted_terms[:10]
        
        return stats
    
    def print_statistics(self) -> None:
        """Print glossary statistics."""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("[STATS] GLOSSARY STATISTICS")
        print("="*60)
        print(f"Total Terms: {stats['total_terms']}")
        print(f"Total Translations: {stats['total_translations']}")
        print(f"Avg Translations/Term: {stats['avg_translations_per_term']:.2f}")
        print(f"\nBy Category:")
        for category, count in sorted(stats['categories'].items()):
            print(f"  {category}: {count} terms")
        print(f"\nTop 10 Frequent Terms:")
        for term, freq in stats['high_frequency_terms']:
            print(f"  '{term}': {freq} occurrences")
        print("="*60 + "\n")


if __name__ == "__main__":
    # Configuration
    csv_files = [
        "100000073345_routes_of_admin.csv",
        "100000110633_units_of_mesu.csv",
        "200000000004_pharma_dose_form.csv",
        "200000000007_combined_terms.csv",
        "200000000014_units_of_presen.csv"
    ]
    
    # Build glossary
    builder = PharmaGlossaryBuilder(output_path="pharma_glossary.json")
    builder.build_glossary(csv_files)
    builder.print_statistics()
    builder.save_glossary()
    
    print("[SUCCESS] Glossary building complete!")
