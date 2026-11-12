# 🚗 WebHunter

Bot automatizado de monitoramento web e curadoria inteligente construído em **Python**, utilizando a **Tavily Search API** para coleta de dados e a **Google Gemini API** (com validação estruturada via **Pydantic**) para filtragem semântica e alertas por e-mail.

## Arquitetura do Pipeline

1. **Coleta (`Tavily API`):** Executa consultas parametrizadas via `config.json` para rastrear oportunidades em portais, classificados e redes sociais.
2. **Triagem Semântica (`Google Gemini + Pydantic`):** Descobre dinamicamente os modelos ativos na conta com fallback automático, interpreta o conteúdo bruto dos anúncios e descarta falsos positivos (peças, leilões, sinistros ou itens fora de especificação), retornando objetos fortemente tipados.
3. **Deduplicação (`SQLite`):** Armazena o histórico de URLs processadas localmente (`webhunter.db`) para garantir que cada oportunidade seja notificada apenas uma vez.
4. **Notificação (`SMTP / HTML`):** Formata e dispara alertas em HTML diretamente para a caixa de entrada configurada.

## Estrutura do Projeto

```text
webhunter/
├── src/
│   ├── __init__.py
│   ├── database.py     # Persistência e deduplicação em SQLite
│   ├── hunter.py       # Integração Tavily + Gemini API + Pydantic
│   └── notifier.py     # Disparo de alertas HTML via SMTP
├── config.json         # Regras de negócio, filtros e queries de busca
├── main.py             # Orquestrador principal do pipeline
├── requirements.txt    # Dependências do projeto
└── .env.example        # Modelo de variáveis de ambiente