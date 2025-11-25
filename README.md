# ☀️ Calculadora de Painéis Solares

Uma ferramenta interativa desenvolvida em Python com Streamlit para calcular a estrutura básica de painéis solares necessários para atender a demanda média dos 12 meses de consumo energético.

## 🚀 Funcionalidades

- **Cálculo Automático**: Dimensionamento automático de módulos fotovoltaicos
- **Análise Mensal**: Comparação entre consumo e geração por mês
- **Cenários Múltiplos**: Análise de diferentes quantidades de módulos
- **Visualizações Interativas**: Gráficos comparativos com Plotly
- **Dimensionamento do Inversor**: Cálculo automático da potência necessária
- **Fatores de Perda**: Consideração automática de perdas por temperatura, sombreamento e conversão (valores padrão)
- **Upload de CSV**: Importação de dados de consumo mensal via arquivo CSV
- **Gráfico de Excedente**: Visualização específica de excedente e déficit de energia
- **Cálculo de Payback**: Análise de retorno do investimento com payback simples e descontado
- **Exportação de PDF**: Geração de relatório completo em PDF com todos os resultados

## 📋 Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

## 🛠️ Instalação

1. Clone ou baixe este repositório
2. Navegue até o diretório do projeto
3. Instale as dependências:

```bash
pip install -r requirements.txt
```

## 🎯 Como Usar

1. Execute a aplicação:

```python -m streamlit run solar_calculator.py
```

2. A aplicação abrirá automaticamente no seu navegador
3. Preencha os dados na barra lateral:
   - **Consumo Mensal**: 
     - **Opção 1**: Faça upload de um arquivo CSV com os dados de consumo mensal
     - **Opção 2**: Insira manualmente o consumo de energia para cada mês
   - **Potência do Módulo**: Defina a potência dos módulos fotovoltaicos
   - **Irradiação Solar**: Defina o valor único de irradiação solar (será usado para todos os meses)

4. Clique em "Calcular Dimensionamento" para ver os resultados
5. Clique em "📥 Baixar Relatório em PDF" para exportar um relatório completo