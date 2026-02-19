import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Hub Comercial - Precificação", page_icon="📊", layout="wide")

# ==========================================
# GERENCIAMENTO DE ESTADO (MEMÓRIA DO APP)
# ==========================================
# Variável para saber qual tela exibir (Fluxo ou Ferramentas)
if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = "Fluxo Principal"

# Variáveis exclusivas do Fluxo de Precificação
if "etapa_fluxo" not in st.session_state:
    st.session_state.etapa_fluxo = 1

if "dados_importados" not in st.session_state:
    st.session_state.dados_importados = {} # Guardará os DataFrames dos arquivos

# Função para mudar de página geral
def mudar_pagina(nome_pagina):
    st.session_state.pagina_atual = nome_pagina

# Função para resetar (quebrar) o fluxo atual e começar do zero
def resetar_fluxo():
    st.session_state.etapa_fluxo = 1
    st.session_state.dados_importados = {}
    st.session_state.pagina_atual = "Fluxo Principal"

# ==========================================
# MENU LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2936/2936690.png", width=60)
    st.title("Hub Comercial")
    
    st.divider()
    
    # ROTEADOR DO FLUXO PRINCIPAL
    st.markdown("### 🔄 Fluxo de Precificação")
    
    # Criando o visualizador de progresso das etapas
    etapas = [
        "1. Importar Arquivos",
        "2. Definições da Análise",
        "3. Tratamento e Limpeza",
        "4. Variação de Preço"
    ]
    
    for i, nome_etapa in enumerate(etapas, start=1):
        if i < st.session_state.etapa_fluxo:
            st.markdown(f"✅ **{nome_etapa}**") # Concluído
        elif i == st.session_state.etapa_fluxo:
            st.markdown(f"📍 <span style='color:#FF4B4B'>**{nome_etapa}**</span>", unsafe_allow_html=True) # Atual
        else:
            st.markdown(f"🔒 <span style='color:gray'>{nome_etapa}</span>", unsafe_allow_html=True) # Bloqueado
    
    # Botões de controle do fluxo
    if st.button("Ir para o Fluxo Atual", use_container_width=True, type="primary"):
        mudar_pagina("Fluxo Principal")
        
    if st.session_state.etapa_fluxo > 1:
        if st.button("⚠️ Cancelar Fluxo e Recomeçar", use_container_width=True):
            resetar_fluxo()
            st.rerun() # Força o app a recarregar a tela imediatamente
            
    st.divider()
    
    # FERRAMENTAS GLOBAIS
    st.markdown("### 🛠️ Ferramentas Globais")
    if st.button("📑 Perfis de Fornecedores", use_container_width=True): mudar_pagina("Perfis")
    if st.button("📋 Logs de Execução", use_container_width=True): mudar_pagina("Logs")

# ==========================================
# ROTEADOR DE PÁGINAS (FRONTEND PRINCIPAL)
# ==========================================
pagina = st.session_state.pagina_atual

