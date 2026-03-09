import streamlit as st
from configuracoes.state_manager import resetar_fluxo
from modulos.exportador import exportar_devolutiva_erros

def renderizar_sidebar():
    with st.sidebar:
        st.caption("ETAPAS DA ANÁLISE")
        
        etapas = ["Importar Arquivos", "Definir Intervalos", "Mapear Colunas", "Tratar Linhas", "Calcular Variação"]
        
        for i, nome in enumerate(etapas, start=1):
            if i < st.session_state.etapa_fluxo:
                st.markdown(f"<span style='color: #28a745;'>✓ {i}. {nome}</span>", unsafe_allow_html=True)
            elif i == st.session_state.etapa_fluxo:
                st.markdown(f"**{i}. {nome}**")
            else:
                st.markdown(f"<span style='color: #6c757d;'>{i}. {nome}</span>", unsafe_allow_html=True)
        
        st.write("") 
        if st.session_state.etapa_fluxo > 1:
            st.button("↺ Resetar Análise", use_container_width=True, on_click=resetar_fluxo)

    # ==========================================
    # ARQUIVOS GERADOS (UI Contextual: Só aparece se existir)
    # ==========================================
    tem_lista_limpa = "lista_limpa" in st.session_state.checkpoints
    
    # Verifica se a etapa de validação já rodou e gerou críticas
    tem_criticas = "df_rejeitados" in st.session_state and not st.session_state.df_rejeitados.empty
    
    if tem_lista_limpa or tem_criticas:
        st.markdown("---")
        st.caption("ARQUIVOS GERADOS")
        
        if tem_lista_limpa:
            st.download_button(
                label="📄 Baixar Lista Limpa",
                data=st.session_state.checkpoints["lista_limpa"],
                file_name=f"01_Lista_Limpa_{st.session_state.fornecedor_selecionado}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
        if tem_criticas:
            # Reutiliza a função de exportação simples para gerar o arquivo na hora se precisar
            excel_devolutiva = exportar_devolutiva_erros(st.session_state.df_rejeitados)
            st.download_button(
                label="🚨 Baixar Lista com Críticas",
                data=excel_devolutiva,
                file_name=f"02_Devolutiva_Erros_{st.session_state.fornecedor_selecionado}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )