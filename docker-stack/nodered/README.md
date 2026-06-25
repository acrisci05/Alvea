# Node-RED — Alvea

`data/flows.json` viene caricato automaticamente all'avvio del container.

## Cosa fa il flow
1. **`alvea/devices/+/telemetry`** (MQTT in) — sottoscrive il topic di
   telemetria di tutti i device sul broker `mosquitto`.
2. **parse JSON** — converte il payload testuale in oggetto.
3. **Soglie + Line Protocol** (function) — applica le soglie cliniche, gestisce
   l'anti-falso-allarme della fascia staccata (debounce 5 s) e costruisce la
   riga in *line protocol* per InfluxDB.
4. **InfluxDB write** (http request) — `POST /api/v2/write` sul bucket `vitals`.
   Il token arriva dalla variabile d'ambiente `INFLUX_TOKEN` (impostata nel
   `docker-compose.yml`): **nessun nodo aggiuntivo da installare**.
5. **`alvea/devices/+/alerts`** (MQTT out) — ripubblica gli allarmi generati
   dalle soglie (oltre a quelli già pubblicati direttamente dal firmware sullo
   stesso topic).

## Note
- Cambiando il token Influx, deve essere aggiornato `INFLUX_ADMIN_TOKEN` nel `.env` perché il flow lo
  legge da `env.get("INFLUX_TOKEN")`.
- Aprire l'editor su <http://localhost:1880> per vedere il flow e i debug.
- In alternativa, usare il nodo `node-red-contrib-influxdb` dalla palette.
