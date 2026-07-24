# Pharmaceutical Regulatory Document Translator

This repository contains a config-driven English-to-German pharmaceutical translation workflow built around Meta's `facebook/nllb-200-distilled-600M` model with a LoRA adapter for regulatory document translation.

The current codebase is organized around these scripts:

- `build_glossary.py` builds the domain glossary from the provided CSV terminology sources.
- `prepare_data.py` combines the EMEA bilingual corpus with glossary context/template pairs and writes the cleaned training dataset.
- `train_improved.py` loads the base NLLB model, adds LoRA adapters, and trains with the settings in `config.yaml`.
- `evaluate_model.py` loads the adapter from `medical_adapter_final` and writes evaluation metrics and sample translations to `outputs/`.
- `process_document_improved.py` loads the same adapter, translates `.docx` content, preserves structure, and writes a translated document plus a JSON report.
- `master_pipeline.py` is the orchestration entry point for the full workflow.

## Current workflow

The scripts in this repository are meant to be run in this order:

1. Build glossary
2. Prepare clean training data
3. Train or continue training the LoRA adapter
4. Evaluate the model
5. Translate a Word document

## Environment setup

On Windows, the expected workflow is:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1

pip install torch transformers peft datasets pandas pyyaml python-docx sacrebleu
```

If the virtual environment is already active, the scripts can be launched directly with:

```powershell
.\venv\Scripts\python.exe <script_name>.py
```

## Quick start

### 1. Prepare the data

```powershell
.\venv\Scripts\python.exe master_pipeline.py --steps data-prep
```

This runs the glossary and data preparation steps via `build_glossary.py` and `prepare_data.py`.

### 2. Train the adapter

```powershell
.\venv\Scripts\python.exe master_pipeline.py --steps train
```

This calls `train_improved.py` and writes training artifacts to `medical_nllb_output_v2/` and the final adapter to `medical_adapter_final/`.

### 3. Evaluate the model

```powershell
.\venv\Scripts\python.exe master_pipeline.py --steps eval
```

This invokes `evaluate_model.py` and saves output to:

- `outputs/evaluation_report.json`
- `outputs/evaluation_samples.csv`

### 4. Translate a document

```powershell
.\venv\Scripts\python.exe master_pipeline.py --steps process --document xarelto_first_3_pages.docx
```

Or run the processor directly:

```powershell
.\venv\Scripts\python.exe process_document_improved.py xarelto_first_3_pages.docx
```

The document processor writes:

- `xarelto_first_3_pages_Translated_DE_v2.docx`
- `xarelto_first_3_pages_Translated_DE_v2.report.json`

## Full pipeline

The full orchestration command is:

```powershell
.\venv\Scripts\python.exe master_pipeline.py --config config.yaml --steps all
```

The current CLI supports these step selections:

- `all`
- `data-prep`
- `train`
- `eval`
- `process`

You can skip selected stages with:

```powershell
.\venv\Scripts\python.exe master_pipeline.py --skip train eval
```

## Important current paths and artifacts

The actual code expects these files and folders:

- `config.yaml` — central repository configuration
- `EMEA.de-en.en` and `EMEA.de-en.de` — bilingual source corpus
- `100000073345_routes_of_admin.csv`
- `100000110633_units_of_mesu.csv`
- `200000000004_pharma_dose_form.csv`
- `200000000007_combined_terms.csv`
- `200000000014_units_of_presen.csv`
- `pharma_glossary.json` — glossary output
- `medical_training_final_cleaned.csv` — cleaned training dataset
- `medical_adapter_final/` — LoRA adapter used at inference time
- `medical_nllb_output_v2/` — training checkpoints and artifacts
- `outputs/` — evaluation outputs
- `tokenized_cache/` — cached tokenized datasets

## Configuration summary

The current repository uses `config.yaml` for almost all major settings, including:

- `model.base_model`
- `model.src_lang` and `model.tgt_lang`
- `training.num_epochs`
- `training.per_device_train_batch_size`
- `training.learning_rate`
- `training.lora.r` and `training.lora.target_modules`
- `validation.bleu_threshold`
- `document_processing.*`

The current LoRA configuration in `config.yaml` is centered on the `q_proj`, `v_proj`, `k_proj`, and `out_proj` modules, with `r: 32` and `lora_alpha: 16`.

## What each script does

### `build_glossary.py`
Builds a regulatory glossary from the provided CSV files and writes `pharma_glossary.json`.

### `prepare_data.py`
Loads the EMEA corpus, mines glossary context pairs, generates fallback glossary templates, cleans the dataset, and writes `medical_training_final_cleaned.csv`.

### `train_improved.py`
Trains the NLLB model with a PEFT LoRA adapter using the parameters in `config.yaml`. It also caches tokenized data under `tokenized_cache/` to speed up reruns.

### `evaluate_model.py`
Loads the adapter from `medical_adapter_final` and computes BLEU, METEOR, ChrF, and TER scores.

### `process_document_improved.py`
Translates `.docx` files while preserving Word structure and writing a JSON report for the processed output.

### `master_pipeline.py`
Provides the single CLI entry point for orchestrating the full process from glossary creation through document translation.

## Notes on current behavior

- The code uses a Windows-friendly PowerShell activation pattern with `.\venv\Scripts\Activate.ps1`.
- The expected adapter path is `medical_adapter_final`, not a separate `medical_adapter_final_v2` directory.
- The document processor produces a `*_Translated_DE_v2.report.json` file, not a separate `*_report.json` naming convention.
- The evaluation and translation scripts are model-path driven by `config.yaml`, so the repository should generally be run from the project root.

## Troubleshooting

### Missing CUDA / training hardware issues

The training script expects a CUDA-enabled GPU. If CUDA is unavailable, training will fail before running the LoRA fine-tuning loop.

### Missing data files

If `prepare_data.py` or the pipeline reports missing files, confirm that the bilingual corpus and all CSV terminology files are present in the project root.

### Missing adapter or outputs

If evaluation or translation fails because the adapter is missing, rerun the training step first, or confirm that `medical_adapter_final/` exists.

### Reusing cached tokenization

The first training run may build the `tokenized_cache/` folders. Subsequent runs can reuse that cache to reduce setup time.

## Summary

This repository is a domain-adapted NLLB + LoRA translation pipeline for pharmaceutical regulatory documents. The current README now reflects the actual command-line entry points, output folders, and script responsibilities used by the code in this workspace.

---

## Data Pipeline

### Step 1: Build Glossary (10 seconds)
```
CSV Files (5 sources)
    ↓
