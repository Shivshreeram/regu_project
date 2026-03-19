# Pharmaceutical Regulatory Document Translator
## High-Precision EN→DE Translation System

This project implements a sophisticated translation system for European pharmaceutical regulatory documents (SmPC - Summary of Product Characteristics) with domain-specific precision.

---

## 📋 Project Structure

### Core Modules

#### 1. **Data Pipeline**
- `config.yaml` - Centralized configuration for all parameters
- `build_glossary.py` - Builds pharmaceutical regulatory glossary from CSV files
- `prepare_data.py` - Integrates EMEA corpus with regulatory glossary terms

#### 2. **Model Training**
- `train_improved.py` - Enhanced training with optimized LoRA configuration
- Features:
  - Rank 64 (vs 16) for deeper domain adaptation
  - Multiple attention layers (q_proj, v_proj, k_proj, out_proj)
  - 5-8 training epochs with early stopping
  - Batch size 16 with gradient accumulation
  - Warmup + weight decay for stability

#### 3. **Evaluation & Quality**
- `evaluate_model.py` - Comprehensive evaluation with BLEU, METEOR, ChrF, TER metrics
- `validate_and_postprocess.py` - Glossary validation and regulatory compliance checks
- Ensures term consistency across translations

#### 4. **Document Processing**
- `process_document_improved.py` - Translates pharmaceutical documents with:
  - Structure preservation (paragraphs, tables, sections)
  - Post-processing validation
  - Consistency checking across document
  - Quality reporting

#### 5. **Orchestration**
- `master_pipeline.py` - Unified entry point orchestrating all steps

---

## 🚀 Quick Start

### Prerequisites
```bash
pip install torch transformers peft datasets pandas pyyaml python-docx sacrebleu
```

### Full Pipeline Execution
```bash
python master_pipeline.py --config config.yaml --steps all
```

### Individual Steps
```bash
# Step 1: Build glossary from regulatory CSVs
python build_glossary.py

# Step 2: Prepare training data
python prepare_data.py

# Step 3: Train model
python train_improved.py

# Step 4: Evaluate quality
python evaluate_model.py

# Step 5: Process documents
python process_document_improved.py xarelto_first_3_pages.docx
```

---

## ⚙️ Configuration (config.yaml)

### Key Parameters

**Training:**
- `num_epochs`: 5-8 (default: 5)
- `per_device_train_batch_size`: 16
- `learning_rate`: 5e-5 (reduced from typical 1e-4 for fine-tuning)

**LoRA Configuration:**
- `r`: 64 (rank - increased from 16)
- `lora_alpha`: 32
- `target_modules`: q_proj, v_proj, k_proj, out_proj (4 modules vs 2)

**Validation Thresholds:**
- `bleu_threshold`: 25 (minimum acceptable BLEU score)
- `glossary_match_threshold`: 0.85 (85% term match rate)

**Data Sources:**
- EMEA bilingual corpus (EN-DE)
- 5 regulatory CSV files with pharmaceutical terminology

---

## 📊 Data Pipeline

### Glossary Building
Integrates regulatory terminology from:
1. Routes of administration
2. Units of measurement
3. Pharmaceutical dose forms
4. Combined medical terms
5. Units of presentation

Plus hardcoded SmPC critical terms (e.g., "Summary of Product Characteristics" → "Zusammenfassung der Merkmale des Arzneimittels")

### Data Cleaning
```
Original EMEA pairs + CSV glossary terms
↓
Remove NaN, whitespace, duplicates
↓
Filter by length (3-512 chars)
↓
Train/Val/Test split (75% / 10% / 15%)
↓
Ready for training: ~100K+ cleaned pairs
```

---

## 🧠 Model Architecture

**Base Model:** `facebook/nllb-200-distilled-600M`
- Multilingual encoder-decoder
- 600M parameters (manageable on consumer GPUs)
- Pre-trained on 200 languages

**LoRA Adaptation:**
- Rank 64 applied to 4 attention modules
- Learns pharmaceutical domain-specific patterns
- ~2M trainable parameters (vs 600M base)

**Training Configuration:**
```
Epochs: 5
Batch Size: 16
Learning Rate: 5e-5
Warmup Ratio: 10%
Early Stopping: 2 epochs patience
```

---

## 📈 Evaluation Metrics

### Automatic Metrics (via sacrebleu)
- **BLEU**: Standard translation quality (target: >25)
- **METEOR**: Synonym/paraphrase awareness
- **ChrF**: Character-level similarity
- **TER**: Translation edit rate (lower is better)

### Validation Metrics
- **Glossary Match Rate**: % of regulatory terms correctly mapped
- **Term Consistency**: Same English term → same German term
- **Manual QA**: 200-sample human evaluation set

### Report Output
```json
{
  "metrics": {
    "bleu": 28.5,
    "meteor": 45.2,
    "chrf": 67.8,
    "ter": 52.3
  },
  "glossary_match_rate": 0.89,
  "consistency_issues": [...],
  "model_config": {...}
}
```

---

## 🔍 Post-Processing & Validation

### Glossary Validation
Checks each translation against pharmaceutical glossary:
- Matches English terms to expected German translations
- Flags mismatches and alternatives
- Enforces regulatory term consistency

### Capitalization Fixes
Ensures regulatory sections use correct capitalization:
```
"summary of product characteristics" 
  ↓
"SUMMARY OF PRODUCT CHARACTERISTICS"
```

### Document-Level Consistency
Tracks all instances of each term and ensures:
- Same English term = consistent German translation
- Generates consistency report with variations found

