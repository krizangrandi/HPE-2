#!/usr/bin/env python3
"""Monitora la disponibilità di un prodotto HPE e avvisa su Telegram.

Solo libreria standard (nessuna installazione necessaria).
Variabili d'ambiente richieste: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
Opzionali: URL (default: il kit supporti motore), STATE_FILE (default: state.txt)
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

URL = os.environ.get(
    "URL",
    "https://www.hpeauto.co.uk/shop/p/xdnts8h6um1jmejixy7rtldm2qi0y7",
)
STATE_FILE = os.environ.get("STATE_FILE", "state.txt")
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; stock-monitor/1.0)"}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_availability(html: str):
    """Ritorna 'in_stock', 'out_of_stock' oppure None se non riconosciuto."""
    m = re.search(
        r'<meta[^>]+property=["\']product:availability["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.I,
    )
    if not m:
        # attributi in ordine inverso: content prima di property
        m = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']product:availability["\']',
            html,
            re.I,
        )
    if not m:
        return None
    value = m.group(1).strip().lower()
    if value in ("oos", "out of stock", "outofstock", "sold out"):
        return "out_of_stock"
    if value in ("instock", "in stock", "in_stock", "available"):
        return "in_stock"
    return None


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


def read_state() -> str:
    try:
        with open(STATE_FILE) as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def write_state(value: str) -> None:
    with open(STATE_FILE, "w") as f:
        f.write(value + "\n")


def main() -> int:
    try:
        status = parse_availability(fetch(URL))
    except Exception as exc:  # rete, blocco del sito, ecc.
        print("Errore nel controllo:", exc)
        return 0  # non far fallire il workflow per un errore temporaneo

    if status is None:
        print("Stato non riconosciuto: la pagina potrebbe essere cambiata.")
        return 0

    previous = read_state()
    print(f"Stato attuale: {status} (precedente: {previous or 'nessuno'})")

    if status == "in_stock" and previous != "in_stock":
        notify(f"Il prodotto è tornato disponibile!\n{URL}")
    if status != previous:
        write_state(status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