build_glossary.py
    ↓
pharma_glossary.json (1,000+ terms)
```

### Step 2: Prepare Training Data (30 seconds)
```
pharma_glossary.json + EMEA corpus
    ↓
prepare_data.py
    ↓
medical_training_final_cleaned.csv (249,136 pairs)
```

### Step 3: Train Model (~5 hours)
```
Training data + Base NLLB model
    ↓
train_improved.py (GPU-optimized)
    ↓
medical_adapter_final/ (LoRA adapter, 10 MB)
```

### Step 4: Evaluate (5 minutes)
```
Test data + Trained model
    ↓
evaluate_model.py
    ↓
evaluation_report.json + Metrics
```

### Step 5: Process Documents (2+ min/doc)
```
Document.docx + Trained model
    ↓
process_document_improved.py
    ↓
Document_Translated_DE_v2.docx + Report.json
```

---

## Troubleshooting

### Problem: CUDA out of memory

**Solution:**
```yaml
# In config.yaml, reduce batch size
per_device_train_batch_size: 4  # Was 8
```

### Problem: "File not found" errors

**Solution:**
```powershell
# Verify all files exist
.\venv\Scripts\python.exe verify_implementation.py
```

### Problem: Poor translation quality (BLEU < 20)

**Solutions:**
1. Check all CSV files exist and are accessible
2. Increase training epochs: `num_train_epochs: 8`
3. Lower learning rate: `learning_rate: 3e-5`
4. Increase training data if available

### Problem: Glossary file missing

**Solution:**
```powershell
# Rebuild glossary
.\venv\Scripts\python.exe build_glossary.py

