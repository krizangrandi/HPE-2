# Monitor disponibilità HPE (GitHub Actions + Telegram)

Controlla ogni ~10 minuti le pagine prodotto di hpeauto.co.uk e manda un
messaggio Telegram quando un articolo passa da esaurito a disponibile.

## File nel repository
- `monitor.py`  -> script (solo libreria standard Python)
- `urls.txt`    -> elenco dei link da monitorare (uno per riga, `#` = ignorata)
- `.github/workflows/monitor.yml` -> workflow GitHub Actions
- `state.json`  -> creato e aggiornato in automatico dal workflow

## Configurazione
1. Bot Telegram: @BotFather -> /newbot -> copia il token.
   Scrivi al bot, poi apri https://api.telegram.org/bot<TOKEN>/getUpdates
   per leggere il chat id.
2. GitHub -> Settings -> Secrets and variables -> Actions -> Repository secrets:
   `TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID`.
3. Il cron interno di GitHub è inaffidabile: l'avvio puntuale è fatto da
   cron-job.org con una richiesta POST ogni 10 minuti a:
   https://api.github.com/repos/<utente>/<repo>/actions/workflows/monitor.yml/dispatches
   - Body: {"ref":"main"}
   - Header:
       Authorization: Bearer <TOKEN_GITHUB>
       Accept: application/vnd.github+json
       Content-Type: application/json
       X-GitHub-Api-Version: 2022-11-28
   - Il token GitHub è "fine-grained", solo sul repo, permesso Actions: Read and write.
   - Risposta attesa: 204 No Content.

## Promemoria
- Segna la scadenza del token GitHub: alla scadenza il monitor si ferma
  (cron-job.org mostrerà errori 401).
- Cancellando `state.json`, al giro successivo riceverai un messaggio
  "Già disponibile" per ogni articolo in stock.
- Per le pagine con varianti (es. Road/Track, K20/K24) lo script guarda lo
  stato generale della pagina.
