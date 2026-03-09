import streamlit as st

# ==========================================
# CONFIGURAÇÃO GLOBAL (Sempre a primeira linha)
# ==========================================
st.set_page_config(page_title="App Comercial", page_icon="🏢", layout="wide")

# ==========================================
# DEFINIÇÃO DAS PÁGINAS (st.Page)
# ==========================================
# O parâmetro 'default=True' faz com que a Home seja a página inicial ao abrir o app
pg_home = st.Page("interface/home.py", title="Página Inicial", icon="👋", default=True)

pg_analise = st.Page("interface/analise_lista/controlador_fluxo.py", title="Análise de Lista", icon="📊")
pg_banco = st.Page("interface/banco_dados.py", title="Banco de Dados", icon="🗄️")
pg_memoria = st.Page("interface/memoria_calc.py", title="Memória de Cálculo (em breve)", icon="🧮")

navegacao = st.navigation([pg_home, pg_analise, pg_banco, pg_memoria])

navegacao.run()