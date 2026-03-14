import streamlit as st
import time
from sqlalchemy.exc import OperationalError, ProgrammingError

# IMPORTAÇÕES DA ARQUITETURA
from configuracoes.state_manager import inicializar_estado, resetar_banco_dados
from banco_de_dados.conexao_benner import executar_consulta_benner
from banco_de_dados.tratamento_sql import higienizar_para_exportacao
from banco_de_dados.repositorio_sql import MENU_CONSULTAS_RAPIDAS
from modulos.exportador import exportar_consulta_sql

# Garante que as variáveis existam
inicializar_estado()

# ==========================================
# CALLBACKS DE TELA
# ==========================================
def callback_combo_prontas():
    escolha = st.session_state.db_combo_biblioteca
    if escolha == "Selecione uma consulta pronta...":
        resetar_banco_dados()
    else:
        # Puxa o SQL diretamente do novo dicionário limpo
        st.session_state.db_query_input = MENU_CONSULTAS_RAPIDAS[escolha]
        st.session_state.db_executar_agora = True

# ==========================================
# UI - CABEÇALHO
# ==========================================
st.title("🗄️ Consultas ao Banco de Dados do Benner")

st.selectbox(
    "Consultas Rápidas:", 
    # É aqui que o texto da interface deve morar, e não no repositório!
    options=["Selecione uma consulta pronta..."] + list(MENU_CONSULTAS_RAPIDAS.keys()), 
    key="db_combo_biblioteca",
    on_change=callback_combo_prontas
)

query_usuario = st.text_area(
    "Comando SQL:", 
    key="db_query_input", 
    height=200, 
    placeholder="SELECT TOP 100 * FROM NOME_DA_TABELA"
)

# ==========================================
# UI - BARRA DE FERRAMENTAS
# ==========================================
col1, col2, col3, col4 = st.columns(4)

btn_executar = col1.button("▶️ Executar Consulta", use_container_width=True)

vai_executar = btn_executar or st.session_state.db_executar_agora
label_btn_limpar = "🛑 Cancelar Consulta" if vai_executar else "🧹 Limpar Tela"
col2.button(label_btn_limpar, on_click=resetar_banco_dados, use_container_width=True)

if "db_resultado_sql" in st.session_state:
    df_bruto = st.session_state.db_resultado_sql
    
    # Adia a geração de bytes até o usuário querer baixar
    with col3.popover("📄 Exportar", use_container_width=True):
        st.caption("Gerar arquivo Excel?")
        if st.button("Sim, processar e baixar .XLSX", key="btn_gerar_excel", use_container_width=True):
            with st.spinner("Gerando arquivo..."):
                df_seguro = higienizar_para_exportacao(df_bruto)
                bytes_excel = exportar_consulta_sql(df_seguro)
                st.download_button(
                    label="⬇️ Clique aqui para baixar", 
                    data=bytes_excel, 
                    file_name="extracao.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                    use_container_width=True
                )
    
    # Cópia para Clipboard
    if len(df_bruto) <= 5000:
        with col4.popover("📋 Copiar Dados", use_container_width=True):
            st.caption("Clique no ícone 📋 no canto da caixa abaixo:")
            df_copia = higienizar_para_exportacao(df_bruto) # Limpa só para cópia
            st.code(df_copia.to_csv(index=False, sep='\t'), language="text")
    else:
        col4.button("🚫 Cópia Bloqueada", disabled=True, use_container_width=True, help="Limite excedido (> 5000 linhas). Baixe o arquivo XLSX.")

# ==========================================
# MOTOR DE EXECUÇÃO
# ==========================================
if vai_executar:
    st.session_state.db_executar_agora = False 
    query = st.session_state.db_query_input.strip()
    
    if not query:
        st.warning("Digite uma query válida.")
    else:
        with st.spinner("Consultando o banco do Benner..."):
            try:
                start_time = time.time()
                df_resultado = executar_consulta_benner(query)
                end_time = time.time()
                
                # Salva apenas o resultado bruto. Tratamento ocorre na hora de exportar/copiar.
                st.session_state.db_resultado_sql = df_resultado
                st.session_state.db_tempo_execucao = end_time - start_time
                st.rerun() # Único rerun necessário e de forma controlada
                
            except ValueError as ve:
                st.error("🛡️ Ação não permitida")
                st.warning(str(ve))
            except ProgrammingError as pe:
                st.error("❌ Erro de Sintaxe SQL")
                st.warning("Verifique o comando digitado.")
                with st.expander("Ver Detalhes Técnicos"): st.code(str(pe))
            except OperationalError as oe:
                st.error("🔌 Falha de Conexão com o Servidor")
                with st.expander("Ver Detalhes Técnicos"): st.code(str(oe))
            except Exception as e:
                st.error("🚨 Erro Inesperado na Execução")
                with st.expander("Ver Detalhes Técnicos"): st.code(str(e))

# ==========================================
# UI - VISUALIZAÇÃO NA TELA
# ==========================================
elif "db_resultado_sql" in st.session_state:
    df = st.session_state.db_resultado_sql
    tempo_segundos = st.session_state.get("db_tempo_execucao", 0.0)
    
    if len(df) > 10:
        st.info("Exibindo apenas as 10 primeiras linhas na tela por performance. Use os botões acima para exportar a extração completa.")
        
    st.caption(f"🔍 Pré-visualização dos Dados (Retornou **{len(df)} linhas** em **{tempo_segundos:.2f} segundos**)")
    st.dataframe(df.head(10), use_container_width=True)