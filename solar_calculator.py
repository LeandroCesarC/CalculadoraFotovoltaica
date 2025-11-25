import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(
    page_title="Calculadora de Painéis Solares",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Função para calcular o dimensionamento
def calcular_dimensionamento(consumo_mensal, potencia_modulo, irradiacao_solar, 
                           perda_temperatura=0.85, perda_sombreamento=0.95, 
                           perda_conversao=0.92, eficiencia_inversor=0.96):
    """
    Calcula o dimensionamento do sistema fotovoltaico
    
    Parâmetros:
    - consumo_mensal: lista com consumo de cada mês (kWh)
    - potencia_modulo: potência do módulo em Wp
    - irradiacao_solar: valor único de irradiação solar (kWh/m²) - será usado para todos os meses
    - perda_temperatura: fator de perda por temperatura (padrão 0.85)
    - perda_sombreamento: fator de perda por sombreamento (padrão 0.95)
    - perda_conversao: fator de perda por conversão (padrão 0.92)
    - eficiencia_inversor: eficiência do inversor (padrão 0.96)
    """
    # Criar lista de irradiação mensal com o mesmo valor para todos os meses
    irradiacao_mensal = [irradiacao_solar] * 12
    
    # Consumo médio diário
    consumo_medio_diario = np.mean(consumo_mensal) / 30
    
    # Consumo médio mensal (demanda média dos 12 meses)
    consumo_medio_mensal = np.mean(consumo_mensal)
    
    # Fator de desempenho do sistema
    fator_desempenho = perda_temperatura * perda_sombreamento * perda_conversao * eficiencia_inversor
    
    # Cálculo do número de módulos necessários para atender a demanda média dos 12 meses
    # Geração diária por módulo (kWh/dia) - usando o valor único de irradiação
    geracao_diaria_modulo = (potencia_modulo / 1000) * irradiacao_solar * fator_desempenho
    
    # Geração mensal por módulo (kWh/mês)
    geracao_mensal_modulo = geracao_diaria_modulo * 30
    
    # Número de módulos necessários para atender a demanda média mensal
    numero_modulos_final = int(np.ceil(consumo_medio_mensal / geracao_mensal_modulo))
    
    # Potência total do sistema
    potencia_total = numero_modulos_final * potencia_modulo
    
    # Dimensionamento do inversor (80-90% da potência do sistema)
    potencia_inversor = potencia_total * 0.85
    
    # Calcular geração mensal com número final de módulos (usando o mesmo valor de irradiação para todos os meses)
    geracao_final = []
    for _ in range(12):
        geracao_diaria_modulo = (potencia_modulo / 1000) * irradiacao_solar * fator_desempenho
        geracao_mensal_final = geracao_diaria_modulo * numero_modulos_final * 30
        geracao_final.append(geracao_mensal_final)
    
    return {
        'numero_modulos': numero_modulos_final,
        'potencia_total': potencia_total,
        'potencia_inversor': potencia_inversor,
        'consumo_medio_diario': consumo_medio_diario,
        'geracao_mensal': geracao_final,
        'fator_desempenho': fator_desempenho
    }

# Função para calcular payback
def calcular_payback(geracao_mensal, consumo_mensal, tarifa_energia, investimento_total, taxa_desconto=0.0):
    """
    Calcula o tempo de retorno do investimento (payback)
    
    Parâmetros:
    - geracao_mensal: lista com geração de cada mês (kWh)
    - consumo_mensal: lista com consumo de cada mês (kWh)
    - tarifa_energia: tarifa de energia em R$/kWh
    - investimento_total: investimento total do sistema em R$
    - taxa_desconto: taxa de desconto anual (opcional, padrão 0.0)
    
    Retorna:
    - payback_simples: tempo de retorno simples em anos
    - economia_anual: economia anual em R$
    - economia_mensal_media: economia mensal média em R$
    - payback_descontado: tempo de retorno descontado em anos (se taxa_desconto > 0)
    """
    # Calcular economia mensal (energia gerada que não precisa comprar da rede)
    economia_mensal = []
    for geracao, consumo in zip(geracao_mensal, consumo_mensal):
        # Economia é a menor entre geração e consumo (não economiza no excedente)
        energia_economizada = min(geracao, consumo)
        economia_mensal.append(energia_economizada * tarifa_energia)
    
    economia_mensal_media = np.mean(economia_mensal)
    economia_anual = sum(economia_mensal)
    
    # Payback simples: investimento / economia anual
    if economia_anual > 0:
        payback_simples = investimento_total / economia_anual
    else:
        payback_simples = float('inf')
    
    # Payback descontado (considerando taxa de desconto)
    payback_descontado = None
    if taxa_desconto > 0 and economia_anual > 0:
        taxa_mensal = taxa_desconto / 12
        valor_presente_acumulado = 0
        meses = 0
        while valor_presente_acumulado < investimento_total and meses < 50 * 12:  # Limite de 50 anos
            meses += 1
            economia_mes = economia_mensal[(meses - 1) % 12]  # Repetir padrão anual
            valor_presente = economia_mes / ((1 + taxa_mensal) ** meses)
            valor_presente_acumulado += valor_presente
        payback_descontado = meses / 12 if meses < 50 * 12 else None
    
    return {
        'payback_simples': payback_simples,
        'economia_anual': economia_anual,
        'economia_mensal_media': economia_mensal_media,
        'economia_mensal': economia_mensal,
        'payback_descontado': payback_descontado
    }

# Função para criar gráficos
def criar_graficos(consumo_mensal, geracao_mensal, meses):
    """Cria gráficos comparativos entre consumo e geração"""
    
    # Gráfico de linha comparativo
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=meses, y=consumo_mensal,
        mode='lines+markers',
        name='Consumo (kWh)',
        line=dict(color='red', width=3),
        marker=dict(size=8)
    ))
    
    fig.add_trace(go.Scatter(
        x=meses, y=geracao_mensal,
        mode='lines+markers',
        name='Geração (kWh)',
        line=dict(color='blue', width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title='Comparação entre Consumo e Geração Mensal',
        xaxis_title='Mês',
        yaxis_title='Energia (kWh)',
        hovermode='x unified',
        template='plotly_white'
    )
    
    return fig

def criar_grafico_barras(consumo_mensal, geracao_mensal, meses):
    """Cria gráfico de barras comparativo"""
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Consumo',
        x=meses,
        y=consumo_mensal,
        marker_color='red',
        opacity=0.7
    ))
    
    fig.add_trace(go.Bar(
        name='Geração',
        x=meses,
        y=geracao_mensal,
        marker_color='blue',
        opacity=0.7
    ))
    
    fig.update_layout(
        title='Comparação Consumo vs Geração por Mês',
        xaxis_title='Mês',
        yaxis_title='Energia (kWh)',
        barmode='group',
        template='plotly_white'
    )
    
    return fig

