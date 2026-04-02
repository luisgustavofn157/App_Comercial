import streamlit as st
from tratamento_de_dados.bronze.gerador_bronze import gerar_camada_bronze

def renderizar_passo_2():
    st.header("👁️ Passo 2: Triagem de Abas e Intervalos")
    st.write("Identifique quais abas contêm as listas de preços reais e descarte lixos (como Históricos ou Capas).")
    
    # ==========================================
    # 1. PRÉ-CARREGAMENTO DAS DECISÕES
    # ==========================================
    # Lemos as sugestões do sistema antes de renderizar a tela para a barra de progresso ser exata
    if "decisoes_usuario" not in st.session_state:
        st.session_state.decisoes_usuario = {}
        for tbl in st.session_state.tabelas_extraidas:
            sugestao = "❓ Pendente"
            if tbl.get('sugestao_acao') == "Consolidar": sugestao = "✅ Consolidar"
            elif tbl.get('sugestao_acao') == "Ignorar": sugestao = "🗑️ Lixo/Ignorar"
            st.session_state.decisoes_usuario[tbl['id_unico']] = sugestao

    # ==========================================
    # 2. PAINEL DE PROGRESSO (O "Norte" do utilizador)
    # ==========================================
    total_abas = len(st.session_state.tabelas_extraidas)
    pendentes = sum(1 for v in st.session_state.decisoes_usuario.values() if "Pendente" in v)
    resolvidas = total_abas - pendentes
    
    st.progress(resolvidas / total_abas if total_abas > 0 else 0)
    
    if pendentes > 0:
        st.warning(f"🎯 **Faltam {pendentes} abas** para classificar antes de poder avançar.")
    else:
        st.success("✨ **Todas as abas classificadas!** A sua lista está pronta para ser consolidada.")
        
    st.divider()

    # ==========================================
    # 3. RENDERIZAÇÃO DOS CARDS (Ação Direta)
    # ==========================================
    opcoes = ["❓ Pendente", "✅ Consolidar", "🗑️ Lixo/Ignorar"]
    
    for tbl in st.session_state.tabelas_extraidas:
        id_tbl = tbl['id_unico']
        valor_atual = st.session_state.decisoes_usuario.get(id_tbl, "❓ Pendente")
        
        # Muda o ícone do título instantaneamente quando a ação muda
        if "Consolidar" in valor_atual:
            icone_status = "✅"
        elif "Ignorar" in valor_atual:
            icone_status = "🗑️"
        else:
            icone_status = "⏳"

        with st.container(border=True):
            
            # Cabeçalho com forte hierarquia visual
            st.subheader(f"{icone_status} Aba: `{tbl['aba']}`")
            st.caption(f"📁 Arquivo Origem: **{tbl['arquivo']}**")

            # Preview compacta e esticada
            st.dataframe(tbl['dados'].head(5), use_container_width=True)
            
            st.markdown("---")
            
            # A pergunta direta com os botões por baixo
            st.session_state.decisoes_usuario[id_tbl] = st.radio(
                "👉 **O que fazer com esta aba?**", 
                opcoes, 
                index=opcoes.index(valor_atual), 
                key=f"r_{id_tbl}",
                horizontal=True
            )
            
    st.divider()
    
    # ==========================================
    # 4. BOTÃO DE AVANÇO (Hard Gate)
    # ==========================================
    if pendentes > 0:
        st.button("Aprovar e Avançar ➡️", disabled=True, use_container_width=True, help="Resolva todas as abas pendentes acima para libertar o botão.")
    else:
        if st.button("Aprovar e Avançar ➡️", type="primary", use_container_width=True):
            with st.spinner("Consolidando dados (Forjando Camada Bronze)..."):
                df_bronze = gerar_camada_bronze(st.session_state.tabelas_extraidas, st.session_state.decisoes_usuario)
                
                if df_bronze is not None and not df_bronze.empty:
                    st.session_state.df_bronze = df_bronze
                    st.session_state.etapa_fluxo = 3
                    st.rerun()
                else:
                    st.error("Nenhuma tabela foi aprovada para consolidação. Revise as suas escolhas.")