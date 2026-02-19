import streamlit as st
import pandas as pd
from modulos.importador_especialista import encontrar_tabela_valida

st.set_page_config(page_title="Hub Comercial - Precificação", page_icon="📊", layout="wide")

# ==========================================
# GERENCIAMENTO DE ESTADO (MEMÓRIA)
# ==========================================
if "pagina_atual" not in st.session_state: st.session_state.pagina_atual = "Fluxo Principal"
if "etapa_fluxo" not in st.session_state: st.session_state.etapa_fluxo = 1
if "tabelas_extraidas" not in st.session_state: st.session_state.tabelas_extraidas = []
# NOVA MEMÓRIA: Para guardar o que o usuário escolheu no st.radio
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
    st.image("https://cdn-icons-png.flaticon.com/512/2936/2936690.png", width=60)
    st.title("Hub Comercial")
    st.divider()
    st.markdown("### 🔄 Fluxo de Precificação")
    
    etapas = ["1. Importar", "2. Auditar Tabelas", "3. Mapear Colunas", "4. Variação"]
    for i, nome in enumerate(etapas, start=1):
        if i < st.session_state.etapa_fluxo: st.markdown(f"✅ **{nome}**")
        elif i == st.session_state.etapa_fluxo: st.markdown(f"📍 <span style='color:#FF4B4B'>**{nome}**</span>", unsafe_allow_html=True)
        else: st.markdown(f"🔒 <span style='color:gray'>{nome}</span>", unsafe_allow_html=True)
    
    if st.session_state.etapa_fluxo > 1:
        if st.button("⚠️ Cancelar Fluxo", use_container_width=True):
            resetar_fluxo()
            st.rerun()

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
        arquivos = st.file_uploader("Selecione Excel ou CSV", type=['csv', 'xlsx', 'xlsb', 'xls'], accept_multiple_files=True)
        
        if arquivos:
            if st.button("Buscar Tabelas Válidas ➡️", type="primary"):
                with st.spinner("O Especialista está escaneando os arquivos..."):
                    st.session_state.tabelas_extraidas = []
                    st.session_state.decisoes_usuario = {} # Limpa decisões antigas
                    
                    for arquivo in arquivos:
                        nome = arquivo.name
                        ext = nome.split('.')[-1].lower()
                        
                        try:
                            if ext == 'csv':
                                df = pd.read_csv(arquivo, sep=None, engine='python', header=None)
                                resultado = encontrar_tabela_valida(df, nome, "CSV")
                                if resultado: st.session_state.tabelas_extraidas.append(resultado)
                            else:
                                dict_abas = pd.read_excel(arquivo, sheet_name=None, header=None)
                                for aba, df_aba in dict_abas.items():
                                    resultado = encontrar_tabela_valida(df_aba, nome, aba)
                                    if resultado: st.session_state.tabelas_extraidas.append(resultado)
                        except Exception as e:
                            st.error(f"Erro ao processar o arquivo {nome}: {e}")
                            st.stop()
                    
                    st.session_state.etapa_fluxo = 2
                    st.rerun()

    # ------------------------------------------
    # ETAPA 2: AUDITORIA DAS EXTRAÇÕES
    # ------------------------------------------
    elif st.session_state.etapa_fluxo == 2:
        st.header("👁️ Passo 2: Auditar Inteligência do Sistema")
        
        if len(st.session_state.tabelas_extraidas) == 0:
            st.error("Nenhuma tabela comercial foi encontrada nesses arquivos. Eles podem ser apenas relatórios textuais ou o cabeçalho não possui palavras-chave comerciais.")
            if st.button("⬅️ Voltar"):
                st.session_state.etapa_fluxo = 1
                st.rerun()
        else:
            st.success(f"O sistema encontrou {len(st.session_state.tabelas_extraidas)} tabela(s) potencial(is). Revise-as abaixo:")
            st.write("A inteligência do sistema já pré-selecionou uma ação baseada no comportamento dos dados, mas a palavra final é sua.")
            
            for tbl in st.session_state.tabelas_extraidas:
                id_unico = tbl['id_unico']
                
                with st.container(border=True):
                    # Divide a tela: 3/4 para a tabela, 1/4 para os botões de ação
                    col_tabela, col_acao = st.columns([3, 1])
                    
                    with col_tabela:
                        st.markdown(f"**Arquivo:** `{tbl['arquivo']}` | **Aba:** `{tbl['aba']}`")
                        st.caption(f"🤖 **Lógica:** {tbl['motivo_escolha']} (Score: {tbl['confianca']})")
                        st.dataframe(tbl['dados'].head(5), use_container_width=True)
                    
                    with col_acao:
                        st.markdown("**O que fazer com esta tabela?**")
                        
                        opcoes_acao = ["❓ Pendente", "✅ Consolidar (Lista Preço)", "ℹ️ Tabela Técnica", "🗑️ Ignorar / Lixo"]
                        sugestao_ia = tbl.get('sugestao_acao', "❓ Pendente")
                        
                        # Acha em qual posição da lista a sugestão da IA está, para deixar marcado sozinho
                        index_sugestao = opcoes_acao.index(sugestao_ia) if sugestao_ia in opcoes_acao else 0
                        
                        decisao = st.radio(
                            "Ação Sugerida:",
                            options=opcoes_acao,
                            index=index_sugestao,
                            key=f"radio_{id_unico}",
                            label_visibility="collapsed" # Esconde o texto duplicado "Ação Sugerida" pra ficar mais limpo
                        )
                        
                        # Salva a decisão na memória
                        st.session_state.decisoes_usuario[id_unico] = decisao

            st.divider()
            
            # Botões de Navegação com Trava de Segurança
            col_voltar, col_avancar = st.columns([1, 4])
            with col_voltar:
                if st.button("⬅️ Voltar"):
                    st.session_state.etapa_fluxo = 1
                    st.rerun()
                    
            with col_avancar:
                # Conta quantos botões ainda estão marcados como "Pendente"
                pendentes = sum(1 for d in st.session_state.decisoes_usuario.values() if d == "❓ Pendente")
                
                if pendentes > 0:
                    st.warning(f"⚠️ Você ainda tem {pendentes} tabela(s) marcada(s) como 'Pendente'. Classifique todas para avançar.")
                else:
                    if st.button("Aprovar e Avançar ➡️", type="primary"):
                        st.session_state.etapa_fluxo = 3
                        st.rerun()

    # ------------------------------------------
    # ETAPA 3: MAPEAMENTO DE COLUNAS
    # ------------------------------------------
    elif st.session_state.etapa_fluxo == 3:
        st.header("🔀 Passo 3: Mapeamento de Colunas")
        st.write("Aqui pegaremos apenas as tabelas marcadas como '✅ Consolidar' para mapear o De/Para.")
        if st.button("⬅️ Voltar"):
            st.session_state.etapa_fluxo = 2
            st.rerun()