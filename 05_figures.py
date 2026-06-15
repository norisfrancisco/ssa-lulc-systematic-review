#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIGURAS DA SEÇÃO 3 — DADOS REAIS (N=164)
Protocolo V2.1 | Revisão Sistemática LULC África Subsaariana
"""
from pathlib import Path
_ROOT     = Path(__file__).parent.parent
DATA_PATH = str(_ROOT / "data" / "dados_LIMPOS_metaregressao.xlsx")
OUT_DIR   = _ROOT / "outputs"
OUT_DIR.mkdir(exist_ok=True)

def _o(name):
    """Helper: retorna path completo para arquivo de output."""
    return str(OUT_DIR / name)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from matplotlib.patches import FancyBboxPatch

# ============ CONFIGURAÇÃO GLOBAL ============
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'DejaVu Sans'],
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.labelweight': 'bold',
    'axes.titlesize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.dpi': 300,
})

# ============ CARREGAR DADOS ============
df = pd.read_excel(DATA_PATH)
df.columns = [c.replace('\n','_').replace(' ','_').replace('★_','') for c in df.columns]
df['Ano'] = pd.to_numeric(df['Ano'], errors='coerce')
df_oa = df[df['OA_PERCENT'].notna()]

# ============ FIGURA 2: EVOLUÇÃO TEMPORAL (A e B) ============
fig, (ax_a, ax_b) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'hspace': 0.35})

# --- Painel A: Evolução Temporal por Geração Algorítmica ---
gen_map = {1: 'GEN1 Paramétrico', 2: 'GEN2 Machine Learning', 3: 'GEN3 Deep Learning', 4: 'GEN4 Híbrido'}
cores_gen = {1: '#2166AC', 2: '#B2182B', 3: '#4DAF4A', 4: '#FF7F00'}

anos = sorted(df['Ano'].dropna().unique())
gen_counts = pd.crosstab(df['Ano'], df['GEN_Algoritmo'])

bottom = np.zeros(len(anos))
for gen in [1, 2, 3, 4]:
    if gen in gen_counts.columns:
        vals = [gen_counts.loc[a, gen] if a in gen_counts.index and gen in gen_counts.columns else 0 for a in anos]
        ax_a.bar(anos, vals, bottom=bottom, color=cores_gen[gen], label=gen_map[gen], alpha=0.85, width=0.7)
        bottom += vals

ax_a.set_ylabel('Frequência')
ax_a.set_xlabel('')
ax_a.legend(loc='upper left', frameon=True, framealpha=0.9)
ax_a.spines['top'].set_visible(False)
ax_a.spines['right'].set_visible(False)
ax_a.text(0.02, 0.95, '(A)', transform=ax_a.transAxes, fontsize=14, fontweight='bold', va='top')

# Marcos tecnológicos
ax_a.axvline(x=2008, color='gray', ls='--', lw=1, alpha=0.6)
ax_a.axvline(x=2013, color='gray', ls='--', lw=1, alpha=0.6)
ax_a.axvline(x=2017, color='gray', ls='--', lw=1, alpha=0.6)
ax_a.text(2008.2, ax_a.get_ylim()[1]*0.9, 'GEE\nlançamento', fontsize=8, color='gray')
ax_a.text(2013.2, ax_a.get_ylim()[1]*0.9, 'Landsat\nopen access', fontsize=8, color='gray')
ax_a.text(2017.2, ax_a.get_ylim()[1]*0.9, 'Landsat\nARD/Col.1', fontsize=8, color='gray')

# --- Painel B: Volume Anual Acumulado ---
vol_anual = df['Ano'].value_counts().sort_index()
ax_b.bar(vol_anual.index, vol_anual.values, color='#2166AC', alpha=0.7, width=0.7)
ax_b.plot(vol_anual.index, vol_anual.values.cumsum()/len(df)*100, 
          color='#B2182B', lw=2, marker='o', ms=4, label='Acumulado (%)')
ax_b2 = ax_b.twinx()
ax_b2.set_ylabel('Acumulado (%)', fontsize=12, fontweight='bold')
ax_b2.plot(vol_anual.index, vol_anual.values.cumsum()/len(df)*100, 
           color='#B2182B', lw=2, marker='o', ms=4)
ax_b2.set_ylim(0, 105)
ax_b2.spines['top'].set_visible(False)

ax_b.set_ylabel('Artigos por ano')
ax_b.set_xlabel('Ano de publicação')
ax_b.spines['top'].set_visible(False)
ax_b.spines['right'].set_visible(False)
ax_b.text(0.02, 0.95, '(B)', transform=ax_b.transAxes, fontsize=14, fontweight='bold', va='top')

plt.savefig(_o('Figura_2_evolucao_temporal.png'), dpi=300, bbox_inches='tight')
plt.savefig(_o('Figura_2_evolucao_temporal.eps'), format='eps', bbox_inches='tight')
plt.close()
print("✓ Figura 2 salva")


# ============ FIGURA 4: DISTRIBUIÇÃO ALGORÍTMICA ============
fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={'wspace': 0.35})

# --- Painel A: Por Geração ---
gen_data = df['GEN_Algoritmo'].value_counts().sort_index()
labels_gen = ['GEN1\nParamétrico', 'GEN2\nMachine Learning', 'GEN3\nDeep Learning', 'GEN4\nHíbrido']
cores = ['#2166AC', '#B2182B', '#4DAF4A', '#FF7F00']
bars = ax_a.bar(range(len(gen_data)), gen_data.values, color=cores, alpha=0.85, width=0.6)
for bar, val in zip(bars, gen_data.values):
    ax_a.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
              f'{val}\n({val/len(df)*100:.1f}%)', ha='center', va='bottom', fontsize=10, fontweight='bold')
ax_a.set_xticks(range(len(gen_data)))
ax_a.set_xticklabels(labels_gen)
ax_a.set_ylabel('Frequência')
ax_a.spines['top'].set_visible(False)
ax_a.spines['right'].set_visible(False)
ax_a.text(0.02, 0.95, '(A)', transform=ax_a.transAxes, fontsize=14, fontweight='bold', va='top')

# --- Painel B: Flags de Risco ---
flag_labels = ['F0\nis_MLC', 'F1\nUsa_TOA', 'F2\nGEE_Native', 'F4\nModel_on_Model', 'F5\nSpatial_CV']
flag_cols = ['is_MLC_(F0)', 'Usa_TOA_(F1)', 'GEE_Native_(F2)', 'ModelOnModel_(F4)', 'Spatial_CV_(F5)']
flag_vals = [int(df[c].sum()) for c in flag_cols]
flag_pcts = [v/len(df)*100 for v in flag_vals]

cores_flag = ['#B2182B' if p > 30 else '#FF7F00' if p > 10 else '#2166AC' for p in flag_pcts]
bars = ax_b.barh(range(len(flag_labels)), flag_vals, color=cores_flag, alpha=0.85, height=0.6)
for bar, val, pct in zip(bars, flag_vals, flag_pcts):
    ax_b.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
              f'{val} ({pct:.1f}%)', va='center', fontsize=10, fontweight='bold')
ax_b.set_yticks(range(len(flag_labels)))
ax_b.set_yticklabels(flag_labels)
ax_b.set_xlabel('Frequência (artigos com flag=1)')
ax_b.spines['top'].set_visible(False)
ax_b.spines['right'].set_visible(False)
ax_b.text(0.02, 0.95, '(B)', transform=ax_b.transAxes, fontsize=14, fontweight='bold', va='top')

plt.savefig(_o('Figura_4_distribuicao_algoritmica_flags.png'), dpi=300, bbox_inches='tight')
plt.savefig(_o('Figura_4_distribuicao_algoritmica_flags.eps'), format='eps', bbox_inches='tight')
plt.close()
print("✓ Figura 4 salva")


# ============ FIGURA 5: DISTRIBUIÇÃO GEOGRÁFICA ============
fig, ax = plt.subplots(figsize=(12, 6))

pais = df['País'].value_counts()
top10 = pais.head(10)
cores_pais = ['#B2182B' if v > 20 else '#FF7F00' if v > 5 else '#2166AC' for v in top10.values]
bars = ax.barh(range(len(top10)), top10.values, color=cores_pais, alpha=0.85, height=0.6)
for bar, val in zip(bars, top10.values):
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
            f'{val} ({val/len(df)*100:.1f}%)', va='center', fontsize=10, fontweight='bold')
ax.set_yticks(range(len(top10)))
ax.set_yticklabels(top10.index)
ax.invert_yaxis()
ax.set_xlabel('Número de artigos')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.savefig(_o('Figura_5_distribuicao_geografica.png'), dpi=300, bbox_inches='tight')
plt.savefig(_o('Figura_5_distribuicao_geografica.eps'), format='eps', bbox_inches='tight')
plt.close()
print("✓ Figura 5 salva")


# ============ FIGURA 6: DISTRIBUIÇÃO OA + BOXPLOT POR GERAÇÃO ============
fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={'wspace': 0.3})

# Painel A: Histograma OA
ax_a.hist(df_oa['OA_PERCENT'], bins=15, color='#2166AC', alpha=0.7, edgecolor='white', lw=0.5)
ax_a.axvline(x=df_oa['OA_PERCENT'].mean(), color='#B2182B', ls='--', lw=2, label=f'Média={df_oa["OA_PERCENT"].mean():.1f}%')
ax_a.axvline(x=df_oa['OA_PERCENT'].median(), color='#4DAF4A', ls='--', lw=2, label=f'Mediana={df_oa["OA_PERCENT"].median():.1f}%')
ax_a.axvline(x=90, color='gray', ls=':', lw=1.5, label='Limiar 90%')
ax_a.set_xlabel('Overall Accuracy (%)')
ax_a.set_ylabel('Frequência')
ax_a.legend(fontsize=9, loc='upper left')
ax_a.spines['top'].set_visible(False)
ax_a.spines['right'].set_visible(False)
ax_a.text(0.02, 0.95, '(A)', transform=ax_a.transAxes, fontsize=14, fontweight='bold', va='top')

# Painel B: Boxplot OA por Geração
gen_map_short = {1: 'GEN1\nParamétrico', 2: 'GEN2\nML', 3: 'GEN3\nDL', 4: 'GEN4\nHíbrido'}
df_oa_gen = df_oa.copy()
df_oa_gen['Gen_Label'] = df_oa_gen['GEN_Algoritmo'].map(gen_map_short)
order = ['GEN1\nParamétrico', 'GEN2\nML', 'GEN3\nDL', 'GEN4\nHíbrido']
existing = [o for o in order if o in df_oa_gen['Gen_Label'].unique()]
sns.boxplot(data=df_oa_gen, x='Gen_Label', y='OA_PERCENT', order=existing, 
            palette=['#2166AC','#B2182B','#4DAF4A','#FF7F00'], ax=ax_b, width=0.5)
ax_b.axhline(y=90, color='gray', ls=':', lw=1.5)
ax_b.set_xlabel('Geração Algorítmica')
ax_b.set_ylabel('Overall Accuracy (%)')
ax_b.spines['top'].set_visible(False)
ax_b.spines['right'].set_visible(False)
ax_b.text(0.02, 0.95, '(B)', transform=ax_b.transAxes, fontsize=14, fontweight='bold', va='top')

plt.savefig(_o('Figura_6_distribuicao_OA.png'), dpi=300, bbox_inches='tight')
plt.savefig(_o('Figura_6_distribuicao_OA.eps'), format='eps', bbox_inches='tight')
plt.close()
print("✓ Figura 6 salva")


# ============ FIGURA 7: SENSORES ============
fig, ax = plt.subplots(figsize=(10, 5))

landsat = df['Sensor'].str.contains('Landsat|L5|L7|L8|L9', case=False, na=False).sum()
sentinel = df['Sensor'].str.contains('Sentinel|S2|S1', case=False, na=False).sum()
multi = df['Sensor'].str.contains('Landsat.*Sentinel|Sentinel.*Landsat', case=False, na=False).sum()
outros = len(df) - landsat - sentinel + multi  # evitar dupla contagem

sensors = ['Landsat\n(exclusivo)', 'Sentinel\n(exclusivo)', 'Landsat+Sentinel\n(combinado)', 'Outros']
vals = [landsat - multi, sentinel - multi, multi, outros]
cores_s = ['#2166AC', '#B2182B', '#4DAF4A', '#FF7F00']
bars = ax.bar(range(len(sensors)), vals, color=cores_s, alpha=0.85, width=0.55)
for bar, val in zip(bars, vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            f'{val}\n({val/len(df)*100:.1f}%)', ha='center', va='bottom', fontsize=10, fontweight='bold')
ax.set_xticks(range(len(sensors)))
ax.set_xticklabels(sensors)
ax.set_ylabel('Frequência')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.savefig(_o('Figura_7_sensores.png'), dpi=300, bbox_inches='tight')
plt.savefig(_o('Figura_7_sensores.eps'), format='eps', bbox_inches='tight')
plt.close()
print("✓ Figura 7 salva")

print("\n✓ Todas as figuras geradas com dados reais (N=164)")
print("  → Figura_2: Evolução temporal (painéis A + B)")
print("  → Figura_4: Distribuição algorítmica + Flags (painéis A + B)")
print("  → Figura_5: Distribuição geográfica (top 10 países)")
print("  → Figura_6: Distribuição OA + Boxplot por Geração (painéis A + B)")
print("  → Figura_7: Sensores por família")
