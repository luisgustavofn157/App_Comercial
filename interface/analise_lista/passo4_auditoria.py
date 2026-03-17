import streamlit as st
import pandas as pd
from modulos.exportador import gerar_excel_critica
from tratamento_de_dados.silver.motor_silver import executar_motor_silver, aplicar_validacao_erp

def renderizar_passo_4():
    st.header("🕵️ Passo 4: Auditoria e Resolução")
    
    # Segurança para garantir que passamos pelo Passo 3
    if "df_gold" not in st.session_state or "df_remocao_auto" not in st.session_state or "df_com_erros" not in st.session_state:
        st.warning("Os dados da Camada Silver não foram encontrados.")
        from configuracoes.state_manager import resetar_fluxo
        st.button("Voltar ao Início", on_click=resetar_fluxo)
        return

    # Puxa as 3 caixas da memória
    df_gold = st.session_state.df_gold
    df_remocao_auto = st.session_state.df_remocao_auto
    df_com_erros = st.session_state.df_com_erros

    # ==========================================
    # 1. PAINEL DE MÉTRICAS (Simplificado e Limpo)
    # ==========================================
    linhas_ok = len(df_gold)
    linhas_removidas = len(df_remocao_auto)
    linhas_erro = len(df_com_erros)
    total_linhas = linhas_ok + linhas_removidas + linhas_erro
    
    taxa = (linhas_ok / total_linhas) * 100 if total_linhas > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 Linhas Analisadas", total_linhas)
    c2.metric("✅ Validadas 100%", linhas_ok, delta=f"{taxa:.1f}% Retenção", delta_color="normal")
    c3.metric("🚨 Com Erros", linhas_erro, delta="Ação Necessária" if linhas_erro > 0 else "0", delta_color="inverse" if linhas_erro > 0 else "off")
    
    with st.expander(f"🗑️ Ver Registos de Remoção Automática ({linhas_removidas} linhas)"):
        st.write("Estas linhas falharam nos critérios mínimos (Falta de SKU/Preço ou eram cópias 100% exatas). Foram removidas do processo.")
        st.dataframe(df_remocao_auto.head(100), use_container_width=True)

    st.divider()

    # ==========================================
    # 2. A BARREIRA INTRANSPONÍVEL (Hard Gate)
    # ==========================================
    tem_bloqueio = (linhas_erro > 0)
    
    if tem_bloqueio:
        st.error("🛑 **Existem linhas retidas na Quarentena.**")
        st.write("1. Faça o download do ficheiro de crítica abaixo.")
        st.write("2. Na aba **'Com Erros'**, verifique a coluna de ALERTA para saber o que falhou (ex: 'NCM Inválido', 'SKU Duplicado com divergência').")
        st.write("3. Altere o valor diretamente no Excel, guarde e faça o upload do ficheiro aqui para revalidar.")
        
        # --- MÁSCARA DE EXPORTAÇÃO (Veste o nome Original do fornecedor) ---
        mapa_reverso = st.session_state.get("mapa_tecnico_para_original", {})
        df_gold_export = df_gold.rename(columns=mapa_reverso)
        df_remocao_export = df_remocao_auto.rename(columns=mapa_reverso)
        df_erros_export = df_com_erros.rename(columns=mapa_reverso)
        
        # Gera o Excel
        excel_bytes = gerar_excel_critica(df_gold_export, df_remocao_export, df_erros_export)
        
        perfil = st.session_state.get("perfil_selecionado", "Geral")
        st.download_button(
            label="📥 1. Baixar Ficheiro de Crítica (.XLSX)",
            data=excel_bytes,
            file_name=f"Critica_Erros_{perfil}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
        
        st.markdown("---")
        st.subheader("📤 2. Enviar Ficheiro Corrigido")
        arquivo_corrigido = st.file_uploader("Suba o Excel corrigido aqui para reavaliar as regras", type=["xlsx"])
        
        if arquivo_corrigido:
            with st.spinner("Lendo ficheiro e aplicando Máquina de Regras novamente..."):
                dict_abas = pd.read_excel(arquivo_corrigido, sheet_name=None)
                
                dfs_para_juntar = []
                for nome_aba, df_aba in dict_abas.items():
                    if not df_aba.empty:
                        dfs_para_juntar.append(df_aba)
                        
                df_reconstruido = pd.concat(dfs_para_juntar, ignore_index=True) if dfs_para_juntar else pd.DataFrame()
                
                # --- MÁSCARA DE IMPORTAÇÃO (Tira a máscara, volta para o TÉCNICO) ---
                mapa_direto = st.session_state.get("mapa_original_para_tecnico", {})
                df_reconstruido = df_reconstruido.rename(columns=mapa_direto)
                
                # Remove o lixo de auditoria para o sistema fazer uma análise limpa
                colunas_auditoria = ["MOTIVO_REJEICAO", "ALERTAS_SISTEMA"]
                df_reconstruido = df_reconstruido.drop(columns=[c for c in colunas_auditoria if c in df_reconstruido.columns])
                
                # O Cérebro: Passa a lista reconstruída pelas esteiras do motor novamente
                novo_df_gold, novo_df_remocao, novo_df_erros = executar_motor_silver(df_reconstruido)
                
                st.session_state.df_gold = novo_df_gold
                st.session_state.df_remocao_auto = novo_df_remocao
                st.session_state.df_com_erros = novo_df_erros
                st.rerun()
                
        st.divider()
        if st.button("⬅️ Voltar ao Mapeamento (Descartar tudo e recomeçar)", type="secondary"):
            for k in ["df_gold", "df_remocao_auto", "df_com_erros"]:
                if k in st.session_state: del st.session_state[k]
            st.session_state.etapa_fluxo = 3
            st.rerun()

    else:
        # ==========================================
        # 3. CAMINHO FELIZ (Consultar ERP)
        # ==========================================
        st.success("🎉 **BASE ÍNTEGRA! As regras de negócio foram atendidas a 100%.**")
        st.write("O sistema cruzou os dados validados com a base de dados do Benner:")
        
        if "df_gold_validado" not in st.session_state:
            with st.spinner("A consultar o ERP para validar SKUs e NCMs..."):
                df_final_cruzado = aplicar_validacao_erp(df_gold)
                st.session_state.df_gold_validado = df_final_cruzado
                
        st.dataframe(st.session_state.df_gold_validado.head(10), use_container_width=True)
        
        st.divider()
        if st.button("Avançar para Cálculo de Variações ➡️", type="primary", use_container_width=True):
            st.session_state.df_lista_purificada = st.session_state.df_gold_validado
            st.session_state.etapa_fluxo = 5
            st.rerun()