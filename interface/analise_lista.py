import streamlit as st
import pandas as pd
import traceback
from modulos.orquestrador_importacao import processar_arquivos_upload
from modulos.consolidador import consolidar_dataframes
from config_erp import DICIONARIO_ERP, NOMES_VISUAIS_ERP, CONCEITOS_MULTIPLOS, REVERSO_ERP
from modulos.classificador.pipeline import classificar_dataset_completo, avaliar_coluna_fase1
from modulos.classificador.aprendizado import registrar_feedback, obter_perfis_salvos
from modulos.exportador import exportar_devolutiva_erros, exportar_lista_limpa
from modulos.validador_comercial import aplicar_filtro_morte, higienizar_dados
from modulos.novo_validador_comercial import processar_validacoes


# ==========================================
# 🛠️ MODO DESENVOLVEDOR (CHAVES DE DEBUG)
# Altere para False quando quiser testar a IA Pura ou Visão de Túnel isoladamente
# ==========================================
DEBUG_USAR_MEMORIA = True
DEBUG_USAR_ARBITRO = True

# ==========================================
# CONFIGURAÇÃO E ESTILIZAÇÃO
# ==========================================

st.markdown("""
    <style>
    div.stButton > button[kind="primary"] { background-color: #0066cc; border-color: #0066cc; color: white; }
    div.stButton > button[kind="primary"]:hover { background-color: #0052a3; border-color: #0052a3; }
    </style>
""", unsafe_allow_html=True)

PERFIS_EXISTENTES = obter_perfis_salvos()

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
    for k in ["df_bruto_consolidado", "mapeamento_temporario", "df_mapeamento_ui", "df_limpo", 
              "df_aprovados", "df_rejeitados", "df_conflitos", "df_conflitos_ui", "auditoria_concluida"]:
        if k in st.session_state: del st.session_state[k]
    st.rerun()

