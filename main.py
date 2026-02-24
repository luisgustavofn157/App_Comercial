import streamlit as st
import pandas as pd
import traceback
import io
from modulos.orquestrador_importacao import processar_arquivos_upload
from modulos.consolidador import consolidar_dataframes
from modulos.limpador_dados import limpar_e_traduzir_dados
from modulos.config_erp import DICIONARIO_ERP, NOMES_VISUAIS_ERP, CONCEITOS_MULTIPLOS, REVERSO_ERP
from modulos.cerebro.orquestrador import avaliar_coluna
from modulos.cerebro.memoria import registrar_feedback

st.set_page_config(page_title="Hub Comercial - Precificação", page_icon="📊", layout="wide")

# ==========================================
# INJEÇÃO DE CSS
# ==========================================
st.markdown("""
    <style>
    div.stButton > button[kind="primary"] { background-color: #0066cc; border-color: #0066cc; color: white; }
    div.stButton > button[kind="primary"]:hover { background-color: #0052a3; border-color: #0052a3; }
    .etapa-atual { background-color: #e6f2ff; color: #0066cc; padding: 8px; border-radius: 6px; font-weight: bold; margin-bottom: 4px; border-left: 4px solid #0066cc; }
    .etapa-concluida { color: #28a745; padding: 8px; margin-bottom: 4px; }
    .etapa-bloqueada { color: #6c757d; padding: 8px; margin-bottom: 4px; opacity: 0.7; }
    </style>
""", unsafe_allow_html=True)

# Simulação de perfis existentes no banco de dados
PERFIS_EXISTENTES = ["Fornecedor DS", "VIEMAR", "Fornecedor NGK"]

# ==========================================
# GERENCIAMENTO DE ESTADO
# ==========================================
if "pagina_atual" not in st.session_state: st.session_state.pagina_atual = "Fluxo Principal"
if "etapa_fluxo" not in st.session_state: st.session_state.etapa_fluxo = 1
if "tabelas_extraidas" not in st.session_state: st.session_state.tabelas_extraidas = []
if "decisoes_usuario" not in st.session_state: st.session_state.decisoes_usuario = {}
if "fornecedor_selecionado" not in st.session_state: st.session_state.fornecedor_selecionado = "" 

def mudar_pagina(nome): st.session_state.pagina_atual = nome
def resetar_fluxo():
    st.session_state.etapa_fluxo = 1
    st.session_state.tabelas_extraidas = []
    st.session_state.decisoes_usuario = {}
    st.session_state.fornecedor_selecionado = ""
    if "df_bruto_consolidado" in st.session_state: del st.session_state.df_bruto_consolidado
    st.session_state.pagina_atual = "Fluxo Principal"

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
        st.write("") 
        if st.button("🛑 Cancelar e Recomeçar", use_container_width=True):
            resetar_fluxo()
            st.rerun()

    st.divider()
    st.markdown("#### 🛠️ Ferramentas Globais")
    if st.button("📑 Perfis de Fornecedores", use_container_width=True): mudar_pagina("Perfis")
    if st.button("📋 Logs de Execução", use_container_width=True): mudar_pagina("Logs")

# ==========================================
# ROTEADOR DE PÁGINAS PRINCIPAL
# ==========================================
pagina = st.session_state.pagina_atual