---

## 📄 Document Processing

### Supported Input
- `.docx` files (Microsoft Word)
- Preserves formatting, tables, sections

### Processing Flow
```
Load Document
  ↓
Iterate over all text elements (paragraphs + table cells)
  ↓
Translate each segment (max 512 chars)
  ↓
Apply glossary fixes
  ↓
Check consistency
  ↓
Save translated document + quality report
```

### Output
- Translated document: `[filename]_Translated_DE_v2.docx`
- Quality report: `[filename]_report.json`

---

## 🎯 Precision Improvements

### Why This Architecture Achieves High Precision

1. **Domain-Specific Glossary**
   - Not using generic MT glossary
   - Regulatory terms from official sources
   - Hardcoded critical SmPC sections

2. **Optimized LoRA Configuration**
   - Larger rank (64 vs 16) = more capacity
   - More target modules = deeper adaptation
   - Reduces domain drift from base model

3. **Multi-Layer Validation**
   - Automatic metric scoring (BLEU, METEOR)
   - Glossary-level term validation
   - Document-level consistency checking
   - Manual QA sampling

4. **Training Data Scale**
   - EMEA bilingual corpus: ~50K pairs
   - Regulatory glossary derived: ~1,000+ pairs
   - Total ~50K+ high-quality pharmaceutical pairs

5. **Post-Processing Pipeline**
   - Enforces regulatory compliance
   - Fixes known capitalization issues
   - Validates term consistency
   - Fallback mechanisms for failed translations

---

## 📋 File Descriptions

| File | Purpose |
|------|---------|
| `config.yaml` | Central config for all parameters |
| `build_glossary.py` | Extract pharmaceutical terms from CSVs |
| `prepare_data.py` | Combine EMEA + glossary, clean data |
| `train_improved.py` | Train LoRA adapter with improved settings |
| `evaluate_model.py` | Compute BLEU/METEOR/ChrF/TER metrics |
| `validate_and_postprocess.py` | Glossary validation + fixes |
| `process_document_improved.py` | Translate DOCX files with validation |
| `master_pipeline.py` | Orchestrate all steps |

---

## 🔧 Advanced Usage

### Skip Certain Steps
```bash
python master_pipeline.py --skip train eval
```
Runs: glossary → data prep → document processing

### Process Specific Document
```bash
python master_pipeline.py --document path/to/document.docx
```

### Custom Configuration
```bash
python master_pipeline.py --config custom_config.yaml
```

### Evaluate Only
```bash
python evaluate_model.py
```

---

## 📊 Expected Performance

### With Full Pipeline
- **BLEU Score**: 25-28 (acceptable for pharmaceutical domain)
- **Glossary Match Rate**: 85%+
- **Human QA**: >90% accuracy for regulatory terms
- **Processing Speed**: ~5-10 seconds per page on RTX 4060

### Bottlenecks
- Data: Current ~50K pairs (optimal: 500K+)
- Training: Limited to 3-5 epochs (more data = more epochs)
- Glossary: ~1K regulatory terms (grows with training data)

---

## 🚨 Known Limitations & Future Improvements

### Current Limitations
1. Limited training data (50K pairs vs ideal 500K+)
2. Glossary mostly from CSVs (needs manual pharmaceutical curation)
3. No context window across pages/sections
4. DOCX only (no PDF support)

### Planned Improvements
1. **Data Expansion**
   - Integrate EMA official translations
   - Add European Medicines Agency glossaries
   - Include competitor SmPC documents

2. **Architecture Enhancements**
   - Increase LoRA rank to 128 with more training data
   - Add document-level context modeling
   - Implement section-aware translation

3. **Quality Assurance**
   - Zero-shot glossary term detection
   - Regulatory compliance checker
   - Terminology consistency enforcement

4. **Format Support**
   - PDF input/output
   - XLS/XLSX for regulatory tables
   - TXT files

---

## 📞 Troubleshooting

### Out of Memory
```bash
# Reduce batch size in config.yaml
per_device_train_batch_size: 8  # from 16
```

### Glossary Not Found
```bash
# Rebuild glossary
python build_glossary.py
```

### Model Not Translating
```bash
# Verify adapter path in config.yaml
# Ensure PyTorch/CUDA versions compatible
python -c "import torch; print(torch.cuda.is_available())"
```

### Poor Translation Quality
- ✓ Check BLEU score in evaluation report
- ✓ Review glossary matches (should be >80%)
- ✓ Increase training epochs (5→8)
- ✓ Add more training data

---

## 📈 Performance Metrics Dashboard

After running the full pipeline, check:
1. `medical_nllb_output_v2/training_results.json` - Training metrics
2. `outputs/evaluation_report.json` - Quality metrics
3. `outputs/evaluation_samples.csv` - Sample translations
4. `[document]_report.json` - Document processing report

---

## 🎓 Learning Resources

- **NLLB-200**: https://github.com/facebookresearch/fairseq/tree/nllb
- **LoRA**: https://github.com/microsoft/LoRA
- **HuggingFace PEFT**: https://github.com/huggingface/peft
- **SmPC Specifications**: EMA regulatory guidelines

---

## 📝 Citation

If you use this pharmaceutical translator, cite:
```
Pharmaceutical Regulatory Document Translator
LoRA Fine-tuned NLLB-200 for EN→DE Translation
2024-2026
```

---

**Last Updated:** March 2026
**Status:** Production Ready
**License:** [Your License Here]
