import streamlit as st
from modulos.orquestrador_importacao import processar_arquivos_upload
from modulos.classificador.aprendizado import obter_perfis_salvos

PERFIS_EXISTENTES = obter_perfis_salvos()

def renderizar_passo_1():
    st.header("📂 Passo 1: Importar Arquivos")
    col_perfil, col_arq = st.columns([1, 2])
    with col_perfil:
        opcoes_perfil = ["Selecione..."] + PERFIS_EXISTENTES + ["➕ Criar Novo Perfil..."]
        perfil_escolhido = st.selectbox("Fornecedor:", opcoes_perfil)
        nome_novo_perfil = st.text_input("Novo fornecedor:") if perfil_escolhido == "➕ Criar Novo Perfil..." else ""
    with col_arq:
        arquivos = st.file_uploader("Arquivos", type=['csv', 'xlsx', 'xlsb', 'xls'], accept_multiple_files=True, label_visibility="collapsed")
    
    st.divider()
    pode_avancar = (arquivos and perfil_escolhido != "Selecione...")
    fornecedor_final = nome_novo_perfil.strip() if perfil_escolhido == "➕ Criar Novo Perfil..." else perfil_escolhido
    
    if st.button("Analisar Arquivos ➡️", type="primary", use_container_width=True, disabled=not pode_avancar):
        st.session_state.fornecedor_selecionado = fornecedor_final
        with st.spinner("Aguardo enquanto o sistema está lendo o arquivo..."):
            tabelas, erros = processar_arquivos_upload(arquivos)
            if erros:
                for erro in erros: st.error(f"🚨 Erro em: {erro['arquivo']}")
                st.stop()
            st.session_state.tabelas_extraidas = tabelas
            bons = [t for t in tabelas if t.get('sugestao_acao') == "Consolidar"]
            if len(tabelas) == 1 and len(bons) == 1:
                st.session_state.decisoes_usuario[tabelas[0]['id_unico']] = "✅ Consolidar"
                st.session_state.etapa_fluxo = 3
            else:
                st.session_state.etapa_fluxo = 2
            st.rerun()