# ==========================================
# MENU LATERAL (MINIMALISTA E ENXUTO)
# ==========================================
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
    
    # Espaço para respirar e o Botão de Reset integrado ao fluxo
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
                resultados_ia = classificar_dataset_completo(
                    df_completo,  
                    NOMES_VISUAIS_ERP, 
                    st.session_state.fornecedor_selecionado,
                    usar_memoria=DEBUG_USAR_MEMORIA,
                    usar_arbitro=DEBUG_USAR_ARBITRO
                )
                
                dados_ui = []
                for col in colunas_reais:
                    match, nota_final, detalhes = resultados_ia[col]
                    
                    if nota_final is None or not detalhes:
                        match = DICIONARIO_ERP["IGNORAR"]
                        nota_final = None 

                    amostra = df_completo[col].dropna().astype(str).head(3).tolist()
                    dados_ui.append({
                        "Coluna Original": str(col),
                        "Confiança": nota_final,
                        "Destino (ERP)": match,
                        "Amostra dos Dados": " | ".join(amostra) if amostra else "(Vazia)"
                    })
                st.session_state.df_mapeamento_ui = pd.DataFrame(dados_ui)

            st.markdown(f"#### ⚙️ Definir Colunas - Perfil: `{st.session_state.fornecedor_selecionado}`")

            altura_dinamica = (len(st.session_state.df_mapeamento_ui) * 35) + 42

            df_editado = st.data_editor(
                st.session_state.df_mapeamento_ui,
                width="stretch", 
                height=altura_dinamica,
                hide_index=True,
                disabled=["Coluna Original", "Confiança", "Amostra dos Dados"],
                column_config={
                    "Coluna Original": st.column_config.TextColumn("Coluna Original", width="medium"),
                    "Confiança": st.column_config.ProgressColumn("Confiança", format="%d%%", min_value=0, max_value=100, width="small"),
                    "Destino (ERP)": st.column_config.SelectboxColumn("Destino (ERP)", options=NOMES_VISUAIS_ERP, required=True, width="medium"),
                    "Amostra dos Dados": st.column_config.TextColumn("Amostra (3 linhas)")
                },
                key="editor_mapeamento"
            )

            houve_alteracao_dropdown = False
            for i in range(len(df_editado)):
                col_excel = df_editado.at[i, "Coluna Original"]
                novo_mapeamento = df_editado.at[i, "Destino (ERP)"]
                mapeamento_antigo = st.session_state.df_mapeamento_ui.at[i, "Destino (ERP)"]

                if novo_mapeamento != mapeamento_antigo:
                    if novo_mapeamento == DICIONARIO_ERP["IGNORAR"]:
                        nova_nota_final = None
                    else:
                        boletim = avaliar_coluna_fase1(col_excel, [novo_mapeamento], st.session_state.fornecedor_selecionado, df_completo)
                        if boletim:
                            nova_nota_final = boletim[0]["nota"]
                        else:
                            nova_nota_final = None
                    
                    df_editado.at[i, "Confiança"] = nova_nota_final
                    houve_alteracao_dropdown = True

            st.session_state.df_mapeamento_ui = df_editado.copy()
            if houve_alteracao_dropdown: st.rerun()

            mapeamento_atualizado = dict(zip(df_editado["Coluna Original"], df_editado["Destino (ERP)"]))
            st.session_state.mapeamento_temporario = mapeamento_atualizado
            
            escolhas = [v for v in mapeamento_atualizado.values() if v != DICIONARIO_ERP["IGNORAR"]]
            conceitos_estritos = [REVERSO_ERP.get(e) for e in escolhas if REVERSO_ERP.get(e) not in CONCEITOS_MULTIPLOS]
            duplicados = [item for item in set(conceitos_estritos) if conceitos_estritos.count(item) > 1]

            if duplicados:
                st.divider()
                st.subheader("⚠️ Gestão de Conflitos de Colunas")
                
                for d in duplicados:
                    cols_conflito = [k for k, v in mapeamento_atualizado.items() if REVERSO_ERP.get(v) == d]
                    
                    df_subset = st.session_state.df_bruto_consolidado[cols_conflito]
                    df_str = df_subset.fillna("").astype(str).apply(lambda col: col.str.strip().str.lower())
                    
                    lixo_planilha = ["nan", "none", "<na>", "null", "0", "0.0", "-", "_", "."]
                    mask_df = (df_str != "") & (~df_str.isin(lixo_planilha))
                    
                    linhas_colisao = (mask_df.sum(axis=1) > 1).sum()
                    total_linhas = len(df_subset)
                    taxa_colisao = linhas_colisao / total_linhas if total_linhas > 0 else 0
                    
                    tem_sobreposicao = taxa_colisao > 0.02
                    
                    with st.container(border=True):
                        if tem_sobreposicao:
                            st.error(f"🚨 **Coluna Duplicada: `{DICIONARIO_ERP[d]}`**")
                            st.write(f"As colunas **{', '.join(cols_conflito)}** possuem valores preenchidos na mesma linha. Mesclá-las causaria **perda de informações**.")
                            st.info("👉 **Ação Exigida:** Revise o painel acima e altere o destino de uma dessas colunas para outro conceito ou 'Ignorar'.")
                        else:
                            st.warning(f"🔀 **Mesclagem Segura Disponível: `{DICIONARIO_ERP[d]}`**")
                            st.write(f"As colunas **{', '.join(cols_conflito)}** são complementares (não se sobrepõem em nenhuma linha).")
                            if st.button(f"🪄 Mesclar colunas sem perda de dados", key=f"unif_{d}", use_container_width=True):
                                col_mestra = cols_conflito[0]
                                for col_sec in cols_conflito[1:]:
                                    
                                    registrar_feedback(col_sec, DICIONARIO_ERP[d], st.session_state.fornecedor_selecionado)
                                    
                                    st.session_state.df_bruto_consolidado[col_mestra] = st.session_state.df_bruto_consolidado[col_mestra].fillna(st.session_state.df_bruto_consolidado[col_sec])
                                    
                                    st.session_state.df_bruto_consolidado = st.session_state.df_bruto_consolidado.drop(columns=[col_sec])
                                    st.session_state.df_mapeamento_ui = st.session_state.df_mapeamento_ui[st.session_state.df_mapeamento_ui["Coluna Original"] != col_sec]
                                    
                                st.session_state.df_mapeamento_ui = st.session_state.df_mapeamento_ui.reset_index(drop=True)
                                st.success("Colunas mescladas e padrão memorizado com segurança!")
                                st.rerun()
            else:
                st.write("")
                if st.button("Salvar Perfil e Avançar ➡️", type="primary", use_container_width=True):
                    # 1. Salva a Memória da IA
                    for col_excel, conceito in mapeamento_atualizado.items():
                        registrar_feedback(col_excel, conceito, st.session_state.fornecedor_selecionado)
                    st.session_state.mapeamento_oficial = mapeamento_atualizado
                    
                    # 2. O Checkpoint do Usuário
                    col_sku_mapeada = next((k for k, v in mapeamento_atualizado.items() if v == DICIONARIO_ERP["SKU"]), None)
                    df_vivos, df_lixo = aplicar_filtro_morte(st.session_state.df_bruto_consolidado, col_sku_mapeada)
                    
                    excel_bytes = exportar_lista_limpa(df_vivos, df_lixo)
                    st.session_state.checkpoints["lista_limpa"] = excel_bytes
                    
                    # 3. O Motor Interno do ERP
                    df_motor = df_vivos.copy()
                    
                    colunas_uteis = {k: v for k, v in mapeamento_atualizado.items() if v != DICIONARIO_ERP["IGNORAR"]}
                    colunas_lixo = [k for k, v in mapeamento_atualizado.items() if v == DICIONARIO_ERP["IGNORAR"]]
                    df_motor = df_motor.drop(columns=[c for c in colunas_lixo if c in df_motor.columns])
                    
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
                            
                    df_motor = df_motor.rename(columns=renomeio_final)
                    
                    df_motor = higienizar_dados(df_motor)
                    st.session_state.df_limpo = df_motor
                    
                    st.session_state.etapa_fluxo = 4
                    st.rerun()

            # # 6. O DATAFRAME REAL (VISUALIZADOR VIVO)
            # st.divider()
            # st.markdown("#### 📄 Visualização Real da Planilha")
            # st.caption("Esta é a base de dados exata que será enviada para a próxima etapa (colunas ignoradas estão ocultas).")
            
            # colunas_para_ocultar = [col for col, destino in mapeamento_atualizado.items() if destino == DICIONARIO_ERP["IGNORAR"]]
            # df_visualizacao = st.session_state.df_bruto_consolidado.drop(
            #     columns=[c for c in colunas_para_ocultar if c in st.session_state.df_bruto_consolidado.columns]
            # )
            
            # colunas_uteis_temp = {k: v for k, v in mapeamento_atualizado.items() if v != DICIONARIO_ERP["IGNORAR"]}
            
            # contagens_vis = {}
            # for destino in colunas_uteis_temp.values():
            #     contagens_vis[destino] = contagens_vis.get(destino, 0) + 1
                
            # renomeio_vis = {}
            # ocorrencias_vis = {}
            # for col_excel, destino in colunas_uteis_temp.items():
            #     if contagens_vis[destino] > 1:
            #         ocorrencias_vis[destino] = ocorrencias_vis.get(destino, 0) + 1
            #         renomeio_vis[col_excel] = f"{destino} ({ocorrencias_vis[destino]})"
            #     else:
            #         renomeio_vis[col_excel] = destino
            
            # df_visualizacao = df_visualizacao.rename(columns=renomeio_vis)
            # st.dataframe(df_visualizacao.head(9), width="stretch")

    # ETAPA 4: TRATAR LINHAS E HUMAN-IN-THE-LOOP
    elif st.session_state.etapa_fluxo == 4:
        st.header("🕵️ Passo 4: Auditoria e Validação Comercial")
        st.write("O Motor de Inteligência aplicou as regras de negócio da Rede Âncora.")
        
        # Roda o motor uma única vez garantindo que a base é checada
        if "df_aprovados" not in st.session_state:
            df_ap, df_rej, df_conf = processar_validacoes(st.session_state.df_limpo, st.session_state.mapeamento_oficial)
            st.session_state.df_aprovados = df_ap
            st.session_state.df_rejeitados = df_rej
            st.session_state.df_conflitos = df_conf
            
            # Prepara a tabela do purgatório com uma coluna de Checkbox sem afetar o dado original
            df_conf_ui = df_conf.copy()
            if not df_conf_ui.empty:
                df_conf_ui.insert(0, "Aprovar Linha", False)
            st.session_state.df_conflitos_ui = df_conf_ui
            
            st.session_state.auditoria_concluida = True

        df_aprovados = st.session_state.df_aprovados
        df_rejeitados = st.session_state.df_rejeitados
        df_conflitos = st.session_state.df_conflitos

        # 📊 1. PAINEL DE MÉTRICAS (Resumo da Faxina)
        total_linhas = len(st.session_state.df_limpo)
        linhas_ok = len(df_aprovados)
        linhas_erro = len(df_rejeitados)
        linhas_conflito = len(df_conflitos)
        taxa = (linhas_ok / total_linhas) * 100 if total_linhas > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Linhas Iniciais", total_linhas)
        c2.metric("✅ Validadas 100%", linhas_ok, delta=f"{taxa:.1f}% Retenção", delta_color="normal")
        c3.metric("🚨 Quarentena (Erros)", linhas_erro, delta="- Remoção Automática", delta_color="off")
        c4.metric("⚖️ Purgatório (Conflitos)", linhas_conflito, delta="Ação Necessária", delta_color="inverse" if linhas_conflito > 0 else "off")
        
        st.divider()

        # ⚖️ 2. O PURGATÓRIO (Human-in-the-Loop)
        if linhas_conflito > 0:
            st.warning("⚠️ **ATENÇÃO: Informações Conflitantes!** O fornecedor enviou o mesmo código de produto mais de uma vez com dados diferentes (ex: preços diferentes).")
            st.write("Decida abaixo qual linha é a verdadeira marcando a caixa **'Aprovar Linha'**. As que sobrarem serão rejeitadas.")
            
            # O Data Editor Mágico do Streamlit
            df_editado = st.data_editor(
                st.session_state.df_conflitos_ui,
                column_config={"Aprovar Linha": st.column_config.CheckboxColumn("✅ Aprovar", default=False)},
                disabled=list(df_conflitos.columns), # Bloqueia edição de dados de forma segura (como lista)
                hide_index=True,
                use_container_width=True
            )
            
            # Salva a decisão do usuário em tempo real
            st.session_state.df_conflitos_ui = df_editado

        # 🚨 3. A DEVOLUTIVA DE ERROS (Quarentena)
        if linhas_erro > 0:
            with st.expander(f"📥 Ver Itens em Quarentena (Total: {linhas_erro})", expanded=False):
                st.error("Estes itens violaram regras de negócio (sem preço, CST inexistente, NCM corrompido) e foram removidos automaticamente.")
                st.dataframe(df_rejeitados.head(50), use_container_width=True)
                
                excel_devolutiva = exportar_devolutiva_erros(df_rejeitados)
                st.download_button(
                    label="Baixar Planilha de Devolutiva (.XLSX)",
                    data=excel_devolutiva,
                    file_name=f"02_Devolutiva_Erros_{st.session_state.fornecedor_selecionado}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

        st.divider()

        # 🚀 4. BOTÃO DE AVANÇO (O Fluxo Nunca Para!)
        st.success("Tudo pronto! A base limpa já pode ser comparada com os preços atuais do ERP.")
        
        col_voltar, col_avancar = st.columns([1, 2])
        
        with col_voltar:
            if st.button("⬅️ Voltar"):
                for k in ["auditoria_concluida", "df_aprovados", "df_rejeitados", "df_conflitos", "df_conflitos_ui"]:
                    if k in st.session_state: del st.session_state[k]
                st.session_state.etapa_fluxo = 3
                st.rerun()
                
        with col_avancar:
            # O pulo do gato: Junta os 100% válidos com os que o usuário marcou no Purgatório!
            if st.button("Calcular Variações de Preço ➡️", type="primary", use_container_width=True):
                
                df_final_para_etapa_5 = df_aprovados.copy()
                
                # Se tinha conflito, pega só os aprovados pelo usuário e junta na base de forma segura
                if linhas_conflito > 0:
                    salvos_pelo_usuario = st.session_state.df_conflitos_ui[st.session_state.df_conflitos_ui["Aprovar Linha"] == True].copy()
                    if not salvos_pelo_usuario.empty:
                        salvos_pelo_usuario = salvos_pelo_usuario.drop(columns=["Aprovar Linha"])
                        df_final_para_etapa_5 = pd.concat([df_final_para_etapa_5, salvos_pelo_usuario], ignore_index=True)
                
                # Guarda a base purificada final para o Motor de Variação
                st.session_state.df_lista_purificada = df_final_para_etapa_5
                st.session_state.etapa_fluxo = 5
                st.rerun()

    # ETAPA 5: CALCULAR VARIAÇÃO 
    elif st.session_state.etapa_fluxo == 5:
        st.header("📈 Passo 5: Calcular Variação")
        st.write("Em breve: Motor de cálculo e integração de dados.")