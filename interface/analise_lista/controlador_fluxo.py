import streamlit as st
from configuracoes.state_manager import inicializar_estado
from interface.analise_lista.menu_lateral import renderizar_sidebar
from interface.analise_lista.passo1_importacao import renderizar_passo_1
from interface.analise_lista.passo2_intervalos import renderizar_passo_2
from interface.analise_lista.passo3_mapeamento import renderizar_passo_3
from interface.analise_lista.passo4_auditoria import renderizar_passo_4
from interface.analise_lista.passo5_variacao import renderizar_passo_5

# ==========================================
# CONFIGURAÇÃO E ESTILIZAÇÃO
# ==========================================
st.set_page_config(page_title="Análise de Lista", layout="wide")

st.markdown("""
    <style>
    div.stButton > button[kind="primary"] { background-color: #0066cc; border-color: #0066cc; color: white; }
    div.stButton > button[kind="primary"]:hover { background-color: #0052a3; border-color: #0052a3; }
    </style>
""", unsafe_allow_html=True)

# Inicializa variáveis
inicializar_estado()

# Rendeniza Menu Lateral
renderizar_sidebar()

if st.session_state.pagina_atual == "Fluxo Principal":
    
    match st.session_state.etapa_fluxo:
        case 1:
            renderizar_passo_1()
        case 2:
            renderizar_passo_2()
        case 3:
            renderizar_passo_3()
        case 4:
            renderizar_passo_4()
        case 5:
            renderizar_passo_5()