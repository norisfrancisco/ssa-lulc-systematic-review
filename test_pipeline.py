#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smoke tests — verificam se o pipeline produz os resultados esperados.
Execute: python -m pytest tests/ -v
         python tests/test_pipeline.py
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path

DATA = Path("data/dados_LIMPOS_metaregressao.xlsx")


def test_data_exists():
    assert DATA.exists(), (
        f"Arquivo não encontrado: {DATA}\n"
        f"Baixe de: https://doi.org/10.5281/zenodo.XXXXXXX"
    )
    print("✓ Dados encontrados")


def test_data_shape():
    df = pd.read_excel(DATA)
    assert df.shape[0] == 164, f"Esperado 164 artigos, encontrado {df.shape[0]}"
    assert df.shape[1] >= 18, f"Colunas insuficientes: {df.shape[1]}"
    print(f"✓ Shape correto: {df.shape}")


def test_meta_regression_results():
    """Verifica que os resultados reproduzem exatamente os valores do manuscrito."""
    import statsmodels.api as sm
    import warnings; warnings.filterwarnings('ignore')

    df = pd.read_excel(DATA)
    df.columns = [c.replace('\n','_').strip() for c in df.columns]

    cols = {
        'TOA': '★ Usa_TOA_(F1)', 'SCV': '★ Spatial_CV_(F5)',
        'GEE': '★ GEE_Native_(F2)', 'MOM': '★ ModelOnModel_(F4)',
        'MLC': '★ is_MLC_(F0)', 'OA': 'OA_PERCENT'
    }
    for k, c in cols.items():
        df[k] = pd.to_numeric(df[c], errors='coerce')

    PRED = ['TOA', 'SCV', 'GEE', 'MOM', 'MLC']
    mask = (df['OA'] >= 50) & (df['OA'] <= 100)
    for p in PRED: mask = mask & df[p].notna()
    d = df[mask].copy()
    d['logit_OA'] = np.log(d['OA']/100 / (1 - d['OA']/100))

    X = sm.add_constant(d[PRED].astype(float))
    m = sm.OLS(d['logit_OA'], X).fit()

    # Valores esperados (manuscrito final, Tabela 2)
    TOL = 1e-3
    assert abs(m.rsquared      - 0.0523) < TOL,  f"R² errado: {m.rsquared:.4f}"
    assert abs(m.fvalue        - 1.6430) < TOL,  f"F errado: {m.fvalue:.4f}"
    assert abs(m.params['MLC'] + 0.3692) < TOL,  f"β_MLC errado: {m.params['MLC']:.4f}"
    assert abs(m.pvalues['MLC']- 0.0245) < TOL,  f"p_MLC errado: {m.pvalues['MLC']:.4f}"
    assert abs(m.params['TOA'] - 0.0641) < TOL,  f"β_TOA errado: {m.params['TOA']:.4f}"
    print(f"✓ Meta-regressão reproduzida:")
    print(f"  R²={m.rsquared:.4f} | F={m.fvalue:.4f} | β_MLC={m.params['MLC']:.4f} | p_MLC={m.pvalues['MLC']:.4f}")


def test_no_outliers_in_oa():
    df = pd.read_excel(DATA)
    oa = pd.to_numeric(df['OA_PERCENT'], errors='coerce')
    n_outliers = (oa > 100).sum()
    assert n_outliers == 0, f"Outliers OA > 100%: {n_outliers}"
    print(f"✓ Sem outliers de OA no ficheiro atual (N={oa.notna().sum()})")


if __name__ == "__main__":
    print("=== SMOKE TESTS — LULC Pipeline ===\n")
    try:
        test_data_exists()
        test_data_shape()
        test_meta_regression_results()
        test_no_outliers_in_oa()
        print("\n✅ TODOS OS TESTES PASSARAM")
    except AssertionError as e:
        print(f"\n❌ FALHA: {e}")
        sys.exit(1)