def criar_grafico_excedente(consumo_mensal, geracao_mensal, meses):
    """Cria gráfico específico de excedente e déficit de energia"""
    
    saldo = np.array(geracao_mensal) - np.array(consumo_mensal)
    excedente = np.where(saldo > 0, saldo, 0)
    deficit = np.where(saldo < 0, saldo, 0)
    
    fig = go.Figure()
    
    # Barras de excedente (verde)
    fig.add_trace(go.Bar(
        name='Excedente (kWh)',
        x=meses,
        y=excedente,
        marker_color='green',
        opacity=0.7,
        text=[f'+{val:.1f}' if val > 0 else '' for val in excedente],
        textposition='outside'
    ))
    
    # Barras de déficit (vermelho)
    fig.add_trace(go.Bar(
        name='Déficit (kWh)',
        x=meses,
        y=deficit,
        marker_color='red',
        opacity=0.7,
        text=[f'{val:.1f}' if val < 0 else '' for val in deficit],
        textposition='outside'
    ))
    
    # Linha zero
    fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
    
    fig.update_layout(
        title='Excedente e Déficit de Energia por Mês',
        xaxis_title='Mês',
        yaxis_title='Saldo de Energia (kWh)',
        barmode='overlay',
        template='plotly_white',
        hovermode='x unified'
    )
    
    return fig

