import json
import logging
import os
import time
from typing import List
from tavily import TavilyClient
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class CarListing(BaseModel):
    title: str = Field(description="Título ou resumo curto do veículo anunciado")
    version: str = Field(description="Versão identificada (EXL ou Touring)")
    year: int = Field(description="Ano do veículo (2017, 2018 ou 2019)")
    price: float = Field(
        description="Preço numérico em reais (ex: 115000.0). Se não informado, use 0.0"
    )
    location: str = Field(description="Cidade/Estado do anúncio")
    source: str = Field(
        description="Plataforma ou nome da loja (ex: Instagram @loja, Facebook Marketplace, Site da Agência)"
    )
    url: str = Field(description="Link direto para o anúncio ou post")
    summary: str = Field(
        description="Resumo dos detalhes relevantes (km, estado de conservação, observações do vendedor)"
    )


class SearchReport(BaseModel):
    listings: List[CarListing] = Field(
        default_factory=list,
        description="Lista apenas dos anúncios que passaram em TODOS os filtros obrigatórios.",
    )


def _fetch_web_results(queries: List[str], max_results_per_query: int = 10) -> List[dict]:
    """Coleta resultados reais da web via Tavily Search API."""
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    raw_results = []
    seen_urls = set()

    for query in queries:
        logging.info("Buscando via Tavily: %s", query)
        try:
            response = tavily.search(
                query=query,
                search_depth="basic",
                max_results=7,
                exclude_domains=["olx.com.br"],
            )
            for item in response.get("results", []):
                url = item.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    raw_results.append({
                        "title": item.get("title", ""),
                        "url": url,
                        "snippet": item.get("content", ""),
                    })
        except Exception as e:
            logging.warning("Falha na consulta '%s': %s", query, e)

    return raw_results

def _get_available_models(client: genai.Client) -> List[str]:
    """Consulta na API os modelos ativos e disponíveis para a chave atual."""
    available = []
    try:
        for m in client.models.list():
            name = m.name.replace("models/", "")
            methods = getattr(m, "supported_actions", []) or []
            if "generateContent" in methods and "gemini" in name.lower():
                available.append(name)
    except Exception as e:
        logging.warning("Não foi possível listar modelos dinamicamente: %s", e)

    # Prioriza modelos Flash/Pro mais rápidos primeiro
    preferred = [m for m in available if "flash" in m or "pro" in m]
    return preferred if preferred else ["gemini-3.8-flash"]

def search_and_filter_listings(config: dict) -> List[CarListing]:
    """Busca anúncios na web e usa o Gemini (Free Tier) para filtrar e estruturar."""
    raw_results = _fetch_web_results(config["search_queries"])
    logging.info("Total de links brutos coletados na web: %d", len(raw_results))

    if not raw_results:
        return []

    client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={"timeout": 30000},
)
    target = config["target"]

    prompt = f"""
    Você é um analista especializado em garimpo automotivo.
    Analise a lista de resultados de busca abaixo (em JSON) e extraia APENAS os anúncios reais de venda de veículos que atendam rigorosamente a TODOS os critérios:

    CRITÉRIOS OBRIGATÓRIOS:f
    - Veículo: {target['vehicle']}
    - Versões permitidas: {', '.join(target['versions'])}
    - Anos permitidos: {', '.join(map(str, target['years']))}
    - Cor obrigatória: {target['color']}
    - Localização permitida: {', '.join(target['locations'])}
    - Preço máximo: R$ {target['max_price']} (se o preço não estiver explícito no trecho, mas o anúncio for válido, retorne 0.0 para revisão manual).

    REGRAS ESTRITAS DE EXCLUSÃO (REJEITE IMEDIATAMENTE SE OCORRER):
    - Domínios proibidos: {', '.join(target['excluded_domains'])}
    - Critérios de rejeição: {', '.join(target['rejection_criteria'])}
    - Use exatamente a URL fornecida nos resultados brutos. Nunca altere ou invente links.

    RESULTADOS BRUTOS COLETADOS:
    {json.dumps(raw_results, ensure_ascii=False, indent=2)}
    """

    models_to_try = _get_available_models(client)
    logging.info("Modelos disponíveis na conta: %s", models_to_try)

    for model_name in models_to_try:
        for attempt in range(2):
            try:
                logging.info("Analisando anúncios com o modelo: %s", model_name)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=SearchReport,
                        temperature=0.1,
                    ),
                )

                if not response.text:
                    return []

                data = json.loads(response.text)
                report = SearchReport(**data)
                return report.listings

            except Exception as e:
                if "503" in str(e) or "429" in str(e):
                    logging.warning("Servidor ocupado (%s). Tentando novamente em 5s...", model_name)
                    time.sleep(5)
                else:
                    logging.warning("Erro com %s: %s", model_name, e)
                    break

    return []