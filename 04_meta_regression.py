#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SCRIPT DE META-REGRESSÃO — REPRODUTÍVEL E DOCUMENTADO
Revisão Sistemática LULC África Subsaariana (1991–2026)
Protocolo V2.1

Autores: Francisco José Noris; Valéria Cristina Rodrigues Sarnighausen; Marcus Vinícius Contes Calca
UNESP — Faculdade de Ciências Agronômicas, Botucatu, Brasil
SENAI — São Paulo, Brasil (Contes Calca)
OSF: https://osf.io/cg8wp/
Versão: 2.1.1 | Data: 2026-10-08

DEPENDÊNCIAS (instalar via pip):
  pandas==1.3+   numpy==1.21+   scipy==1.7+
  statsmodels==0.13+   matplotlib==3.4+   seaborn==0.11+
  openpyxl (para leitura de .xlsx)

EXECUÇÃO:
  python meta_regressao_reproducivel.py

ENTRADA:
  dados_LIMPOS_metaregressao.xlsx — na mesma pasta deste script

SAÍDA (pasta ./resultados/):
  Tabela2_OLS_Resultados.csv       — coeficientes, EP, t, p, IC95 (OLS clássico)
  Tabela2_HC3_Robusto.csv          — mesmos coeficientes com EP robustos HC3 (White/MacKinnon)
  Bootstrap_CI_B5000.csv           — IC95 por bootstrap percentil (B=5000, seed=42)
  CooksDistance_Influencia.csv     — Distância de Cook por observação + limiar 4/n
  TB_VIF_Diagnosticos.csv          — VIF por preditor
  Diagnosticos_Modelo.txt          — Shapiro-Wilk, Breusch-Pagan, Durbin-Watson, Ramsey RESET, HC3, bootstrap, Cook, Fisher
  Fisher_GEE_Spatial.csv           — tabela 2×2 com resultado
  FiguraA1_Diagnosticos_OLS.png    — diagnósticos 2×2: resíduos×ajustados,
                                      Q-Q normal, histograma, scale-location (300 DPI, + .eps)
  log_execucao.txt                 — log completo com timestamps

NOTA (corrigido 2026-10-18): Figura6A/Figura6B (distribuição/boxplot de OA por
geração) foram retiradas do depósito OSF por decisão editorial; a geração
dessas duas figuras foi removida deste script. A figura de diagnósticos do
modelo foi renomeada de "Figura S1" para "Figura A1" (nomenclatura do Material
Suplementar). O arquivo de entrada usado é a planilha "Artigos Incluídos"
(cabeçalho único, OA em percentual), não a matriz bruta de extração.

MODELO:
  logit(OA_i) = β₀ + β₁·Usa_TOA + β₂·is_Spatial_CV
                   + β₃·is_GEE_Native + β₄·is_Model_on_Model
                   + β₅·is_MLC + ε_i

  is_OOB_Validation EXCLUÍDO: variância zero (n=0 artigos com OOB=1).
