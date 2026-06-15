#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
                     REVISÃO SISTEMÁTICA LULC - FASE 1
                    DEDUPLICAÇÃO ROBUSTA E REPRODUCÍVEL
                         (VERSÃO 2.1 - COMPATÍVEL)
================================================================================

Script: FASE_1_deduplicacao_v2_1_compativel.py
Versão: 2.1 (Compatível com todas as versões de bibtexparser)
Data: 2026-06-02
Autor: Revisão Sistemática LULC-SSA

CORREÇÕES V2.1:
  ✅ Compatível com bibtexparser 1.4+ e antigas
  ✅ Fallback automático para parser manual
  ✅ Tratamento de divisão por zero
  ✅ Melhor detecção de API

================================================================================
"""

import os
import sys
import re
import json
import hashlib
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import unicodedata

# Tentar importar bibtexparser com fallback
try:
    import bibtexparser
    
    # Detectar versão e API
    if hasattr(bibtexparser, 'parse_string'):
        BIBTEXPARSER_NEW = True
        PARSER_INFO = "bibtexparser (versão nova, parse_string)"
    elif hasattr(bibtexparser, 'loads'):
        BIBTEXPARSER_NEW = False
        PARSER_INFO = "bibtexparser (versão antiga, loads)"
    else:
        BIBTEXPARSER_NEW = False
        PARSER_INFO = "bibtexparser (fallback para parser manual)"
    
    USAR_BIBTEXPARSER = True
except ImportError:
    USAR_BIBTEXPARSER = False
    PARSER_INFO = "Parser manual (bibtexparser não instalado)"

# ═════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO CENTRALIZADA
# ═════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path.cwd()

CONFIG = {
    'versao_script': '2.1',
    'data_execucao': datetime.now().isoformat(),
    'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
    
    'input_dir': BASE_DIR / '00_raw_data',
    'output_dir': BASE_DIR / '01_deduplicacao',
    
    'criterios': {
        'dedup_camada_1': 'DOI normalizado',
        'dedup_camada_2': 'Título normalizado (sem DOI)',
        'dedup_camada_3': 'Título + Primeiro Autor + Ano (sem DOI)',
        'normalizacao': 'Unicode NFD + lowercase + remover especiais'
    },
    
    'parser': PARSER_INFO,
    'log_verbose': True
}

CONFIG['input_dir'].mkdir(parents=True, exist_ok=True)
CONFIG['output_dir'].mkdir(parents=True, exist_ok=True)

print("="*80)
print("FASE 1: DEDUPLICAÇÃO PREMIUM v2.1 (COMPATÍVEL)")
print("="*80 + "\n")

print("📁 Criando/verificando diretórios...")
print(f"   Input:  {CONFIG['input_dir']}")
print(f"   Output: {CONFIG['output_dir']}")
print(f"   Parser: {PARSER_INFO}\n")

# ═════════════════════════════════════════════════════════════════════════════
# LOGGER
# ═════════════════════════════════════════════════════════════════════════════

class LoggerEstruturado:
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.logs = []
    
    def log(self, nivel, mensagem, dados_adicionais=None):
        entrada = {
            'timestamp': datetime.now().isoformat(),
            'nivel': nivel,
            'mensagem': mensagem,
            'dados': dados_adicionais or {}
        }
        self.logs.append(entrada)
        print(f"[{nivel:8s}] {mensagem}")
        if dados_adicionais and CONFIG['log_verbose']:
            for chave, valor in dados_adicionais.items():
                print(f"           {chave}: {valor}")
    
    def salvar(self):
        arquivo_json = self.output_dir / 'log.json'
        with open(arquivo_json, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, indent=2, ensure_ascii=False)
        
        arquivo_txt = self.output_dir / 'log.txt'
        with open(arquivo_txt, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("LOG DE AUDITORIA - FASE 1 DEDUPLICAÇÃO v2.1\n")
            f.write(f"Data: {datetime.now().isoformat()}\n")
            f.write("="*80 + "\n\n")
            
            for entrada in self.logs:
                f.write(f"[{entrada['timestamp']}] {entrada['nivel']}\n")
                f.write(f"  {entrada['mensagem']}\n")
                if entrada['dados']:
                    for chave, valor in entrada['dados'].items():
                        f.write(f"    • {chave}: {valor}\n")
                f.write("\n")
        
        return arquivo_json, arquivo_txt

# ═════════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE NORMALIZAÇÃO
# ═════════════════════════════════════════════════════════════════════════════

def normalizar_unicode(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.lower().strip()

def normalizar_doi(doi):
    if not doi:
        return None
    doi = re.sub(r'^(https?://)?doi\.org/', '', doi, flags=re.IGNORECASE)
    doi = re.sub(r'^doi:', '', doi, flags=re.IGNORECASE)
    doi = re.sub(r'\s+', '', doi).lower().strip()
    return doi if doi else None

def normalizar_titulo(titulo):
    if not titulo:
        return None
    titulo = normalizar_unicode(titulo)
    titulo = re.sub(r'[^a-z0-9\s]', '', titulo)
    titulo = re.sub(r'\s+', ' ', titulo).strip()
    stopwords = {'the', 'a', 'an', 'and', 'or', 'in', 'on', 'at', 'to', 'of', 'for'}
    palavras = [p for p in titulo.split() if p not in stopwords]
    return ' '.join(palavras)

def extrair_primeiro_autor(autores):
    if not autores:
        return None
    primeiro = autores.split(',')[0].split('and')[0].strip()
    primeiro = normalizar_unicode(primeiro)
    primeiro = re.sub(r'[^a-z\s]', '', primeiro)
    return primeiro.split()[0] if primeiro.split() else None

# ═════════════════════════════════════════════════════════════════════════════
# PARSER BIBTEX - COMPATÍVEL COM MÚLTIPLAS VERSÕES
# ═════════════════════════════════════════════════════════════════════════════

def parse_bibtex_v2_1(filename):
    """Parser BibTeX com fallback automático"""
    
    if USAR_BIBTEXPARSER:
        if BIBTEXPARSER_NEW:
            return parse_bibtex_new_api(filename)
        else:
            return parse_bibtex_old_api(filename)
    else:
        return parse_bibtex_manual(filename)

def parse_bibtex_new_api(filename):
    """API nova: bibtexparser.parse_string() (v1.4+)"""
    artigos = []
    
    try:
        with open(filename, 'r', encoding='utf-8-sig', errors='replace') as f:
            bibtex_str = f.read()
        
        library = bibtexparser.parse_string(bibtex_str)
        
        for entry in library.entries:
            artigo = {
                'doi': entry.fields_dict.get('doi', '').lower().strip() if 'doi' in entry.fields_dict else '',
                'titulo': entry.fields_dict.get('title', '').strip() if 'title' in entry.fields_dict else '',
                'autores': entry.fields_dict.get('author', '').strip() if 'author' in entry.fields_dict else '',
                'ano': entry.fields_dict.get('year', '').strip() if 'year' in entry.fields_dict else '',
                'resumo': entry.fields_dict.get('abstract', '').strip()[:1000] if 'abstract' in entry.fields_dict else '',
                'revista': entry.fields_dict.get('journal', '').strip() if 'journal' in entry.fields_dict else '',
                'tipo_entrada': entry.entry_type
            }
            
            if artigo['titulo']:
                artigos.append(artigo)
        
        return artigos
    
    except Exception as e:
        print(f"⚠️  Erro na API nova: {e}, tentando parser manual...")
        return parse_bibtex_manual(filename)

def parse_bibtex_old_api(filename):
    """API antiga: bibtexparser.loads() (<v1.4)"""
    artigos = []
    
    try:
        with open(filename, 'r', encoding='utf-8-sig', errors='replace') as f:
            bibtex_str = f.read()
        
        bib_database = bibtexparser.loads(bibtex_str)
        
        for entry in bib_database.entries:
            artigo = {
                'doi': entry.get('doi', '').lower().strip(),
                'titulo': entry.get('title', '').strip(),
                'autores': entry.get('author', '').strip(),
                'ano': entry.get('year', '').strip(),
                'resumo': entry.get('abstract', '').strip()[:1000],
                'revista': entry.get('journal', '').strip(),
                'tipo_entrada': entry.get('ENTRYTYPE', 'article')
            }
            
            if artigo['titulo']:
                artigos.append(artigo)
        
        return artigos
    
    except Exception as e:
        print(f"⚠️  Erro na API antiga: {e}, tentando parser manual...")
        return parse_bibtex_manual(filename)

def parse_bibtex_manual(filename):
    """Parser manual (fallback universal)"""
    artigos = []
    
    try:
        with open(filename, 'r', encoding='utf-8-sig', errors='replace') as f:
            conteudo = f.read()
    except Exception as e:
        print(f"❌ Erro ao ler {filename}: {e}")
        return artigos
    
    linhas = conteudo.split('\n')
    entrada_atual = []
    tipo_entrada = None
    
    for linha in linhas:
        if linha.strip().startswith('@'):
            if entrada_atual:
                artigo = processar_entrada_bibtex(entrada_atual, tipo_entrada)
                if artigo and artigo.get('titulo'):
                    artigos.append(artigo)
            
            entrada_atual = [linha]
            tipo_entrada = linha.split('{')[0].strip().lower()
        else:
            entrada_atual.append(linha)
    
    if entrada_atual:
        artigo = processar_entrada_bibtex(entrada_atual, tipo_entrada)
        if artigo and artigo.get('titulo'):
            artigos.append(artigo)
    
    return artigos

def processar_entrada_bibtex(linhas, tipo_entrada):
    """Extrair campos de uma entrada BibTeX"""
    texto = '\n'.join(linhas).lower()
    
    campos = {
        'doi': '',
        'titulo': '',
        'autores': '',
        'ano': '',
        'resumo': '',
        'revista': '',
        'tipo_entrada': tipo_entrada or 'article'
    }
    
    patterns = {
        'doi': r'(?:doi|DOI)\s*=\s*\{?["\']?([^",\}\n]+)',
        'titulo': r'(?:title|TITLE|Title)\s*=\s*\{?["\']?([^"\}]{0,500})',
        'autores': r'(?:author|AUTHOR|Author)\s*=\s*\{?["\']?([^"\}]{0,500})',
        'ano': r'(?:year|YEAR|Year)\s*=\s*\{?["\']?(\d{4})',
        'resumo': r'(?:abstract|ABSTRACT|Abstract)\s*=\s*\{?["\']?([^"\}]{0,1000})',
        'revista': r'(?:journal|JOURNAL|Journal)\s*=\s*\{?["\']?([^"\}]{0,200})',
    }
    
    for campo, pattern in patterns.items():
        match = re.search(pattern, texto)
        if match:
            valor = match.group(1).strip()
            valor = re.sub(r'[^\w\s\-\.,:;@()\[\]/]', '', valor)
            campos[campo] = valor
    
    return campos

# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    logger = LoggerEstruturado(CONFIG['output_dir'])
    
    logger.log("INICIO", "Iniciando FASE 1 - Deduplicação v2.1", {
        'parser_usado': CONFIG['parser'],
        'diretorio_entrada': str(CONFIG['input_dir']),
        'diretorio_saida': str(CONFIG['output_dir'])
    })
    
    # PASSO 1: CARREGAR FICHEIROS
    logger.log("PASSO1", "Carregando ficheiros BibTeX")
    
    ficheiros_bib = sorted(CONFIG['input_dir'].glob('*.bib'))
    if not ficheiros_bib:
        logger.log("ERRO", f"Nenhum ficheiro .bib encontrado em {CONFIG['input_dir']}")
        logger.salvar()
        sys.exit(1)
    
    artigos_brutos = []
    
    for bib_file in ficheiros_bib:
        logger.log("INFO", f"Processando {bib_file.name}")
        
        try:
            artigos = parse_bibtex_v2_1(str(bib_file))
            fonte = 'Scopus' if 'scopus' in bib_file.name.lower() else 'WoS'
            
            for art in artigos:
                art['fonte'] = fonte
            
            artigos_brutos.extend(artigos)
            
            logger.log("OK", f"Carregados {len(artigos)} artigos", {
                'ficheiro': bib_file.name,
                'fonte': fonte,
                'total_acumulado': len(artigos_brutos)
            })
        
        except Exception as e:
            logger.log("AVISO", f"Erro ao processar {bib_file.name}: {e}")
            continue
    
    logger.log("SUMMARY", f"Total carregado: {len(artigos_brutos)} artigos")
    
    if len(artigos_brutos) == 0:
        logger.log("ERRO", "Nenhum artigo carregado! Verifique os ficheiros BibTeX.")
        logger.salvar()
        print("\n❌ ERRO: Nenhum artigo foi carregado!")
        print("   Verifique se os ficheiros .bib têm conteúdo válido.")
        sys.exit(1)
    
    # PASSO 2: DEDUPLICAÇÃO CAMADA 1
    logger.log("PASSO2", "Deduplicação Camada 1: DOI")
    
    artigos_com_doi = [a for a in artigos_brutos if a.get('doi')]
    artigos_sem_doi = [a for a in artigos_brutos if not a.get('doi')]
    
    dois_vistos = {}
    artigos_unicos_doi = []
    duplicados_camada1 = []
    
    for artigo in artigos_com_doi:
        doi_norm = normalizar_doi(artigo['doi'])
        if doi_norm:
            if doi_norm not in dois_vistos:
                dois_vistos[doi_norm] = artigo
                artigos_unicos_doi.append(artigo)
            else:
                duplicados_camada1.append({
                    'artigo_novo': artigo,
                    'artigo_original': dois_vistos[doi_norm],
                    'motivo': 'DOI duplicado'
                })
    
    logger.log("OK", "Deduplicação Camada 1 concluída", {
        'com_doi_original': len(artigos_com_doi),
        'unicos_doi': len(artigos_unicos_doi),
        'duplicados_c1': len(duplicados_camada1)
    })
    
    # PASSO 3: DEDUPLICAÇÃO CAMADA 2
    logger.log("PASSO3", "Deduplicação Camada 2: Título normalizado")
    
    titulos_vistos = {}
    artigos_unicos_titulo = []
    duplicados_camada2 = []
    
    for artigo in artigos_sem_doi:
        titulo_norm = normalizar_titulo(artigo.get('titulo', ''))
        if titulo_norm:
            if titulo_norm not in titulos_vistos:
                titulos_vistos[titulo_norm] = artigo
                artigos_unicos_titulo.append(artigo)
            else:
                duplicados_camada2.append({
                    'artigo_novo': artigo,
                    'artigo_original': titulos_vistos[titulo_norm],
                    'motivo': 'Título duplicado (sem DOI)'
                })
    
    logger.log("OK", "Deduplicação Camada 2 concluída", {
        'sem_doi_original': len(artigos_sem_doi),
        'unicos_titulo': len(artigos_unicos_titulo),
        'duplicados_c2': len(duplicados_camada2)
    })
    
    # PASSO 4: DEDUPLICAÇÃO CAMADA 3
    logger.log("PASSO4", "Deduplicação Camada 3: Título + Primeiro Autor + Ano")
    
    chave_vistos = {}
    artigos_unicos_composto = []
    duplicados_camada3 = []
    
    for artigo in artigos_unicos_titulo:
        titulo_norm = normalizar_titulo(artigo.get('titulo', ''))
        primeiro_autor = extrair_primeiro_autor(artigo.get('autores', ''))
        ano = artigo.get('ano', '')
        
        if titulo_norm and primeiro_autor and ano:
            chave = f"{titulo_norm}#{primeiro_autor}#{ano}"
            
            if chave not in chave_vistos:
                chave_vistos[chave] = artigo
                artigos_unicos_composto.append(artigo)
            else:
                duplicados_camada3.append({
                    'artigo_novo': artigo,
                    'artigo_original': chave_vistos[chave],
                    'motivo': 'Título+Autor+Ano duplicado (sem DOI)',
                    'chave': chave
                })
        else:
            artigos_unicos_composto.append(artigo)
    
    logger.log("OK", "Deduplicação Camada 3 concluída", {
        'candidatos_c3': len(artigos_unicos_titulo),
        'com_chave_completa': len(chave_vistos),
        'duplicados_c3': len(duplicados_camada3)
    })
    
    # CONSOLIDAÇÃO
    artigos_finais = artigos_unicos_doi + artigos_unicos_composto
    total_duplicados = len(duplicados_camada1) + len(duplicados_camada2) + len(duplicados_camada3)
    
    # TRATAMENTO DE DIVISÃO POR ZERO
    if len(artigos_brutos) > 0:
        pct_duplicados = 100 * total_duplicados / len(artigos_brutos)
    else:
        pct_duplicados = 0
    
    logger.log("CONSOLIDACAO", "Deduplicação finalizada", {
        'artigos_brutos': len(artigos_brutos),
        'artigos_finais': len(artigos_finais),
        'duplicados_totais': total_duplicados,
        'percentagem_duplicados': f"{pct_duplicados:.1f}%"
    })
    
    # PASSO 5: SALVAR ARTIGOS
    logger.log("PASSO5", "Salvando artigos únicos")
    
    arquivo_artigos = CONFIG['output_dir'] / 'artigos.txt'
    with open(arquivo_artigos, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("ARTIGOS ÚNICOS - FASE 1 DEDUPLICAÇÃO v2.1\n")
        f.write(f"Data: {datetime.now().isoformat()}\n")
        f.write(f"Total: {len(artigos_finais)} artigos\n")
        f.write("="*80 + "\n\n")
        
        for idx, artigo in enumerate(artigos_finais, 1):
            f.write(f"[ARTIGO {idx}]\n")
            f.write(f"FONTE: {artigo.get('fonte', 'DESCONHECIDA')}\n")
            f.write(f"DOI: {artigo.get('doi', 'N/A')}\n")
            f.write(f"TITULO: {artigo.get('titulo', 'N/A')}\n")
            f.write(f"AUTORES: {artigo.get('autores', 'N/A')}\n")
            f.write(f"ANO: {artigo.get('ano', 'N/A')}\n")
            f.write(f"REVISTA: {artigo.get('revista', 'N/A')}\n")
            f.write(f"RESUMO: {artigo.get('resumo', 'N/A')}\n")
            f.write("\n" + "-"*80 + "\n\n")
    
    logger.log("OK", "Artigos únicos salvos")
    
    # PASSO 6: RELATÓRIO
    logger.log("PASSO6", "Gerando relatório detalhado")
    
    arquivo_relatorio = CONFIG['output_dir'] / 'relatorio.txt'
    with open(arquivo_relatorio, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("RELATÓRIO - FASE 1 DEDUPLICAÇÃO v2.1\n")
        f.write("="*80 + "\n\n")
        
        f.write("CONFIGURAÇÃO\n")
        f.write("-"*80 + "\n")
        f.write(f"Versão: {CONFIG['versao_script']}\n")
        f.write(f"Parser: {CONFIG['parser']}\n")
        f.write(f"Data: {CONFIG['data_execucao']}\n\n")
        
        f.write("ESTATÍSTICAS\n")
        f.write("-"*80 + "\n")
        f.write(f"Artigos brutos: {len(artigos_brutos):,}\n")
        if len(artigos_brutos) > 0:
            f.write(f"  • Com DOI: {len(artigos_com_doi):,} ({100*len(artigos_com_doi)/len(artigos_brutos):.1f}%)\n")
            f.write(f"  • Sem DOI: {len(artigos_sem_doi):,} ({100*len(artigos_sem_doi)/len(artigos_brutos):.1f}%)\n")
        f.write(f"\nDuplicatas removidas: {total_duplicados:,} ({pct_duplicados:.1f}%)\n")
        f.write(f"Artigos únicos: {len(artigos_finais):,}\n")
    
    logger.log("OK", "Relatório salvo")
    
    # FINAL
    logger.log("FIM", "FASE 1 Deduplicação concluída com sucesso")
    logger.salvar()
    
    print("\n" + "="*80)
    print("✅ FASE 1 DEDUPLICAÇÃO v2.1 CONCLUÍDA COM SUCESSO")
    print("="*80)
    print(f"\n📊 RESUMO FINAL:")
    print(f"  Artigos brutos: {len(artigos_brutos):,}")
    print(f"  Duplicatas removidas: {total_duplicados:,} ({pct_duplicados:.1f}%)")
    print(f"  Artigos únicos: {len(artigos_finais):,}")
    print(f"\n📁 FICHEIROS GERADOS EM: {CONFIG['output_dir']}")
    print(f"  ✅ artigos.txt")
    print(f"  ✅ relatorio.txt")
    print(f"  ✅ log.txt")
    print(f"  ✅ log.json")
    print(f"\n👉 PRÓXIMO PASSO:")
    print(f"  python scripts/FASE_2_regex_rigoroso_v2.py")
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
