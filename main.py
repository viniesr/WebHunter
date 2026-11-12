import json
import logging
from pathlib import Path
from dotenv import load_dotenv

from src.database import init_db, is_ad_seen, mark_ad_as_seen
from src.hunter import search_and_filter_listings
from src.notifier import send_email_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def load_config() -> dict:
    with open(Path("config.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def run_hunter() -> None:
    load_dotenv()
    init_db()
    config = load_config()

    logging.info("Iniciando varredura: %s", config["project_name"])
    found_listings = search_and_filter_listings(config)
    logging.info("Total de anúncios válidos retornados pela IA: %d", len(found_listings))

    new_listings = []
    for ad in found_listings:
        # Dupla checagem de segurança via código além do prompt
        if "olx.com.br" in ad.url.lower():
            continue
        if ad.price > config["target"]["max_price"]:
            continue

        if not is_ad_seen(ad.url):
            new_listings.append(ad)
            mark_ad_as_seen(ad.url, ad.title, ad.price, ad.source)

    if new_listings:
        logging.info("Enviando alerta com %d anúncio(s) inédito(s)...", len(new_listings))
        send_email_alert(new_listings)
        logging.info("E-mail disparado com sucesso!")
    else:
        logging.info("Nenhum anúncio novo encontrado nesta execução.")


if __name__ == "__main__":
    run_hunter()