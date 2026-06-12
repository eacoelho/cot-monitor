# COT Monitor 🌾

Pipeline semanal automatizado que busca o relatório **Commitment of Traders (COT)** do CFTC, combina com preços de futuros do Yahoo Finance, gera gráficos individuais por commodity e envia uma análise escrita por IA (Groq / Llama 3.3) em português brasileiro via Telegram.

---

## O que faz

Toda sexta-feira, após o CFTC publicar o relatório semanal, o pipeline:

1. **Aguarda** a publicação no endpoint do CFTC (polling a cada 5 min) — trata atrasos por feriados americanos ou shutdown do governo
2. **Coleta** posições net de Managed Money (futuros + opções) via [CFTC Disaggregated COT API](https://publicreporting.cftc.gov/) — últimas 52 semanas
3. **Coleta** preços semanais de fechamento de cada commodity via Yahoo Finance
4. **Gera** um gráfico PNG individual por commodity com tema escuro, dual Y-axis (posição net + preço), otimizado para leitura em smartphone
5. **Analisa** os dados via Groq (Llama 3.3) e produz um parágrafo de análise em PT-BR
6. **Envia** imagem + texto para um chat ou canal do Telegram — uma mensagem por commodity

### Formato da mensagem no Telegram

```
*Soja*
📊 Net Fundos: +45.200 contratos  (+3.100 na semana)
💰 Preço: 1.042,50  (-1,8% na semana)

🟢 Os fundos mantêm posição comprada expressiva, próxima ao
topo histórico do período analisado. A aceleração recente das
compras, combinada com a alta do preço, indica convergência
entre o posicionamento especulativo e a tendência de mercado...
```

### Commodities monitoradas

| Commodity | Mercado CFTC | Ticker Yahoo Finance |
|---|---|---|
| Soja | SOYBEANS – CBOT | ZS=F |
| Milho | CORN – CBOT | ZC=F |
| Trigo SRW | WHEAT – CBOT | ZW=F |
| Farelo de Soja | SOYBEAN MEAL – CBOT | ZM=F |
| Óleo de Soja | SOYBEAN OIL – CBOT | ZL=F |
| Algodão | COTTON NO. 2 – ICE | CT=F |
| Café | COFFEE C – ICE | KC=F |
| Açúcar | SUGAR NO. 11 – ICE | SB=F |
| Cacau | COCOA – ICE | CC=F |

---

## Requisitos

- Python 3.11+
- VPS ou servidor com acesso à internet (testado em Ubuntu 22.04 LTS)
- Token de bot do Telegram e ID do chat/canal
- [Chave de API Groq](https://console.groq.com/) (plano gratuito disponível)

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/YOUR_USERNAME/cot-monitor.git
cd cot-monitor

# 2. Crie e ative o ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as credenciais
cp config-original.py config.py
nano config.py
```

### Configuração do `config.py`

```python
# Telegram
TELEGRAM_BOT_TOKEN = "seu_token_aqui"
TELEGRAM_CHAT_ID   = "seu_chat_id_aqui"

# Groq
GROQ_API_KEY = "sua_chave_groq_aqui"
GROQ_MODEL   = "llama-3.3-70b-versatile"

# Janela de histórico
LOOKBACK_WEEKS = 52   # ~12 meses

# Parâmetros de gráfico
CHART_DPI     = 180       # resolução da imagem
CHART_FIGSIZE = (14, 8)   # largura × altura em polegadas

# API do CFTC
CFTC_API_URL   = "https://publicreporting.cftc.gov/resource/kh3c-gbw2.json"
CFTC_PAGE_SIZE = 5000
```

> **Segurança**: se o repositório for público, prefira carregar credenciais via variáveis de ambiente e adapte `config.py` para usar `os.getenv()`.

---

## Execução manual

```bash
source venv/bin/activate
python cot_runner.py
```

Em execuções manuais (dia diferente de sexta-feira), o script pula a espera pelo CFTC e processa os dados mais recentes disponíveis.

Logs são gravados em `logs/cot_monitor.log` e no stdout.

---

## Execução automática semanal (systemd)

Abordagem recomendada para VPS em produção.

```bash
# 1. Copie os arquivos de serviço
sudo cp cot-monitor.service /etc/systemd/system/
sudo cp cot-monitor.timer   /etc/systemd/system/

# 2. Ative e inicie o timer
sudo systemctl daemon-reload
sudo systemctl enable --now cot-monitor.timer

# 3. Verifique
sudo systemctl list-timers --all | grep cot
```

### Lógica de horário

O timer dispara toda **sexta-feira às 19:25 UTC**. A partir daí, o script faz polling do endpoint do CFTC a cada 5 minutos até os dados aparecerem:

| Cenário | Comportamento |
|---|---|
| Publicação normal (EDT/verão) | Dados às ~19:30 UTC → pipeline roda ~19:35 UTC |
| Publicação normal (EST/inverno) | Dados às ~20:30 UTC → pipeline roda ~20:35 UTC |
| Atraso (feriado, sobrecarga) | Continua tentando a cada 5 min |
| Não publicado em 4 horas | Exit 0 com log explicativo; retoma na próxima sexta |

### Comandos úteis

```bash
# Status da última execução
sudo systemctl status cot-monitor.service

# Logs do serviço (systemd journal)
journalctl -u cot-monitor.service -n 50 --no-pager

# Executar imediatamente (teste)
sudo systemctl start cot-monitor.service

# Acompanhar log em tempo real
tail -f logs/cot_monitor.log
```

---

## Estrutura do projeto

```
cot-monitor/
├── config.py             # Credenciais, commodities e parâmetros (não versionado)
├── config-original.py    # Template de configuração (copie para config.py)
├── cot_runner.py         # Orquestrador do pipeline (entry point)
├── cot_collector.py      # Coleta de dados: CFTC API + Yahoo Finance
├── cot_chart.py          # Geração de gráficos PNG por commodity
├── cot_analyst.py        # Análise via Groq LLM (cabeçalho + parágrafo IA)
├── cot_notifier.py       # Envio via Telegram Bot API
├── requirements.txt      # Dependências Python
├── cot-monitor.service   # Unit systemd (serviço)
├── cot-monitor.timer     # Unit systemd (timer semanal sexta 19:25 UTC)
├── logs/                 # Logs de execução (criado automaticamente)
├── charts/               # PNGs gerados (criado automaticamente)
└── README.md
```

---

## Fontes de dados

| Fonte | Dado | Acesso |
|---|---|---|
| [CFTC Socrata API](https://publicreporting.cftc.gov/resource/kh3c-gbw2.json) | Disaggregated COT – Managed Money (Fut+Opt) | Gratuito, sem autenticação |
| [Yahoo Finance (yfinance)](https://github.com/ranaroussi/yfinance) | Preços semanais de futuros contínuos | Gratuito, sem autenticação |
| [Groq](https://console.groq.com/) | Inferência Llama 3.3 70B | Plano gratuito disponível |
| [Telegram Bot API](https://core.telegram.org/bots/api) | Entrega de mensagens | Gratuito |

---

## Diagnóstico de nomes CFTC

Se uma commodity não retornar dados, use o utilitário de validação para verificar o nome exato no dataset:

```bash
python -c "from cot_collector import validate_cftc_names; validate_cftc_names()"
```

Isso lista todos os valores de `market_and_exchange_names` disponíveis para cada commodity. Atualize `cftc_name` em `config.py` se necessário.

---

## Limitações conhecidas

- **Yahoo Finance** não garante continuidade para tickers de futuros. Se um ticker parar de retornar dados, atualize `yf_ticker` em `config.py`.
- **Groq free tier** possui limites de taxa. O módulo de análise inclui retry com backoff exponencial (3 tentativas, até 15s de espera).
- **Telegram comprime imagens** enviadas via `sendPhoto`. Se a qualidade degradar no destinatário, aumente `CHART_DPI` em `config.py`.

---

## Licença

GNU General Public License v2