# Check it was created
Test-Path pharma_glossary.json
```

### Problem: Training interrupted

**Solution:**
```powershell
# Re-run training (automatic checkpoint recovery)
.\venv\Scripts\python.exe train_improved.py
```

### Problem: Slow document processing

**Solution:**
The tokenization cache builds on first run. Subsequent runs are 20x faster.
- First run: ~30-60 seconds setup time
- Subsequent runs: ~2 minutes per 3-page document

### Problem: "torch_dtype is deprecated" warning

**Solution:** This is a non-critical deprecation warning from the transformers library. The code still works correctly. Will be fixed in next library update.

---

## Performance Tuning

### For Faster Training
```yaml
lower per_device_train_batch_size to 4
reduce num_train_epochs to 3
increase learning_rate to 1e-4
```

### For Better Quality
```yaml
increase num_train_epochs to 8
lower learning_rate to 3e-5
enable gradient_accumulation_steps: 2
add more training data if available
```

### For Low-Memory GPUs (< 6GB)
```yaml
per_device_train_batch_size: 4
lora.r: 16  (was 32)
gradient_checkpointing: true
torch_dtype: "bfloat16"
```

### For Multiple GPUs
```yaml
distributed_type: "multi_gpu"
fp16: true
per_device_train_batch_size: 16
```

---

## API Reference

### process_document_improved.py

```python
from PIL import Image
# Main function handles .docx file translation
# Loads model, translates document, generates report
```

**Usage:**
```powershell
.\venv\Scripts\python.exe process_document_improved.py <document.docx>
```

**Output:**
- `<document>_Translated_DE_v2.docx` - Translation
- `<document>_Translated_DE_v2.report.json` - Metrics

### evaluate_model.py

Evaluates model on test data with 4 metrics (BLEU, METEOR, ChrF, TER).

**Usage:**
```powershell
.\venv\Scripts\python.exe evaluate_model.py
```

**Output:**
- `outputs/evaluation_report.json` - Metrics report
- `outputs/evaluation_samples.csv` - Sample translations

### master_pipeline.py

Orchestrates all 5 pipeline steps with flexible control.

**Usage:**
```powershell
# All steps
.\venv\Scripts\python.exe master_pipeline.py --steps all

# Skip specific steps
.\venv\Scripts\python.exe master_pipeline.py --skip train eval

