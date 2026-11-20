#!/usr/bin/env python3
"""Monitora la disponibilità di più prodotti HPE e avvisa su Telegram.

Solo libreria standard (nessuna installazione necessaria).
- Elenco prodotti: urls.txt (un link per riga, righe con # ignorate)
- Stato salvato in state.json (un valore per ogni link)
Variabili d'ambiente: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
"""
import html as htmllib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

URLS_FILE = os.environ.get("URLS_FILE", "urls.txt")
STATE_FILE = os.environ.get("STATE_FILE", "state.json")
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; stock-monitor/1.0)"}


def load_urls():
    with open(URLS_FILE, encoding="utf-8") as f:
        lines = [line.strip() for line in f]
    return [ln for ln in lines if ln and not ln.startswith("#")]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def get_meta(page: str, prop: str):
    for pattern in (
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']*)["\']',
        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']{re.escape(prop)}["\']',
    ):
        m = re.search(pattern, page, re.I)
        if m:
            return htmllib.unescape(m.group(1)).strip()
    return None


def parse_availability(page: str):
    """Ritorna 'in_stock', 'out_of_stock' oppure None se non riconosciuto."""
    value = get_meta(page, "product:availability")
    if value is None:
        return None
    value = value.lower()
    if value in ("oos", "out of stock", "outofstock", "sold out"):
        return "out_of_stock"
    if value in ("instock", "in stock", "in_stock", "available"):
        return "in_stock"
    return None


def parse_title(page: str, fallback: str) -> str:
    title = get_meta(page, "og:title") or fallback
    return re.sub(r"\s+[—-]\s+HPE\s*$", "", title)


def notify(text: str) -> None:
    if not TOKEN or not CHAT_ID:
        print("Telegram non configurato, messaggio:", text)
        return
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        json.load(resp)


def read_state() -> dict:
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def main() -> int:
    urls = load_urls()
    state = read_state()
    changed = False

    for i, url in enumerate(urls):
        if i:
            time.sleep(2)  # gentili col sito
        try:
            page = fetch(url)
        except Exception as exc:  # rete, blocco del sito, ecc.
            print(f"Errore su {url}: {exc}")
            continue

        status = parse_availability(page)
        title = parse_title(page, url)
        if status is None:
            print(f"Stato non riconosciuto per {title}: la pagina potrebbe essere cambiata.")
            continue

        previous = state.get(url, "")
        print(f"{title}: {status} (precedente: {previous or 'nessuno'})")

        if status == "in_stock" and previous != "in_stock":
            prefix = "Già disponibile" if previous == "" else "Tornato disponibile"
            try:
                notify(f"{prefix}: {title}\n{url}")
            except Exception as exc:
                # non salvare lo stato: riproverà al prossimo giro
                print(f"Invio Telegram fallito: {exc}")
                continue

        if status != previous:
            state[url] = status
            changed = True

    if changed:
        write_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