# ------------------------------------------
# TELA 1: O FLUXO DE PRECIFICAÇÃO (CONTROLA AS 4 ETAPAS)
# ------------------------------------------
if pagina == "Fluxo Principal":
    
    # ETAPA 1: IMPORTAÇÃO
    if st.session_state.etapa_fluxo == 1:
        st.header("📂 Passo 1: Importar Arquivos do Fornecedor")
        st.write("Arraste e solte as listas de preços. Você pode enviar múltiplos arquivos de uma vez.")
        
        # O uploader aceita múltiplas extensões e arquivos
        arquivos_upados = st.file_uploader(
            "Selecione os arquivos (Excel ou CSV)", 
            type=['csv', 'xlsx', 'xlsm', 'xlsb', 'xls'],
            accept_multiple_files=True
        )
        
        if arquivos_upados:
            st.info(f"{len(arquivos_upados)} arquivo(s) carregado(s) na memória temporária.")
            
            if st.button("Processar Arquivos e Avançar ➡️", type="primary"):
                with st.spinner("Lendo arquivos e convertendo dados..."):
                    
                    # Processa cada arquivo individualmente
                    for arquivo in arquivos_upados:
                        nome = arquivo.name
                        extensao = nome.split('.')[-1].lower()
                        
                        try:
                            # O Pandas escolhe o "motor" certo dependendo da extensão
                            if extensao == 'csv':
                                # Usamos sep=None e engine='python' para o Pandas tentar adivinhar se o separador é vírgula ou ponto e vírgula
                                df = pd.read_csv(arquivo, sep=None, engine='python')
                            elif extensao == 'xlsb':
                                df = pd.read_excel(arquivo, engine='pyxlsb')
                            elif extensao == 'xls':
                                df = pd.read_excel(arquivo, engine='xlrd')
                            else: # xlsx, xlsm
                                df = pd.read_excel(arquivo, engine='openpyxl')
                            
                            # Salva o dataframe na "memória" do nosso fluxo
                            st.session_state.dados_importados[nome] = df
                            
                        except Exception as e:
                            st.error(f"Erro ao ler o arquivo {nome}: {e}")
                            st.stop() # Para o processo se um arquivo estiver corrompido
                    
                    # Se tudo deu certo, avança a etapa e recarrega a tela
                    st.session_state.etapa_fluxo = 2
                    st.rerun()

    # ETAPA 2: DEFINIÇÕES DA ANÁLISE
    elif st.session_state.etapa_fluxo == 2:
        st.header("⚙️ Passo 2: Definições da Análise")
        st.write("Os arquivos foram lidos com sucesso! Analise uma amostra abaixo e defina os parâmetros.")
        
        # Mostra as abas para cada arquivo importado
        nomes_arquivos = list(st.session_state.dados_importados.keys())
        abas = st.tabs(nomes_arquivos)
        
        for i, nome in enumerate(nomes_arquivos):
            with abas[i]:
                df = st.session_state.dados_importados[nome]
                st.caption(f"Amostra dos dados do arquivo (Total de linhas: {len(df)})")
                st.dataframe(df.head(10), use_container_width=True) # Mostra apenas as 10 primeiras linhas para não pesar
        
        st.divider()
        st.subheader("Sugestões do Sistema 🤖")
        st.info("Aqui entrará a inteligência de analisar o cabeçalho e sugerir de qual fornecedor é esta lista.")
        
        # Botões de navegação
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("⬅️ Voltar"):
                st.session_state.etapa_fluxo = 1
                st.rerun()
        with col2:
            if st.button("Avançar ➡️", type="primary"):
                st.session_state.etapa_fluxo = 3
                st.rerun()

    # ETAPA 3: TRATAMENTO
    elif st.session_state.etapa_fluxo == 3:
        st.header("🔀 Passo 3: Tratamento e Limpeza")
        st.write("Painel de de/para e padronização dos dados.")
        
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("⬅️ Voltar"):
                st.session_state.etapa_fluxo = 2
                st.rerun()

    # ETAPA 4: VARIAÇÃO DE PREÇO
    elif st.session_state.etapa_fluxo == 4:
        st.header("📈 Passo 4: Variação de Preço")
        st.write("Cruzamento com os dados do ERP e cálculo de distorção.")
        
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("⬅️ Voltar"):
                st.session_state.etapa_fluxo = 3
                st.rerun()

# ------------------------------------------
# TELAS DAS FERRAMENTAS GLOBAIS
# ------------------------------------------
elif pagina == "Perfis":
    st.header("📑 Gestão de Templates de Fornecedores")
    st.write("Nesta tela, configuraremos como cada fornecedor manda a tabela para deixar o Passo 2 mais inteligente.")

elif pagina == "Logs":
    st.header("📋 Logs de Execução")
    st.write("Auditoria: Quais listas foram processadas, por quem, e quando.")