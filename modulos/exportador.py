import pandas as pd
import io
from openpyxl.styles import PatternFill, Font, Border, Side

# A cor escolhida em formato Hexadecimal (RGB: 31, 73, 125)
COR_PRIMARIA_HEX = "1F497D"

def aplicar_estilo_ancora(worksheet, df):
    """
    Varre a aba do Excel recém-criada e aplica a identidade visual:
    - Cabeçalho: Fundo Azul Escuro, Fonte Branca em Negrito.
    - Linhas de Dados: Bordas finas na mesma cor do cabeçalho.
    """
    # 1. Definição dos Estilos (A paleta de pintura)
    estilo_fundo_cabecalho = PatternFill(start_color=COR_PRIMARIA_HEX, end_color=COR_PRIMARIA_HEX, fill_type="solid")
    estilo_fonte_cabecalho = Font(bold=True, color="FFFFFF") # Branco para dar contraste no azul escuro
    
    linha_borda = Side(border_style="thin", color=COR_PRIMARIA_HEX)
    estilo_borda_celula = Border(left=linha_borda, right=linha_borda, top=linha_borda, bottom=linha_borda)
    
    # 2. Identifica o tamanho da tabela
    max_row = df.shape[0] + 1 # +1 por causa da linha do cabeçalho
    max_col = df.shape[1]
    
    # 3. Aplica os estilos célula por célula
    for r in range(1, max_row + 1):
        for c in range(1, max_col + 1):
            cell = worksheet.cell(row=r, column=c)
            
            # Aplica a borda colorida em TODAS as células
            cell.border = estilo_borda_celula
            
            # Se for a primeira linha (Cabeçalho), pinta o fundo e a letra
            if r == 1:
                cell.fill = estilo_fundo_cabecalho
                cell.font = estilo_fonte_cabecalho

def exportar_excel_simples(df_dados):
    """Gera um arquivo Excel nativo (.xlsx) de uma única aba com estilo."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        nome_aba = 'Devolutiva_Erros'
        df_dados.to_excel(writer, sheet_name=nome_aba, index=False)
        
        # Aplica o banho de loja na aba criada
        worksheet = writer.sheets[nome_aba]
        aplicar_estilo_ancora(worksheet, df_dados)
        
    return output.getvalue()

def exportar_excel_com_abas(df_principal, df_excluidos):
    """Gera um arquivo Excel nativo (.xlsx) com múltiplas abas e estilo."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        
        # Aba 1: Lista Consolidada
        df_principal.to_excel(writer, sheet_name='Lista_Consolidada', index=False)
        worksheet1 = writer.sheets['Lista_Consolidada']
        aplicar_estilo_ancora(worksheet1, df_principal)
        
        # Aba 2: Lixo / Excluídos
        if not df_excluidos.empty:
            df_excluidos.to_excel(writer, sheet_name='Excluidos_Automaticamente', index=False)
            worksheet2 = writer.sheets['Excluidos_Automaticamente']
            aplicar_estilo_ancora(worksheet2, df_excluidos)
        else:
            # Planilha vazia de registro
            df_vazio = pd.DataFrame([{"Mensagem": "Nenhuma linha precisou ser excluída automaticamente."}])
            df_vazio.to_excel(writer, sheet_name='Excluidos_Automaticamente', index=False)
            worksheet2 = writer.sheets['Excluidos_Automaticamente']
            aplicar_estilo_ancora(worksheet2, df_vazio)
            
    return output.getvalue()