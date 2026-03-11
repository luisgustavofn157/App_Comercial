import streamlit as st
from modulos.orquestrador_importacao import processar_arquivos_upload
from memoria.gerenciador_memoria import obter_marcas, obter_perfis, atualizar_marcas_do_perfil

def obter_todas_marcas_cadastradas():
    """Busca a lista de marcas direto do banco SQLite local"""
    # Importe o conectar_banco no topo do arquivo se já não estiver lá
    from memoria.inicializar_sqlite import conectar_banco 
    
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # O ORDER BY garante que a lista apareça em ordem alfabética no Streamlit
    cursor.execute("SELECT nome_marca FROM tb_marca ORDER BY nome_marca")
    
    # Extrai os nomes das marcas e transforma em uma lista do Python
    marcas = [linha['nome_marca'] for linha in cursor.fetchall()]
    
    conn.close()
    return marcas

def salvar_edicao_callback(perfil, chave_do_widget):
    """Callback executado ANTES da tela recarregar ao clicar em Salvar"""
    # Lemos as marcas buscando pela chave dinâmica exata daquele perfil
    novas_marcas = st.session_state[chave_do_widget] 
    atualizar_marcas_do_perfil(perfil, novas_marcas)
    st.session_state.toggle_edicao = False # Desliga o toggle com segurança

def cancelar_edicao_callback():
    """Callback executado ANTES da tela recarregar ao clicar em Cancelar"""
    st.session_state.toggle_edicao = False # Desliga o toggle com segurança


def renderizar_passo_1():
    st.header("📂 Passo 1: Importar Arquivos")
    
    col_perfil, col_marca, col_arq = st.columns([1.5, 2, 2])
    
    todas_marcas_db = obter_marcas()
    
    # IMPORTANTE: Buscar os perfis DENTRO da função de renderização garante
    # que a lista esteja sempre atualizada se um perfil for criado em outra tela.
    perfis_existentes = obter_perfis()
    
    with col_perfil:
        opcoes_perfil = ["Selecione..."] + ["➕ Criar Novo Perfil..."] + perfis_existentes
        perfil_escolhido = st.selectbox("Perfil:", opcoes_perfil)
        
        if perfil_escolhido == "➕ Criar Novo Perfil...":
            nome_novo_perfil = st.text_input("Nome do Novo Perfil:")
        else:
            nome_novo_perfil = ""

    with col_marca:
        # Cenário 1: Nada selecionado
        if perfil_escolhido == "Selecione...":
            marcas_escolhidas = st.multiselect("Marcas vinculadas:", options=[], disabled=True)
            
        # Cenário 2: Criando um perfil do zero
        elif perfil_escolhido == "➕ Criar Novo Perfil...":
            marcas_escolhidas = st.multiselect(
                "Selecione as marcas deste novo perfil:", 
                options=todas_marcas_db,
                placeholder="Escolha uma ou mais marcas..."
            )
            
            # Ciclo encapsulado para CRIAR NOVO PERFIL
            if nome_novo_perfil.strip() and marcas_escolhidas:
                if st.button("💾 Salvar Novo Perfil", type="primary", use_container_width=True):
                    atualizar_marcas_do_perfil(nome_novo_perfil, marcas_escolhidas)
                    st.toast("✅ Perfil criado com sucesso!")
                    st.rerun()
            
        # Cenário 3: Perfil já existente
        else:
            marcas_vinculadas_db = obter_marcas(perfil_escolhido)
            opcoes_disponiveis = list(set(todas_marcas_db + marcas_vinculadas_db))
            
            # O Toggle
            modo_edicao = st.toggle("✏️ Editar marcas deste perfil", key="toggle_edicao")
            
            # 💡 A CHAVE MÁGICA: O nome do perfil faz parte da key do widget
            chave_dinamica = f"marcas_widget_{perfil_escolhido}"
            
            marcas_escolhidas = st.multiselect(
                "Marcas vinculadas:",
                options=opcoes_disponiveis,
                default=marcas_vinculadas_db,
                disabled=not modo_edicao,
                key=chave_dinamica, # <-- Usamos a chave dinâmica aqui
                placeholder="Nenhuma marca vinculada." if modo_edicao else ""
            )
            
            # Ciclo encapsulado com Callbacks
            if modo_edicao:
                col_btn_salvar, col_btn_cancelar = st.columns(2)
                
                with col_btn_salvar:
                    st.button(
                        "💾 Salvar", 
                        type="primary", 
                        use_container_width=True,
                        on_click=salvar_edicao_callback,
                        # Passamos o perfil e a chave dinâmica para o callback saber onde ler
                        args=(perfil_escolhido, chave_dinamica) 
                    )
                        
                with col_btn_cancelar:
                    st.button(
                        "❌ Cancelar", 
                        use_container_width=True,
                        on_click=cancelar_edicao_callback
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
    
    # Regras para poder avançar
    tem_nome_perfil = bool(nome_novo_perfil.strip()) if perfil_escolhido == "➕ Criar Novo Perfil..." else True
    tem_marcas = len(marcas_escolhidas) > 0
    
    # Se a chave do toggle existir e for True, ele está editando
    esta_editando = st.session_state.get("toggle_edicao", False) 
    
    # Adicionamos 'not esta_editando' na trava. Não avança se tiver edição pendente.
    pode_avancar = (arquivos and perfil_escolhido != "Selecione..." and tem_nome_perfil and tem_marcas and not esta_editando)
    
    perfil_final = nome_novo_perfil.strip() if perfil_escolhido == "➕ Criar Novo Perfil..." else perfil_escolhido
    
    if st.button("Analisar Arquivos ➡️", type="primary", use_container_width=True, disabled=not pode_avancar):
        st.session_state.perfil_selecionado = perfil_final
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