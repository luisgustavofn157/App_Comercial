import streamlit as st
from modulos.orquestrador_importacao import processar_arquivos_upload
from banco_de_dados.gerenciador_memoria import obter_perfis, atualizar_marcas_do_perfil, obter_marcas_por_perfil
from banco_de_dados.conexao_benner import executar_consulta_benner

def salvar_edicao_callback(perfil, chave_do_widget, chave_do_toggle):
    novas_marcas = st.session_state[chave_do_widget] 
    atualizar_marcas_do_perfil(perfil, novas_marcas)
    st.session_state[chave_do_toggle] = False 

def cancelar_edicao_callback(chave_do_toggle):
    st.session_state[chave_do_toggle] = False 

def renderizar_passo_1():
    st.header("📂 Passo 1: Importar Listas de Preço")
    
    col_perfil, col_marca, col_arq = st.columns([1, 1, 2])
    
    perfis_existentes = obter_perfis()
    
    with col_perfil:
        opcoes_perfil = ["Selecione..."] + ["➕ Criar Novo Perfil..."] + perfis_existentes
        perfil_escolhido = st.selectbox("Perfil:", opcoes_perfil, key="selectbox_perfil")
        
        if perfil_escolhido == "➕ Criar Novo Perfil...":
            nome_novo_perfil = st.text_input("Nome do Novo Perfil:")
        else:
            nome_novo_perfil = ""

    chave_toggle = f"toggle_edicao_{perfil_escolhido}"

    with col_marca:
        if perfil_escolhido == "Selecione...":
            marcas_escolhidas = st.multiselect("Marcas vinculadas:", options=[], disabled=True)
            
        elif perfil_escolhido == "➕ Criar Novo Perfil...":
            # CARREGAMENTO SOB DEMANDA 1: Vai ao Benner apenas ao criar perfil
            with st.spinner("🔄 A consultar o Benner em tempo real..."):
                QUERY_BENNER = "select nome from PD_MARCASPRODUTOS pm"
                df_marcas = executar_consulta_benner(QUERY_BENNER)
                todas_marcas_db = sorted(df_marcas.iloc[:, 0].astype(str).str.strip().dropna().unique().tolist())
                
            marcas_escolhidas = st.multiselect(
                "Selecione as marcas deste novo perfil:", 
                options=todas_marcas_db,
                placeholder="Escolha uma ou mais marcas..."
            )
            
            if nome_novo_perfil.strip() and marcas_escolhidas:
                if st.button("💾 Salvar Novo Perfil", type="primary", use_container_width=True):
                    atualizar_marcas_do_perfil(nome_novo_perfil, marcas_escolhidas)
                    st.toast("✅ Perfil criado com sucesso!")
                    st.rerun()
                    
        else:
            # DIA A DIA: Carrega ultra-rápido APENAS do banco local SQLite
            marcas_vinculadas_db = obter_marcas_por_perfil(perfil_escolhido)
            modo_edicao = st.toggle("✏️ Editar marcas deste perfil", key=chave_toggle)
            chave_dinamica_widget = f"marcas_widget_{perfil_escolhido}"
            
            if not modo_edicao:
                # O ecrã fica bloqueado mostrando os dados da memória local (Zero queries ao Benner)
                marcas_escolhidas = st.multiselect(
                    "Marcas vinculadas:",
                    options=marcas_vinculadas_db,
                    default=marcas_vinculadas_db,
                    disabled=True,
                    key=chave_dinamica_widget
                )
            else:
                # CARREGAMENTO SOB DEMANDA 2: Vai ao Benner apenas se o toggle de edição for ativado
                with st.spinner("🔄 A consultar o Benner em tempo real para edição..."):
                    QUERY_BENNER = "select nome from PD_MARCASPRODUTOS pm"
                    df_marcas = executar_consulta_benner(QUERY_BENNER)
                    todas_marcas_db = sorted(df_marcas.iloc[:, 0].astype(str).str.strip().dropna().unique().tolist())
                
                # O filtro de segurança para não travar o Streamlit continua ativo
                marcas_validas_padrao = [m for m in marcas_vinculadas_db if m in todas_marcas_db]
                
                marcas_escolhidas = st.multiselect(
                    "Marcas vinculadas:",
                    options=todas_marcas_db,
                    default=marcas_validas_padrao,
                    key=chave_dinamica_widget
                )
                
                col_btn_salvar, col_btn_cancelar = st.columns(2)
                
                with col_btn_salvar:
                    st.button(
                        "💾 Salvar", 
                        type="primary", 
                        use_container_width=True,
                        on_click=salvar_edicao_callback,
                        args=(perfil_escolhido, chave_dinamica_widget, chave_toggle) 
                    )
                        
                with col_btn_cancelar:
                    st.button(
                        "❌ Cancelar", 
                        use_container_width=True,
                        on_click=cancelar_edicao_callback,
                        args=(chave_toggle,)
                    )

    with col_arq:
        st.write("Upload de Arquivos")
        arquivos = st.file_uploader(
            "Arquivos", 
            type=['csv', 'xlsx', 'xlsb', 'xls'], 
            accept_multiple_files=True, 
            label_visibility="collapsed"
        )
    
    st.divider()
    
    # --- REGRAS DE AVANÇO CORRIGIDAS ---
    esta_editando = st.session_state.get(chave_toggle, False)
    tem_marcas = len(marcas_escolhidas) > 0
    
    # Bloqueia estritamente o avanço se o usuário estiver na tela de criação (evita "perfil fantasma")
    perfil_valido_para_avanco = perfil_escolhido not in ["Selecione...", "➕ Criar Novo Perfil..."]
    
    pode_avancar = (
        arquivos and 
        perfil_valido_para_avanco and 
        tem_marcas and 
        not esta_editando
    )
    
    if st.button("Analisar Arquivos ➡️", type="primary", use_container_width=True, disabled=not pode_avancar):
        st.session_state.perfil_selecionado = perfil_escolhido
        st.session_state.marcas_selecionadas = marcas_escolhidas 
        
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