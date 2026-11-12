import json
import os
from typing import List
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


def search_and_filter_listings(config: dict) -> List[CarListing]:
    """Executa buscas na web via Gemini Grounding e filtra os resultados via Pydantic."""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    target = config["target"]
    queries = "\n".join(f"- {q}" for q in config["search_queries"])

    prompt = f"""
    Você é um analista especializado em garimpo automotivo.
    Realize pesquisas na web utilizando a ferramenta do Google Search para encontrar anúncios reais e recentes de venda de veículos com base nas seguintes diretrizes:

    ALVO DE BUSCA:
    - Veículo: {target['vehicle']}
    - Versões permitidas: {', '.join(target['versions'])}
    - Anos permitidos: {', '.join(map(str, target['years']))}
    - Cor obrigatória: {target['color']}
    - Localização permitida: {', '.join(target['locations'])}
    - Preço máximo: R$ {target['max_price']}
    - Data máxima da publicação: Últimos {target['max_age_months']} meses (considere o ano atual como 2026).

    FONTES PRIORITÁRIAS:
    {', '.join(target['priority_sources'])}

    REGRAS ESTRITAS DE EXCLUSÃO (REJEITE IMEDIATAMENTE SE OCORRER):
    - Domínios proibidos: {', '.join(target['excluded_domains'])}
    - Critérios de rejeição: {', '.join(target['rejection_criteria'])}
    - Não invente links. Retorne apenas URLs reais encontradas na pesquisa.

    SUGESTÕES DE CONSULTAS PARA EXECUTAR:
    {queries}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}],
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