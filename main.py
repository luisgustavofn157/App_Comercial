import streamlit as st
import pandas as pd
import traceback
from modulos.orquestrador_importacao import processar_arquivos_upload
from modulos.consolidador import consolidar_dataframes
from config_erp import DICIONARIO_ERP, NOMES_VISUAIS_ERP, CONCEITOS_MULTIPLOS, REVERSO_ERP
from modulos.cerebro.orquestrador import avaliar_coluna
from modulos.cerebro.memoria import registrar_feedback
from modulos.validador_comercial import higienizar_dados, processar_validacoes
from modulos.exportador import exportar_csv_br


# ==========================================
# CONFIGURAÇÃO E ESTILIZAÇÃO
# ==========================================
st.set_page_config(page_title="App Comercial", page_icon="🏢", layout="wide")

st.markdown("""
    <style>
    div.stButton > button[kind="primary"] { background-color: #0066cc; border-color: #0066cc; color: white; }
    div.stButton > button[kind="primary"]:hover { background-color: #0052a3; border-color: #0052a3; }
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
if "checkpoints" not in st.session_state: st.session_state.checkpoints = {} 

def resetar_fluxo():
    st.session_state.etapa_fluxo = 1
    st.session_state.tabelas_extraidas = []
    st.session_state.decisoes_usuario = {}
    st.session_state.fornecedor_selecionado = ""
    st.session_state.checkpoints = {}
    for k in ["df_bruto_consolidado", "mapeamento_temporario", "df_mapeamento_ui", "df_limpo", "df_aprovados", "df_rejeitados"]:
        if k in st.session_state: del st.session_state[k]
    st.rerun()

# ==========================================
# MENU LATERAL (MINIMALISTA)
# ==========================================
with st.sidebar:
    st.markdown("## 🏢 App Comercial")
    st.markdown("---")
    
    # Seção 1: Navegação do Fluxo
    st.caption("📍 FLUXO DE TRABALHO")
    etapas = ["Importar", "Definir Intervalos", "Mapear Colunas", "Tratar Linhas", "Calcular Variação"]
    
    for i, nome in enumerate(etapas, start=1):
        if i < st.session_state.etapa_fluxo:
            # Etapa Concluída (Verde e discreto)
            st.markdown(f"**✅ {i}. {nome}**")
        elif i == st.session_state.etapa_fluxo:
            # Etapa Atual (Azul e com destaque visual)
            st.markdown(f"**🟦 {i}. {nome}** 👈")
        else:
            # Etapa Bloqueada (Cinza para não poluir a visão)
            st.markdown(f"<span style='color: #6c757d;'>🔒 {i}. {nome}</span>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Seção 2: Arquivos de Saída
    st.caption("📥 ARQUIVOS GERADOS")
    
    if "lista_limpa" in st.session_state.checkpoints:
        st.download_button(
            label="📄 1. Lista Limpa",
            data=st.session_state.checkpoints["lista_limpa"],
            file_name=f"01_Lista_Limpa_{st.session_state.fornecedor_selecionado}.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary" # Fica azul para chamar a atenção quando libera
        )
    else:
        st.button("🔒 1. Lista Limpa", disabled=True, use_container_width=True)
        
    st.button("🔒 2. Relatório de Variação", disabled=True, use_container_width=True)
    st.button("🔒 3. Script SQL (ERP)", disabled=True, use_container_width=True)
    
    st.markdown("---")
    
    # Botão de emergência discreto no rodapé
    if st.session_state.etapa_fluxo > 1:
        st.button("🛑 Cancelar e Recomeçar", use_container_width=True, on_click=resetar_fluxo)

# ==========================================
# ROTEADOR DE PÁGINAS PRINCIPAL
# ==========================================
if st.session_state.pagina_atual == "Fluxo Principal":
    
    # ETAPA 1: IMPORTAÇÃO E CONTEXTO
    if st.session_state.etapa_fluxo == 1:
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
            with st.spinner("Analisando..."):
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

    # ETAPA 2: DEFINIR INTERVALOS
    elif st.session_state.etapa_fluxo == 2:
        st.header("👁️ Passo 2: Definir Intervalos")
        for tbl in st.session_state.tabelas_extraidas:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"📄 `{tbl['arquivo']}` | 📑 `{tbl['aba']}`")
                    st.dataframe(tbl['dados'].head(3), width="stretch")
                with c2:
                    opcoes = ["❓ Pendente", "✅ Consolidar", "🗑️ Lixo/Ignorar"]
                    sugestao = 1 if tbl.get('sugestao_acao') == "Consolidar" else (2 if tbl.get('sugestao_acao') == "Ignorar" else 0)
                    st.session_state.decisoes_usuario[tbl['id_unico']] = st.radio("Ação:", opcoes, index=sugestao, key=f"r_{tbl['id_unico']}")
        if st.button("Aprovar e Avançar ➡️", type="primary", use_container_width=True):
            st.session_state.etapa_fluxo = 3
            st.rerun()

    # ETAPA 3: MAPEAR COLUNAS
    elif st.session_state.etapa_fluxo == 3:
        st.header("🔀 Passo 3: Mapear Colunas")
        
        aprovadas = [t for t in st.session_state.tabelas_extraidas if st.session_state.decisoes_usuario.get(t['id_unico']) == "✅ Consolidar"]
        if not aprovadas:
            st.warning("Nada selecionado."); st.button("Voltar", on_click=resetar_fluxo)
        else:
            if "df_bruto_consolidado" not in st.session_state:
                st.session_state.df_bruto_consolidado = consolidar_dataframes(aprovadas)
            
            df_completo = st.session_state.df_bruto_consolidado
            colunas_reais = [c for c in df_completo.columns if not str(c).startswith("__")]
            
            if "df_mapeamento_ui" not in st.session_state:
                dados_ui = []
                for col in colunas_reais:
                    match, nota, _ = avaliar_coluna(col, NOMES_VISUAIS_ERP, st.session_state.fornecedor_selecionado, df_completo.head(10))
                    nota_float = float(nota) if pd.notna(nota) else 0.0
                    
                    if nota_float >= 70.0:
                        sugestao_final = match
                        nota_final = nota_float
                    else:
                        sugestao_final = DICIONARIO_ERP["IGNORAR"]
                        nota_final = None 

                    amostra = df_completo[col].dropna().astype(str).head(3).tolist()
                    dados_ui.append({
                        "Coluna no Arquivo": str(col),
                        "Confiança IA": nota_final,
                        "Mapeamento (ERP)": sugestao_final,
                        "Amostra dos Dados": " | ".join(amostra) if amostra else "(Coluna Vazia)"
                    })
                st.session_state.df_mapeamento_ui = pd.DataFrame(dados_ui)

            st.markdown(f"#### ⚙️ Definir Colunas - Perfil: `{st.session_state.fornecedor_selecionado}`")
            altura_dinamica = (len(st.session_state.df_mapeamento_ui) * 35) + 42

            df_editado = st.data_editor(
                st.session_state.df_mapeamento_ui,
                width="stretch", 
                height=altura_dinamica,
                hide_index=True,
                disabled=["Coluna no Arquivo", "Confiança IA", "Amostra dos Dados"],
                column_config={
                    "Coluna no Arquivo": st.column_config.TextColumn("Coluna Original"),
                    "Confiança IA": st.column_config.ProgressColumn("🤖 Confiança", format="%d%%", min_value=0, max_value=100),
                    "Mapeamento (ERP)": st.column_config.SelectboxColumn("Destino (ERP)", options=NOMES_VISUAIS_ERP, required=True),
                    "Amostra dos Dados": st.column_config.TextColumn("Amostra (3 linhas)")
                },
                key="editor_mapeamento"
            )

            houve_alteracao_dropdown = False
            for i in range(len(df_editado)):
                col_excel = df_editado.at[i, "Coluna no Arquivo"]
                novo_mapeamento = df_editado.at[i, "Mapeamento (ERP)"]
                mapeamento_antigo = st.session_state.df_mapeamento_ui.at[i, "Mapeamento (ERP)"]

                if novo_mapeamento != mapeamento_antigo:
                    if novo_mapeamento == DICIONARIO_ERP["IGNORAR"]:
                        nova_nota_final = None
                    else:
                        match_recalculado, nota_recalculada, _ = avaliar_coluna(col_excel, [novo_mapeamento], st.session_state.fornecedor_selecionado, df_completo.head(10))
                        nota_float_recalculada = float(nota_recalculada) if pd.notna(nota_recalculada) else 0.0
                        nova_nota_final = nota_float_recalculada if nota_float_recalculada >= 70.0 else None
                    
                    df_editado.at[i, "Confiança IA"] = nova_nota_final
                    houve_alteracao_dropdown = True

            st.session_state.df_mapeamento_ui = df_editado.copy()
            if houve_alteracao_dropdown: st.rerun()

            mapeamento_atualizado = dict(zip(df_editado["Coluna no Arquivo"], df_editado["Mapeamento (ERP)"]))
            st.session_state.mapeamento_temporario = mapeamento_atualizado
            
            escolhas = [v for v in mapeamento_atualizado.values() if v != DICIONARIO_ERP["IGNORAR"]]
            conceitos_estritos = [REVERSO_ERP.get(e) for e in escolhas if REVERSO_ERP.get(e) not in CONCEITOS_MULTIPLOS]
            duplicados = [item for item in set(conceitos_estritos) if conceitos_estritos.count(item) > 1]

            if duplicados:
                st.divider()
                st.subheader("⚠️ Gestão de Conflitos de Colunas")
                
                for d in duplicados:
                    cols_conflito = [k for k, v in mapeamento_atualizado.items() if REVERSO_ERP.get(v) == d]
                    
                    # --- NOVA LÓGICA: VERIFICAÇÃO DE SOBREPOSIÇÃO (OVERLAP) ---
                    df_subset = st.session_state.df_bruto_consolidado[cols_conflito]
                    
                    # 1. Cria uma máscara: True onde tem dado útil, False onde é vazio/NaN
                    # Transformamos em string, tiramos espaços em branco e convertemos pra minúsculo para checar nulos
                    df_str = df_subset.fillna("").astype(str).apply(lambda col: col.str.strip().str.lower())
                    mask_df = (df_str != "") & (~df_str.isin(["nan", "none", "<na>"]))
                    
                    # 2. Soma a quantidade de colunas preenchidas linha a linha
                    # Se alguma linha tiver soma > 1, significa que há choque de dados!
                    tem_sobreposicao = (mask_df.sum(axis=1) > 1).any()
                    
                    with st.container(border=True):
                        if tem_sobreposicao:
                            st.error(f"🚨 **Conflito de Dados Bloqueante em: `{DICIONARIO_ERP[d]}`**")
                            st.write(f"As colunas **{', '.join(cols_conflito)}** possuem valores preenchidos na mesma linha. Mesclá-las causaria **perda de informações**.")
                            st.info("👉 **Ação Exigida:** Revise o painel acima e altere o destino de uma dessas colunas para outro conceito ou 'Ignorar'.")
                        else:
                            st.warning(f"🔀 **Mesclagem Segura Disponível: `{DICIONARIO_ERP[d]}`**")
                            st.write(f"As colunas **{', '.join(cols_conflito)}** são complementares (não se sobrepõem em nenhuma linha).")
                            if st.button(f"🪄 Mesclar colunas sem perda de dados", key=f"unif_{d}", use_container_width=True):
                                col_mestra = cols_conflito[0]
                                for col_sec in cols_conflito[1:]:
                                    st.session_state.df_bruto_consolidado[col_mestra] = st.session_state.df_bruto_consolidado[col_mestra].fillna(st.session_state.df_bruto_consolidado[col_sec])
                                    st.session_state.df_bruto_consolidado = st.session_state.df_bruto_consolidado.drop(columns=[col_sec])
                                    st.session_state.df_mapeamento_ui = st.session_state.df_mapeamento_ui[st.session_state.df_mapeamento_ui["Coluna no Arquivo"] != col_sec]
                                st.session_state.df_mapeamento_ui = st.session_state.df_mapeamento_ui.reset_index(drop=True)
                                st.success("Colunas mescladas com segurança!")
                                st.rerun()
            else:
                st.write("")
                if st.button("Salvar Perfil e Avançar ➡️", type="primary", use_container_width=True):
                    for col_excel, conceito in mapeamento_atualizado.items():
                        registrar_feedback(col_excel, conceito, NOMES_VISUAIS_ERP, st.session_state.fornecedor_selecionado)
                    st.session_state.mapeamento_oficial = mapeamento_atualizado
                    
                    # PREPARAÇÃO DO DATAFRAME LIMPO
                    df_limpo = st.session_state.df_bruto_consolidado.copy()
                    colunas_uteis = {k: v for k, v in mapeamento_atualizado.items() if v != DICIONARIO_ERP["IGNORAR"]}
                    colunas_lixo = [k for k, v in mapeamento_atualizado.items() if v == DICIONARIO_ERP["IGNORAR"]]
                    
                    df_limpo = df_limpo.drop(columns=[c for c in colunas_lixo if c in df_limpo.columns])
                    
                    # Desambiguação de Colunas Repetidas (Resolve o erro do PyArrow)
                    contagens = {}
                    for destino in colunas_uteis.values():
                        contagens[destino] = contagens.get(destino, 0) + 1
                        
                    renomeio_final = {}
                    ocorrencias = {}
                    for col_excel, destino in colunas_uteis.items():
                        if contagens[destino] > 1:
                            ocorrencias[destino] = ocorrencias.get(destino, 0) + 1
                            renomeio_final[col_excel] = f"{destino} ({ocorrencias[destino]})"
                        else:
                            renomeio_final[col_excel] = destino
                            
                    df_limpo = df_limpo.rename(columns=renomeio_final)
                    
                    # --- A MÁGICA: CHAMA A TIPAGEM ANTES DE EXPORTAR ---
                    df_limpo = higienizar_dados(df_limpo)
                    
                    # Salva no estado para a Etapa 4 usar
                    st.session_state.df_limpo = df_limpo
                    
                    # A MÁGICA DO EXCEL: Usando nosso exportador blindado
                    csv_bytes = exportar_csv_br(df_limpo)
                    st.session_state.checkpoints["lista_limpa"] = csv_bytes
                    
                    st.session_state.etapa_fluxo = 4
                    st.rerun()

            # 6. O DATAFRAME REAL (VISUALIZADOR VIVO)
            st.divider()
            st.markdown("#### 📄 Visualização Real da Planilha")
            st.caption("Esta é a base de dados exata que será enviada para a próxima etapa (colunas ignoradas estão ocultas).")
            
            # --- MÁGICA DO VISUALIZADOR VIVO ---
            # Identifica em tempo real tudo o que o usuário marcou como IGNORAR
            colunas_para_ocultar = [col for col, destino in mapeamento_atualizado.items() if destino == DICIONARIO_ERP["IGNORAR"]]
            
            # Cria uma cópia apenas para exibição, dropando o "lixo"
            df_visualizacao = st.session_state.df_bruto_consolidado.drop(
                columns=[c for c in colunas_para_ocultar if c in st.session_state.df_bruto_consolidado.columns]
            )
            
            # Renomeia o cabeçalho para o usuário já ver como vai ficar no ERP
            colunas_uteis_temp = {k: v for k, v in mapeamento_atualizado.items() if v != DICIONARIO_ERP["IGNORAR"]}
            df_visualizacao = df_visualizacao.rename(columns=colunas_uteis_temp)
            
            # Desenha a tabela limpa
            st.dataframe(df_visualizacao.head(9), width="stretch")

    # ETAPA 4: TRATAR LINHAS (O MOTOR DE VALIDAÇÃO ISOLADO)
    elif st.session_state.etapa_fluxo == 4:
        st.header("🕵️ Passo 4: Auditoria e Validação Comercial")
        st.write("Aplicando regras de higienização e validação aos dados mapeados...")
        
        # Executa o Motor de Regras apenas uma vez e salva no estado
        if "df_aprovados" not in st.session_state:
            df_aprovados, df_rejeitados = processar_validacoes(st.session_state.df_limpo)
            st.session_state.df_aprovados = df_aprovados
            st.session_state.df_rejeitados = df_rejeitados

        df_aprovados = st.session_state.df_aprovados
        df_rejeitados = st.session_state.df_rejeitados
        
        # KPIs
        total_linhas = len(st.session_state.df_limpo)
        linhas_erro = len(df_rejeitados)
        linhas_ok = len(df_aprovados)
        taxa = (linhas_ok / total_linhas) * 100 if total_linhas > 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("📦 Total de Produtos", total_linhas)
        c2.metric("✅ Prontos para Variação", linhas_ok)
        c3.metric("🚨 Com Críticas", linhas_erro, delta=f"{taxa:.1f}% de Aceitação", delta_color="off")
        
        st.divider()

        if df_rejeitados.empty:
            st.success("🎉 Sensacional! Todos os dados estão higienizados e validados com 100% de precisão.")
            col_vazia, col_btn = st.columns([3, 1])
            with col_btn:
                if st.button("Avançar para Variação ➡️", type="primary", use_container_width=True):
                    st.session_state.etapa_fluxo = 5
                    st.rerun()
        else:
            st.error("⚠️ **Foram encontradas inconsistências na lista do Fornecedor.**")
            st.write("Abaixo estão os itens que não passaram nas regras de negócio após a tentativa de higienização. Baixe o relatório para envio de devolutiva.")
            
            # Mostra o relatório na tela para conferência rápida
            st.dataframe(df_rejeitados.head(50), width="stretch", hide_index=True)
            
            # Geração do Arquivo de Devolutiva (Checkpoint 2) usando o exportador blindado
            csv_devolutiva = exportar_csv_br(df_rejeitados)
            
            col_down, col_avancar = st.columns([1, 1])
            with col_down:
                st.download_button(
                    label="📥 Baixar Devolutiva ao Fornecedor (.CSV)",
                    data=csv_devolutiva,
                    file_name=f"02_Devolutiva_Erros_{st.session_state.fornecedor_selecionado}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    type="primary"
                )
            with col_avancar:
                st.warning("Deseja seguir apenas com os produtos validados?")
                if st.button("Ignorar erros e Avançar com Aprovados ➡️", use_container_width=True):
                    st.session_state.etapa_fluxo = 5
                    st.rerun()

        st.divider()
        if st.button("⬅️ Voltar para Ajustes de Mapeamento"):
            # Limpa o cache das validações se o usuário voltar para mudar o mapeamento
            for k in ["df_aprovados", "df_rejeitados"]:
                if k in st.session_state: del st.session_state[k]
            st.session_state.etapa_fluxo = 3
            st.rerun()

    # ETAPA 5: CALCULAR VARIAÇÃO 
    elif st.session_state.etapa_fluxo == 5:
        st.header("📈 Passo 5: Calcular Variação")
        st.write("Em breve: Motor de cálculo e integração de dados.")