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
        f"Arquivo nao encontrado: {DATA}\n"
        f"Baixe de: https://doi.org/10.5281/zenodo.20701518"
    )
    print("checkmark Dados encontrados")


def test_data_shape():
    df = pd.read_excel(DATA)
    assert df.shape[0] == 164, f"Esperado 164 artigos, encontrado {df.shape[0]}"
    # dados_LIMPOS_metaregressao.xlsx (TabelaA_Artigos_Incluidos): 18 colunas
    # (verificado 2026-10-18 contra o arquivo real; nao e a matriz bruta de
    # extracao do Zenodo, que tem contagem de colunas diferente)
    assert df.shape[1] == 18, f"Esperado 18 colunas, encontrado {df.shape[1]}"
    print(f"checkmark Shape correto: {df.shape}")


def test_meta_regression_results():
    """Verifica que os resultados reproduzem exatamente os valores do manuscrito."""
    import statsmodels.api as sm
    import warnings; warnings.filterwarnings('ignore')

    df = pd.read_excel(DATA)
    df.columns = [c.replace('\n','_').strip() for c in df.columns]

    cols = {
        'TOA': 'F1_Usa_TOA', 'SCV': 'F5_Spatial_CV',
        'GEE': 'F2_GEE_Native', 'MOM': 'F4_Model_on_Model',
        'MLC': 'F0_is_MLC', 'OA': 'OA_percent'
    }
    for k, c in cols.items():
        df[k] = pd.to_numeric(df[c], errors='coerce')

    PRED = ['TOA', 'SCV', 'GEE', 'MOM', 'MLC']
    mask = (df['OA'] >= 50) & (df['OA'] <= 100)
    for p in PRED: mask = mask & df[p].notna()
    d = df[mask].copy()
    d['logit_OA'] = np.log(d['OA']/100 / (1 - d['OA']/100))

    X = sm.add_constant(d[PRED].astype(float))
    fit = getattr(sm.OLS(d['logit_OA'], X), 'fit')()

    TOL = 1e-3
    assert abs(fit.rsquared      - 0.0523) < TOL,  f"R2 errado: {fit.rsquared:.4f}"
    assert abs(fit.fvalue        - 1.6430) < TOL,  f"F errado: {fit.fvalue:.4f}"
    assert abs(fit.params['MLC'] + 0.3692) < TOL,  f"beta_MLC errado: {fit.params['MLC']:.4f}"
    assert abs(fit.pvalues['MLC']- 0.0245) < TOL,  f"p_MLC errado: {fit.pvalues['MLC']:.4f}"
    assert abs(fit.params['TOA'] - 0.0641) < TOL,  f"beta_TOA errado: {fit.params['TOA']:.4f}"
    print(f"checkmark Meta-regressao reproduzida:")
    print(f"  R2={fit.rsquared:.4f} | F={fit.fvalue:.4f} | beta_MLC={fit.params['MLC']:.4f} | p_MLC={fit.pvalues['MLC']:.4f}")


