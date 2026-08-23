# 🛒 FlyerScout AI • Instagram Supermarket Flyers Scraper

> **Automação completa para raspagem de encartes de supermercados no Instagram, extração inteligente de preços com IA de Visão, persistência em Banco de Dados com deduplicação, alertas no Telegram e execução 100% autônoma em Nuvem (GitHub Actions).**

---

## 🌟 Visão Geral

O **FlyerScout AI** transforma o processo manual de conferência de folhetos e encartes de supermercados em uma esteira 100% automatizada e autônoma:
1. **Coleta e Raspagem:** Extrai postagens e carrosséis de imagens dos perfis do Instagram dos supermercados.
2. **Inteligência Artificial de Visão:** Identifica nomes completos de produtos, unidades de medida e preços promocionais.
3. **Classificação Automática:** Categoriza produtos em Carnes, Bebidas, Mercearia, Laticínios, Limpeza, Higiene, Hortifruti, Bazar, etc.
4. **Banco de Dados & Deduplicação:** Armazena tudo no banco SQLite local (`data/offers.db`) gerando um hash único para identificar ofertas repetidas e salvar **somente as novas**.
5. **Alertas no Telegram:** Envia o resumo das novas ofertas do dia e anexa a planilha Excel formatada diretamente no seu chat, canal ou grupo do Telegram.
6. **Automação Diária em Nuvem:** Roda diariamente de forma 100% independente via **GitHub Actions** (gratuito) ou em servidores na nuvem (Docker / VPS / Render), sem precisar do seu computador ligado.

---

## ✨ Funcionalidades Principais

- ⚡ **Interface Web Leve & Rápida:** Inicialização instantânea, baixo uso de recursos e responsiva (FastAPI + Vanilla CSS).
- 💾 **Banco de Dados SQLite com Deduplicação:**
  - Hashing SHA-256 (`supermercado + item + valor + data`) que impede ofertas duplicadas.
  - Painel de visualização e busca de todas as ofertas acumuladas no banco de dados.
  - Download direto do arquivo do banco de dados `.db`.
- 📲 **Integração com Bot do Telegram:**
  - Disparo de resumos diários com novos itens cadastrados.
  - Envio automático da planilha Excel (`.xlsx`) como documento no Telegram.
  - Botão de **"Testar Envio no Telegram"** na interface web.
- ☁️ **Automação 100% em Nuvem (GitHub Actions):**
  - Workflow agendado para rodar todo dia às **07:00 da manhã** (Horário de Brasília).
  - Execução manual com 1 clique pelo botão "Run workflow" no GitHub.
  - Gravação automática do banco de dados e arquivos gerados de volta no repositório.
- 🎯 **Gerenciamento Dinâmico de Perfis:**
  - Adicione, remova, ative ou desative perfis de supermercados pela interface web.
- 🧠 **Motor de IA Visual Híbrido:**
  - **Google Gemini Flash (Recomendado):** Ultra-rápido, alta acurácia na leitura de textos e preços em encartes e consumo mínimo de recursos.
  - **OpenAI GPT-4o / GPT-4o-mini:** Suporte nativo para chaves da OpenAI.
- 📊 **Exportação Profissional:**
  - Planilha **Excel (.xlsx)** estilizada com abas por Supermercado e por Categoria.
  - Exportação direta para **CSV** e **JSON**.

---

## 🏗️ Estrutura do Projeto

```
instagram_flyers_scraper/
├── .github/
│   └── workflows/
│       └── daily_scraper.yml  # Automação diária no GitHub Actions (Nuvem)
├── cron_job.py                # Script CLI para automação diária autônoma
├── app.py                     # Servidor FastAPI com rotas REST e streaming SSE
├── run.bat                    # Executável de 1 clique para Windows
├── requirements.txt           # Dependências otimizadas
├── Dockerfile                 # Contêiner para deploy na nuvem
├── .env.example               # Template de variáveis de ambiente
├── core/
│   ├── config.py              # Gestão segura de chaves e parâmetros
│   ├── database.py            # SQLite com deduplicação por hash SHA-256
│   ├── telegram_notifier.py   # Bot do Telegram para alertas e envio de Excel
│   ├── scraper.py             # Raspagem do Instagram via Apify
│   ├── vision_ai.py           # Extração visual por IA (Gemini / OpenAI)
│   ├── categorizer.py         # Categorização inteligente de produtos
│   ├── exporter.py            # Geração de Excel (.xlsx), CSV e JSON
│   └── task_runner.py         # Pipeline assíncrono com streaming de logs
├── data/
│   ├── config.json            # Configurações locais e perfis
│   └── offers.db              # Banco de dados SQLite persistido
├── output/                    # Planilhas Excel e relatórios gerados
├── static/                    # Interface web frontend (CSS e JS)
└── templates/
    └── index.html             # Dashboard interativo
```

