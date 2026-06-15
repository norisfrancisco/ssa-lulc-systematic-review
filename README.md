# LULC Sub-Saharan Africa — Systematic Review & Meta-Regression Pipeline

**Authors:** Francisco José Noris · Valéria Cristina Rodrigues Sarnighausen  
**Institution:** UNESP — Faculdade de Ciências Agronômicas, Botucatu, Brazil  
**Paper:** *Methodologies of land use mapping in Sub-Saharan Africa: a systematic review*  
**Target journal:** Remote Sensing of Environment (Elsevier)  

[![OSF](https://img.shields.io/badge/OSF-osf.io%2Fcg8wp-blue)](https://osf.io/cg8wp/)
[![Zenodo](https://img.shields.io/badge/Zenodo-DOI%20pending-green)](https://zenodo.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Data: CC-BY 4.0](https://img.shields.io/badge/Data-CC--BY%204.0-orange)](https://creativecommons.org/licenses/by/4.0/)

---

## Overview

This repository contains the complete computational pipeline for the systematic review
of LULC classification methodologies in Sub-Saharan Africa (1991–2026).

**The pipeline covers four stages:**

```
Stage 1: BibTeX deduplication      →  01_deduplication.py
Stage 2: Automated REGEX screening →  02_regex_screening.py
Stage 3: REGEX audit sampling      →  03_validation_sampling.py
Stage 4: OLS meta-regression       →  04_meta_regression.py   ← main results
Stage 5: Figure generation         →  05_figures.py
```

**Key result (fully reproducible):**
- N = 155 studies with quantitative Overall Accuracy
- is_MLC: β = −0.369 (SE = 0.162; t = −2.273; p = 0.024)
- Confirmed robust under HC3, bootstrap (B=5,000) and Cook's D sensitivity analysis

---

## Quickstart

```bash
# 1. Clone repository
git clone https://github.com/[username]/LULC-SubSahara-MetaRegression.git
cd LULC-SubSahara-MetaRegression

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download data (from Zenodo — NOT included in this repository)
# Place dados_LIMPOS_metaregressao.xlsx in the data/ folder
# Data DOI: https://doi.org/10.5281/zenodo.XXXXXXX

# 4. Run the full pipeline
python src/04_meta_regression.py        # Main results (Table 2)
python src/05_figures.py                # All manuscript figures

# Expected output:
# outputs/Tabela2_OLS_Resultados.csv    ← R²=0.052, is_MLC p=0.024
# outputs/TB_VIF_Diagnosticos.csv       ← all VIF < 1.6
# outputs/FiguraS1_Diagnosticos_OLS.png ← 300 DPI diagnostic plots
```

---

## Repository Structure

```
LULC-SubSahara-MetaRegression/
├── README.md
├── LICENSE                         ← MIT (code)
├── requirements.txt
├── .gitignore
├── src/
│   ├── 01_deduplication.py         ← Stage 1: BibTeX deduplication (Levenshtein ≥0.92)
│   ├── 02_regex_screening.py       ← Stage 2: REGEX-based title/abstract screening
│   ├── 03_validation_sampling.py   ← Stage 3: Cochran sampling (N=363, seed=42)
│   ├── 04_meta_regression.py       ← Stage 4: OLS on Logit(OA) — MAIN ANALYSIS
│   └── 05_figures.py               ← Stage 5: All manuscript figures (300 DPI)
├── data/
│   └── README.txt                  ← "Download from Zenodo DOI: ..."
├── notebooks/
│   └── REVISAO_SISTEMATICA.ipynb   ← Exploratory notebook (TERA v3.0)
├── outputs/                        ← .gitignored; created at runtime
└── tests/
    └── test_pipeline.py            ← Smoke tests for reproducibility
```

---

## Data Availability

**Data are NOT stored in this repository** (FAIR principles — data should be in a
permanent repository with a DOI, not in a version-controlled code repository).

| Dataset | Repository | DOI | License |
|---|---|---|---|
| Extraction matrix (164 × 22) | Zenodo | [pending] | CC-BY 4.0 |
| Supplementary tables S1–S4 | Zenodo | [pending] | CC-BY 4.0 |
| Boolean search strings | OSF | https://osf.io/cg8wp/ | CC-BY 4.0 |
| Extraction protocol V2.1 | OSF | https://osf.io/cg8wp/ | CC-BY 4.0 |

---

## Reproducibility

Running `python src/04_meta_regression.py` with `dados_LIMPOS_metaregressao.xlsx`
in the `data/` folder must produce exactly:

```
R² = 0.0523
F(5, 149) = 1.6430
p(F) = 0.1521
is_MLC: β = -0.3692  SE = 0.1624  t = -2.2728  p = 0.0245
Condition Number = 8.17
Shapiro-Wilk: W = 0.9495  p = 0.000022
Breusch-Pagan: LM = 7.3554  p = 0.1955
Fisher exact (GEE × Spatial_CV): OR = 1.5714  p = 0.5445
```

Any deviation from these values indicates a data or environment issue.

---

## Environment

```
Python: 3.10+
pandas: 1.3+
numpy: 1.21+
scipy: 1.7+
statsmodels: 0.13+
matplotlib: 3.4+
seaborn: 0.11+
openpyxl: 3.0+
rapidfuzz: 2.6+
bibtexparser: 1.2+
```

---

## Citation

```bibtex
@article{noris2026lulc,
  title   = {Methodologies of land use mapping in Sub-Saharan Africa: a systematic review},
  author  = {Noris, Francisco José and Sarnighausen, Valéria Cristina Rodrigues},
  journal = {Remote Sensing of Environment},
  year    = {2026},
  note    = {In submission},
  doi     = {[pending]}
}
```

**Code:**
> Noris, F.J. (2026). *LULC Sub-Saharan Africa — Systematic Review Pipeline* (v1.0.0).
> GitHub. https://github.com/[username]/LULC-SubSahara-MetaRegression.
> Zenodo. https://doi.org/10.5281/zenodo.XXXXXXX

---

## License

- **Code:** MIT License (see `LICENSE`)  
- **Data:** Creative Commons Attribution 4.0 (CC-BY 4.0)

---

## Errata

**v1.0.0 (2026-06-15):**
- Fisher's exact test yields OR = 1.57; p = 0.544.
- β_TOA corrected to +0.064 (not −0.064 as in earlier draft).
- p_TOA corrected to 0.656; p_ModelOnModel corrected to 0.522.
- t_MLC corrected to −2.273 (not −2.283).
- Stage 5 (FASE_5) logistic binary regression removed — EPV = 4:1 precludes
  reliable estimation; Fisher's exact test is the appropriate alternative.