# Função para gerar PDF
def gerar_pdf(consumo_mensal, resultado, meses, potencia_modulo, irradiacao_solar,
               resultado_payback=None, investimento_total=0, tarifa_energia=0):
    """
    Gera um relatório em PDF com os resultados do dimensionamento
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, 
                           topMargin=30, bottomMargin=18)
    story = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Título
    story.append(Paragraph("Relatório de Dimensionamento do Sistema Fotovoltaico", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Dados de entrada
    story.append(Paragraph("Dados de Entrada", heading_style))
    dados_entrada = [
        ['Parâmetro', 'Valor'],
        ['Potência do Módulo', f'{potencia_modulo} Wp'],
        ['Irradiação Solar', f'{irradiacao_solar} kWh/m²'],
        ['Consumo Médio Mensal', f'{np.mean(consumo_mensal):.1f} kWh'],
        ['Consumo Total Anual', f'{sum(consumo_mensal):.1f} kWh']
    ]
    t = Table(dados_entrada, colWidths=[3*inch, 2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3*inch))
    
    # Resultados principais
    story.append(Paragraph("Resultados do Dimensionamento", heading_style))
    resultados_principais = [
        ['Métrica', 'Valor'],
        ['Número de Módulos', f"{resultado['numero_modulos']}"],
        ['Potência Total', f"{resultado['potencia_total']:.0f} Wp"],
        ['Potência do Inversor', f"{resultado['potencia_inversor']:.0f} W"],
        ['Consumo Médio Diário', f"{resultado['consumo_medio_diario']:.1f} kWh/dia"],
        ['Fator de Desempenho', f"{resultado['fator_desempenho']:.3f}"]
    ]
    t = Table(resultados_principais, colWidths=[3*inch, 2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3*inch))
    
    # Tabela mensal
    story.append(Paragraph("Análise Mensal", heading_style))
    dados_mensais = [['Mês', 'Consumo (kWh)', 'Geração (kWh)', 'Saldo (kWh)', 'Cobertura (%)']]
    for i, mes in enumerate(meses):
        consumo = consumo_mensal[i]
        geracao = resultado['geracao_mensal'][i]
        saldo = geracao - consumo
        cobertura = (geracao / consumo * 100) if consumo > 0 else 0
        dados_mensais.append([
            mes,
            f'{consumo:.1f}',
            f'{geracao:.1f}',
            f'{saldo:.1f}',
            f'{cobertura:.1f}'
        ])
    
    t = Table(dados_mensais, colWidths=[0.8*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3*inch))
    
    # Resumo anual
    story.append(Paragraph("Resumo Anual", heading_style))
    resumo_anual = [
        ['Indicador', 'Valor'],
        ['Consumo Total', f'{sum(consumo_mensal):.1f} kWh/ano'],
        ['Geração Total', f'{sum(resultado["geracao_mensal"]):.1f} kWh/ano'],
        ['Saldo Anual', f'{sum(resultado["geracao_mensal"]) - sum(consumo_mensal):.1f} kWh'],
        ['Cobertura Média', f'{np.mean([(g/c*100) if c > 0 else 0 for g, c in zip(resultado["geracao_mensal"], consumo_mensal)]):.1f}%']
    ]
    t = Table(resumo_anual, colWidths=[3*inch, 2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    
    # Análise de Payback (se disponível)
    if resultado_payback and investimento_total > 0:
        story.append(PageBreak())
        story.append(Paragraph("Análise de Retorno do Investimento", heading_style))
        
        payback_dados = [
            ['Parâmetro', 'Valor'],
            ['Investimento Total', f'R$ {investimento_total:,.2f}'],
            ['Tarifa de Energia', f'R$ {tarifa_energia:.4f}/kWh'],
            ['Economia Anual', f'R$ {resultado_payback["economia_anual"]:,.2f}'],
            ['Economia Mensal Média', f'R$ {resultado_payback["economia_mensal_media"]:,.2f}']
        ]
        
        if resultado_payback['payback_simples'] != float('inf'):
            anos = int(resultado_payback['payback_simples'])
            meses_pb = int((resultado_payback['payback_simples'] - anos) * 12)
            payback_dados.append(['Payback Simples', f'{anos} anos e {meses_pb} meses'])
        
        if resultado_payback['payback_descontado'] is not None:
            anos_desc = int(resultado_payback['payback_descontado'])
            meses_desc = int((resultado_payback['payback_descontado'] - anos_desc) * 12)
            payback_dados.append(['Payback Descontado', f'{anos_desc} anos e {meses_desc} meses'])
        
        economia_25_anos = resultado_payback['economia_anual'] * 25
        lucro_liquido = economia_25_anos - investimento_total
        payback_dados.append(['Economia em 25 anos', f'R$ {economia_25_anos:,.2f}'])
        payback_dados.append(['Lucro Líquido (25 anos)', f'R$ {lucro_liquido:,.2f}'])
        
        t = Table(payback_dados, colWidths=[3*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightyellow),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3*inch))
        
        # Tabela de economia mensal
        story.append(Paragraph("Economia Mensal Estimada", heading_style))
        economia_mensal_dados = [['Mês', 'Economia (R$)']]
        for i, mes in enumerate(meses):
            economia_mensal_dados.append([
                mes,
                f'R$ {resultado_payback["economia_mensal"][i]:,.2f}'
            ])
        
        t = Table(economia_mensal_dados, colWidths=[1*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(t)
    
    # Rodapé
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("Relatório gerado pela Calculadora de Painéis Solares", 
                          styles['Normal']))
    
    # Construir PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

# Interface principal
def main():
    # Título principal com botão de PDF
    col_title, col_pdf = st.columns([4, 1])
    with col_title:
        st.title("☀️ Calculadora de Painéis Solares")
    with col_pdf:
        st.write("")  # Espaçamento
        st.write("")  # Espaçamento
        # Container para o botão PDF (será atualizado quando houver resultados)
        pdf_button_container = st.empty()
    
    st.markdown("---")
    
    # Sidebar para entrada de dados
    st.sidebar.header("📊 Dados de Entrada")
    
    # Consumo mensal
    st.sidebar.subheader("Consumo Mensal (kWh)")
    meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
             'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    # Opção de upload de CSV
    st.sidebar.markdown("**Opção 1: Upload de CSV**")
    
    # Criar CSV modelo para download apenas com valores de consumo
    csv_modelo = pd.DataFrame({
        'Consumo_Mensal_kWh': [350, 380, 320, 300, 280, 250, 240, 260, 290, 320, 340, 360]
    })
    csv_string = csv_modelo.to_csv(index=False)
    
    st.sidebar.download_button(
        label="📥 Baixar Modelo CSV",
        data=csv_string,
        file_name="modelo_consumo_mensal.csv",
        mime="text/csv",
        help="Baixe este arquivo modelo. O CSV deve ter apenas uma coluna com os valores de consumo (12 linhas, uma para cada mês: Jan a Dez)."
    )
    
    uploaded_file = st.sidebar.file_uploader(
        "Faça upload de um arquivo CSV com os dados de consumo mensal",
        type=['csv'],
        help="O CSV deve conter apenas uma coluna com os valores de consumo (12 valores, um para cada mês). Veja o modelo para o formato.",
        key="csv_uploader"
    )
    
    # Inicializar session_state se não existir
    if 'consumo_mensal' not in st.session_state:
        st.session_state.consumo_mensal = [300.0] * 12
    if 'potencia_modulo' not in st.session_state:
        st.session_state.potencia_modulo = 400.0
    if 'irradiacao_solar' not in st.session_state:
        st.session_state.irradiacao_solar = 4.5  # Valor médio típico para Brasil
    if 'csv_file_id' not in st.session_state:
        st.session_state.csv_file_id = None
    if 'pdf_disponivel' not in st.session_state:
        st.session_state.pdf_disponivel = False
    
    # Processar CSV quando um arquivo é carregado
    csv_file_id_atual = uploaded_file.name if uploaded_file is not None else None
    
    if uploaded_file is not None and st.session_state.csv_file_id != csv_file_id_atual:
        try:
            # Tentar ler o CSV
            df_csv = pd.read_csv(uploaded_file)
            
            # Procurar por colunas com nomes relacionados
            colunas = [col.lower().strip() for col in df_csv.columns]
            
            # Identificar coluna de consumo
            consumo_col = None
            for idx, col in enumerate(colunas):
                if 'consumo' in col or 'consum' in col:
                    consumo_col = df_csv.columns[idx]
                    break
            
            # Processar consumo mensal
            if consumo_col:
                valores = pd.to_numeric(df_csv[consumo_col], errors='coerce').dropna().values
                # Filtrar valores válidos (remover NaN e valores muito grandes)
                valores = valores[(valores >= 0) & (valores < 10000)]
                if len(valores) >= 12:
                    st.session_state.consumo_mensal = valores[:12].tolist()
                elif len(valores) > 0:
                    consumo_temp = valores.tolist()
                    while len(consumo_temp) < 12:
                        consumo_temp.append(0.0)
                    st.session_state.consumo_mensal = consumo_temp
            elif len(df_csv.columns) > 0:
                # Se não encontrou coluna específica, tentar primeira coluna numérica
                valores = pd.to_numeric(df_csv.iloc[:, 0], errors='coerce').dropna().values
                valores = valores[(valores >= 0) & (valores < 10000)]
                if len(valores) >= 12:
                    st.session_state.consumo_mensal = valores[:12].tolist()
            
            st.sidebar.success(f"✅ CSV carregado com sucesso!")
            st.session_state.csv_file_id = csv_file_id_atual
                    
        except Exception as e:
            st.sidebar.error(f"❌ Erro ao ler CSV: {str(e)}")
    
    # Opção de entrada manual
    st.sidebar.markdown("**Opção 2: Entrada Manual**")
    
    # Campos de entrada manual (podem ser editados mesmo com CSV carregado)
    # Usar uma chave única baseada no arquivo CSV para forçar atualização dos campos
    key_suffix = st.session_state.csv_file_id if st.session_state.csv_file_id else "manual"
    
    consumo_mensal = []
    for i, mes in enumerate(meses):
        # Usar valor do session_state
        valor_padrao = float(st.session_state.consumo_mensal[i]) if i < len(st.session_state.consumo_mensal) else 300.0
        
        # Usar chave única que muda quando CSV é carregado para forçar atualização
        valor = st.sidebar.number_input(
            f"{mes}:", 
            min_value=0.0, 
            value=valor_padrao, 
            step=10.0,
            key=f"consumo_{i}_{key_suffix}"
        )
        consumo_mensal.append(valor)
        
        # Atualizar session_state quando o usuário edita manualmente
        st.session_state.consumo_mensal[i] = valor
    
    # Parâmetros do sistema
    st.sidebar.subheader("Parâmetros do Sistema")
    
    # Usar chave única baseada no arquivo CSV para forçar atualização
    key_suffix = st.session_state.csv_file_id if st.session_state.csv_file_id else "manual"
    
    potencia_modulo = st.sidebar.number_input(
        "Potência do Módulo (Wp):", 
        min_value=100, 
        value=int(st.session_state.potencia_modulo), 
        step=50,
        key=f"potencia_{key_suffix}"
    )
    st.session_state.potencia_modulo = float(potencia_modulo)
    
    irradiacao_solar = st.sidebar.number_input(
        "Irradiação Solar (kWh/m²):", 
        min_value=0.0, 
        value=float(st.session_state.irradiacao_solar), 
        step=0.1,
        help="Valor médio de irradiação solar diária (será usado para todos os meses)",
        key=f"irradiacao_{key_suffix}"
    )
    st.session_state.irradiacao_solar = float(irradiacao_solar)
    
    # Seção de Análise Econômica (Payback)
    st.sidebar.markdown("---")
    st.sidebar.subheader("💰 Análise Econômica")
    
    # Inicializar session_state para valores econômicos
    if 'investimento_total' not in st.session_state:
        st.session_state.investimento_total = 0.0
    if 'tarifa_energia' not in st.session_state:
        st.session_state.tarifa_energia = 0.65  # Valor típico no Brasil
    if 'taxa_desconto' not in st.session_state:
        st.session_state.taxa_desconto = 0.0
    
    calcular_payback_option = st.sidebar.checkbox(
        "Calcular Payback",
        value=False,
        help="Marque para calcular o tempo de retorno do investimento"
    )
    
    # Inicializar variáveis de payback
    investimento_total = 0.0
    tarifa_energia = 0.0
    taxa_desconto = 0.0
    
    if calcular_payback_option:
        investimento_total = st.sidebar.number_input(
            "Investimento Total (R$):", 
            min_value=0.0, 
            value=float(st.session_state.investimento_total), 
            step=1000.0,
            help="Custo total do sistema fotovoltaico",
            key=f"investimento_{key_suffix}"
        )
        st.session_state.investimento_total = float(investimento_total)
        
        tarifa_energia = st.sidebar.number_input(
            "Tarifa de Energia (R$/kWh):", 
            min_value=0.0, 
            value=float(st.session_state.tarifa_energia), 
            step=0.01,
            help="Tarifa de energia elétrica cobrada pela concessionária",
            key=f"tarifa_{key_suffix}"
        )
        st.session_state.tarifa_energia = float(tarifa_energia)
        
        taxa_desconto = st.sidebar.number_input(
            "Taxa de Desconto Anual (%):", 
            min_value=0.0, 
            max_value=20.0,
            value=float(st.session_state.taxa_desconto), 
            step=0.5,
            help="Taxa de desconto para cálculo de payback descontado (opcional)",
            key=f"taxa_desconto_{key_suffix}"
        )
        st.session_state.taxa_desconto = float(taxa_desconto)
    
    # Botão para calcular
    if st.sidebar.button("🔧 Calcular Dimensionamento", type="primary"):
        # Realizar cálculos com valores padrão de fatores de perda
        resultado = calcular_dimensionamento(
            consumo_mensal, potencia_modulo, irradiacao_solar
        )
        
        # Exibir resultados principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Número de Módulos", 
                f"{resultado['numero_modulos']}",
                help="Quantidade de módulos fotovoltaicos necessários"
            )
        
        with col2:
            st.metric(
                "Potência Total", 
                f"{resultado['potencia_total']:.0f} Wp",
                help="Potência total do sistema fotovoltaico"
            )
        
        with col3:
            st.metric(
                "Potência do Inversor", 
                f"{resultado['potencia_inversor']:.0f} W",
                help="Potência recomendada para o inversor"
            )
        
        with col4:
            st.metric(
                "Consumo Médio Diário", 
                f"{resultado['consumo_medio_diario']:.1f} kWh/dia",
                help="Consumo médio diário de energia"
            )
        
        # Tabela de resultados mensais
        st.subheader("📋 Resultados Mensais")
        
        df_resultados = pd.DataFrame({
            'Mês': meses,
            'Consumo (kWh)': consumo_mensal,
            'Geração (kWh)': resultado['geracao_mensal'],
            'Saldo (kWh)': np.array(resultado['geracao_mensal']) - np.array(consumo_mensal),
            'Cobertura (%)': (np.array(resultado['geracao_mensal']) / np.array(consumo_mensal) * 100).round(1)
        })
        
        st.dataframe(df_resultados, use_container_width=True)
        
        # Gráficos
        st.subheader("📈 Visualizações")
        
        # Gráfico de linha comparativo
        fig_linha = criar_graficos(consumo_mensal, resultado['geracao_mensal'], meses)
        st.plotly_chart(fig_linha, use_container_width=True)
        
        # Gráfico de excedente de energia
        st.subheader("⚡ Excedente e Déficit de Energia")
        fig_excedente = criar_grafico_excedente(consumo_mensal, resultado['geracao_mensal'], meses)
        st.plotly_chart(fig_excedente, use_container_width=True)
        
        # Análise de cenários
        st.subheader("🔍 Análise de Cenários")
        
        st.write("**Cenários com diferentes quantidades de módulos:**")
        
        cenarios = [resultado['numero_modulos'], resultado['numero_modulos'] + 1, resultado['numero_modulos'] + 2]
        
        # Calcular geração média para cada cenário antes de criar o DataFrame
        geracao_media_lista = []
        for cenario in cenarios:
            # Usar o valor único de irradiação solar para todos os meses
            geracao_media = (potencia_modulo / 1000) * irradiacao_solar * resultado['fator_desempenho'] * cenario * 30
            geracao_media_lista.append(f"{geracao_media:.1f}")
        
        df_cenarios = pd.DataFrame({
            'Cenário': [f'{i} módulos' for i in cenarios],
            'Módulos': cenarios,
            'Potência Total (Wp)': [i * potencia_modulo for i in cenarios],
            'Geração Média Mensal (kWh)': geracao_media_lista
        })
        
        st.dataframe(df_cenarios, use_container_width=True)
        
        # Estatísticas do sistema
        st.subheader("📊 Estatísticas do Sistema")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Resumo Anual:**")
            st.write(f"- Consumo Total: {sum(consumo_mensal):.1f} kWh/ano")
            st.write(f"- Geração Total: {sum(resultado['geracao_mensal']):.1f} kWh/ano")
            st.write(f"- Saldo Anual: {sum(resultado['geracao_mensal']) - sum(consumo_mensal):.1f} kWh")
            st.write(f"- Cobertura Média: {np.mean(df_resultados['Cobertura (%)']):.1f}%")
        
        with col2:
            st.write("**Fator de Desempenho do Sistema:**")
            st.write(f"- Fator Total: {resultado['fator_desempenho']:.3f}")
            st.write(f"- Considera perdas por temperatura, sombreamento, conversão e eficiência do inversor")
        
        # Preparar e armazenar PDF no session_state para o botão no topo
        resultado_payback_pdf = None
        if calcular_payback_option and investimento_total > 0 and tarifa_energia > 0:
            resultado_payback_pdf = calcular_payback(
                resultado['geracao_mensal'],
                consumo_mensal,
                tarifa_energia,
                investimento_total,
                taxa_desconto / 100 if taxa_desconto > 0 else 0.0
            )
        
        # Gerar PDF e armazenar
        pdf_buffer = gerar_pdf(
            consumo_mensal,
            resultado,
            meses,
            potencia_modulo,
            irradiacao_solar,
            resultado_payback_pdf,
            investimento_total if calcular_payback_option and investimento_total > 0 else 0,
            tarifa_energia if calcular_payback_option and tarifa_energia > 0 else 0
        )
        st.session_state.pdf_buffer = pdf_buffer
        st.session_state.pdf_disponivel = True
        
        # Atualizar botão PDF no topo
        pdf_button_container.download_button(
            label="Gerar Relatório",
            data=pdf_buffer,
            file_name="relatorio_dimensionamento_solar.pdf",
            mime="application/pdf",
            help="Baixar relatório completo em PDF",
            use_container_width=True,
            key="pdf_button_top"
        )
        
        # Análise de Payback
        if calcular_payback_option and investimento_total > 0 and tarifa_energia > 0:
            st.subheader("💰 Análise de Retorno do Investimento (Payback)")
            
            resultado_payback = calcular_payback(
                resultado['geracao_mensal'],
                consumo_mensal,
                tarifa_energia,
                investimento_total,
                taxa_desconto / 100 if taxa_desconto > 0 else 0.0
            )
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if resultado_payback['payback_simples'] != float('inf'):
                    anos = int(resultado_payback['payback_simples'])
                    meses_payback = int((resultado_payback['payback_simples'] - anos) * 12)
                    st.metric(
                        "Payback Simples",
                        f"{anos} anos e {meses_payback} meses",
                        help="Tempo necessário para recuperar o investimento"
                    )
                else:
                    st.metric("Payback Simples", "Não viável", help="Economia insuficiente")
            
            with col2:
                st.metric(
                    "Economia Anual",
                    f"R$ {resultado_payback['economia_anual']:,.2f}",
                    help="Economia anual estimada com o sistema"
                )
            
            with col3:
                st.metric(
                    "Economia Mensal Média",
                    f"R$ {resultado_payback['economia_mensal_media']:,.2f}",
                    help="Economia mensal média estimada"
                )
            
            with col4:
                if resultado_payback['payback_descontado'] is not None:
                    anos_desc = int(resultado_payback['payback_descontado'])
                    meses_desc = int((resultado_payback['payback_descontado'] - anos_desc) * 12)
                    st.metric(
                        "Payback Descontado",
                        f"{anos_desc} anos e {meses_desc} meses",
                        help="Payback considerando taxa de desconto"
                    )
                elif taxa_desconto > 0:
                    st.metric("Payback Descontado", "> 50 anos", help="Payback muito longo")
            
            # Gráfico de economia mensal
            st.subheader("📊 Economia Mensal Estimada")
            meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                          'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
            df_economia = pd.DataFrame({
                'Mês': meses_nomes,
                'Economia (R$)': resultado_payback['economia_mensal']
            })
            
            fig_economia = go.Figure()
            fig_economia.add_trace(go.Bar(
                x=meses_nomes,
                y=resultado_payback['economia_mensal'],
                marker_color='green',
                opacity=0.7,
                text=[f'R$ {val:.2f}' for val in resultado_payback['economia_mensal']],
                textposition='outside'
            ))
            fig_economia.update_layout(
                title='Economia Mensal Estimada',
                xaxis_title='Mês',
                yaxis_title='Economia (R$)',
                template='plotly_white'
            )
            st.plotly_chart(fig_economia, use_container_width=True)
            
            # Resumo financeiro
            st.subheader("💵 Resumo Financeiro")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Investimento e Retorno:**")
                st.write(f"- Investimento Total: R$ {investimento_total:,.2f}")
                st.write(f"- Economia Anual: R$ {resultado_payback['economia_anual']:,.2f}")
                if resultado_payback['payback_simples'] != float('inf'):
                    st.write(f"- Payback: {resultado_payback['payback_simples']:.2f} anos")
                    # Calcular economia em 25 anos (vida útil típica)
                    economia_25_anos = resultado_payback['economia_anual'] * 25
                    lucro_liquido = economia_25_anos - investimento_total
                    st.write(f"- Economia em 25 anos: R$ {economia_25_anos:,.2f}")
                    st.write(f"- Lucro Líquido (25 anos): R$ {lucro_liquido:,.2f}")
            
            with col2:
                st.write("**Informações Adicionais:**")
                st.write(f"- Tarifa de Energia: R$ {tarifa_energia:.4f}/kWh")
                if taxa_desconto > 0:
                    st.write(f"- Taxa de Desconto: {taxa_desconto:.2f}% ao ano")
                    if resultado_payback['payback_descontado'] is not None:
                        st.write(f"- Payback Descontado: {resultado_payback['payback_descontado']:.2f} anos")
                st.write(f"- Custo por kWp: R$ {investimento_total / (resultado['potencia_total'] / 1000):,.2f}/kWp")

if __name__ == "__main__":
    main()


