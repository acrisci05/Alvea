# Fase 3 — Diagramma dei Casi d'Uso

[cite_start]Attori: **Paziente / Caregiver** (attore primario), **Medico** (attore primario con permessi estesi) [cite: 39, 41][cite_start], e **Dispositivo ESP32** (attore secondario che immette telemetria e riceve configurazioni)[cite: 106].

```mermaid
flowchart LR
    subgraph attori_primari[" "]
        PAZ((Paziente / Caregiver))
        MED((Medico))
    end
    
    subgraph Sistema["Sistema Alvea (Asma Pediatrico)"]
        UC1(["Autenticazione (RBAC)"])
        UC2(["Visualizzare parametri asma in tempo reale"])
        UC3(["Ricevere e visualizzare alert"])
        UC4(["Consultare storico e statistiche"])
        UC5(["Configurare parametri e soglie device"])
        UC6(["Gestire scheda anamnestica"])
        UC7(["Inviare telemetria clinica"])
        UC8(["Ricevere comandi di configurazione"])
        UC9(["Valutare soglie e generare alert"])
    end
    
    subgraph attori_secondari[" "]
        ESP((Dispositivo ESP32))
    end

    PAZ --> UC1
    PAZ --> UC2
    PAZ --> UC3
    PAZ --> UC4

    MED --> UC1
    MED --> UC3
    MED --> UC4
    MED --> UC5
    MED --> UC6

    ESP --> UC7
    ESP --> UC8

    UC7 -. include .-> UC9
    UC9 -. extend .-> UC3
    UC5 -. include .-> UC8
```

## Specifica del caso d'uso principale — *Visualizzare in tempo reale* (UC3)

- **Attore primario:** Caregiver
- **Precondizioni:** L'utente è autenticato con il ruolo corretto (RQ-12) ; il dispositivo ESP32 è associato al paziente (RQ-14).
- **Flusso base:**
1. Il paziente apre la schermata Monitor dell'app mobile.
2. L'app apre il canale WebSocket/SSE verso il backend API.
3. L'ESP32 pubblica una lettura MQTT completa (SpO2, frequenza respiratoria, BPM, Temp).
4. Il backend la riceve, la storicizza su InfluxDB e la inoltra istantaneamente via WebSocket.
5. L'app aggiorna l'interfaccia grafica con i nuovi valori fisiologici.
- **Flusso alternativo A (fascia staccata):** se `sensor_contact == false`, il
  sistema mostra l'avviso tecnico e sospende la valutazione fisiologica (RQ-08).
- **Postcondizioni:** la lettura è persistita e visibile anche su Grafana (RQ-11).

> Mermaid non ha la notazione UML "a palloncino" nativa: questa è
> un'approssimazione fedele.
