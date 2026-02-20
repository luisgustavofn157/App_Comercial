import streamlit as st
import pandas as pd
import traceback
import io
from modulos.importador_especialista import encontrar_tabela_valida
from modulos.orquestrador_importacao import processar_arquivos_upload

st.set_page_config(page_title="Hub Comercial - Precificação", page_icon="📊", layout="wide")

# ==========================================
# INJEÇÃO DE CSS (DESIGN E UX)
# ==========================================
st.markdown("""
    <style>
    div.stButton > button[kind="primary"] {
        background-color: #0066cc;
        border-color: #0066cc;
        color: white;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #0052a3;
        border-color: #0052a3;
    }
    .etapa-atual {
        background-color: #e6f2ff;
        color: #0066cc;
        padding: 8px;
        border-radius: 6px;
        font-weight: bold;
        margin-bottom: 4px;
        border-left: 4px solid #0066cc;
    }
    .etapa-concluida {
        color: #28a745;
        padding: 8px;
        margin-bottom: 4px;
    }
    .etapa-bloqueada {
        color: #6c757d;
        padding: 8px;
        margin-bottom: 4px;
        opacity: 0.7;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# GERENCIAMENTO DE ESTADO (MEMÓRIA)
# ==========================================
if "pagina_atual" not in st.session_state: st.session_state.pagina_atual = "Fluxo Principal"
if "etapa_fluxo" not in st.session_state: st.session_state.etapa_fluxo = 1
if "tabelas_extraidas" not in st.session_state: st.session_state.tabelas_extraidas = []
if "decisoes_usuario" not in st.session_state: st.session_state.decisoes_usuario = {}

def mudar_pagina(nome): st.session_state.pagina_atual = nome

def resetar_fluxo():
    st.session_state.etapa_fluxo = 1
    st.session_state.tabelas_extraidas = []
    st.session_state.decisoes_usuario = {}
    st.session_state.pagina_atual = "Fluxo Principal"

# ==========================================
# MENU LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    col_img, col_txt = st.columns([1, 3])
    with col_img: st.image("https://cdn-icons-png.flaticon.com/512/2936/2936690.png", width=50)
    with col_txt: st.markdown("### Hub Comercial\nPrecificação")
    
    st.divider()
    
    st.markdown("#### 🔄 Fluxo de Precificação")
    
    etapas = ["1. Importação", "2. Auditoria", "3. Mapeamento", "4. Variação"]
    for i, nome in enumerate(etapas, start=1):
        if i < st.session_state.etapa_fluxo: 
            st.markdown(f"<div class='etapa-concluida'>✅ {nome}</div>", unsafe_allow_html=True)
        elif i == st.session_state.etapa_fluxo: 
            st.markdown(f"<div class='etapa-atual'>▶ {nome}</div>", unsafe_allow_html=True)
        else: 
            st.markdown(f"<div class='etapa-bloqueada'>🔒 {nome}</div>", unsafe_allow_html=True)
    
    if st.session_state.etapa_fluxo > 1:
        st.write("") 
        if st.button("🛑 Cancelar e Recomeçar", use_container_width=True):
            resetar_fluxo()
            st.rerun()

    st.divider()
    
    st.markdown("#### 🛠️ Ferramentas Globais")
    if st.button("📑 Perfis de Fornecedores", use_container_width=True): mudar_pagina("Perfis")
    if st.button("📋 Logs de Execução", use_container_width=True): mudar_pagina("Logs")

# ==========================================
# ROTEADOR DE PÁGINAS PRINCIPAL
# ==========================================
pagina = st.session_state.pagina_atual

if pagina == "Fluxo Principal":
    
    # ------------------------------------------
    # ETAPA 1: IMPORTAÇÃO E TERCEIRIZAÇÃO
    # ------------------------------------------
    if st.session_state.etapa_fluxo == 1:
        st.header("📂 Passo 1: Importar Arquivos")
        st.info("Arraste as listas de preços enviadas pelo fornecedor. O sistema tentará encontrar as tabelas válidas automaticamente.")
        
        arquivos = st.file_uploader("Selecione Excel ou CSV", type=['csv', 'xlsx', 'xlsb', 'xls'], accept_multiple_files=True, label_visibility="collapsed")
        
        if arquivos:
            st.write("")
            if st.button("Analisar Arquivos ➡️", type="primary"):
                with st.spinner("O Especialista está lendo e fatiando os arquivos..."):
                    
                    # O Frontend APENAS chama o Orquestrador e espera a resposta
                    tabelas, erros = processar_arquivos_upload(arquivos)
                    
                    # Se vieram erros, a interface exibe de forma elegante
                    if erros:
                        for erro in erros:
                            st.error(f"🚨 Falha crítica no arquivo: {erro['arquivo']}")
                            with st.expander("Ver Raio-X do erro técnico"):
                                st.code(erro['traceback'])
                        st.stop() # Trava a tela para o usuário ver o erro
                    
                    # Se tudo deu certo, salva na memória e avança a página
                    st.session_state.tabelas_extraidas = tabelas
                    st.session_state.decisoes_usuario = {} 
                    st.session_state.etapa_fluxo = 2
                    st.rerun()

    # ------------------------------------------
    # ETAPA 2: AUDITORIA DAS EXTRAÇÕES
    # ------------------------------------------
    elif st.session_state.etapa_fluxo == 2:
        st.header("👁️ Passo 2: Auditar Inteligência do Sistema")
        
        if len(st.session_state.tabelas_extraidas) == 0:
            st.warning("Nenhuma tabela comercial foi encontrada. Os arquivos podem ser apenas relatórios em texto ou não possuem as colunas obrigatórias (Código e Preço).")
            if st.button("⬅️ Voltar e Tentar Novamente"):
                st.session_state.etapa_fluxo = 1
                st.rerun()
        else:
            st.success(f"O sistema encontrou {len(st.session_state.tabelas_extraidas)} tabela(s) potencial(is).")
            st.write("Revise as extrações abaixo. O sistema já pré-selecionou uma sugestão, mas você deve validar antes de consolidar o arquivo final.")
            
            for tbl in st.session_state.tabelas_extraidas:
                id_unico = tbl['id_unico']
                
                with st.container(border=True):
                    col_tabela, col_acao = st.columns([3, 1])
                    
                    with col_tabela:
                        st.markdown(f"📄 **Arquivo:** `{tbl['arquivo']}` &nbsp;|&nbsp; 📑 **Aba:** `{tbl['aba']}`")
                        st.caption(f"🤖 **Motivo da Escolha:** {tbl['motivo_escolha']}")
                        st.dataframe(tbl['dados'].head(5), use_container_width=True)
                    
                    with col_acao:
                        st.markdown("**Ação para esta tabela:**")
                        opcoes_acao = ["❓ Pendente", "✅ Consolidar", "ℹ️ Info Técnica", "🗑️ Lixo/Ignorar"]
                        
                        # CORREÇÃO AQUI: Alinhando o nome da variável para 'sugestao_ia' em todo o bloco
                        sugestao_ia = tbl.get('sugestao_acao', "❓ Pendente")
                        
                        if "Lista Preço" in sugestao_ia: sugestao_ia = "✅ Consolidar"
                        elif "Tabela Técnica" in sugestao_ia: sugestao_ia = "ℹ️ Info Técnica"
                        
                        index_sugestao = opcoes_acao.index(sugestao_ia) if sugestao_ia in opcoes_acao else 0
                        
                        decisao = st.radio(
                            "Ação Sugerida:",
                            options=opcoes_acao,
                            index=index_sugestao,
                            key=f"radio_{id_unico}",
                            label_visibility="collapsed"
                        )
                        st.session_state.decisoes_usuario[id_unico] = decisao

            st.divider()
            col_voltar, col_vazio, col_avancar = st.columns([2, 5, 3])
            
            with col_voltar:
                if st.button("⬅️ Voltar ao Início", use_container_width=True):
                    st.session_state.etapa_fluxo = 1
                    st.rerun()
                    
            with col_avancar:
                pendentes = sum(1 for d in st.session_state.decisoes_usuario.values() if d == "❓ Pendente")
                if pendentes > 0:
                    st.error(f"⚠️ Há {pendentes} tabela(s) Pendente(s).")
                else:
                    if st.button("Aprovar e Avançar ➡️", type="primary", use_container_width=True):
                        st.session_state.etapa_fluxo = 3
                        st.rerun()

    # ------------------------------------------
    # ETAPA 3: MAPEAMENTO DE COLUNAS
    # ------------------------------------------
    elif st.session_state.etapa_fluxo == 3:
        st.header("🔀 Passo 3: Mapeamento de Colunas")
        st.write("Apenas as tabelas aprovadas chegaram aqui. Vamos definir o De/Para.")
        
        st.divider()
        if st.button("⬅️ Voltar para Auditoria"):
            st.session_state.etapa_fluxo = 2
            st.rerun()

# Ferramentas globais vazias por enquanto para não quebrar a navegação
elif pagina == "Perfis":
    st.header("📑 Perfis de Fornecedores")
    st.write("Em construção...")
elif pagina == "Logs":
    st.header("📋 Logs de Execução")
    st.write("Em construção...")