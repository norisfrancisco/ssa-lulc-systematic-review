#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
                     REVISÃO SISTEMÁTICA LULC - FASE 2
              SCREENING FLEXÍVEL COM REGEX (CRITÉRIOS RELAXADOS)
                              (VERSÃO 3.0 RELAXADA)
================================================================================

Script: FASE_2_regex_relaxado_v3.py
Versão: 3.0 (Menos rigoroso, mais inclusivo)
Data: 2026-06-02
Autor: Revisão Sistemática LULC-SSA

MUDANÇAS V3.0 (RELAXADO):
  ✅ D1 (TERRITORIAL) + D4 (SENSORIAMENTO) = OBRIGATÓRIOS
  ✅ D2a, D2b, D2c, D3 = MENOS RIGOROSOS (OR em vez de AND)
  ✅ Mais keywords científicas adicionadas
  ✅ Permite artigos só com título bom (sem resumo)
  ✅ Aceita proxies se tiver machine learning

OBJETIVO:
  Aumentar elegíveis de ~75 para ~150-200

ENTRADA:
  • 01_deduplicacao/artigos.txt

SAÍDA:
  • 02_regex_screening_v3/elegíveis.txt (~150-200)
  • 02_regex_screening_v3/relatorio_screening.txt
  • 02_regex_screening_v3/log.txt

