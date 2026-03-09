import streamlit as st

def renderizar_passo_2():
    st.header("👁️ Passo 2: Definir Intervalos")
    
    for tbl in st.session_state.tabelas_extraidas:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"📄 `{tbl['arquivo']}` | 📑 `{tbl['aba']}`")
                st.dataframe(tbl['dados'].head(3), width="stretch")
            with c2:
                opcoes = ["❓ Pendente", "✅ Consolidar", "🗑️ Lixo/Ignorar"]
                # Lógica de sugestão
                sugestao = 1 if tbl.get('sugestao_acao') == "Consolidar" else (2 if tbl.get('sugestao_acao') == "Ignorar" else 0)
                
                st.session_state.decisoes_usuario[tbl['id_unico']] = st.radio(
                    "Ação:", 
                    opcoes, 
                    index=sugestao, 
                    key=f"r_{tbl['id_unico']}"
                )
                
    if st.button("Aprovar e Avançar ➡️", type="primary", use_container_width=True):
        st.session_state.etapa_fluxo = 3
        st.rerun()