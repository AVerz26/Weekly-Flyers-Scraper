# 🛒 FlyerScout AI • Instagram Supermarket Flyers Scraper

> **Automação completa para raspagem de encartes de supermercados no Instagram, extração inteligente de preços com IA de Visão e geração de planilhas Excel formatadas.**

---

## 🌟 Visão Geral

O **FlyerScout AI** transforma o processo manual de conferência de folhetos e encartes de supermercados em uma esteira 100% automatizada. A aplicação conta com um backend assíncrono e uma interface web moderna, leve e responsiva (FastAPI + Vanilla CSS Glassmorphism) que executa em segundo plano com logs e progresso em tempo real.

![Interface FlyerScout AI](https://raw.githubusercontent.com/averz26/instagram-flyers-scraper/main/docs/preview.png)

---

## ✨ Funcionalidades Principais

- ⚡ **Interface Web Leve & Rápida:** Sem frameworks pesados no frontend; inicialização instantânea, baixo uso de RAM e responsiva.
- 🎯 **Raspagem Dinâmica de Perfis do Instagram:**
  - Gerenciador interativo de supermercados (adicionar, editar, desativar ou excluir perfis).
  - Pré-carregado com os supermercados da região.
- 📅 **Filtros Temporais Flexíveis:**
  - *Ontem e Hoje (Padrão)*
  - *Apenas Hoje*
  - *Últimos 3 ou 7 dias*
  - *Intervalo de Datas Personalizado*
- 🧠 **Motor de IA Visual Híbrido:**
  - **Google Gemini Flash (Recomendado):** Ultra-rápido, alta acurácia na leitura de textos e preços em encartes e consumo mínimo de recursos.
  - **OpenAI GPT-4o / GPT-4o-mini:** Suporte nativo para chaves da OpenAI.
  - **Qwen2.5-VL / Local:** Suporte opcional para modelos locais via PyTorch.
- 🏷️ **Categorização Semântica Automática:**
  - Classificação inteligente em categorias do varejo alimentar (Carnes, Bebidas, Mercearia, Laticínios, Limpeza, Higiene, Hortifruti, Bazar, Pet).
- 📊 **Exportação Profissional:**
  - Planilha **Excel (.xlsx)** estilizada com cabeçalhos profissionais, cores contrastantes, abas de resumo por mercado e comparativo por categoria.
  - Exportação direta para **CSV** e **JSON**.
- 📟 **Terminal de Logs ao Vivo:**
  - Acompanhamento do progresso em tempo real via *Server-Sent Events (SSE)*.
  - Pré-visualização do encarte original direto no navegador.
- 🔒 **Segurança & Privacidade:**
  - Suas chaves de API (Apify, Gemini, OpenAI) ficam armazenadas exclusivamente no seu arquivo local `.env` e nunca são versionadas no Git.

---

## 🏗️ Estrutura do Projeto

```
instagram_flyers_scraper/
├── app.py                     # Servidor FastAPI com rotas REST e streaming SSE
├── run.bat                    # Executável de 1 clique para Windows
├── requirements.txt           # Dependências otimizadas
├── .env.example               # Template de variáveis de ambiente
├── .gitignore                 # Proteção contra vazamento de chaves e dados
├── README.md                  # Documentação do projeto
├── core/
│   ├── config.py              # Gestão segura de chaves e perfis salvos
│   ├── scraper.py             # Integração com Apify Instagram Scraper e filtros de data
│   ├── vision_ai.py           # Motor de extração visual (Gemini, OpenAI, Qwen)
│   ├── categorizer.py         # Classificador semântico de produtos de supermercado
│   ├── exporter.py            # Geração de planilhas Excel (.xlsx) estilizadas
│   └── task_runner.py         # Gerenciador de background tasks e streaming
├── static/
│   ├── css/style.css          # Estilo moderno com tema escuro e glassmorphism
│   └── js/app.js              # Lógica reativa do frontend e comunicação SSE
└── templates/
    └── index.html             # Dashboard interativo
```

---

## 🚀 Como Executar

### 1. Pré-requisitos
- Python 3.10 ou superior
- Conta no [Apify](https://console.apify.com/) para obter seu `APIFY_TOKEN`.
- Chave de API do [Google AI Studio](https://aistudio.google.com/app/apikey) para o Gemini (gratuito) ou [OpenAI](https://platform.openai.com/).

### 2. Instalação e Inicialização no Windows

Basta dar dois cliques no arquivo **`run.bat`** ou executar no terminal:

```powershell
# Clone o repositório
git clone https://github.com/averz26/instagram-flyers-scraper.git
cd instagram-flyers-scraper

# Instale as dependências
pip install -r requirements.txt

# Inicie a aplicação
python app.py
```

Abra o navegador no endereço: **`http://localhost:8000`**

---

## ⚙️ Configuração Inicial

1. Na interface web, clique no botão **"⚙️ Configurações"** no topo.
2. Insira o seu **Token do Apify** (`apify_api_...`).
3. Insira sua **Chave do Google Gemini** (`AIzaSy...`).
4. Clique em **Salvar Configurações**.
5. No painel principal, selecione o período desejado e clique em **"🚀 Iniciar Extração"**.

---

## 📁 Planilhas Geradas

As planilhas são salvas automaticamente na pasta `output/` e ficam disponíveis para download direto na aba **"Histórico de Planilhas"** ou pelo botão **"📥 Excel (.xlsx)"** no topo da tabela.

Estrutura das abas da planilha Excel:
1. **Todas as Ofertas:** Lista completa com Supermercado, Categoria, Produto, Preço (R$), Data e Link do Encarte.
2. **Por Supermercado:** Métricas de quantidade de itens, preço médio, menor e maior preço de cada mercado.
3. **Por Categoria:** Média e menor preço encontrado por categoria de alimento.

---

## 🛡️ Licença & Autor

Desenvolvido por **André Verzoto** ([@averz26](https://github.com/averz26)).
Licença MIT.
