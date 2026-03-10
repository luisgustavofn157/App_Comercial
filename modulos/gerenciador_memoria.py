import json
from pathlib import Path
import streamlit as st

# 1. A ÂNCORA ABSOLUTA
# __file__ é este arquivo (gerenciador_memoria.py)
# .parent é a pasta 'modulos'
# .parent.parent é a raiz 'APP_COMERCIAL'
DIRETORIO_RAIZ = Path(__file__).resolve().parent.parent

# Caminhos exatos e imutáveis para os bancos de dados JSON
ARQUIVO_MARCAS = DIRETORIO_RAIZ / 'memoria' / 'memoria_marca_por_perfil.json'
ARQUIVO_COLUNAS = DIRETORIO_RAIZ / 'memoria' / 'memoria_coluna_por_perfil.json'

def _ler_json(caminho_arquivo):
    """
    Função interna (privada) responsável apenas por abrir e validar JSONs.
    Aplica o conceito de Fail-Fast: se quebrar, para o app e avisa o usuário.
    """
    if not caminho_arquivo.exists():
        st.error(f"🚨 ERRO DE ARQUITETURA: O banco de dados não foi encontrado no caminho: {caminho_arquivo}")
        st.stop() # Interrompe a execução imediatamente
        
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        st.error(f"🚨 ERRO DE CORRUPÇÃO: O arquivo {caminho_arquivo.name} está vazio ou com o JSON quebrado. Detalhes: {e}")
        st.stop()
    except PermissionError:
        st.error(f"🚨 ERRO DE PERMISSÃO: O sistema bloqueou a leitura do arquivo {caminho_arquivo.name}.")
        st.stop()

def _salvar_json(caminho_arquivo, dados):
    """Função interna para gravar dados com segurança."""
    try:
        with open(caminho_arquivo, 'w', encoding='utf-8-sig') as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"🚨 ERRO DE GRAVAÇÃO: Não foi possível salvar no arquivo {caminho_arquivo.name}. Detalhes: {e}")
        st.stop()

# ==========================================
# FUNÇÕES PÚBLICAS (O que a interface vai usar)
# ==========================================

def carregar_mapa_marcas():
    """Retorna o dicionário completo de marcas por perfil."""
    return _ler_json(ARQUIVO_MARCAS)

def obter_marcas_por_perfil(perfil):
    """Retorna a lista de marcas de um perfil específico com Raio-X ativado."""
    if not perfil or perfil == "Selecione...":
        return []
    
    mapa = carregar_mapa_marcas()
    perfil_limpo = perfil.strip()

    return mapa.get(perfil_limpo, [])
    
    mapa = carregar_mapa_marcas()
    return mapa.get(perfil.strip(), [])

def obter_perfis_salvos():
    """
    Retorna a lista de perfis existentes lendo DIRETAMENTE do arquivo de marcas.
    Isso garante a Fonte Única da Verdade (Single Source of Truth).
    """
    mapa = carregar_mapa_marcas()
    return sorted(list(mapa.keys()))

def atualizar_marcas_do_perfil(perfil, novas_marcas):
    """Atualiza as marcas de um perfil e salva no JSON."""
    mapa = carregar_mapa_marcas()
    mapa[perfil.strip()] = novas_marcas
    _salvar_json(ARQUIVO_MARCAS, mapa)