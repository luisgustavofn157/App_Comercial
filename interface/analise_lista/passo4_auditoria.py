import streamlit as st
import pandas as pd
from modulos.novo_validador_comercial import processar_validacoes
from modulos.exportador import exportar_devolutiva_erros

def renderizar_passo_4():
    st.header("🕵️ Passo 4: Auditoria e Validação Comercial")
    st.write("O Motor de Inteligência aplicou as regras de negócio.")
    
    if "df_aprovados" not in st.session_state:
        df_ap, df_rej, df_conf = processar_validacoes(st.session_state.df_limpo, st.session_state.mapeamento_oficial)
        st.session_state.df_aprovados = df_ap
        st.session_state.df_rejeitados = df_rej
        st.session_state.df_conflitos = df_conf
        
        df_conf_ui = df_conf.copy()
        if not df_conf_ui.empty:
            df_conf_ui.insert(0, "Aprovar Linha", False)
        st.session_state.df_conflitos_ui = df_conf_ui
        st.session_state.auditoria_concluida = True

    df_aprovados = st.session_state.df_aprovados
    df_rejeitados = st.session_state.df_rejeitados
    df_conflitos = st.session_state.df_conflitos

    # 📊 1. PAINEL DE MÉTRICAS
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

    # ⚖️ 2. O PURGATÓRIO
    if linhas_conflito > 0:
        st.warning("⚠️ **ATENÇÃO: Informações Conflitantes!** O fornecedor enviou o mesmo código de produto mais de uma vez com dados diferentes.")
        st.write("Decida abaixo qual linha é a verdadeira marcando a caixa **'Aprovar Linha'**. As que sobrarem serão rejeitadas.")
        
        df_editado = st.data_editor(
            st.session_state.df_conflitos_ui,
            column_config={"Aprovar Linha": st.column_config.CheckboxColumn("✅ Aprovar", default=False)},
            disabled=list(df_conflitos.columns), 
            hide_index=True,
            use_container_width=True
        )
        st.session_state.df_conflitos_ui = df_editado

    # 🚨 3. A DEVOLUTIVA DE ERROS
    if linhas_erro > 0:
        with st.expander(f"📥 Ver Itens em Quarentena (Total: {linhas_erro})", expanded=False):
            st.error("Estes itens violaram regras de negócio e foram removidos.")
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

    # 🚀 4. BOTÕES DE NAVEGAÇÃO
    st.success("Tudo pronto! A base limpa já pode ser comparada com os preços atuais do ERP.")
    
    col_voltar, col_avancar = st.columns([1, 2])
    
    with col_voltar:
        if st.button("⬅️ Voltar"):
            for k in ["auditoria_concluida", "df_aprovados", "df_rejeitados", "df_conflitos", "df_conflitos_ui"]:
                if k in st.session_state: del st.session_state[k]
            st.session_state.etapa_fluxo = 3
            st.rerun()
            
    with col_avancar:
        if st.button("Calcular Variações de Preço ➡️", type="primary", use_container_width=True):
            df_final_para_etapa_5 = df_aprovados.copy()
            
            if linhas_conflito > 0:
                salvos_pelo_usuario = st.session_state.df_conflitos_ui[st.session_state.df_conflitos_ui["Aprovar Linha"] == True].copy()
                if not salvos_pelo_usuario.empty:
                    salvos_pelo_usuario = salvos_pelo_usuario.drop(columns=["Aprovar Linha"])
                    df_final_para_etapa_5 = pd.concat([df_final_para_etapa_5, salvos_pelo_usuario], ignore_index=True)
            
            st.session_state.df_lista_purificada = df_final_para_etapa_5
            st.session_state.etapa_fluxo = 5
            st.rerun()