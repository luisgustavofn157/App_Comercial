import streamlit as st
from tratamento_de_dados.landing.gerador_bronze import gerar_camada_bronze

def renderizar_passo_2():
    st.header("👁️ Passo 2: Definir Intervalos de Preço")
    st.write("Selecione somente os intervalos de dados que se referem a lista de preços (Descarte quando for aba de Descontinuados, Histórico, etc...)")
    
    # Inicializa o dicionário de decisões se não existir
    if "decisoes_usuario" not in st.session_state:
        st.session_state.decisoes_usuario = {}
    
    for tbl in st.session_state.tabelas_extraidas:
        with st.container(border=True):
            # Layout atualizado: coluna central de espaçamento para empurrar a ação mais à direita
            c_info, c_espaco, c_acao = st.columns([5, 1, 2])
            
            with c_info:
                st.markdown(f"📄 `{tbl['arquivo']}` | 📑 `{tbl['aba']}`")
                st.dataframe(tbl['dados'].head(3), width="stretch")
                
            with c_acao:
                opcoes = ["❓ Pendente", "✅ Consolidar", "🗑️ Lixo/Ignorar"]
                
                sugestao_idx = 0
                if tbl.get('sugestao_acao') == "Consolidar": sugestao_idx = 1
                elif tbl.get('sugestao_acao') == "Ignorar": sugestao_idx = 2
                
                # Se o usuário já tiver tomado uma decisão antes, mantemos ela
                valor_atual = st.session_state.decisoes_usuario.get(tbl['id_unico'])
                index_final = opcoes.index(valor_atual) if valor_atual in opcoes else sugestao_idx
                
                st.session_state.decisoes_usuario[tbl['id_unico']] = st.radio(
                    "Ação:", 
                    opcoes, 
                    index=index_final, 
                    key=f"r_{tbl['id_unico']}"
                )
                
    st.divider()
    
    # Validação para avançar: O usuário não pode deixar nada como "Pendente"
    pendentes = sum(1 for v in st.session_state.decisoes_usuario.values() if "Pendente" in v)
    
    if pendentes > 0:
        st.warning(f"⚠️ Defina a ação para todas as {pendentes} tabelas pendentes antes de avançar.")
        st.button("Aprovar e Avançar ➡️", disabled=True, use_container_width=True)
    else:
        if st.button("Aprovar e Avançar ➡️", type="primary", use_container_width=True):
            with st.spinner("Consolidando dados (Forjando Camada Bronze)..."):
                df_bronze = gerar_camada_bronze(st.session_state.tabelas_extraidas, st.session_state.decisoes_usuario)
                
                if df_bronze is not None and not df_bronze.empty:
                    # Tranca o df bruto consolidado na memória do sistema
                    st.session_state.df_bronze = df_bronze
                    st.session_state.etapa_fluxo = 3
                    st.rerun()
                else:
                    st.error("Nenhuma tabela foi aprovada para consolidação. Revise suas escolhas.")