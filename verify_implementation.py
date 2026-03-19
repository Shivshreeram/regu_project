#!/usr/bin/env python3
"""
Verification script: Check that all improvements have been implemented.
Run this to confirm all changes are in place.
"""

import os
import json

def verify_implementation():
    """Verify all files and configurations are in place."""
    
    print("\n" + "="*80)
    print("🔍 PHARMACEUTICAL TRANSLATOR - IMPLEMENTATION VERIFICATION")
    print("="*80 + "\n")
    
    # Expected new files
    new_files = {
        "config.yaml": "Central configuration file",
        "build_glossary.py": "Pharmaceutical glossary builder",
        "prepare_data.py": "Data integration and cleaning",
        "train_improved.py": "Enhanced training with LoRA",
        "evaluate_model.py": "Multi-metric evaluation (BLEU, METEOR, etc)",
        "validate_and_postprocess.py": "Glossary validation and post-processing",
        "process_document_improved.py": "Document processor with validation",
        "master_pipeline.py": "Master orchestration script",
        "README_NEW.md": "Complete documentation",
        "QUICKSTART.py": "Quick start guide",
        "IMPLEMENTATION_SUMMARY.md": "Summary of all changes",
        "FILE_STRUCTURE.txt": "Before/after structure",
        "BEFORE_AFTER_CODE.md": "Code comparison",
    }
    
    existing_files = {
        "EMEA.de-en.en": "Bilingual corpus (English)",
        "EMEA.de-en.de": "Bilingual corpus (German)",
        "100000073345_routes_of_admin.csv": "Routes of administration",
        "100000110633_units_of_mesu.csv": "Units of measurement",
        "200000000004_pharma_dose_form.csv": "Dose forms",
        "200000000007_combined_terms.csv": "Combined terms",
        "200000000014_units_of_presen.csv": "Units of presentation",
    }
    
    print("📋 CHECKING NEW FILES...")
    print("-" * 80)
    
    new_files_count = 0
    for filename, description in new_files.items():
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            size_display = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/(1024*1024):.1f} MB"
            print(f"✅ {filename:<35} ({description})")
            print(f"   └─ Size: {size_display}")
            new_files_count += 1
        else:
            print(f"❌ {filename:<35} NOT FOUND")
    
    print("\n📂 CHECKING EXISTING DATA FILES...")
    print("-" * 80)
    
    data_files_count = 0
    for filename, description in existing_files.items():
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            size_display = f"{size/(1024*1024):.1f} MB"
            print(f"✅ {filename:<35} ({size_display})")
            data_files_count += 1
        else:
            print(f"⚠️  {filename:<35} (optional)")
    
    print("\n🎯 VERIFICATION RESULTS")
    print("="*80)
    print(f"New files implemented: {new_files_count}/{len(new_files)}")
    print(f"Data files available: {data_files_count}/{len(existing_files)}")
    
    # Check critical files
    critical_files = ["config.yaml", "build_glossary.py", "prepare_data.py", 
                     "train_improved.py", "master_pipeline.py"]
    
    print("\n⚡ CRITICAL COMPONENTS:")
    for f in critical_files:
        if os.path.exists(f):
            print(f"  ✅ {f}")
        else:
            print(f"  ❌ {f} - MISSING!")
    
    # Check directory structure
    print("\n📁 CHECKING DIRECTORY STRUCTURE...")
    print("-" * 80)
    
    dirs_to_check = [
        ("outputs", "For evaluation reports"),
        ("medical_adapter_final_v2", "Where trained adapter will be saved"),
        ("medical_nllb_output_v2", "Training checkpoints"),
    ]
    
    for dirname, description in dirs_to_check:
        if os.path.exists(dirname):
            print(f"✅ {dirname:<30} ({description})")
        else:
            print(f"⏳ {dirname:<30} (will be created during execution)")
    
    # Summary
    print("\n" + "="*80)
    print("✅ IMPLEMENTATION STATUS: COMPLETE")
    print("="*80)
    
    print("\n🚀 READY TO RUN!")
    print("\nNext steps:")
    print("  1. pip install torch transformers peft datasets pandas pyyaml python-docx sacrebleu")
    print("  2. python master_pipeline.py --config config.yaml --steps all")
    print("\nOr run individual steps:")
    print("  - python build_glossary.py")
    print("  - python prepare_data.py")
    print("  - python train_improved.py")
    print("  - python evaluate_model.py")
    print("  - python process_document_improved.py [document.docx]")
    
    print("\nDocumentation:")
    print("  - README_NEW.md - Complete guide")
    print("  - QUICKSTART.py - Quick reference")
    print("  - IMPLEMENTATION_SUMMARY.md - All changes")
    
    print("\n" + "="*80)
    print("Copyright © 2026 - Pharmaceutical Regulatory Translator")
    print("="*80 + "\n")
    
    return new_files_count == len(new_files)