if pagina == "Fluxo Principal":
    
    # ------------------------------------------
    # ETAPA 1: IMPORTAÇÃO E CONTEXTO
    # ------------------------------------------
    if st.session_state.etapa_fluxo == 1:
        st.header("📂 Passo 1: Contexto e Importação")
        
        col_perfil, col_arq = st.columns([1, 2])
        
        with col_perfil:
            st.markdown("### 1️⃣ Defina o Perfil")
            st.write("A IA usará a memória deste fornecedor.")
            
            opcoes_perfil = ["Selecione..."] + PERFIS_EXISTENTES + ["GERAL (Sem Perfil)", "➕ Criar Novo Perfil..."]
            perfil_escolhido = st.selectbox("Fornecedor:", opcoes_perfil)
            
            nome_novo_perfil = ""
            if perfil_escolhido == "➕ Criar Novo Perfil...":
                nome_novo_perfil = st.text_input("Digite o nome do novo fornecedor:")
        
        with col_arq:
            st.markdown("### 2️⃣ Envie as Listas")
            st.write("Formatos aceitos: Excel ou CSV.")
            arquivos = st.file_uploader("Selecione os arquivos", type=['csv', 'xlsx', 'xlsb', 'xls'], accept_multiple_files=True, label_visibility="collapsed")
        
        st.divider()
        
        # --- Lógica de Validação do Botão ---
        pode_avancar = False
        fornecedor_final = ""
        
        if arquivos:
            if perfil_escolhido not in ["Selecione...", "➕ Criar Novo Perfil..."]:
                pode_avancar = True
                fornecedor_final = perfil_escolhido
            elif perfil_escolhido == "➕ Criar Novo Perfil..." and len(nome_novo_perfil.strip()) > 0:
                pode_avancar = True
                fornecedor_final = nome_novo_perfil.strip()
        
        col_vazio, col_btn = st.columns([7, 3])
        with col_btn:
            if pode_avancar:
                if st.button("Analisar Arquivos ➡️", type="primary", use_container_width=True):
                    st.session_state.fornecedor_selecionado = fornecedor_final
                    
                    with st.spinner("A IA está escaneando os arquivos e carregando as memórias..."):
                        tabelas, erros = processar_arquivos_upload(arquivos)
                        if erros:
                            for erro in erros:
                                st.error(f"🚨 Falha crítica no arquivo: {erro['arquivo']}")
                                with st.expander("Ver Raio-X do erro técnico"): st.code(erro['traceback'])
                            st.stop()
                        
                        st.session_state.tabelas_extraidas = tabelas
                        st.session_state.decisoes_usuario = {} 
                        st.session_state.etapa_fluxo = 2
                        st.rerun()
            else:
                st.button("Analisar Arquivos ➡️", disabled=True, use_container_width=True)
                if arquivos and not pode_avancar:
                    st.warning("Selecione ou crie um perfil para habilitar a análise.")

    # ------------------------------------------
    # ETAPA 2: AUDITORIA DAS EXTRAÇÕES
    # ------------------------------------------
    elif st.session_state.etapa_fluxo == 2:
        st.header("👁️ Passo 2: Auditar Inteligência do Sistema")
        if len(st.session_state.tabelas_extraidas) == 0:
            st.warning("Nenhuma tabela comercial foi encontrada.")
            if st.button("⬅️ Voltar e Tentar Novamente"):
                st.session_state.etapa_fluxo = 1
                st.rerun()
        else:
            st.success(f"O sistema encontrou {len(st.session_state.tabelas_extraidas)} tabela(s) potencial(is).")
            for tbl in st.session_state.tabelas_extraidas:
                id_unico = tbl['id_unico']
                with st.container(border=True):
                    col_tabela, col_acao = st.columns([3, 1])
                    with col_tabela:
                        st.markdown(f"📄 **Arquivo:** `{tbl['arquivo']}` &nbsp;|&nbsp; 📑 **Aba:** `{tbl['aba']}`")
                        st.caption(f"🤖 **Motivo:** {tbl['motivo_escolha']}")
                        st.dataframe(tbl['dados'].head(5), use_container_width=True)
                    with col_acao:
                        opcoes_acao = ["❓ Pendente", "✅ Consolidar", "ℹ️ Info Técnica", "🗑️ Lixo/Ignorar"]
                        sugestao_ia = tbl.get('sugestao_acao', "❓ Pendente")
                        if "Lista Preço" in sugestao_ia: sugestao_ia = "✅ Consolidar"
                        elif "Tabela Técnica" in sugestao_ia: sugestao_ia = "ℹ️ Info Técnica"
                        
                        decisao = st.radio("Ação Sugerida:", options=opcoes_acao, index=opcoes_acao.index(sugestao_ia) if sugestao_ia in opcoes_acao else 0, key=f"radio_{id_unico}", label_visibility="collapsed")
                        st.session_state.decisoes_usuario[id_unico] = decisao

            st.divider()
            col_voltar, col_vazio, col_avancar = st.columns([2, 5, 3])
            with col_voltar:
                if st.button("⬅️ Voltar ao Início", use_container_width=True):
                    st.session_state.etapa_fluxo = 1
                    st.rerun()
            with col_avancar:
                pendentes = sum(1 for d in st.session_state.decisoes_usuario.values() if d == "❓ Pendente")
                if pendentes > 0: st.error(f"⚠️ Há {pendentes} tabela(s) Pendente(s).")
                else:
                    if st.button("Aprovar e Avançar ➡️", type="primary", use_container_width=True):
                        st.session_state.etapa_fluxo = 3
                        st.rerun()

    # ------------------------------------------
    # ETAPA 3: O GRANDE CALDEIRÃO E O DE/PARA
    # ------------------------------------------
    elif st.session_state.etapa_fluxo == 3:
        st.header("🔀 Passo 3: Base Consolidada e Mapeamento")
        
        tabelas_aprovadas = [t for t in st.session_state.tabelas_extraidas if st.session_state.decisoes_usuario.get(t['id_unico']) == "✅ Consolidar"]
        
        if len(tabelas_aprovadas) == 0:
            st.warning("Nenhuma tabela foi marcada para consolidação.")
            if st.button("⬅️ Voltar para Auditoria"): st.session_state.etapa_fluxo = 2; st.rerun()
        else:
            if "df_bruto_consolidado" not in st.session_state:
                with st.spinner("Normalizando cabeçalhos e fundindo os dados..."):
                    st.session_state.df_bruto_consolidado = consolidar_dataframes(tabelas_aprovadas)
            
            fornecedor_atual = st.session_state.fornecedor_selecionado
            st.markdown(f"### 🤖 Mapeamento Automático - Perfil: **{fornecedor_atual}**")
            st.write("A IA cruzou as colunas extraídas com a memória deste perfil. Revise as sugestões abaixo:")
            
            df = st.session_state.df_bruto_consolidado
            colunas_excel = [c for c in df.columns if not c.startswith("__")] 
            
            mapeamento_usuario = {}
            
            resultados_ia = {}
            for col in colunas_excel:
                # O Orquestrador avalia tudo, mas ainda não desenha na tela
                match, nota, detalhes = avaliar_coluna(
                    col, 
                    NOMES_VISUAIS_ERP, 
                    fornecedor_atual, 
                    df_amostra=df.head(50) 
                )
                resultados_ia[col] = {"match": match, "nota": nota, "detalhes": detalhes}

            # --- FASE 2: O TRIBUNAL (DESEMPATE AUTOMÁTICO) ---
            # Agrupa as colunas pelas sugestões da IA para caçar os conflitos
            sugestoes_por_id = {}
            for col, res in resultados_ia.items():
                match = res["match"]
                if match == DICIONARIO_ERP["IGNORAR"]: continue
                
                id_conceito = REVERSO_ERP.get(match)
                
                # Se o conceito NÃO tem passe livre (é 1:1), nós vigiamos ele
                if id_conceito not in CONCEITOS_MULTIPLOS:
                    if id_conceito not in sugestoes_por_id:
                        sugestoes_por_id[id_conceito] = []
                    sugestoes_por_id[id_conceito].append({"coluna": col, "nota": res["nota"]})
            
            # O Executor de Rebaixamento
            for id_conceito, colunas_sugeridas in sugestoes_por_id.items():
                if len(colunas_sugeridas) > 1:
                    # Ordena do maior pro menor: O que tiver mais nota fica em primeiro [0]
                    ordenados = sorted(colunas_sugeridas, key=lambda x: x["nota"], reverse=True)
                    
                    # Do segundo colocado em diante, sofrem rebaixamento compulsório
                    for perdedor in ordenados[1:]:
                        col_perdedora = perdedor["coluna"]
                        resultados_ia[col_perdedora]["match"] = DICIONARIO_ERP["IGNORAR"]
                        resultados_ia[col_perdedora]["nota"] = 0.0 # Zera a nota pra não confundir

        # --- FASE 3: O GUARDIÃO DA TELA (PREPARAÇÃO) ---
            # Lemos o estado atual dos widgets ANTES de desenhar a tela
            selecoes_atuais = {}
            for col in colunas_excel:
                widget_key = f"map_{col}"
                # Se o usuário já mexeu na caixa, pega a escolha dele. Se não, usa a sugestão limpa da IA.
                if widget_key in st.session_state:
                    selecoes_atuais[col] = st.session_state[widget_key]
                else:
                    selecoes_atuais[col] = resultados_ia[col]["match"]

            # Contamos as aparições dos conceitos estritos (Regra 1:1)
            contagem_estritos = {}
            for col, escolha in selecoes_atuais.items():
                if escolha == DICIONARIO_ERP["IGNORAR"]: continue
                
                id_conceito = REVERSO_ERP.get(escolha)
                if id_conceito not in CONCEITOS_MULTIPLOS:
                    contagem_estritos[escolha] = contagem_estritos.get(escolha, 0) + 1

            tem_conflito_bloqueante = False

            # --- FASE 4: EXIBIÇÃO NA TELA ---
            for col in colunas_excel:
                res = resultados_ia[col]
                maior_nota = res["nota"]
                
                escolha_atual = selecoes_atuais[col]
                id_conceito_atual = REVERSO_ERP.get(escolha_atual)
                
                # Verifica se esta linha específica está quebrando a regra
                linha_em_conflito = False
                if escolha_atual != DICIONARIO_ERP["IGNORAR"] and id_conceito_atual not in CONCEITOS_MULTIPLOS:
                    if contagem_estritos.get(escolha_atual, 0) > 1:
                        linha_em_conflito = True
                        tem_conflito_bloqueante = True
                
                with st.container(border=True):
                    # O Alerta Vermelho In-line
                    if linha_em_conflito:
                        st.error(f"⚠️ **Conflito de Regra:** Apenas uma coluna pode ser mapeada como `{escolha_atual}`. Corrija o conflito.")
                        
                    c1, c2, c3 = st.columns([3, 1, 4])
                    with c1:
                        st.markdown(f"Excel: **`{col}`**")
                        amostra = df[col].dropna().astype(str).head(3).tolist()
                        st.caption(f"Ex: {', '.join(amostra)}..." if amostra else "Ex: (Vazio)")
                    with c2:
                        st.markdown("➡️")
                        if res["match"] != DICIONARIO_ERP["IGNORAR"]:
                            cor = "#28a745" if maior_nota >= 85 else "#fd7e14"
                            st.markdown(
                                f"<span style='color:{cor}; font-size:13px; font-weight:600;'>"
                                f"🎯 {int(maior_nota)}% Match</span>", 
                                unsafe_allow_html=True
                            )
                    with c3:
                        # ATENÇÃO: O index agora obedece à selecao_atual, garantindo que a tela grave a mudança do usuário
                        index_atual = NOMES_VISUAIS_ERP.index(escolha_atual)
                        escolha = st.selectbox("Benner/WMS:", options=NOMES_VISUAIS_ERP, index=index_atual, key=f"map_{col}", label_visibility="collapsed")
                        mapeamento_usuario[col] = escolha
            
            st.divider()
            
            # O Aviso Global no Rodapé
            if tem_conflito_bloqueante:
                st.error("🛑 **Ação Bloqueada:** O sistema detectou regras de negócio violadas (vermelho acima). Você mapeou conceitos únicos em mais de uma coluna. Resolva antes de avançar.")
            
            col_voltar, col_vazio, col_avancar = st.columns([2, 5, 3])
            with col_voltar:
                if st.button("⬅️ Voltar para Auditoria"):
                    if "df_bruto_consolidado" in st.session_state: del st.session_state.df_bruto_consolidado
                    st.session_state.etapa_fluxo = 2
                    st.rerun()

            with col_avancar:
                # O bloqueio físico do botão!
                if st.button("Salvar Perfil e Avançar ➡️", type="primary", use_container_width=True, disabled=tem_conflito_bloqueante):
                    
                    for col_excel, conceito_erp in mapeamento_usuario.items():
                        registrar_feedback(col_excel, conceito_erp, NOMES_VISUAIS_ERP, fornecedor_atual)
                    
                    st.session_state.mapeamento_oficial = mapeamento_usuario
                    
                    st.success("Mapeamento aprendido com sucesso!")
                    st.session_state.etapa_fluxo = 4
                    st.rerun()