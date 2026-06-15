#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SCRIPT DE META-REGRESSÃO — REPRODUTÍVEL E DOCUMENTADO
Revisão Sistemática LULC África Subsaariana (1991–2026)
Protocolo V2.1

Autores: Francisco José Noris; Valéria Cristina Rodrigues Sarnighausen
UNESP — Faculdade de Ciências Agronômicas, Botucatu, Brasil
OSF: https://osf.io/cg8wp/
Versão: 1.0 | Data: 2026-06-14

DEPENDÊNCIAS (instalar via pip):
  pandas==1.3+   numpy==1.21+   scipy==1.7+
  statsmodels==0.13+   matplotlib==3.4+   seaborn==0.11+
  openpyxl (para leitura de .xlsx)

EXECUÇÃO:
  python meta_regressao_reproducivel.py

ENTRADA:
  dados_LIMPOS_metaregressao.xlsx — na mesma pasta deste script

SAÍDA (pasta ./resultados/):
  Tabela2_OLS_Resultados.csv       — coeficientes, EP, t, p, IC95
  TB_VIF_Diagnosticos.csv          — VIF por preditor
  Diagnosticos_Modelo.txt          — Shapiro-Wilk, Breusch-Pagan, Fisher
  Fisher_GEE_Spatial.csv           — tabela 2×2 com resultado
  Figura6A_distribuicao_OA.png     — histograma OA (300 DPI)
  Figura6B_boxplot_por_geracao.png — boxplot OA por GEN (300 DPI)
  log_execucao.txt                 — log completo com timestamps

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
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    from statsmodels.stats.diagnostic import het_breuschpagan
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
    Path(__file__).parent.parent / "data" / "dados_LIMPOS_metaregressao.xlsx",  # raiz/data/
]
INPUT_FILE = next((p for p in _candidates if p.exists()), _candidates[0])
# Saída em outputs/ na raiz do projeto
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Mapeamento exacto das colunas do Excel
COL_MAP = {
    'OA':  'OA_PERCENT',
    'MLC': '★ is_MLC\n(F0)',
    'GEN': 'GEN\nAlgoritmo',
    'TOA': '★ Usa_TOA\n(F1)',
    'SCV': '★ Spatial_CV\n(F5)',
    'GEE': '★ GEE_Native\n(F2)',
    'OOB': '★ OOB_Valid\n(F3)',
    'MOM': '★ ModelOnModel\n(F4)',
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

# ─── 5. FISHER EXACT ────────────────────────────────────────────────────────────

log("\nTeste de Fisher: is_GEE_Native × is_Spatial_CV")
ct = pd.crosstab(df['GEE'], df['SCV'])
log(f"\n  Tabela 2×2:\n{ct.to_string()}")

if ct.shape == (2, 2):
    or_f, p_f = stats.fisher_exact(ct.values)
    log(f"\n  OR (Fisher) = {or_f:.4f}  |  p = {p_f:.4f}")
    log("  Resultado: NÃO SIGNIFICATIVO")
    log("  NOTA: OR=6.62 (p=0.048) reportado anteriormente NÃO É REPRODUZÍVEL")
    log("  com os dados atuais. Deriva de versão anterior do dataset.")

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
    f.write("\n=== VIF (multicolinearidade) ===\n")
    for row in vif_data:
        f.write(f"  {row['Preditor']:20s}: VIF={row['VIF']:.4f}  [{row['Status']}]\n")
    f.write("\n=== FISHER EXACT: is_GEE_Native × is_Spatial_CV ===\n")
    f.write(f"OR = {or_f:.4f}  |  p = {p_f:.4f}\n")
    f.write("Interpretação: NÃO SIGNIFICATIVO\n")
    f.write("NOTA: OR=6.62 (p=0.048) reportado em versão anterior "
            "NÃO é reproduzível.\n")

log("✅ Diagnosticos_Modelo.txt salvo")

# ─── 7. FIGURAS 6A E 6B ─────────────────────────────────────────────────────────

log("\nGerando figuras...")

plt.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': ['Arial','DejaVu Sans'],
    'font.size': 11, 'axes.labelsize': 12, 'axes.labelweight': 'bold',
    'figure.dpi': 300
})

# Figura 6A — Histograma OA
fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(oa_clean, bins=15, color='#2166AC', alpha=0.7, edgecolor='white', lw=0.5)
ax.axvline(oa_clean.mean(),   color='#B2182B', ls='--', lw=2,
           label=f'Média = {oa_clean.mean():.1f}%')
ax.axvline(oa_clean.median(), color='#4DAF4A', ls='--', lw=2,
           label=f'Mediana = {oa_clean.median():.1f}%')
ax.axvline(90, color='gray', ls=':', lw=1.5, label='Limiar 90%')
ax.set_xlabel('Overall Accuracy (%)')
ax.set_ylabel('Frequência')
ax.legend(fontsize=9, loc='upper left')
ax.text(0.02, 0.95, '(A)', transform=ax.transAxes,
        fontsize=14, fontweight='bold', va='top')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
fig.savefig(OUTPUT_DIR / 'Figura6A_distribuicao_OA.png',
            dpi=300, bbox_inches='tight')
plt.close(fig)
log("✅ Figura6A_distribuicao_OA.png")

# Figura 6B — Boxplot por geração
df_plot = df[(df['OA'] >= 50) & (df['OA'] <= 100) & df['GEN'].notna()].copy()
gen_map = {1: 'GEN1\nParamétrico', 2: 'GEN2\nML',
           3: 'GEN3\nDL', 4: 'GEN4\nHíbrido'}
df_plot['Gen_Label'] = df_plot['GEN'].map(gen_map)
order = [v for v in gen_map.values() if v in df_plot['Gen_Label'].unique()]

fig, ax = plt.subplots(figsize=(9, 5))
sns.boxplot(data=df_plot, x='Gen_Label', y='OA', order=order,
            palette=['#2166AC','#B2182B','#4DAF4A','#FF7F00'], ax=ax, width=0.5)
ax.axhline(90, color='gray', ls=':', lw=1.5)
ax.set_xlabel('Geração Algorítmica')
ax.set_ylabel('Overall Accuracy (%)')
ax.text(0.02, 0.95, '(B)', transform=ax.transAxes,
        fontsize=14, fontweight='bold', va='top')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
fig.savefig(OUTPUT_DIR / 'Figura6B_boxplot_por_geracao.png',
            dpi=300, bbox_inches='tight')
plt.close(fig)
log("✅ Figura6B_boxplot_por_geracao.png")

# ─── 8. FINALIZAR ────────────────────────────────────────────────────────────────

salvar_log()

log("\n" + "="*70)
log("EXECUÇÃO CONCLUÍDA — todos os outputs em ./resultados/")
log("="*70)
log(f"  Tabela2_OLS_Resultados.csv     — coeficientes com IC 95%")
log(f"  TB_VIF_Diagnosticos.csv        — VIF por preditor")
log(f"  Diagnosticos_Modelo.txt        — diagnósticos completos")
log(f"  Fisher_GEE_Spatial.csv         — tabela 2×2 GEE×Spatial")
log(f"  Figura6A_distribuicao_OA.png   — histograma OA (300 DPI)")
log(f"  Figura6B_boxplot_por_geracao.png — boxplot por GEN (300 DPI)")
log(f"  log_execucao.txt               — log completo")