# Only data preparation
.\venv\Scripts\python.exe master_pipeline.py --steps prep
```

---

## System Requirements

### Minimum Requirements
- **Python:** 3.8+
- **GPU:** RTX 4060 (6GB VRAM) or equivalent
- **RAM:** 16GB system RAM
- **Storage:** 50GB free (for models, data, cache)
- **OS:** Windows 10+, Linux, macOS

### Recommended Setup
- **Python:** 3.10+
- **GPU:** RTX 4070+ (12GB+ VRAM)
- **RAM:** 32GB system RAM
- **Storage:** 100GB SSD
- **CUDA:** 11.8+
- **cuDNN:** 9.0+

### Python Dependencies
```
torch>=2.0.0 (with CUDA support)
transformers>=4.35.0
peft>=0.7.0
datasets>=2.14.0
pandas>=2.0.0
pyyaml>=6.0
python-docx>=0.8.11
sacrebleu>=2.3.1 (optional, for additional metrics)
bitsandbytes>=0.42.0 (for 8-bit optimizer)
```

---

## GPU Support

### Automatic GPU Detection
The code automatically detects available GPU and uses it. No configuration needed.

```powershell
# Check GPU status
(GPU info printed at script start)
```

### Manual GPU Selection (if needed)
```python
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # Use GPU 0
```

### CPU-Only Mode (not recommended)
```python
# Edit config.yaml
device_map: "cpu"  # Forces CPU (very slow)
torch_dtype: "float32"  # Use full precision
```

---

## Contributing

### Add Your Own Data

1. **Prepare CSV:** `source_lang | target_lang`
2. **Update prepare_data.py:** Add your CSV path
3. **Retrain:** `python train_improved.py`
4. **Evaluate:** `python evaluate_model.py`

### Add New Features

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes and test
4. Submit pull request

---

## Model Files Explanation

### medical_adapter_final/
- **adapter_config.json** - LoRA configuration (rank, alpha, target modules)
- **adapter_model.safetensors** - LoRA weights (~10 MB)
- **tokenizer.json** - Tokenizer config
- **sentencepiece.bpe.model** - BPE vocabulary

### medical_nllb_output_v2/
- **checkpoints/** - Training checkpoints (can resume from any)
- **trainer_state.json** - Training history and timestamps
- **optimizer.pt, scheduler.pt** - Optimizer state (for resuming)

### tokenized_cache/
- **train/**, **val/**, **test/** - Cached tokenized data
- Auto-generated, safe to delete (will regenerate)
- Provides 20x speedup on subsequent runs

---

## Performance Benchmarks

### Tested On
- **GPU:** NVIDIA GeForce RTX 4060 Laptop (8.59GB VRAM)
- **CPU:** Intel i7-12700H
- **RAM:** 32GB DDR5
- **OS:** Windows 11 Pro

### Benchmarks
| Task | Time | Notes |
|------|------|-------|
| Model loading | ~5-10 sec | First load slower |
| Data prep | ~30 sec | 249K pairs |
| Training (5 epochs) | ~5 hours | Full GPU utilization |
| Evaluation (100 samples) | ~5 min | Metrics calculation |
| Document translation | ~2 min/3 pages | Structure preserved |
| Tokenization (first run) | ~20-30 sec | Cache stored |
| Tokenization (cached) | ~1-2 sec | Instant reuse |

---

## License

This project uses:
- **NLLB-200 Model:** Meta AI, CC-BY-NC-4.0
- **EMEA Corpus:** European Medicines Agency (public domain)
- **Custom Code:** MIT License

---

## Citation

If you use this translator in your work, please cite:

```
@software{prdtl2024,
  title = {Pharmaceutical Regulatory Document Translator},
  author = {Your Name},
  year = {2024},
  url = {https://github.com/Shivshreeram/regu_project}
}
```

---

## Support & Contact

- **Issues:** GitHub Issues
- **Questions:** GitHub Discussions
- **Email:** shreeram@example.com

---

## Changelog

### Version 1.0 (March 2024)
- Initial release with LoRA adapter
- GPU optimization for RTX 4060
- BLEU score: 25-28
- Pharma glossary: 1,000+ terms
- Document translation pipeline
- Tokenization caching

---

## FAQ

**Q: Can I use this with CPU only?**
A: Yes, but it will be 50-100x slower. Not recommended for production.

**Q: How do I add more training data?**
A: Add CSV rows to `medical_training_final_cleaned.csv` and retrain.

**Q: Can this translate other language pairs?**
A: NLLB supports 200+ languages. You can modify config for other pairs.

**Q: How often should I retrain?**
A: Retrain when you add significant new training data (10%+ more samples).

**Q: What if the translation quality is poor?**
A: Check glossary matching, increase epochs (5→8), or add more domain data.

**Q: Can I use this adapter with other NLLB models?**
A: The adapter is tied to NLLBDistributed-600M-Distilled. Use with other NLLB-600M configs with caution.

**Q: Are translations perfect?**
A: No, post-edit is recommended for regulatory submission. BLEU 25-28 indicates good quality but not publication-ready.

---

## Appendix: Command Reference

```powershell
# Setup
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Build glossary
.\venv\Scripts\python.exe build_glossary.py

# Prepare data
.\venv\Scripts\python.exe prepare_data.py

# Train
.\venv\Scripts\python.exe train_improved.py

# Evaluate
.\venv\Scripts\python.exe evaluate_model.py

# Process document
.\venv\Scripts\python.exe process_document_improved.py document.docx

# Full pipeline
.\venv\Scripts\python.exe master_pipeline.py --steps all

# Verify setup
.\venv\Scripts\python.exe verify_implementation.py
```

---

**Last Updated:** March 22, 2024  
**Status:** Production Ready  
**Maintained by:** Shreeram