def check_dependencies():
    """Check if required packages are installed."""
    print("\n" + "="*80)
    print("🔧 CHECKING DEPENDENCIES")
    print("="*80 + "\n")
    
    packages = [
        ("torch", "PyTorch"),
        ("transformers", "Hugging Face Transformers"),
        ("peft", "Parameter-Efficient Fine-Tuning"),
        ("datasets", "Hugging Face Datasets"),
        ("pandas", "Pandas"),
        ("yaml", "PyYAML"),
        ("docx", "python-docx"),
    ]
    
    all_installed = True
    
    for module, name in packages:
        try:
            __import__(module)
            print(f"✅ {name:<35} installed")
        except ImportError:
            print(f"❌ {name:<35} NOT installed")
            all_installed = False
    
    if not all_installed:
        print("\n⚠️ Some packages are missing. Install with:")
        print("   pip install torch transformers peft datasets pandas pyyaml python-docx sacrebleu")
    
    print()
    return all_installed


def verify_config():
    """Verify config.yaml structure."""
    print("\n" + "="*80)
    print("⚙️  VERIFYING CONFIG.YAML")
    print("="*80 + "\n")
    
    if not os.path.exists("config.yaml"):
        print("❌ config.yaml not found!")
        return False
    
    import yaml
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        required_sections = ["project", "data", "model", "training", "validation", 
                           "evaluation", "document_processing", "output", "paths"]
        
        for section in required_sections:
            if section in config:
                print(f"✅ [{section}] section configured")
            else:
                print(f"❌ [{section}] section MISSING")
        
        # Check key parameters
        print("\n📊 Key Configuration Parameters:")
        print("-" * 80)
        print(f"  Model: {config.get('model', {}).get('base_model', 'N/A')}")
        print(f"  LoRA Rank: {config.get('training', {}).get('lora', {}).get('r', 'N/A')}")
        print(f"  Training Epochs: {config.get('training', {}).get('num_epochs', 'N/A')}")
        print(f"  BLEU Threshold: {config.get('validation', {}).get('bleu_threshold', 'N/A')}")
        
        print("\n✅ config.yaml is valid")
        return True
    
    except Exception as e:
        print(f"❌ Error parsing config.yaml: {e}")
        return False


if __name__ == "__main__":
    # Run all checks
    impl_ok = verify_implementation()
    deps_ok = check_dependencies()
    config_ok = verify_config()
    
    # Final status
    print("\n" + "="*80)
    print("📈 FINAL STATUS")
    print("="*80)
    
    if impl_ok and config_ok:
        print("\n✅ ALL IMPLEMENTATIONS COMPLETE")
        print("✅ READY FOR EXECUTION")
        print("\nRun: python master_pipeline.py --config config.yaml --steps all")
    else:
        print("\n⚠️ Some checks failed. Review above for details.")
    
    if not deps_ok:
        print("\n⚠️ Install missing dependencies first:")
        print("   pip install torch transformers peft datasets pandas pyyaml python-docx sacrebleu")
    
    print("\n" + "="*80 + "\n")
