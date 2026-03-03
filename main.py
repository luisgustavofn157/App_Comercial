import streamlit as st
import pandas as pd
import traceback
from modulos.orquestrador_importacao import processar_arquivos_upload
from modulos.consolidador import consolidar_dataframes
from config_erp import DICIONARIO_ERP, NOMES_VISUAIS_ERP, CONCEITOS_MULTIPLOS, REVERSO_ERP
from modulos.cerebro.orquestrador import avaliar_coluna
from modulos.cerebro.memoria import registrar_feedback

# ==========================================
# CONFIGURAÇÃO E ESTILIZAÇÃO
# ==========================================
st.set_page_config(page_title="Hub Comercial - Precificação", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    div.stButton > button[kind="primary"] { background-color: #0066cc; border-color: #0066cc; color: white; }
    div.stButton > button[kind="primary"]:hover { background-color: #0052a3; border-color: #0052a3; }
    .etapa-atual { background-color: #e6f2ff; color: #0066cc; padding: 8px; border-radius: 6px; font-weight: bold; margin-bottom: 4px; border-left: 4px solid #0066cc; }
    .etapa-concluida { color: #28a745; padding: 8px; margin-bottom: 4px; }
    .etapa-bloqueada { color: #6c757d; padding: 8px; margin-bottom: 4px; opacity: 0.7; }
    </style>
""", unsafe_allow_html=True)

PERFIS_EXISTENTES = ["DS", "VIEMAR"]

# ==========================================
# GERENCIAMENTO DE ESTADO
# ==========================================
if "pagina_atual" not in st.session_state: st.session_state.pagina_atual = "Fluxo Principal"
if "etapa_fluxo" not in st.session_state: st.session_state.etapa_fluxo = 1
if "tabelas_extraidas" not in st.session_state: st.session_state.tabelas_extraidas = []
if "decisoes_usuario" not in st.session_state: st.session_state.decisoes_usuario = {}
if "fornecedor_selecionado" not in st.session_state: st.session_state.fornecedor_selecionado = "" 

def resetar_fluxo():
    st.session_state.etapa_fluxo = 1
    st.session_state.tabelas_extraidas = []
    st.session_state.decisoes_usuario = {}
    st.session_state.fornecedor_selecionado = ""
    for k in ["df_bruto_consolidado", "mapeamento_temporario", "df_mapeamento_ui", "editor_mapeamento"]:
        if k in st.session_state: del st.session_state[k]
    st.rerun()

# ==========================================
# MENU LATERAL
# ==========================================
with st.sidebar:
    col_img, col_txt = st.columns([1, 3])
    with col_img: st.image("https://cdn-icons-png.flaticon.com/512/2936/2936690.png", width=50)
    with col_txt: st.markdown("### Hub Comercial\nPrecificação")
    st.divider()
    
    st.markdown("#### 🔄 Fluxo de Precificação")
    etapas = ["1. Importação", "2. Auditoria", "3. Mapeamento", "4. Variação"]
    for i, nome in enumerate(etapas, start=1):
        if i < st.session_state.etapa_fluxo: st.markdown(f"<div class='etapa-concluida'>✅ {nome}</div>", unsafe_allow_html=True)
        elif i == st.session_state.etapa_fluxo: st.markdown(f"<div class='etapa-atual'>▶ {nome}</div>", unsafe_allow_html=True)
        else: st.markdown(f"<div class='etapa-bloqueada'>🔒 {nome}</div>", unsafe_allow_html=True)
    
    if st.session_state.etapa_fluxo > 1:
        st.button("🛑 Cancelar e Recomeçar", use_container_width=True, on_click=resetar_fluxo)

# ==========================================
# ROTEADOR DE PÁGINAS PRINCIPAL
# ==========================================
if st.session_state.pagina_atual == "Fluxo Principal":
    
    # ETAPA 1: IMPORTAÇÃO E CONTEXTO
    if st.session_state.etapa_fluxo == 1:
        st.header("📂 Passo 1: Contexto e Importação")
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
            with st.spinner("Analisando..."):
                tabelas, erros = processar_arquivos_upload(arquivos)
                if erros:
                    for erro in erros:
                        st.error(f"🚨 Erro em: {erro['arquivo']}")
                        with st.expander("Raio-X Técnico"): st.code(erro['traceback'])
                    st.stop()
                st.session_state.tabelas_extraidas = tabelas
                
                bons = [t for t in tabelas if t.get('sugestao_acao') == "Consolidar"]
                if len(tabelas) == 1 and len(bons) == 1:
                    st.session_state.decisoes_usuario[tabelas[0]['id_unico']] = "✅ Consolidar"
                    st.session_state.etapa_fluxo = 3
                else:
                    st.session_state.etapa_fluxo = 2
                st.rerun()

    # ETAPA 2: AUDITORIA
    elif st.session_state.etapa_fluxo == 2:
        st.header("👁️ Passo 2: Auditoria de Intervalos")
        for tbl in st.session_state.tabelas_extraidas:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"📄 `{tbl['arquivo']}` | 📑 `{tbl['aba']}`")
                    st.dataframe(tbl['dados'].head(3), width="stretch") # Corrigido width
                with c2:
                    opcoes = ["❓ Pendente", "✅ Consolidar", "🗑️ Lixo/Ignorar"]
                    sugestao = 1 if tbl.get('sugestao_acao') == "Consolidar" else (2 if tbl.get('sugestao_acao') == "Ignorar" else 0)
                    st.session_state.decisoes_usuario[tbl['id_unico']] = st.radio("Ação:", opcoes, index=sugestao, key=f"r_{tbl['id_unico']}")
        if st.button("Aprovar e Avançar ➡️", type="primary", use_container_width=True):
            st.session_state.etapa_fluxo = 3
            st.rerun()

    # ETAPA 3: MAPEAMENTO PROFISSIONAL (ESTILO POWERQUERY)
    elif st.session_state.etapa_fluxo == 3:
        st.header("🔀 Passo 3: Mapeamento e Estruturação")
        
        aprovadas = [t for t in st.session_state.tabelas_extraidas if st.session_state.decisoes_usuario.get(t['id_unico']) == "✅ Consolidar"]
        
        if not aprovadas:
            st.warning("Nada selecionado."); st.button("Voltar", on_click=resetar_fluxo)
        else:
            if "df_bruto_consolidado" not in st.session_state:
                st.session_state.df_bruto_consolidado = consolidar_dataframes(aprovadas)
            
            df_completo = st.session_state.df_bruto_consolidado
            colunas_reais = [c for c in df_completo.columns if not str(c).startswith("__")]
            
            # 1. CRIANDO A TABELA DE UI APENAS UMA VEZ
            if "df_mapeamento_ui" not in st.session_state:
                sugestoes = {}
                notas_ia = {}
                for col in colunas_reais:
                    match, nota, _ = avaliar_coluna(col, NOMES_VISUAIS_ERP, st.session_state.fornecedor_selecionado, df_completo.head(10))
                    sugestoes[col] = match
                    notas_ia[col] = float(nota) if pd.notna(nota) else 0.0
                
                dados_ui = []
                for col in colunas_reais:
                    amostra = df_completo[col].dropna().astype(str).head(3).tolist()
                    dados_ui.append({
                        "Coluna no Arquivo": str(col),
                        "Confiança IA": notas_ia.get(col, 0.0),
                        "Mapeamento (ERP)": sugestoes.get(col, DICIONARIO_ERP["IGNORAR"]),
                        "Amostra dos Dados": " | ".join(amostra) if amostra else "(Coluna Vazia)"
                    })
                
                # A base de dados nunca é sobrescrita para evitar o Cabo de Guerra
                st.session_state.df_mapeamento_ui = pd.DataFrame(dados_ui)

            # 2. CONSTRUÇÃO DO PAINEL DE MAPEAMENTO
            st.markdown(f"#### ⚙️ Definir Colunas - Perfil: `{st.session_state.fornecedor_selecionado}`")
            
            # Editor com width="stretch" (Fim daquele log chato no terminal)
            df_editado = st.data_editor(
                st.session_state.df_mapeamento_ui,
                width="stretch", 
                hide_index=True,
                disabled=["Coluna no Arquivo", "Confiança IA", "Amostra dos Dados"],
                column_config={
                    "Coluna no Arquivo": st.column_config.TextColumn("Coluna Original"),
                    "Confiança IA": st.column_config.ProgressColumn("🤖 Confiança", format="%d%%", min_value=0, max_value=100),
                    "Mapeamento (ERP)": st.column_config.SelectboxColumn("Destino (ERP)", options=NOMES_VISUAIS_ERP, required=True),
                    "Amostra dos Dados": st.column_config.TextColumn("Amostra (3 linhas)")
                },
                key="editor_mapeamento" # Essa chave guarda as edições do usuário!
            )
            
            # 3. ATUALIZAÇÃO E ANÁLISE DE CONFLITOS
            mapeamento_atualizado = dict(zip(df_editado["Coluna no Arquivo"], df_editado["Mapeamento (ERP)"]))
            st.session_state.mapeamento_temporario = mapeamento_atualizado
            
            escolhas = [v for v in mapeamento_atualizado.values() if v != DICIONARIO_ERP["IGNORAR"]]
            conceitos_estritos = [REVERSO_ERP.get(e) for e in escolhas if REVERSO_ERP.get(e) not in CONCEITOS_MULTIPLOS]
            duplicados = [item for item in set(conceitos_estritos) if conceitos_estritos.count(item) > 1]

            # 4. AÇÕES DE UNIFICAÇÃO
            if duplicados:
                st.divider()
                st.error("⚠️ **Conflitos de Mapeamento Encontrados**")
                st.info("O ERP não aceita múltiplas colunas para os campos abaixo. Você pode unificá-las em uma só clicando no botão.")
                
                col_avisos, col_vazia = st.columns([2, 1])
                with col_avisos:
                    for d in duplicados:
                        cols_conflito = [k for k, v in mapeamento_atualizado.items() if REVERSO_ERP.get(v) == d]
                        
                        if st.button(f"🪄 Mesclar colunas: {', '.join(cols_conflito)} ➡️ {DICIONARIO_ERP[d]}", key=f"unif_{d}", use_container_width=True):
                            col_mestra = cols_conflito[0]
                            for col_sec in cols_conflito[1:]:
                                st.session_state.df_bruto_consolidado[col_mestra] = st.session_state.df_bruto_consolidado[col_mestra].fillna(st.session_state.df_bruto_consolidado[col_sec])
                                st.session_state.df_bruto_consolidado = st.session_state.df_bruto_consolidado.drop(columns=[col_sec])
                            
                            # Limpamos a memória do UI para forçar a recarregar as novas colunas
                            del st.session_state.df_mapeamento_ui
                            if "editor_mapeamento" in st.session_state:
                                del st.session_state.editor_mapeamento
                            st.success("Colunas mescladas!")
                            st.rerun()
            else:
                st.write("")
                if st.button("Salvar Perfil e Avançar ➡️", type="primary", use_container_width=True):
                    for col_excel, conceito in mapeamento_atualizado.items():
                        registrar_feedback(col_excel, conceito, NOMES_VISUAIS_ERP, st.session_state.fornecedor_selecionado)
                    st.session_state.mapeamento_oficial = mapeamento_atualizado
                    st.session_state.etapa_fluxo = 4
                    st.rerun()

            # 5. O DATAFRAME REAL
            st.divider()
            st.markdown("#### 📄 Visualização Real da Planilha")
            st.caption("Esta é a base de dados exata que será enviada para os motores de cálculo.")
            st.dataframe(st.session_state.df_bruto_consolidado.head(20), width="stretch") # Corrigido width

    # ETAPA 4: VARIAÇÃO
    elif st.session_state.etapa_fluxo == 4:
        st.header("📈 Passo 4: Variação e Exportação")
        st.success("Base de dados preparada com sucesso!")
        if st.button("⬅️ Voltar ao Mapeamento"):
            st.session_state.etapa_fluxo = 3
            st.rerun()