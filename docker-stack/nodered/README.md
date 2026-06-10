# Node-RED — PulseGuard-Baby

`data/flows.json` viene caricato automaticamente all'avvio del container.

## Cosa fa il flow
1. **`baby/data`** (MQTT in) — sottoscrive `pulseguard/baby/data` sul broker `mosquitto`.
2. **parse JSON** — converte il payload testuale in oggetto.
3. **Soglie + Line Protocol** (function) — applica le soglie cliniche, gestisce
   l'anti-falso-allarme della fascia staccata (debounce 5 s) e costruisce la
   riga in *line protocol* per InfluxDB.
4. **InfluxDB write** (http request) — `POST /api/v2/write` sul bucket `vitals`.
   Il token arriva dalla variabile d'ambiente `INFLUX_TOKEN` (impostata nel
   `docker-compose.yml`): **nessun nodo aggiuntivo da installare**.
5. **`baby/alerts`** (MQTT out) — ripubblica gli allarmi su `pulseguard/baby/alerts`.

## Note
- Se cambi il token Influx, aggiorna `INFLUX_ADMIN_TOKEN` nel `.env`: il flow lo
  legge da `env.get("INFLUX_TOKEN")`, non serve toccare i nodi.
- Apri l'editor su <http://localhost:1880> per vedere il flow e i debug.
- In alternativa puoi usare il nodo `node-red-contrib-influxdb` dalla palette;
  il flow attuale non lo richiede per restare auto-contenuto.