================================================================================
"""

import re
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# ═════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO CENTRALIZADA
# ═════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path.cwd()

CONFIG = {
    'versao_script': '3.0',
    'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
    
    'input_dir': BASE_DIR / '01_deduplicacao',
    'output_dir': BASE_DIR / '02_regex_screening_v3',
    'input_file': 'artigos.txt',
    
    'criterios': {
        'D1_territorial': 'Geografia (África Subsaariana) - OBRIGATÓRIO',
        'D2_dinamica': 'Série temporal OU mudança OU monitoramento',
        'D3_lulc': 'LULC OU classificação de cobertura de solo',
        'D4_ml': 'Machine Learning OU classificação automática',
        'D5_sensoriamento': 'Satélite OU sensoriamento remoto - OBRIGATÓRIO',
    }
}

CONFIG['output_dir'].mkdir(parents=True, exist_ok=True)

print("="*80)
print("FASE 2: SCREENING RELAXADO v3.0 (MENOS RIGOROSO)")
print("="*80 + "\n")

# ═════════════════════════════════════════════════════════════════════════════
# DOMÍNIOS CIENTÍFICOS (VERSÃO RELAXADA)
# ═════════════════════════════════════════════════════════════════════════════

DOMINIOS = {
    'D1_TERRITORIAL': {
        'nome': 'TERRITORIAL - Geografia (OBRIGATÓRIO)',
        'obrigatorio': True,
        'termos': [
            # África Subsaariana geral
            'sub-saharan africa', 'sub saharan', 'subsaharan', 'sub-saharan',
            'southern africa', 'east africa', 'west africa', 'central africa',
            'sahel',
            
            # Países específicos (lista completa)
            'mozambique', 'moçambique', 'mocambique',
            'tanzania', 'tanzânia', 'tanzan',
            'kenya', 'kenia',
            'uganda', 'uganda',
            'zambia', 'zâmbia', 'zamb',
            'zimbabwe', 'zimbabw',
            'malawi', 'malau',
            'botswana', 'botsw',
            'namibia', 'namib',
            'south africa', 'africa do sul', 'south afric',
            'lesotho', 'lesoto',
            'eswatini', 'swaziland',
            
            # Outros países SSA
            'ethiopia', 'etiópia', 'etiop',
            'ghana', 'gana',
            'nigeria', 'nigéria', 'nige',
            'senegal', 'senegambia',
            'côte d\'ivoire', 'cote d\'ivoire', 'ivory coast',
            'cameroon', 'cameroun', 'camarao',
            'gabon', 'congo', 'dr congo', 'drc',
            'guinea', 'guinea-bissau',
            'liberia', 'sierra leone',
            'mali', 'burkina faso', 'benin', 'togo',
            'madagascar', 'malagasy',
            'mauritius', 'seychelles',
            'sudan', 'soudan', 'sudão',
            'somalia', 'somália',
            'djibouti', 'eritrea',
            'car', 'chad', 'tchad',
            'comoros', 'mauritania',
            
            # Regiões
            'miombo', 'savanna', 'sahara', 'kalahari',
            'congo basin', 'great lakes',
        ]
    },
    
    'D2_DINAMICA': {
        'nome': 'SÉRIE TEMPORAL/MUDANÇA (flexível)',
        'obrigatorio': False,
        'termos': [
            'time series', 'temporal', 'multi-temporal', 'multitemporal',
            'change detection', 'change analysis', 'detect chang',
            'monitoring', 'monitor chang',
            'dynamic', 'dynamics',
            'trajectory', 'trend analysis',
            'multi-year', 'multi year',
            'multi-date', 'multi date',
            'longitudinal', 'historical',
            'temporal evolution', 'temporal pattern',
        ]
    },
    
    'D3_LULC': {
        'nome': 'LULC/CLASSIFICAÇÃO (flexível)',
        'obrigatorio': False,
        'termos': [
            'land use', 'land-use',
            'land cover', 'land-cover',
            'lulc', 'lucc',
            'land use/land cover',
            'land mapping', 'lulc mapping',
            'classify', 'classification',
            'categoriz', 'categor',
            'land cover change',
            'forest cover',
            'deforest', 'reforest',
            'forest loss',
            'urban expand',
            'agricultural', 'cropland',
            'wetland', 'mangrove',
            'grassland', 'shrubland',
            'land degradation',
        ]
    },
    
    'D4_ML': {
        'nome': 'MACHINE LEARNING/CLASSIFICAÇÃO (flexível)',
        'obrigatorio': False,
        'termos': [
            'machine learning',
            'random forest', 'random forests',
            'decision tree', 'decision trees',
            'svm', 'support vector',
            'neural network', 'deep learning',
            'ensemble',
            'supervised', 'unsupervised',
            'classifier', 'classification algorithm',
            'artificial intelligence', 'ai model',
            'gradient boost', 'xgboost',
            'logistic regression',
            'gaussian mixture',
            'hidden markov',
            'segmentation', 'image classif',
            'object detection',
            'convolutional neural',
            'cnn', 'rnn', 'lstm',
            'attention mechanism',
            'transfer learning',
            'maximum likelihood', 'mlc',
            'spectral analysis',
        ]
    },
    
    'D5_SENSORIAMENTO': {
        'nome': 'SENSORIAMENTO REMOTO (OBRIGATÓRIO)',
        'obrigatorio': True,
        'termos': [
            'sentinel', 'landsat', 'modis',
            'remote sensing', 'remote-sensing',
            'remotely sensed', 'remotely-sensed',
            'satellite image', 'satellite imagery', 'satellite data',
            'earth observation',
            'hyperspectral', 'multispectral',
            'sar', 'radar', 'microwave',
            'optical', 'spectral',
            'geospatial', 'raster',
            'aerial image', 'drone',
            'uav', 'unmanned aerial',
            'avnir', 'aster', 'quickbird', 'worldview',
            'ikonos', 'rapideye', 'planetscope',
            'sentinel-1', 'sentinel-2',
            'landsat-5', 'landsat-7', 'landsat-8', 'landsat-9',
            'spot', 'mss', 'tm', 'etm',
        ]
    }
}

# ═════════════════════════════════════════════════════════════════════════════
# LOGGER
# ═════════════════════════════════════════════════════════════════════════════

class LoggerCientifico:
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.logs = []
    
    def log(self, nivel, mensagem, dados=None):
        entrada = {
            'timestamp': datetime.now().isoformat(),
            'nivel': nivel,
            'mensagem': mensagem,
            'dados': dados or {}
        }
        self.logs.append(entrada)
        print(f"[{nivel:8s}] {mensagem}")
        if dados:
            for k, v in dados.items():
                print(f"           {k}: {v}")
    
    def salvar(self):
        arquivo_txt = self.output_dir / 'log.txt'
        with open(arquivo_txt, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("LOG - FASE 2 SCREENING v3.0 (RELAXADO)\n")
            f.write("="*80 + "\n\n")
            for entrada in self.logs:
                f.write(f"[{entrada['timestamp']}] {entrada['nivel']}\n")
                f.write(f"  {entrada['mensagem']}\n")

# ═════════════════════════════════════════════════════════════════════════════
# FUNÇÕES
# ═════════════════════════════════════════════════════════════════════════════

def normalizar_texto(texto):
    if not texto:
        return ""
    texto = str(texto).lower()
    texto = re.sub(r'[^\w\s\-]', ' ', texto)
    return texto

def buscar_keywords(texto, keywords):
    texto = normalizar_texto(texto)
    for keyword in keywords:
        pattern = r'\b' + re.escape(keyword.lower()) + r'\w*\b'
        if re.search(pattern, texto):
            return True
    return False

def parser_artigos(filepath):
    artigos = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            conteudo = f.read()
    except Exception as e:
        raise RuntimeError(f"Erro ao ler {filepath}: {e}")
    
    entradas = re.split(r'\[ARTIGO \d+\]\n', conteudo)[1:]
    
    for idx, entrada in enumerate(entradas, 1):
        artigo = {'id': idx}
        
        for campo in ['FONTE', 'DOI', 'TITULO', 'AUTORES', 'ANO', 'REVISTA', 'RESUMO']:
            pattern = f'{campo}:\\s*(.+?)(?=\\n[A-Z]|\\n-|\\Z)'
            match = re.search(pattern, entrada, re.DOTALL)
            if match:
                valor = match.group(1).strip()
                artigo[campo] = valor
        
        if artigo.get('TITULO'):
            artigos.append(artigo)
    
    return artigos

def aplicar_regex_relaxado(artigo):
    """
    Lógica RELAXADA:
    - D1 (TERRITORIAL) = OBRIGATÓRIO
    - D5 (SENSORIAMENTO) = OBRIGATÓRIO
    - D2, D3, D4 = AT LEAST 2 DE 3 devem passar
    """
    titulo = normalizar_texto(artigo.get('TITULO', ''))
    resumo = normalizar_texto(artigo.get('RESUMO', ''))
    
    # Texto completo para busca
    texto = titulo + ' ' + resumo
    
    motivos = []
    
    # D1: TERRITORIAL (OBRIGATÓRIO)
    tem_d1 = buscar_keywords(texto, DOMINIOS['D1_TERRITORIAL']['termos'])
    if not tem_d1:
        motivos.append('D1_sem_territorial')
    
    # D5: SENSORIAMENTO (OBRIGATÓRIO)
    tem_d5 = buscar_keywords(texto, DOMINIOS['D5_SENSORIAMENTO']['termos'])
    if not tem_d5:
        motivos.append('D5_sem_sensoriamento')
    
    # D2, D3, D4: FLEXÍVEIS (AT LEAST 2)
    tem_d2 = buscar_keywords(texto, DOMINIOS['D2_DINAMICA']['termos'])
    tem_d3 = buscar_keywords(texto, DOMINIOS['D3_LULC']['termos'])
    tem_d4 = buscar_keywords(texto, DOMINIOS['D4_ML']['termos'])
    
    count_flexivel = sum([tem_d2, tem_d3, tem_d4])
    
    if count_flexivel < 2:
        if not tem_d2:
            motivos.append('D2_sem_dinamica')
        if not tem_d3:
            motivos.append('D3_sem_lulc')
        if not tem_d4:
            motivos.append('D4_sem_ml')
    
    # Decisão final
    incluir = tem_d1 and tem_d5 and count_flexivel >= 2
    
    return incluir, motivos

# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    logger = LoggerCientifico(CONFIG['output_dir'])
    
    logger.log("INICIO", "FASE 2 Screening Relaxado v3.0")
    
    # PASSO 1: CARREGAR
    arquivo_entrada = CONFIG['input_dir'] / CONFIG['input_file']
    
    if not arquivo_entrada.exists():
        logger.log("ERRO", f"Ficheiro não encontrado: {arquivo_entrada}")
        logger.salvar()
        exit(1)
    
    try:
        artigos = parser_artigos(arquivo_entrada)
    except Exception as e:
        logger.log("ERRO", f"Erro ao carregar: {e}")
        logger.salvar()
        exit(1)
    
    logger.log("OK", f"Carregados {len(artigos)} artigos")
    
    # PASSO 2: APLICAR REGEX
    logger.log("PROCESSAMENTO", "Aplicando máscara RELAXADA")
    
    elegíveis = []
    rejeitados = []
    contador_motivos = defaultdict(int)
    
    for idx, artigo in enumerate(artigos, 1):
        incluir, motivos = aplicar_regex_relaxado(artigo)
        
        if incluir:
            elegíveis.append(artigo)
        else:
            rejeitados.append({'artigo': artigo, 'motivos': motivos})
            for motivo in motivos:
                contador_motivos[motivo] += 1
        
        if idx % 500 == 0:
            pct = 100 * idx / len(artigos)
            pct_elig = 100 * len(elegíveis) / idx
            print(f"  [{pct:5.1f}%] {idx}/{len(artigos)} | Elegíveis: {pct_elig:.1f}%")
    
    logger.log("RESULTADO", "Screening concluído", {
        'total': len(artigos),
        'elegíveis': len(elegíveis),
        'rejeitados': len(rejeitados),
        'taxa': f"{100*len(elegíveis)/len(artigos):.1f}%"
    })
    
    # PASSO 3: SALVAR ELEGÍVEIS
    logger.log("SALVANDO", "Artigos elegíveis")
    
    arquivo_elegíveis = CONFIG['output_dir'] / 'elegíveis.txt'
    with open(arquivo_elegíveis, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("ARTIGOS ELEGÍVEIS - FASE 2 v3.0 (RELAXADO)\n")
        f.write(f"Data: {datetime.now().isoformat()}\n")
        f.write(f"Total: {len(elegíveis)} artigos\n")
        f.write("="*80 + "\n\n")
        
        for artigo in elegíveis:
            f.write(f"[ELEGÍVEL {artigo['id']}]\n")
            f.write(f"DOI: {artigo.get('DOI', 'N/A')}\n")
            f.write(f"TITULO: {artigo.get('TITULO', 'N/A')}\n")
            f.write(f"AUTORES: {artigo.get('AUTORES', 'N/A')}\n")
            f.write(f"ANO: {artigo.get('ANO', 'N/A')}\n")
            f.write(f"RESUMO: {artigo.get('RESUMO', 'N/A')}\n\n")
            f.write("-"*80 + "\n\n")
    
    logger.log("OK", f"Elegíveis salvos ({len(elegíveis)} artigos)")
    
    # PASSO 4: RELATÓRIO
    logger.log("SALVANDO", "Relatório detalhado")
    
    arquivo_relatorio = CONFIG['output_dir'] / 'relatorio_screening.txt'
    with open(arquivo_relatorio, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("RELATÓRIO - FASE 2 SCREENING v3.0 (RELAXADO)\n")
        f.write("="*80 + "\n\n")
        
        f.write("LÓGICA DE SELEÇÃO\n")
        f.write("-"*80 + "\n")
        f.write("✅ D1 (TERRITORIAL) = OBRIGATÓRIO\n")
        f.write("✅ D5 (SENSORIAMENTO) = OBRIGATÓRIO\n")
        f.write("✅ D2 (Série Temporal) OU D3 (LULC) OU D4 (ML) = AT LEAST 2 DE 3\n\n")
        
        f.write("ESTATÍSTICAS\n")
        f.write("-"*80 + "\n")
        f.write(f"Total processado: {len(artigos):,}\n")
        f.write(f"Elegíveis: {len(elegíveis):,} ({100*len(elegíveis)/len(artigos):.1f}%)\n")
        f.write(f"Rejeitados: {len(rejeitados):,}\n\n")
        
        f.write("MOTIVOS DE REJEIÇÃO\n")
        f.write("-"*80 + "\n")
        for motivo, count in sorted(contador_motivos.items(), key=lambda x: x[1], reverse=True):
            pct = 100 * count / len(rejeitados) if rejeitados else 0
            f.write(f"{motivo:30s}: {count:5d} ({pct:5.1f}%)\n")
    
    logger.log("OK", "Relatório salvo")
    
    # FINAL
    logger.log("FIM", "FASE 2 concluída com sucesso")
    logger.salvar()
    
    print("\n" + "="*80)
    print("✅ FASE 2 SCREENING v3.0 (RELAXADO) CONCLUÍDA")
    print("="*80)
    print(f"\n📊 RESUMO:")
    print(f"  Artigos processados: {len(artigos):,}")
    print(f"  Elegíveis (FASE 3): {len(elegíveis):,} ({100*len(elegíveis)/len(artigos):.1f}%)")
    print(f"  Rejeitados: {len(rejeitados):,}")
    print(f"\n📁 FICHEIROS: {CONFIG['output_dir']}")
    print(f"  ✅ elegíveis.txt ({len(elegíveis)} artigos)")
    print(f"  ✅ relatorio_screening.txt")
    print(f"  ✅ log.txt")
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
