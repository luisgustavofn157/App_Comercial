import streamlit as st

def inicializar_estado():
    """Inicializa todas as variáveis de sessão necessárias para o sistema."""
    # --- Fluxo Principal ---
    if "pagina_atual" not in st.session_state: st.session_state.pagina_atual = "Fluxo Principal"
    if "etapa_fluxo" not in st.session_state: st.session_state.etapa_fluxo = 1
    if "tabelas_extraidas" not in st.session_state: st.session_state.tabelas_extraidas = []
    if "decisoes_usuario" not in st.session_state: st.session_state.decisoes_usuario = {}
    if "fornecedor_selecionado" not in st.session_state: st.session_state.fornecedor_selecionado = "" 
    if "checkpoints" not in st.session_state: st.session_state.checkpoints = {} 

    # --- Tela Banco de Dados ---
    if "db_query_input" not in st.session_state: st.session_state.db_query_input = ""
    if "db_combo_biblioteca" not in st.session_state: st.session_state.db_combo_biblioteca = "Selecione uma consulta pronta..."
    if "db_executar_agora" not in st.session_state: st.session_state.db_executar_agora = False

def resetar_fluxo():
    """Limpa o estado e recomeça o fluxo de análise de lista."""
    st.session_state.etapa_fluxo = 1
    st.session_state.tabelas_extraidas = []
    st.session_state.decisoes_usuario = {}
    st.session_state.fornecedor_selecionado = ""
    st.session_state.checkpoints = {}
    
    chaves_para_limpar = [
        "df_bruto_consolidado", "mapeamento_temporario", "df_mapeamento_ui", 
        "df_limpo", "df_aprovados", "df_rejeitados", "df_conflitos", 
        "df_conflitos_ui", "auditoria_concluida"
    ]
    for k in chaves_para_limpar:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

def resetar_banco_dados():
    """Limpa a tela e a memória da interface do banco de dados."""
    st.session_state.db_query_input = ""
    st.session_state.db_combo_biblioteca = "Selecione uma consulta pronta..."
    st.session_state.db_executar_agora = False
    
    chaves_db = ["db_resultado_sql", "db_df_seguro", "db_excel_bytes", "db_tempo_execucao"]
    for k in chaves_db:
        if k in st.session_state:
            del st.session_state[k]