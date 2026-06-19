# Sicurezza e avvertenze

**Alvea è un progetto didattico, NON un dispositivo medico.**

- Non è certificato e **non deve essere usato** per decisioni sulla salute di un
  neonato o di alcuna persona. Non sostituisce la sorveglianza di un adulto né
  un dispositivo medico approvato.
- I valori, le soglie e gli allarmi hanno scopo **dimostrativo** (laboratorio).
- **Alimentazione:** solo tramite USB del PC o power bank a bassa tensione (3.3–5 V).
  Non collegare mai l'elettronica indossata alla rete elettrica 220 V.
- **AD8232 / elettrodi:** uso a scopo di esperimento su soggetti adulti
  consenzienti e in salute. Non utilizzare su persone con pacemaker o altri
  dispositivi impiantati. Non applicare a neonati reali.
- **Privacy (RQ-20):** le credenziali Wi-Fi stanno in `secrets.py`, escluso dal
  repository. Tutto il traffico resta nella rete locale: nessun dato sanitario
  viene inviato a servizi esterni o in cloud.

---

## Autenticazione, ruoli e autorizzazioni (RBAC)

L'API richiede autenticazione per tutti gli endpoint sui dati. Il flusso:

1. `POST /register` — crea un account. Campo opzionale `role` (default `caregiver`).
2. `POST /login` — restituisce un **JWT** (HS256) con scadenza configurabile
   (`ACCESS_TOKEN_EXPIRE_MINUTES`). La password è salvata con hash **bcrypt**
   (mai in chiaro).
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

Questo garantisce il requisito *"ogni utente visualizza esclusivamente i propri dati"*.

> ⚠️ **Limitazione nota (didattica):** i canali realtime `/ws/live` e `/sse/live`
> trasmettono in broadcast la telemetria di tutti i device e **non applicano**
> ancora autenticazione/filtro per utente. Per un uso reale andrebbero
> autenticati e filtrati per proprietà (vale la stessa regola REST). Sul mio
> perimetro l'isolamento è garantito sugli endpoint REST.

## Gestione alert (core)

Ogni allarme generato (`backend/app/alerts.py`) contiene i campi richiesti:
**paziente** (`device_id`), **parametro** (`bpm` | `temperature` | `contact`),
**descrizione** (`message`), **livello di gravità** (`severity`:
`warning` | `critical` | `technical`) e **timestamp** (`ts`).
Regola d'oro: con fascia staccata si emette solo un allarme **tecnico**, mai
allarmi fisiologici (eviterebbe falsi positivi).

## Soglie configurabili dal medico

Le soglie cliniche sono per-device (`DeviceThreshold`) e modificabili solo dal
medico via `PUT /devices/{id}/thresholds`. In assenza di una configurazione
dedicata si usano i default di `config.DEFAULT_THRESHOLDS`. La pipeline MQTT
applica automaticamente le soglie del device in fase di valutazione.

## Scheda paziente e anamnesi

`GET/PUT /devices/{id}/patient` gestiscono la scheda del neonato: dati
anagrafici più informazioni cliniche (**patologie note**, **farmaci**,
**allergie**). Accessibile al proprietario e al medico.

## Audit log (tracciamento operazioni rilevanti)

Tutte le operazioni sensibili sono registrate in modo append-only
(`AuditLog`): `login` / `login_failed`, `register`, `claim_device`,
`read_history`, `read_alerts`, `update_thresholds`, `read_patient_record`,
`update_patient_record`. Ogni voce traccia **chi** (username/ruolo), **cosa**
(azione), **su cosa** (device), **quando** (timestamp) e l'**IP** del client.
Il registro è consultabile solo dal medico via `GET /audit`.

## Note operative

- In produzione impostare `SECRET_KEY` (variabile d'ambiente) con un valore
  robusto e casuale: il default `CAMBIAMI_IN_PRODUZIONE` è solo per sviluppo.
- Configurare `CORS_ORIGINS` con le origini effettive: con `*` (default dev) le
  credenziali via cookie sono disattivate per conformità alla spec CORS
  (l'auth usa comunque header Bearer).
- L'auto-registrazione con ruolo `medico` è ammessa **solo a scopo didattico**;
  in un contesto reale gli account medico andrebbero creati da un amministratore.
