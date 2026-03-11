import streamlit as st
import pandas as pd
from modulos.consolidador import consolidar_dataframes
from configuracoes.config_erp import DICIONARIO_ERP, NOMES_VISUAIS_ERP, CONCEITOS_MULTIPLOS, REVERSO_ERP
from modulos.classificador.pipeline import classificar_dataset_completo, avaliar_coluna_fase1
from modulos.classificador.aprendizado import registrar_feedback
from modulos.validador_comercial import aplicar_filtro_morte, higienizar_dados
from modulos.exportador import exportar_lista_limpa

# Ajuste as variáveis de debug conforme sua necessidade
DEBUG_USAR_MEMORIA = True
DEBUG_USAR_ARBITRO = True

def renderizar_passo_3():
    st.header("🔀 Passo 3: Mapear Colunas")
    
    aprovadas = [t for t in st.session_state.tabelas_extraidas if st.session_state.decisoes_usuario.get(t['id_unico']) == "✅ Consolidar"]
    
    if not aprovadas:
        st.warning("Nada selecionado.")
        # Como resetar_fluxo deve estar no seu state_manager, você pode importá-lo aqui se precisar do botão de voltar
        from utils.state_manager import resetar_fluxo
        st.button("Voltar", on_click=resetar_fluxo)
        return

    if "df_bruto_consolidado" not in st.session_state:
        st.session_state.df_bruto_consolidado = consolidar_dataframes(aprovadas)
    
    df_completo = st.session_state.df_bruto_consolidado
    colunas_reais = [c for c in df_completo.columns if not str(c).startswith("__")]
    
    if "df_mapeamento_ui" not in st.session_state:
        resultados_ia = classificar_dataset_completo(
            df_completo,  
            NOMES_VISUAIS_ERP, 
            st.session_state.perfil_selecionado,
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
                "Tipo de Dado": match,
                "Amostra dos Dados": " | ".join(amostra) if amostra else "(Vazia)"
            })
        st.session_state.df_mapeamento_ui = pd.DataFrame(dados_ui)

    st.markdown(f"#### ⚙️ Perfil Selecionado: `{st.session_state.perfil_selecionado}`")
    st.write("O sistema já identificou algumas colunas, revise e corrija se necessário")

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
            "Tipo de Dado": st.column_config.SelectboxColumn("Tipo de Dado", options=NOMES_VISUAIS_ERP, required=True, width="medium"),
            "Amostra dos Dados": st.column_config.TextColumn("Amostra (3 linhas)")
        },
        key="editor_mapeamento"
    )

    houve_alteracao_dropdown = False
    for i in range(len(df_editado)):
        col_excel = df_editado.at[i, "Coluna Original"]
        novo_mapeamento = df_editado.at[i, "Tipo de Dado"]
        mapeamento_antigo = st.session_state.df_mapeamento_ui.at[i, "Tipo de Dado"]

        if novo_mapeamento != mapeamento_antigo:
            if novo_mapeamento == DICIONARIO_ERP["IGNORAR"]:
                nova_nota_final = None
            else:
                boletim = avaliar_coluna_fase1(col_excel, [novo_mapeamento], st.session_state.perfil_selecionado, df_completo)
                nova_nota_final = boletim[0]["nota"] if boletim else None
            
            df_editado.at[i, "Confiança"] = nova_nota_final
            houve_alteracao_dropdown = True

    st.session_state.df_mapeamento_ui = df_editado.copy()
    if houve_alteracao_dropdown: st.rerun()

    mapeamento_atualizado = dict(zip(df_editado["Coluna Original"], df_editado["Tipo de Dado"]))
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
                            registrar_feedback(col_sec, DICIONARIO_ERP[d], st.session_state.perfil_selecionado)
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
                registrar_feedback(col_excel, conceito, st.session_state.perfil_selecionado)
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