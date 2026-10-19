# LULC Sub-Saharan Africa — Systematic Review & Meta-Regression Pipeline

**Authors:** Francisco José Noris · Marcus Vinícius Contes Calca · Valéria Cristina Rodrigues Sarnighausen  
**Institution:** UNESP — Faculdade de Ciências Agronômicas, Botucatu, Brazil  
**Paper:** *Methodologies of land use mapping in Sub-Saharan Africa: a systematic review*  
**Target journal:** Remote Sensing of Environment (Elsevier)  

[![OSF](https://img.shields.io/badge/OSF-osf.io%2Fcg8wp-blue)](https://osf.io/cg8wp/)
[![Zenodo](https://img.shields.io/badge/Zenodo-10.5281%2Fzenodo.20701518-blue)](https://doi.org/10.5281/zenodo.20701518)
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
- Robust under HC3 (SE = 0.159; p = 0.020), non-parametric bootstrap (B = 5,000;
  95% CI [−0.659, −0.046], excludes zero), and Cook's Distance sensitivity analysis
  (14/155 observations above the 4/n threshold; excluding them: β = −0.321, p = 0.024)
- Ramsey RESET (functional-form specification test, power=2): F = 5.0561, p = 0.0260 —
  **significant**, indicating possible linear functional-form misspecification
  (see Limitations)

---

## Quickstart

```bash
# 1. Clone repository
git clone https://github.com/norisfrancisco/ssa-lulc-systematic-review.git
cd ssa-lulc-systematic-review

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download data (from Zenodo — NOT included in this repository)
# Place dados_LIMPOS_metaregressao.xlsx in the data/ folder
# Data DOI: https://doi.org/10.5281/zenodo.20701518

# 4. Run the full pipeline
python 04_meta_regression.py            # Main results (Table 2)
python 05_figures.py                    # All manuscript figures

# Expected output:
# outputs/Tabela2_OLS_Resultados.csv       ← R²=0.052, is_MLC p=0.024
# outputs/Tabela2_HC3_Robusto.csv          ← HC3 robust SE, is_MLC p=0.020
# outputs/Bootstrap_CI_B5000.csv           ← percentile 95% CI, B=5,000, seed=42
# outputs/CooksDistance_Influencia.csv     ← Cook's D per observation, threshold 4/n
# outputs/TB_VIF_Diagnosticos.csv          ← all VIF < 1.6
# outputs/FiguraA1_Diagnosticos_OLS.png    ← 300 DPI diagnostic plots (+ .eps)
# outputs/Figura_2_evolucao_temporal.png              ← Temporal evolution (panels A+B)
# outputs/Figura_4_distribuicao_algoritmica_flags.png ← Algorithmic distribution + flags (panels A+B)
# outputs/Figura_5_distribuicao_geografica.png        ← Geographic distribution (top 10 countries)
# outputs/Figura_6_distribuicao_OA.png                ← OA distribution + boxplot by generation (panels A+B)
# outputs/Figura_7_sensores.png                       ← Sensor/platform distribution
# (each Figura_*.png above also has a .eps vector sibling)
```

---

## Repository Structure

```
ssa-lulc-systematic-review/
├── README.md
├── LICENSE                         ← MIT (code)
├── requirements.txt
├── .gitignore
├── 01_deduplication.py             ← Stage 1: BibTeX deduplication (Levenshtein ≥0.92)
├── 02_regex_screening.py           ← Stage 2: REGEX-based title/abstract screening
├── 03_validation_sampling.py       ← Stage 3: Cochran sampling (N=363, seed=42)
├── 04_meta_regression.py           ← Stage 4: OLS on Logit(OA) — MAIN ANALYSIS
├── 05_figures.py                   ← Stage 5: All manuscript figures (300 DPI)
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
| Extraction matrix (164 × 21) | Zenodo | https://doi.org/10.5281/zenodo.20701518 | CC-BY 4.0 |
| Supplementary tables S1–S4 | Zenodo | https://doi.org/10.5281/zenodo.20701518 | CC-BY 4.0 |
| Boolean search strings | OSF | https://osf.io/cg8wp/ | CC-BY 4.0 |
| Extraction protocol V2.1 | OSF | https://osf.io/cg8wp/ | CC-BY 4.0 |

---

## Reproducibility

Running `python 04_meta_regression.py` with `dados_LIMPOS_metaregressao.xlsx`
in the `data/` folder must produce exactly:

```
R² = 0.0523
F(5, 149) = 1.6430
p(F) = 0.1521
is_MLC (OLS classical):  β = -0.3692  SE = 0.1624  t = -2.2728  p = 0.0245
is_MLC (HC3 robust SE):  β = -0.3692  SE = 0.1589  t = -2.3233  p = 0.0202
is_MLC (bootstrap, B=5000, seed=42): 95% CI [-0.659, -0.046] (excludes zero)
Condition Number = 8.17
Shapiro-Wilk: W = 0.9495  p = 0.000022  (Skew = 0.778, Kurtosis = 3.491)
Breusch-Pagan: LM = 7.3554  p = 0.1955
Cook's Distance: 14/155 observations above threshold 4/n (max = 0.2265);
  excluding them → is_MLC β = -0.3207, p = 0.0239 (conclusion unchanged)
Ramsey RESET (power=2): F = 5.0561  p = 0.0260  (significant — see Limitations)
Fisher exact (GEE × Spatial_CV): OR = 1.5714  p = 0.5445
```

Any deviation from these values indicates a data or environment issue. Minor floating-point
variation in the bootstrap CI across platforms is expected despite the fixed seed (NumPy's
default BitGenerator can differ by version); the HC3 and OLS rows are exact.

---

## Descriptive Statistics (N = 164)

Summary values extracted from the manuscript figures (`05_figures.py`):

### Classification Generation (GEN)
| Category | N | % |
|---|---|---|
| GEN 1 — Paramétrico | 69 | 42.1% |
| GEN 2 — Machine Learning | 63 | 38.4% |
| GEN 3 — Deep Learning | 3 | 1.8% |
| GEN 4 — Híbrido | 29 | 17.7% |

### Algorithm Flags
| Flag | N | % |
|---|---|---|
| F0 — is_MLC (Maximum Likelihood) | 80 | 48.8% |
| F1 — Usa_TOA (Top-of-Atmosphere reflectance) | 77 | 47.0% |
| F2 — GEE_Native (Google Earth Engine) | 29 | 17.7% |
| F4 — ModelOnModel (ensemble/stacking) | 7 | 4.3% |
| F5 — Spatial_CV (spatial cross-validation) | 4 | 2.4% |

### Overall Accuracy (OA) — studies with OA only (N = 155)
- Mean OA: **91.8%**
- Median OA: **92.0%**
- Reference threshold: 90%

### Country of Study
| Country | N | % |
|---|---|---|
| Etiópia | 58 | 35.4% |
| África do Sul | 28 | 17.1% |
| Gana | 17 | 10.4% |
| Others | 61 | 37.2% |

### Sensor / Platform
| Sensor | N | % |
|---|---|---|
| Landsat (exclusive) | 126 | 76.8% |
| Sentinel | 15 | 9.1% |
| Landsat + Sentinel | 5 | 3.0% |
| Outros | 18 | 11.0% |

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
  author  = {Noris, Francisco José and Contes Calca, Marcus Vinícius and Sarnighausen, Valéria Cristina Rodrigues},
  journal = {Remote Sensing of Environment},
  year    = {2026},
  note    = {In submission},
  doi     = {[pending]}
}
```

**Code:**
> Noris, F.J., Contes Calca, M.V., & Sarnighausen, V.C.R. (2026). *LULC Sub-Saharan Africa — Systematic Review Pipeline* (v2.1.1).
> GitHub. https://github.com/norisfrancisco/ssa-lulc-systematic-review.
> Zenodo. https://doi.org/10.5281/zenodo.20701518

---

## License

- **Code:** MIT License (see `LICENSE`)  
- **Data:** Creative Commons Attribution 4.0 (CC-BY 4.0)


