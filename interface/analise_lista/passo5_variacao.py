import streamlit as st

def renderizar_passo_5():
    st.header("📈 Passo 5: Calcular Variação")
    st.write("Em breve: Motor de cálculo e integração de dados.")
    
    # Exemplo rápido para você ver os dados puros chegando aqui:
    if "df_lista_purificada" in st.session_state:
        st.dataframe(st.session_state.df_lista_purificada.head())