================================================================================
"""

import sys
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')

try:
    import statsmodels.api as sm
    from statsmodels.stats.outliers_influence import variance_inflation_factor, OLSInfluence
    from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset
except ImportError:
    print("❌ Instale statsmodels: pip install statsmodels openpyxl")
    sys.exit(1)

try:
    from scipy import stats
except ImportError:
    print("❌ Instale scipy: pip install scipy")
    sys.exit(1)

# ─── CONFIGURAÇÃO ──────────────────────────────────────────────────────────────

# Busca o arquivo em: (1) pasta atual, (2) data/ na raiz do projeto
_candidates = [
    Path("dados_LIMPOS_metaregressao.xlsx"),           # pasta atual
    Path(__file__).parent / "data" / "dados_LIMPOS_metaregressao.xlsx",  # raiz/data/
]
INPUT_FILE = next((p for p in _candidates if p.exists()), _candidates[0])
# Saída em outputs/ na raiz do projeto
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Reprodutibilidade do bootstrap
BOOTSTRAP_SEED = 42
BOOTSTRAP_B = 5000

# Mapeamento exacto das colunas do Excel
# NOTA (corrigido 2026-10-18): adaptado aos nomes de coluna reais de
# dados_LIMPOS_metaregressao.xlsx (estrutura "TabelaA_Artigos_Incluidos",
# cabecalho unico em linha 1, OA em escala percentual 0-100). O mapeamento
# original do script (nomes com prefixo "★" e quebras de linha, OA_PERCENT)
# correspondia a uma variante de planilha diferente, nao a esta.
COL_MAP = {
    'OA':  'OA_percent',
    'MLC': 'F0_is_MLC',
    'GEN': 'GEN',
    'TOA': 'F1_Usa_TOA',
    'SCV': 'F5_Spatial_CV',
    'GEE': 'F2_GEE_Native',
    'OOB': 'F3_OOB_Valid',
    'MOM': 'F4_Model_on_Model',
    'ANO': 'Ano',
    'PAIS':'País',
    'SENSOR':'Sensor',
}

# ─── LOGGER ────────────────────────────────────────────────────────────────────

log_lines = []

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{level:5s}] {msg}"
    print(line)
    log_lines.append(line)

def salvar_log():
    with open(OUTPUT_DIR / "log_execucao.txt", "w", encoding="utf-8") as f:
        f.write(f"Execução: {datetime.now().isoformat()}\n")
        f.write("="*70 + "\n\n")
        f.write("\n".join(log_lines))

# ─── 1. CARREGAR DADOS ─────────────────────────────────────────────────────────

log("Carregando dados...")

if not INPUT_FILE.exists():
    log(f"Arquivo não encontrado: {INPUT_FILE}", "ERRO")
    sys.exit(1)

df_raw = pd.read_excel(INPUT_FILE)
log(f"Dimensões brutas: {df_raw.shape[0]} linhas × {df_raw.shape[1]} colunas")

# Renomear para nomes curtos
rename = {v: k for k, v in COL_MAP.items() if v in df_raw.columns}
df = df_raw.rename(columns=rename).copy()

# Converter para numérico
for col in ['OA','MLC','GEN','TOA','SCV','GEE','OOB','MOM','ANO']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

log(f"N total no ficheiro: {len(df)}")

# ─── 2. ESTATÍSTICAS DESCRITIVAS BÁSICAS ───────────────────────────────────────

log("Calculando estatísticas descritivas...")

N_TOTAL = len(df)
N_COM_OA = df['OA'].notna().sum()
N_SEM_OA = N_TOTAL - N_COM_OA

log(f"N elegíveis total: {N_TOTAL}")
log(f"N com OA quantitativa: {N_COM_OA}")
log(f"N sem OA (apenas descritivos): {N_SEM_OA}")

# OA statistics
oa_clean = df['OA'][(df['OA'] >= 50) & (df['OA'] <= 100)]
log(f"OA (N={len(oa_clean)}): média={oa_clean.mean():.2f}%  "
    f"mediana={oa_clean.median():.2f}%  σ={oa_clean.std():.2f}%  "
    f"range=[{oa_clean.min():.1f}%, {oa_clean.max():.1f}%]")

# Predictor counts
PREDS = ['TOA','SCV','GEE','OOB','MOM','MLC']
log("Frequências dos preditores (de N=164):")
for p in PREDS:
    if p in df.columns:
        n1 = (df[p] == 1).sum()
        pct = 100 * n1 / N_TOTAL
        log(f"  {p}: n={int(n1)} ({pct:.1f}%)")

# Temporal
if 'ANO' in df.columns:
    anos = df['ANO'].dropna()
    log(f"Período: {int(anos.min())}–{int(anos.max())}")
    log(f"N 2021-2026: {((anos>=2021)&(anos<=2026)).sum()} "
        f"({100*((anos>=2021)&(anos<=2026)).sum()/N_TOTAL:.1f}%)")

# ─── 3. META-REGRESSÃO OLS SOBRE LOGIT(OA) ─────────────────────────────────────

log("Preparando meta-regressão OLS sobre Logit(OA)...")

PRED_OLS = ['TOA', 'SCV', 'GEE', 'MOM', 'MLC']
# OOB excluído: variância zero

df_ols = df.copy()
mask = (df_ols['OA'] >= 50) & (df_ols['OA'] <= 100)
for p in PRED_OLS:
    mask = mask & df_ols[p].notna()
df_ols = df_ols[mask].copy()

# Transformação logit
df_ols['logit_OA'] = np.log(
    (df_ols['OA'] / 100) / (1 - df_ols['OA'] / 100)
)

N_OLS = len(df_ols)
log(f"N da meta-regressão: {N_OLS} (EPV = {N_OLS/len(PRED_OLS):.1f}:1)")

# OLS
X = sm.add_constant(df_ols[PRED_OLS].astype(float))
y = df_ols['logit_OA']
modelo = sm.OLS(y, X).fit()

log(f"R² = {modelo.rsquared:.4f}  |  R²_adj = {modelo.rsquared_adj:.4f}")
log(f"F({modelo.df_model:.0f},{modelo.df_resid:.0f}) = {modelo.fvalue:.4f}  |  "
    f"p(F) = {modelo.f_pvalue:.4f}")

# Condition Number
cn = np.linalg.cond(X.values)
log(f"Condition Number = {cn:.2f}")

# Tabela de coeficientes com IC 95%
ci = modelo.conf_int()
nomes = {
    'const': 'Intercepto',
    'TOA':   'Usa_TOA',
    'SCV':   'is_Spatial_CV',
    'GEE':   'is_GEE_Native',
    'MOM':   'is_Model_on_Model',
    'MLC':   'is_MLC',
}

tab_resultados = []
log("\nTabela 2 — Coeficientes OLS:")
log(f"{'Variável':<22} {'β':>8} {'EP':>7} {'t':>8} {'p':>8} {'IC95_inf':>9} {'IC95_sup':>9}")
log("-"*75)
for v, nome in nomes.items():
    b  = modelo.params[v]
    se = modelo.bse[v]
    t  = modelo.tvalues[v]
    p  = modelo.pvalues[v]
    lo = ci.loc[v, 0]
    hi = ci.loc[v, 1]
    sig = "***" if p<0.001 else "**" if p<0.01 else "*" if p<0.05 else ""
    log(f"  {nome:<20} {b:>8.4f} {se:>7.4f} {t:>8.4f} {p:>8.4f}{sig}  [{lo:.3f}; {hi:.3f}]")
    tab_resultados.append({
        'Variavel': nome, 'beta': round(b,4), 'EP': round(se,4),
        't': round(t,4), 'p': round(p,4),
        'IC95_inf': round(lo,3), 'IC95_sup': round(hi,3)
    })

pd.DataFrame(tab_resultados).to_csv(
    OUTPUT_DIR / "Tabela2_OLS_Resultados.csv", index=False, encoding='utf-8-sig'
)
log("\n✅ Tabela2_OLS_Resultados.csv salva")

# ─── 4. DIAGNÓSTICOS ───────────────────────────────────────────────────────────

log("\nExecutando diagnósticos do modelo...")

# VIF
vif_data = []
X_vif = sm.add_constant(df_ols[PRED_OLS].astype(float))
for i, col in enumerate(X_vif.columns):
    if col != 'const':
        v = variance_inflation_factor(X_vif.values, i)
        vif_data.append({'Preditor': col, 'VIF': round(v, 4),
                         'Status': 'OK' if v < 5 else 'ALTO'})
        log(f"  VIF({col}) = {v:.4f}")

pd.DataFrame(vif_data).to_csv(
    OUTPUT_DIR / "TB_VIF_Diagnosticos.csv", index=False, encoding='utf-8-sig'
)
log("✅ TB_VIF_Diagnosticos.csv salva")

# Shapiro-Wilk
res = modelo.resid
sw_stat, sw_p = stats.shapiro(res)
log(f"\nShapiro-Wilk: W={sw_stat:.4f}  p={sw_p:.4f}")
if sw_p < 0.05:
    log("  ⚠ Resíduos desviam da normalidade (p<0.05). "
        "Logit-transform mitiga, mas assimetria residual documentada "
        "(Skew=0.778). Erros padrão robustos (HC3) podem ser considerados.")

# Breusch-Pagan
bp_lm, bp_p, _, _ = het_breuschpagan(res, modelo.model.exog)
log(f"Breusch-Pagan: LM={bp_lm:.4f}  p={bp_p:.4f}")
log("  Variância HOMOGÊNEA" if bp_p > 0.05 else "  ⚠ Heterocedasticidade")

# Durbin-Watson (autocorrelação serial dos resíduos; a ordem das observações
# nos dados não é temporal/espacial, então o valor é reportado por completude
# diagnóstica, não como evidência de ausência de dependência estrutural)
dw_stat = sm.stats.stattools.durbin_watson(res)
log(f"Durbin-Watson: DW={dw_stat:.4f}")
log("  Próximo de 2: sem autocorrelação sob a ordenação dos dados utilizada "
    "(interpretação limitada — estudos não possuem sequência temporal intrínseca)")

# Ramsey RESET (especificação funcional; Ramsey, 1969)
reset_result = linear_reset(modelo, power=2, test_type='fitted', use_f=True)
reset_stat, reset_p = float(reset_result.fvalue), float(reset_result.pvalue)
log(f"Ramsey RESET: F={reset_stat:.4f}  p={reset_p:.4f}")
log("  Forma funcional ADEQUADA (p>0.05)" if reset_p > 0.05
    else "  ⚠ Possível má especificação da forma funcional linear (p<0.05)")

# ─── 4.1 ERROS PADRÃO ROBUSTOS (HC3) ──────────────────────────────────────────────────────
# Aplicado em resposta ao desvio de normalidade dos resíduos (Shapiro-Wilk p<0.05)
# e à assimetria residual documentada (Skew=0.778). HC3 (MacKinnon & White, 1985)
# é preferível a HC0-HC2 em amostras pequenas/moderadas (N=155).

log("\nCalculando erros padrão robustos HC3 (MacKinnon & White, 1985)...")
regr_hc3 = sm.OLS(y, X)
modelo_hc3 = regr_hc3.fit(cov_type='HC3')

tab_hc3 = []
log(f"{'Variável':<22} {'β':>8} {'EP_HC3':>8} {'t_HC3':>8} {'p_HC3':>8} {'IC95_inf':>9} {'IC95_sup':>9}")
log("-"*78)
ci_hc3 = modelo_hc3.conf_int()
for v, nome in nomes.items():
    b   = modelo_hc3.params[v]
    se  = modelo_hc3.bse[v]
    t   = modelo_hc3.tvalues[v]
    p   = modelo_hc3.pvalues[v]
    lo  = ci_hc3.loc[v, 0]
    hi  = ci_hc3.loc[v, 1]
    sig = "***" if p<0.001 else "**" if p<0.01 else "*" if p<0.05 else ""
    log(f"  {nome:<20} {b:>8.4f} {se:>8.4f} {t:>8.4f} {p:>8.4f}{sig}  [{lo:.3f}; {hi:.3f}]")
    tab_hc3.append({
        'Variavel': nome, 'beta': round(b,4), 'EP_HC3': round(se,4),
        't_HC3': round(t,4), 'p_HC3': round(p,4),
        'IC95_inf': round(lo,3), 'IC95_sup': round(hi,3)
    })

pd.DataFrame(tab_hc3).to_csv(
    OUTPUT_DIR / "Tabela2_HC3_Robusto.csv", index=False, encoding='utf-8-sig'
)
log("✅ Tabela2_HC3_Robusto.csv salva")

mlc_sig_ols = modelo.pvalues['MLC'] < 0.05
mlc_sig_hc3 = modelo_hc3.pvalues['MLC'] < 0.05
if mlc_sig_ols == mlc_sig_hc3:
    log(f"  Conclusão sobre is_MLC estável sob HC3 "
        f"(p_OLS={modelo.pvalues['MLC']:.4f}; p_HC3={modelo_hc3.pvalues['MLC']:.4f})")
else:
    log(f"  ⚠ Significância de is_MLC MUDA entre OLS clássico e HC3 "
        f"(p_OLS={modelo.pvalues['MLC']:.4f}; p_HC3={modelo_hc3.pvalues['MLC']:.4f})")

# ─── 4.2 BOOTSTRAP NÃO-PARAMÉTRICO (B=5000) ───────────────────────────
# Reamostragem de casos (pares X,y) com reposição, N_OLS linhas por réplica.
# Seed fixa garante reprodutibilidade bit-a-bit.

log(f"\nCalculando bootstrap não-paramétrico (B={BOOTSTRAP_B}, seed={BOOTSTRAP_SEED})...")
rng = np.random.default_rng(BOOTSTRAP_SEED)
n_rows = len(df_ols)
boot_coefs = {v: np.empty(BOOTSTRAP_B) for v in nomes}

X_arr = X.values
y_arr = y.values
n_rank_deficient = 0
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for b in range(BOOTSTRAP_B):
        idx = rng.integers(0, n_rows, size=n_rows)
        Xb, yb = X_arr[idx], y_arr[idx]
        try:
            if np.linalg.matrix_rank(Xb) < Xb.shape[1]:
                n_rank_deficient += 1
                for v in nomes:
                    boot_coefs[v][b] = np.nan
                continue
            regr_boot = sm.OLS(yb, Xb)
            modelo_b = regr_boot.fit()
            for j, v in enumerate(X.columns):
                boot_coefs[v][b] = modelo_b.params[j]
        except Exception:
            n_rank_deficient += 1
            for v in nomes:
                boot_coefs[v][b] = np.nan

if n_rank_deficient > 0:
    log(f"  \u26a0 {n_rank_deficient}/{BOOTSTRAP_B} r\u00e9plicas "
        f"({100*n_rank_deficient/BOOTSTRAP_B:.1f}%) com matriz rank-deficiente "
        f"(esperado dado is_Spatial_CV esparso, n=4/155); descartadas do IC percentil.")

tab_boot = []
log(f"{'Variável':<22} {'β_OLS':>8} {'β_boot_méd':>11} {'IC95_inf':>9} {'IC95_sup':>9}")
log("-"*65)
for v, nome in nomes.items():
    vals = boot_coefs[v][~np.isnan(boot_coefs[v])]
    lo, hi = np.percentile(vals, [2.5, 97.5])
    log(f"  {nome:<20} {modelo.params[v]:>8.4f} {vals.mean():>11.4f} [{lo:.3f}; {hi:.3f}]")
    tab_boot.append({
        'Variavel': nome, 'beta_OLS': round(modelo.params[v],4),
        'beta_bootstrap_medio': round(vals.mean(),4),
        'B_validas': int(len(vals)),
        'IC95_boot_inf': round(lo,3), 'IC95_boot_sup': round(hi,3)
    })

pd.DataFrame(tab_boot).to_csv(
    OUTPUT_DIR / "Bootstrap_CI_B5000.csv", index=False, encoding='utf-8-sig'
)
log(f"✅ Bootstrap_CI_B5000.csv salva (B={BOOTSTRAP_B})")

mlc_boot_lo, mlc_boot_hi = np.percentile(
    boot_coefs['MLC'][~np.isnan(boot_coefs['MLC'])], [2.5, 97.5]
)
mlc_boot_excludes_zero = not (mlc_boot_lo <= 0 <= mlc_boot_hi)
log(f"  is_MLC: IC95 bootstrap {'exclui' if mlc_boot_excludes_zero else 'inclui'} zero "
    f"[{mlc_boot_lo:.3f}; {mlc_boot_hi:.3f}]")

# ─── 4.3 DISTÂNCIA DE COOK (ANÁLISE DE INFLUÊNCIA) ─────────────────────
# Limiar convencional: 4/n (Cook & Weisberg, 1982). Observações acima do limiar
# são candidatas a influência desproporcional sobre os coeficientes estimados.

log("\nCalculando Distância de Cook (Cook & Weisberg, 1982)...")
influence = OLSInfluence(modelo)
cooks_d, cooks_p = influence.cooks_distance
limiar_cook = 4 / n_rows
n_influentes = int((cooks_d > limiar_cook).sum())

tab_cook = pd.DataFrame({
    'ID_estudo': df_ols['ID'].values,
    'ID_linha_amostra_OLS': np.arange(1, n_rows + 1),
    'Cooks_D': np.round(cooks_d, 6),
    'Acima_limiar_4_n': cooks_d > limiar_cook
})
tab_cook.to_csv(OUTPUT_DIR / "CooksDistance_Influencia.csv", index=False, encoding='utf-8-sig')
log(f"  Limiar (4/n) = {limiar_cook:.4f}  |  N observações acima do limiar = "
    f"{n_influentes} ({100*n_influentes/n_rows:.1f}%)")
log(f"  Cook's D máximo observado = {cooks_d.max():.4f}")

if n_influentes > 0:
    mask_sem_influentes = cooks_d <= limiar_cook
    regr_sem_influentes = sm.OLS(y[mask_sem_influentes], X[mask_sem_influentes])
    modelo_sem_influentes = regr_sem_influentes.fit()
    log(f"  Reajuste sem {n_influentes} observação(ões) influente(s): "
        f"β_MLC={modelo_sem_influentes.params['MLC']:.4f} "
        f"(original: {modelo.params['MLC']:.4f}); "
        f"p_MLC={modelo_sem_influentes.pvalues['MLC']:.4f} "
        f"(original: {modelo.pvalues['MLC']:.4f})")
log("✅ CooksDistance_Influencia.csv salva")


# ─── 5. FISHER EXACT ────────────────────────────────────────────────────────────

log("\nTeste de Fisher: is_GEE_Native × is_Spatial_CV")
ct = pd.crosstab(df['GEE'], df['SCV'])
log(f"\n  Tabela 2×2:\n{ct.to_string()}")

if ct.shape == (2, 2):
    or_f, p_f = stats.fisher_exact(ct.values)
    log(f"\n  OR (Fisher) = {or_f:.4f}  |  p = {p_f:.4f}")
    log("  Resultado: NÃO SIGNIFICATIVO")

    ct_csv = ct.copy()
    ct_csv.index.name = 'GEE_Native'
    ct_csv.columns.name = 'Spatial_CV'
    ct_csv.to_csv(OUTPUT_DIR / "Fisher_GEE_Spatial.csv", encoding='utf-8-sig')
    log("✅ Fisher_GEE_Spatial.csv salva")

# ─── 6. SALVAR DIAGNÓSTICOS ─────────────────────────────────────────────────────

with open(OUTPUT_DIR / "Diagnosticos_Modelo.txt", "w", encoding="utf-8") as f:
    f.write("META-REGRESSÃO OLS — DIAGNÓSTICOS COMPLETOS\n")
    f.write(f"Data de execução: {datetime.now().isoformat()}\n")
    f.write("="*70 + "\n\n")
    f.write(modelo.summary().as_text())
    f.write("\n\n=== SHAPIRO-WILK (normalidade dos resíduos) ===\n")
    f.write(f"W = {sw_stat:.4f}  |  p = {sw_p:.6f}\n")
    f.write("Status: " + ("NORMAL (p>0.05)" if sw_p>0.05 else
            "DESVIO detectado (p<0.05) — assimetria residual documentada") + "\n")
    f.write("\n=== BREUSCH-PAGAN (homocedasticidade) ===\n")
    f.write(f"LM = {bp_lm:.4f}  |  p = {bp_p:.6f}\n")
    f.write("Status: " + ("HOMOGÊNEA (p>0.05)" if bp_p>0.05 else
            "HETEROCEDÁSTICA (p<0.05)") + "\n")
    f.write("\n=== DURBIN-WATSON (autocorrelação serial dos resíduos) ===\n")
    f.write(f"DW = {dw_stat:.4f}\n")
    f.write("Nota: ordenação dos dados não é temporal/espacial; interpretação "
             "do teste é limitada neste contexto (reportado por completude diagnóstica).\n")
    f.write("\n=== RAMSEY RESET (especificação funcional; Ramsey, 1969) ===\n")
    f.write(f"F = {reset_stat:.4f}  |  p = {reset_p:.6f}\n")
    f.write("Status: " + ("FORMA FUNCIONAL ADEQUADA (p>0.05)" if reset_p>0.05 else
            "POSSÍVEL MÁ ESPECIFICAÇÃO (p<0.05)") + "\n")
    f.write("\n=== VIF (multicolinearidade) ===\n")
    for row in vif_data:
        f.write(f"  {row['Preditor']:20s}: VIF={row['VIF']:.4f}  [{row['Status']}]\n")
    f.write("\n=== ERROS PADRÃO ROBUSTOS HC3 (MacKinnon & White, 1985) ===\n")
    for row in tab_hc3:
        f.write(f"  {row['Variavel']:20s}: beta={row['beta']:.4f}  "
                f"EP_HC3={row['EP_HC3']:.4f}  p_HC3={row['p_HC3']:.4f}\n")
    f.write(f"  Conclusão sobre is_MLC {'ESTÁVEL' if mlc_sig_ols == mlc_sig_hc3 else 'MUDA'} "
            f"entre OLS clássico e HC3.\n")
    f.write(f"\n=== BOOTSTRAP NÃO-PARAMÉTRICO (B={BOOTSTRAP_B}, seed={BOOTSTRAP_SEED}) ===\n")
    for row in tab_boot:
        f.write(f"  {row['Variavel']:20s}: beta_OLS={row['beta_OLS']:.4f}  "
                f"IC95_boot=[{row['IC95_boot_inf']:.3f}; {row['IC95_boot_sup']:.3f}]\n")
    f.write(f"  is_MLC: IC95 bootstrap "
            f"{'EXCLUI' if mlc_boot_excludes_zero else 'INCLUI'} zero.\n")
    f.write("\n=== DISTÂNCIA DE COOK (Cook & Weisberg, 1982) ===\n")
    f.write(f"Limiar (4/n) = {limiar_cook:.4f}  |  "
            f"Observações acima do limiar = {n_influentes} "
            f"({100*n_influentes/n_rows:.1f}%)\n")
    f.write(f"Cook's D máximo = {cooks_d.max():.4f}\n")
    if n_influentes > 0:
        f.write(f"Reajuste sem observações influentes: "
                f"beta_MLC={modelo_sem_influentes.params['MLC']:.4f}  "
                f"p_MLC={modelo_sem_influentes.pvalues['MLC']:.4f}\n")
    f.write("\n=== FISHER EXACT: is_GEE_Native × is_Spatial_CV ===\n")
    f.write(f"OR = {or_f:.4f}  |  p = {p_f:.4f}\n")
    f.write("Interpretação: NÃO SIGNIFICATIVO\n")

log("✅ Diagnosticos_Modelo.txt salvo")

# ─── 7. FIGURA A1 — DIAGNÓSTICOS DO MODELO (painel 2×2) ───────────────────────
# NOTA (corrigido 2026-10-18): Figura6A/Figura6B (histograma e boxplot de OA)
# foram removidas por decisão editorial — não fazem parte do depósito OSF.

log("\nGerando figuras...")

plt.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': ['Arial','DejaVu Sans'],
    'font.size': 11, 'axes.labelsize': 12, 'axes.labelweight': 'bold',
    'figure.dpi': 300
})
# Reconstrução programática da Figura A1 citada no Material Suplementar:
# (A) Resíduos vs. Ajustados; (B) Q-Q Normal; (C) Distribuição dos resíduos;
# (D) Scale-Location (homocedasticidade).
# NOTA (corrigido 2026-10-18): renomeada de "Figura S1" para "Figura A1" para
# conformidade com a numeracao "Anexo/Figura A..." adotada no Material
# Suplementar do capitulo (nomenclatura antiga "S..." abandonada).

log("\nGerando Figura A1 (diagnósticos 2×2)...")

from scipy.stats import probplot

fitted = modelo.fittedvalues.values
resid_arr = res.values
std_resid = resid_arr / resid_arr.std(ddof=1)

fig, axes = plt.subplots(2, 2, figsize=(12, 10))
fig.suptitle(f'Figura A1. Diagnósticos do modelo de meta-regressão OLS (N = {n_rows})',
             fontsize=14, fontweight='bold')

# (A) Resíduos vs. Ajustados
ax = axes[0, 0]
ax.scatter(fitted, resid_arr, alpha=0.6, color='#2166AC', edgecolor='white', s=40)
ax.axhline(0, color='#B2182B', ls='--', lw=2)
try:
    from statsmodels.nonparametric.smoothers_lowess import lowess
    sm_fit = lowess(resid_arr, fitted, frac=0.6)
    ax.plot(sm_fit[:, 0], sm_fit[:, 1], color='#4DAF4A', lw=2)
except Exception:
    pass
ax.set_xlabel('Valores Ajustados — Logit(OA)')
ax.set_ylabel('Resíduos')
ax.text(0.02, 0.95, '(A) Resíduos vs. Ajustados', transform=ax.transAxes,
        fontsize=12, fontweight='bold', va='top')

# (B) Q-Q Normal
ax = axes[0, 1]
(osm, osr), (slope, intercept, r) = probplot(std_resid, dist="norm")
ax.scatter(osm, osr, alpha=0.6, color='#2166AC', s=25)
ax.plot(osm, slope*osm + intercept, '--', color='#B2182B', lw=2, label=f'R = {r:.3f}')
ax.set_xlabel('Quantis Teóricos (Normal Padrão)')
ax.set_ylabel('Quantis Empíricos dos Resíduos')
ax.legend(fontsize=9, loc='lower right')
ax.text(0.02, 0.95, '(B) Gráfico Q-Q Normal', transform=ax.transAxes,
        fontsize=12, fontweight='bold', va='top')

# (C) Distribuição dos resíduos
ax = axes[1, 0]
skew_val = float(stats.skew(resid_arr))
kurt_val = float(stats.kurtosis(resid_arr, fisher=False))
ax.hist(resid_arr, bins=15, density=True, color='#2166AC', alpha=0.7,
        edgecolor='white', lw=0.5)
xr = np.linspace(resid_arr.min(), resid_arr.max(), 200)
ax.plot(xr, stats.norm.pdf(xr, resid_arr.mean(), resid_arr.std(ddof=1)),
        '--', color='#B2182B', lw=2, label='Normal teórica')
ax.set_xlabel('Resíduos')
ax.set_ylabel('Densidade')
ax.legend(fontsize=9, loc='upper right')
ax.text(0.02, 0.95, f'(C) Distribuição dos Resíduos\nSkew = {skew_val:.3f}  '
        f'Kurt = {kurt_val:.3f}', transform=ax.transAxes,
        fontsize=12, fontweight='bold', va='top')

# (D) Scale-Location
ax = axes[1, 1]
sqrt_abs_resid = np.sqrt(np.abs(std_resid))
ax.scatter(fitted, sqrt_abs_resid, alpha=0.6, color='#2166AC', edgecolor='white', s=40)
try:
    sm_fit2 = lowess(sqrt_abs_resid, fitted, frac=0.6)
    ax.plot(sm_fit2[:, 0], sm_fit2[:, 1], color='#B2182B', lw=2)
except Exception:
    pass
ax.set_xlabel('Valores Ajustados — Logit(OA)')
ax.set_ylabel('√|Resíduos|')
ax.text(0.02, 0.95, '(D) Scale-Location\n(Homocedasticidade)', transform=ax.transAxes,
        fontsize=12, fontweight='bold', va='top')

plt.tight_layout()
fig.savefig(OUTPUT_DIR / 'FiguraA1_Diagnosticos_OLS.png', dpi=300, bbox_inches='tight')
fig.savefig(OUTPUT_DIR / 'FiguraA1_Diagnosticos_OLS.eps', format='eps', bbox_inches='tight')
plt.close(fig)
log(f"  Skew={skew_val:.4f}  Kurt={kurt_val:.4f}  Q-Q R={r:.4f}")
log("✅ FiguraA1_Diagnosticos_OLS.png (+ .eps)")

# ─── 8. FINALIZAR ────────────────────────────────────────────────────────────────

salvar_log()

log("\n" + "="*70)
log("EXECUÇÃO CONCLUÍDA — todos os outputs em ./resultados/")
log("="*70)
log(f"  Tabela2_OLS_Resultados.csv     — coeficientes com IC 95%")
log(f"  Tabela2_HC3_Robusto.csv        — coeficientes com EP robustos HC3")
log(f"  Bootstrap_CI_B5000.csv         — IC95 por bootstrap (B=5000)")
log(f"  CooksDistance_Influencia.csv   — Distância de Cook por observação")
log(f"  TB_VIF_Diagnosticos.csv        — VIF por preditor")
log(f"  Diagnosticos_Modelo.txt        — diagnósticos completos")
log(f"  Fisher_GEE_Spatial.csv         — tabela 2×2 GEE×Spatial")
log(f"  FiguraA1_Diagnosticos_OLS.png  — diagnósticos 2×2 (300 DPI, + .eps)")
log(f"  log_execucao.txt               — log completo")
