#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
                     REVISÃO SISTEMÁTICA LULC - FASE 3
                   AMOSTRAGEM PARA AUDITORIA DO REGEX (N=363)
================================================================================
Script: 03_validation_sampling.py | Protocolo V2.1

OBJETIVO:
  Selecionar N=363 artigos para auditoria manual da triagem REGEX (Fase 2),
  estimando a taxa de falsos negativos do pipeline automatizado.

FÓRMULA COCHRAN (1954):
  n₀ = (Z² × p × q) / e²   [Z=1,96; p=0,50; e=0,05]  →  n₀ = 384
  n  = n₀ / (1 + (n₀−1)/N) [N=6473]                   →  n  = 363
  Semente deterministíca: 42 — resultado sempre idêntico.

ENTRADA : data/triagem_fase2_completa.csv (output da Fase 2)
SAÍDA   : outputs/amostra_363_auditoria.xlsx

REFERÊNCIA:
  COCHRAN, W.G. Biometrics, v.10, n.4, p.417-451, 1954.
================================================================================
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

INPUT  = Path("data/triagem_fase2_completa.csv")
OUTPUT = Path("outputs")
OUTPUT.mkdir(exist_ok=True)

SEED       = 42     # Não alterar — reprodutibilidade garantida
N_POP      = 6473
N_AMOSTRA  = 363


def cochran_n(N: int, z=1.96, p=0.5, e=0.05) -> int:
    n0 = (z**2 * p * (1-p)) / e**2
    return int(np.ceil(n0 / (1 + (n0-1)/N)))


def main():
    n_calc = cochran_n(N_POP)
    print(f"N Cochran calculado: {n_calc} (configurado: {N_AMOSTRA})")
    if n_calc != N_AMOSTRA:
        print(f"⚠️  Divergência: {n_calc} ≠ {N_AMOSTRA}")
        sys.exit(1)

    if not INPUT.exists():
        print(f"⚠️  Arquivo ausente: {INPUT}")
        print("   Execute 02_regex_screening.py primeiro.")
        sys.exit(1)

    df = pd.read_csv(INPUT, encoding='utf-8-sig')
    print(f"Registros carregados: {len(df)}")

    amostra = df.sample(n=N_AMOSTRA, random_state=SEED).copy()
    amostra.insert(0, 'ID_auditoria', range(1, N_AMOSTRA+1))
    amostra['auditado']  = ''
    amostra['decisao']   = ''   # INCLUIR / EXCLUIR / DUVIDA
    amostra['notas']     = ''

    out = OUTPUT / "amostra_363_auditoria.xlsx"
    amostra.to_excel(out, index=False)
    print(f"✓ {out} — semente={SEED}, N={N_AMOSTRA}")


if __name__ == "__main__":
    main()