def test_hc3_and_bootstrap_robustness():
    """Verifica que is_MLC permanece significativo sob HC3 e que o IC95
    por bootstrap (B=5000, seed=42) exclui zero — robustez declarada no README."""
    import statsmodels.api as sm
    import warnings; warnings.filterwarnings('ignore')

    df = pd.read_excel(DATA)
    df.columns = [c.replace('\n', '_').strip() for c in df.columns]
    cols = {
        'TOA': 'F1_Usa_TOA', 'SCV': 'F5_Spatial_CV',
        'GEE': 'F2_GEE_Native', 'MOM': 'F4_Model_on_Model',
        'MLC': 'F0_is_MLC', 'OA': 'OA_percent'
    }
    for k, c in cols.items():
        df[k] = pd.to_numeric(df[c], errors='coerce')

    PRED = ['TOA', 'SCV', 'GEE', 'MOM', 'MLC']
    mask = (df['OA'] >= 50) & (df['OA'] <= 100)
    for p in PRED: mask = mask & df[p].notna()
    d = df[mask].copy()
    d['logit_OA'] = np.log(d['OA'] / 100 / (1 - d['OA'] / 100))
    X = sm.add_constant(d[PRED].astype(float))
    y = d['logit_OA']

    fit_hc3 = getattr(sm.OLS(y, X), 'fit')(cov_type='HC3')
    assert fit_hc3.pvalues['MLC'] < 0.05, (
        f"is_MLC deixou de ser significativo sob HC3: p={fit_hc3.pvalues['MLC']:.4f}"
    )

    rng = np.random.default_rng(42)
    n = len(d)
    boot = np.empty(5000)
    X_arr, y_arr = X.values, y.values
    for b in range(5000):
        idx = rng.integers(0, n, size=n)
        try:
            fit_b = getattr(sm.OLS(y_arr[idx], X_arr[idx]), 'fit')()
            boot[b] = fit_b.params[list(X.columns).index('MLC')]
        except Exception:
            boot[b] = np.nan
    lo, hi = np.nanpercentile(boot, [2.5, 97.5])
    assert not (lo <= 0 <= hi), f"IC95 bootstrap de is_MLC inclui zero: [{lo:.3f}; {hi:.3f}]"
    print(f"checkmark HC3 (p={fit_hc3.pvalues['MLC']:.4f}) e bootstrap "
          f"(IC95=[{lo:.3f}; {hi:.3f}]) confirmam is_MLC significativo")


def test_ramsey_reset():
    """Verifica que o teste de Ramsey RESET (especificação funcional) é computado
    e reproduz o valor declarado no manuscrito/README (F≈5.0561, p≈0.0260)."""
    import statsmodels.api as sm
    from statsmodels.stats.diagnostic import linear_reset
    import warnings; warnings.filterwarnings('ignore')

    df = pd.read_excel(DATA)
    df.columns = [c.replace('\n', '_').strip() for c in df.columns]
    cols = {
        'TOA': 'F1_Usa_TOA', 'SCV': 'F5_Spatial_CV',
        'GEE': 'F2_GEE_Native', 'MOM': 'F4_Model_on_Model',
        'MLC': 'F0_is_MLC', 'OA': 'OA_percent'
    }
    for k, c in cols.items():
        df[k] = pd.to_numeric(df[c], errors='coerce')

    PRED = ['TOA', 'SCV', 'GEE', 'MOM', 'MLC']
    mask = (df['OA'] >= 50) & (df['OA'] <= 100)
    for p in PRED: mask = mask & df[p].notna()
    d = df[mask].copy()
    d['logit_OA'] = np.log(d['OA'] / 100 / (1 - d['OA'] / 100))
    X = sm.add_constant(d[PRED].astype(float))
    y = d['logit_OA']
    fit = getattr(sm.OLS(y, X), 'fit')()

    reset_result = linear_reset(fit, power=2, test_type='fitted', use_f=True)
    TOL = 1e-3
    assert abs(reset_result.fvalue - 5.0561) < TOL, f"Ramsey F errado: {reset_result.fvalue:.4f}"
    assert abs(reset_result.pvalue - 0.0260) < 5e-3, f"Ramsey p errado: {reset_result.pvalue:.4f}"
    print(f"checkmark Ramsey RESET reproduzido: F={reset_result.fvalue:.4f} p={reset_result.pvalue:.4f}")


def test_no_outliers_in_oa():
    df = pd.read_excel(DATA)
    oa = pd.to_numeric(df['OA_percent'], errors='coerce')
    n_outliers = (oa > 100).sum()
    assert n_outliers == 0, f"Outliers OA > 100%: {n_outliers}"
    print(f"checkmark Sem outliers de OA (N={oa.notna().sum()})")


if __name__ == "__main__":
    print("=== SMOKE TESTS — LULC Pipeline ===\n")
    try:
        test_data_exists()
        test_data_shape()
        test_meta_regression_results()
        test_hc3_and_bootstrap_robustness()
        test_ramsey_reset()
        test_no_outliers_in_oa()
        print("\nALL TESTS PASSED")
    except AssertionError as e:
        print(f"\nFAIL: {e}")
        sys.exit(1)