---

## ☁️ Como Configurar a Automação Diária na Nuvem (GitHub Actions)

Com o GitHub Actions configurado, a coleta roda **automaticamente todos os dias às 07:00 da manhã** nos servidores do GitHub, salva no banco e envia o resumo e a planilha no seu Telegram. **Seu computador não precisa estar ligado!**

### Passo 1: Criar o Bot no Telegram (1 minuto)
1. No Telegram, abra a conversa com o **[@BotFather](https://t.me/botfather)**.
2. Envie o comando `/newbot` e siga as instruções para escolher o nome e username do bot.
3. O BotFather fornecerá o seu **Token do Bot** (ex: `7123456789:AAFxxx...`).
4. Inicie uma conversa com o seu bot recém-criado clicando em **Começar / Start**.
5. Para descobrir seu **Chat ID**, converse com o **[@userinfobot](https://t.me/userinfobot)** e copie o `Id` (ex: `123456789`).
   - *Se quiser enviar para um canal/grupo:* Adicione o bot como administrador do canal e use `@nome_do_canal` ou o ID do grupo (ex: `-100123456789`).

### Passo 2: Cadastrar as Chaves nos Secrets do Repositório GitHub
1. No GitHub, acesse a página do seu repositório.
2. Vá em **Settings** > **Secrets and variables** > **Actions**.
3. Clique em **"New repository secret"** e cadastre as seguintes variáveis:
   - `APIFY_TOKEN`: Seu token do Apify (`apify_api_...`)
   - `GEMINI_API_KEY`: Sua chave do Google Gemini (`AIzaSy...`)
   - `TELEGRAM_BOT_TOKEN`: O token do seu bot criado no @BotFather
   - `TELEGRAM_CHAT_ID`: O seu Chat ID ou `@canal`
4. (Opcional) Vá em **Settings** > **Actions** > **General** > **Workflow permissions** e marque **"Read and write permissions"** (para permitir que o GitHub Actions salve o banco `data/offers.db` no repositório).

### Passo 3: Testar a Execução na Nuvem
1. No GitHub, vá na aba **Actions**.
2. Clique no workflow **"Daily Supermarket Flyers Scraper"** na barra lateral.
3. Clique no botão **"Run workflow"** para testar manualmente.
4. Em instantes, o robô executará o pipeline e você receberá a notificação e a planilha Excel no seu Telegram!

---

## 💻 Como Executar Localmente

### 1. Pré-requisitos
- Python 3.10 ou superior
- Conta no [Apify](https://console.apify.com/) (`APIFY_TOKEN`)
- Chave de API do [Google AI Studio](https://aistudio.google.com/app/apikey) (`GEMINI_API_KEY`)

### 2. Iniciar a Interface Web
No Windows, dê dois cliques em **`run.bat`** ou rode no terminal:
```powershell
pip install -r requirements.txt
python app.py
```
Abra o navegador em: **`http://localhost:8000`**

### 3. Executar Automação via Linha de Comando (CLI)
Você também pode rodar a extração diretamente via terminal:
```bash
# Executa com período padrão (ontem e hoje)
python cron_job.py

# Filtra últimos 3 dias e limite de 5 posts por mercado
python cron_job.py --date-mode last_3_days --limit 5

# Desativa o envio de Telegram momentaneamente
python cron_job.py --no-telegram
```

---

## 📊 Estrutura do Banco de Dados SQLite

O banco `data/offers.db` possui a tabela `offers` com os seguintes campos:
- `id`: Identificador autoincremental
- `hash_dedup`: Hash SHA-256 único de cada produto e data (garante deduplicação automática)
- `supermercado`: Nome do supermercado
- `categoria`: Classificação do produto (Carnes, Bebidas, etc.)
- `item`: Descrição completa do produto
- `valor`: Preço promocional (número decimal)
- `data_postagem`: Data da publicação no Instagram
- `link`: URL da imagem do encarte
- `post_url`: Link direto para o post no Instagram
- `created_at`: Data e hora da inserção no banco de dados

---

## 🔒 Segurança e Privacidade

- Credenciais de API e tokens do Telegram nunca são versionadas no Git.
- Todos os segredos no GitHub Actions ficam protegidos criptograficamente pelo GitHub Secrets.
- O `.gitignore` protege os arquivos `.env`, bancos de dados locais e planilhas temporárias.
