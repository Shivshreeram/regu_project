"""
Glossary validation and post-processing module.
Ensures translation consistency and regulatory compliance.
"""

import json
import re
import os
from typing import Dict, List, Tuple
from collections import defaultdict
import yaml

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class GlossaryValidator:
    """Validates translations against pharmaceutical glossary."""
    
    def __init__(self, glossary_path: str = None, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        
        if glossary_path is None:
            glossary_path = self.config["data"]["glossary_output"]
        
        self.glossary_path = glossary_path
        self.glossary = self._load_glossary()
        self.term_map = self._build_term_map()
    
    def _load_glossary(self) -> Dict:
        """Load glossary from JSON."""
        if not os.path.exists(self.glossary_path):
            print(f"⚠️  Glossary not found: {self.glossary_path}")
            return {}
        
        with open(self.glossary_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _build_term_map(self) -> Dict[str, List[str]]:
        """Build lowercase term to translations mapping."""
        term_map = defaultdict(list)
        
        for en_term, data in self.glossary.items():
            original_en = data.get("original_en", en_term)
            translations = data.get("translations", [])
            
            # Add all variants
            term_map[en_term.lower()].extend(translations)
            term_map[original_en.lower()].extend(translations)
        
        return term_map
    
    def validate_translation(self, source_text: str, translated_text: str) -> Dict:
        """
        Validate translation against glossary.
        Returns validation results with matches and mismatches.
        """
        results = {
            "source": source_text,
            "translation": translated_text,
            "match_score": 0.0,
            "matched_terms": [],
            "unmatched_terms": [],
            "issues": []
        }
        
        # Extract terms from source (split on word boundaries)
        source_terms = self._extract_terms(source_text)
        target_terms = self._extract_terms(translated_text.lower())
        
        matched = 0
        unmatched = 0
        
        for source_term in source_terms:
            source_key = source_term.lower()
            
            if source_key in self.term_map:
                expected_translations = self.term_map[source_key]
                
                # Check if any expected translation appears in output
                found = False
                for expected in expected_translations:
                    if expected.lower() in translated_text.lower():
                        results["matched_terms"].append({
                            "source": source_term,
                            "expected": expected,
                            "found": True
                        })
                        matched += 1
                        found = True
                        break
                
                if not found:
                    results["unmatched_terms"].append({
                        "source": source_term,
                        "expected_options": expected_translations
                    })
                    results["issues"].append(
                        f"Glossary term '{source_term}' not properly translated"
                    )
                    unmatched += 1
        
        # Calculate match score
        total_glossary_terms = matched + unmatched
        if total_glossary_terms > 0:
            results["match_score"] = matched / total_glossary_terms
        
        return results
    
    def _extract_terms(self, text: str, min_length: int = 3) -> List[str]:
        """Extract meaningful terms from text."""
        # Remove punctuation but keep words
        words = re.findall(r'\b[a-zA-Zäöüß]+\b', text)
        
        # Filter by minimum length and remove common words
        common_words = {'the', 'and', 'or', 'is', 'of', 'in', 'to', 'for', 'a', 'an',
                       'der', 'die', 'das', 'und', 'oder', 'ist', 'von', 'in', 'zu', 'für'}
        
        terms = [w for w in words if len(w) >= min_length and w.lower() not in common_words]
        return terms
    
    def validate_consistency(self, text_segment: str, term_translations: Dict) -> Dict:
        """
        Ensure consistent translation of terms within a segment.
        term_translations: {english_term: [list of german translations used]}
        """
        consistency_results = {
            "issues": [],
            "inconsistent_terms": []
        }
        
        for en_term, de_translations in term_translations.items():
            if len(set(de_translations)) > 1:
                consistency_results["inconsistent_terms"].append({
                    "term": en_term,
                    "variations": list(set(de_translations)),
                    "count": len(de_translations)
                })
                consistency_results["issues"].append(
                    f"Term '{en_term}' translated as {set(de_translations)} (inconsistent)"
                )
        
        return consistency_results
    
    def fix_capitalization(self, text: str) -> str:
        """Fix capitalization for regulatory terms."""
        # Regulatory sections should be uppercase
        regulatory_patterns = [
            (r'summary of product characteristics', 'SUMMARY OF PRODUCT CHARACTERISTICS'),
            (r'qualitative and quantitative composition', 'QUALITATIVE AND QUANTITATIVE COMPOSITION'),
            (r'pharmaceutical form', 'Pharmaceutical Form'),
            (r'active ingredient', 'Active Ingredient')
        ]
        
        result = text
        for pattern, replacement in regulatory_patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    def apply_glossary_fixes(self, translated_text: str) -> Tuple[str, List[str]]:
        """
        Apply glossary fixes to translated text.
        Returns fixed text and list of applied fixes.
        """
        fixed_text = translated_text
        applied_fixes = []
        
        # Case-insensitive replacement of known terms
        for en_term, de_options in self.term_map.items():
            if de_options:
                # Use first option as canonical
                canonical_de = de_options[0]
                
                # Find all case-insensitive occurrences
                pattern = re.compile(re.escape(en_term), re.IGNORECASE)
                if pattern.search(fixed_text):
                    fixed_text = pattern.sub(canonical_de, fixed_text)
                    applied_fixes.append(f"'{en_term}' → '{canonical_de}'")
        
        return fixed_text, applied_fixes


class PostProcessingPipeline:
    """Post-processing pipeline for translations."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.validator = GlossaryValidator(config_path=config_path)
    
    def process_translation(self, source_text: str, raw_translation: str) -> Dict:
        """Apply full post-processing pipeline."""
        results = {
            "source": source_text,
            "raw_translation": raw_translation,
            "steps_applied": [],
            "final_translation": raw_translation
        }
        
        current_text = raw_translation
        
        # Step 1: Validate against glossary
        if self.config["document_processing"]["apply_glossary_validation"]:
            validation = self.validator.validate_translation(source_text, current_text)
            results["glossary_validation"] = validation
            results["steps_applied"].append("glossary_validation")
        
        # Step 2: Fix capitalization
        if self.config["document_processing"]["fix_capitalization"]:
            current_text = self.validator.fix_capitalization(current_text)
            results["steps_applied"].append("capitalization_fix")
        
        # Step 3: Apply glossary fixes
        if self.config["document_processing"]["apply_glossary_validation"]:
            fixed_text, fixes = self.validator.apply_glossary_fixes(current_text)
            current_text = fixed_text
            results["applied_glossary_fixes"] = fixes
            results["steps_applied"].append("glossary_fixes")
        
        results["final_translation"] = current_text
        return results
    
    def validate_document_consistency(self, document_terms_log: Dict[str, List[str]]) -> Dict:
        """
        Validate consistency across entire document.
        document_terms_log: {english_term: [list of german translations used]}
        """
        return self.validator.validate_consistency("", document_terms_log)


def create_quality_report(validation_results: List[Dict], output_path: str) -> str:
    """Create quality report from validation results."""
    
    report = {
        "total_translations": len(validation_results),
        "average_match_score": np.mean([r.get("match_score", 0) for r in validation_results]),
        "translations_with_issues": len([r for r in validation_results if r["issues"]]),
        "all_issues": []
    }
    
    for result in validation_results:
        if result["issues"]:
            report["all_issues"].extend(result["issues"])
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    
    return output_path


if __name__ == "__main__":
    import numpy as np
    
    print("🔍 Glossary Validation and Post-Processing Module")
    print("="*70)
    
    validator = GlossaryValidator()
    
    # Test validation
    test_source = "The vial should be stored in the original package."
    test_translation = "Das Fläschchen sollte im originalpaket gelagert werden."
    
    result = validator.validate_translation(test_source, test_translation)
    print("\nValidation Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Test post-processing
    pipeline = PostProcessingPipeline()
    processed = pipeline.process_translation(test_source, test_translation)
    print("\nPost-Processing Result:")
    print(json.dumps(processed, indent=2, ensure_ascii=False))
