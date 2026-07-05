# Sicurezza e avvertenze

**Alvea è un progetto didattico, NON un dispositivo medico.**

- Non è certificato e **non deve essere usato** per decisioni sulla salute di un
  bambino o di alcuna persona. Non sostituisce la sorveglianza di un adulto né
  un dispositivo medico approvato (es. saturimetro clinico).
- **Alimentazione:** usare solo alimentazione a batteria (singola cella LiPo) o power bank a bassa tensione (3.3–5 V).
  Non collegare mai l'elettronica indossata alla rete elettrica 220 V.
- **Sensori (AD8232 per ECG, termistore NTC di precisione per la temperatura):** uso a scopo di esperimento su soggetti
  consenzienti e in salute. Non utilizzare elettrodi ECG su persone con pacemaker o altri
  dispositivi impiantati.
- **Privacy (RQ-20):** le credenziali Wi-Fi vanno inserite in `firmware/secrets.py` (copiandolo dal template `firmware/secrets_example.py`, che contiene solo placeholder), mentre le variabili d'ambiente del server vanno in `docker-stack/.env` (copiato da `.env.example`). Entrambi i file (`secrets.py` e `.env`, non i rispettivi template) sono esclusi dal repository tramite `.gitignore`: vanno creati localmente. Tutto il traffico clinico transita nella rete locale: nessun dato sanitario viene inviato a servizi cloud pubblici di terze parti.

---

## Autenticazione, ruoli e autorizzazioni (RBAC)

L'API richiede autenticazione per tutti gli endpoint sui dati. Il flusso:

1. `POST /register` — crea un account. Campo opzionale `role` (default `caregiver`).
2. `POST /login` — restituisce un **JWT** (HS256) con scadenza configurabile
   (`ACCESS_TOKEN_EXPIRE_MINUTES`) e, per comodità dell'app, anche `role` e
   `device_id` principale. La password è salvata con hash **bcrypt** (mai in chiaro).
3. Le richieste successive includono l'header `Authorization: Bearer <token>`.

### Ruoli

| Ruolo | Mappatura requisito | Permessi |
|-------|---------------------|----------|
| `caregiver` | lato **Paziente** | Vede e gestisce **solo i propri** device (scheda paziente inclusa). |
| `medico` | **Medico** | Vede **tutti** i pazienti, **configura le soglie** cliniche e consulta l'**audit log**. |

### Controllo di proprietà (data isolation)

Ogni accesso ai dati di un device passa dalla dipendenza `authorized_device()`:

- `medico` → accesso a qualsiasi device;
- `caregiver` → consentito **solo** se è il proprietario (`owner_id`), altrimenti
  `403 Forbidden`; device inesistente → `404`.

L'isolamento vale **anche sul canale realtime**: `/ws/live` (WebSocket) e
`/sse/live` (SSE) richiedono un JWT valido come query string (`?token=...`,
come fa l'app) e una connessione senza token o con token non valido viene
rifiutata. Dal token il backend ricava l'ambito di visibilità e filtra il
broadcast: il `caregiver` riceve in tempo reale **solo** la telemetria dei
propri device, il `medico` quella di tutti. Così un genitore non può ricevere,
nemmeno via WebSocket, le letture del figlio di un altro utente.

## Gestione alert (core)

Ogni allarme generato (`backend/app/alerts.py`) contiene i campi: **paziente** (`device_id`), **parametro** (`respiration_rate` | `bpm` |
`skin_temperature` | `contact`), **descrizione** (`message`), **livello di
gravità** (`severity`: `warning` | `critical` | `technical`) e **timestamp** (`ts`).
La regola antipanico: con sensore staccato (o `device_status` di errore) si
emette solo un allarme **tecnico**, mai allarmi fisiologici, per evitare falsi
positivi. Condizioni cliniche rilevate: **tachipnea/bradipnea** (frequenza
respiratoria da EDR), **tachicardia/bradicardia** (BPM) e **febbre/ipotermia**
(temperatura cutanea). Gli alert hardware del firmware (batteria, guasto sensore)
arrivano sul topic `.../alerts` e vengono normalizzati nello stesso formato.

## Soglie configurabili dal medico

Le soglie cliniche sono per-device (`DeviceThreshold`) e modificabili solo dal
medico via `PUT /devices/{id}/thresholds` (validazione di coerenza:
`crit_low <= warn_low <= warn_high <= crit_high`). In assenza di una
configurazione dedicata si usano i default di `config.DEFAULT_THRESHOLDS`. La
pipeline MQTT applica automaticamente le soglie del device in fase di valutazione.

## Scheda paziente e anamnesi

`GET/PUT /devices/{id}/patient` gestiscono la scheda del paziente (bambino): dati
anagrafici più informazioni cliniche (**patologie note**, **farmaci**,
**allergie**). Accessibile al proprietario e al medico.

## Audit log (tracciamento operazioni rilevanti)

Tutte le operazioni sensibili sono registrate in modo append-only (`AuditLog`):
`login` / `login_failed`, `register`, `claim_device`, `read_history`,
`read_alerts`, `update_thresholds`, `read_patient_record`,
`update_patient_record`, `send_command`. Ogni voce traccia **chi** (username/ruolo),
**cosa** (azione), **su cosa** (device), **quando** (timestamp) e l'**IP** del
client. Il registro è consultabile solo dal medico via `GET /audit`.

## Note operative

- In produzione impostare `SECRET_KEY` (variabile d'ambiente) con un valore
  robusto e casuale: il default `CAMBIAMI_IN_PRODUZIONE` è solo per sviluppo.
- Configurare `CORS_ORIGINS` con le origini effettive: con `*` (default dev) le
  credenziali via cookie sono disattivate per conformità alla spec CORS
  (l'auth usa comunque header Bearer).
- L'auto-registrazione con ruolo `medico` è ammessa **solo a scopo didattico**;
  in un contesto reale gli account medico andrebbero creati da un amministratore.
