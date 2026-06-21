// src/context/TelemetryContext.js
//
// Stato condiviso di telemetria per tutti i pazienti/device, coerente con
// il modello relazionale Caregiver 1:N Device 1:N {Reading, Alert}
// (Relazione, Sez. 4). Alimenta sia la vista Caregiver (un solo paziente)
// sia la vista Medico (lista multi-paziente).
//
// In modalita' simulata (default) avanza un proprio loop locale ogni
// secondo, replicando la frequenza di pubblicazione di default del
// firmware (DEFAULT_PUBLISH_PERIOD_S = 1, modificabile via comando come
// in main_real_mqtt.py). In modalita' 'backend' si sottoscrive invece al
// canale realtime reale (WS /ws/live).

import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { createSimulatedDevice, tickDevice, deriveStatusInfo } from '../services/simulator';
import { isSimulated, sendCommand, api } from '../services/dataSource';
import { useAuth } from './AuthContext';

const TelemetryContext = createContext(null);

const SEED_PATIENTS = [
  {
    id: 'pt1',
    name: 'Sofia',
    ageBand: 'prescolare',
    deviceId: 'ALVEA_04',
    patientId: 'p_0007',
    isCaregiverPatient: true,
    profile: {
      asma: 'Asma lieve persistente (GINA step 2)',
      allergie: 'Acari della polvere, nessuna allergia alimentare nota',
      terapia: 'Broncodilatatore al bisogno (salbutamolo), nessuna terapia di fondo attuale',
      medico: 'Dott.ssa R. Iacoviello — Pneumologia pediatrica',
      note: 'Riacutizzazioni stagionali in autunno; buona aderenza alla cavigliera',
    },
  },
  {
    id: 'pt2',
    name: 'Marco',
    ageBand: 'scolare',
    deviceId: 'ALVEA_07',
    patientId: 'p_0012',
    isCaregiverPatient: false,
    profile: {
      asma: 'Asma moderata persistente (GINA step 3)',
      allergie: 'Pollini graminacee, dermatite atopica',
      terapia: "Corticosteroide inalatorio + LABA, piano d'azione scritto attivo",
      medico: 'Dott.ssa R. Iacoviello — Pneumologia pediatrica',
      note: 'Sport agonistico (nuoto); monitoraggio anche notturno',
    },
  },
  {
    id: 'pt3',
    name: 'Giulia',
    ageBand: 'prescolare',
    deviceId: 'ALVEA_11',
    patientId: 'p_0019',
    isCaregiverPatient: false,
    profile: {
      asma: 'Wheezing ricorrente in valutazione, asma non confermata',
      allergie: 'Nessuna nota',
      terapia: 'Broncodilatatore al bisogno durante episodi febbrili',
      medico: 'Dott. A. Crisci — Pediatria generale',
      note: 'Fascia prescolare: soglie cliniche più permissive da matrice per età (design, non ancora attivo nel prototipo)',
    },
  },
];

function buildInitialDevices() {
  const map = {};
  SEED_PATIENTS.forEach((p) => {
    map[p.id] = {
      ...p,
      ...createSimulatedDevice({ id: p.id, deviceId: p.deviceId, patientId: p.patientId, ageBand: p.ageBand }),
    };
  });
  return map;
}

export function TelemetryProvider({ children }) {
  const { session } = useAuth();
  const [devices, setDevices] = useState(buildInitialDevices);
  const tickCountRef = useRef(0);

  // Applica nome/fascia d'eta' del bambino registrato dal caregiver al
  // device "pt1" (associazione device_id <-> patient_id del caregiver,
  // Relazione Sez. 4.1). Si attiva quando l'utente effettua login/registrazione.
  useEffect(() => {
    if (session?.role === 'caregiver' && session.childName) {
      setDevices((prev) => ({
        ...prev,
        pt1: {
          ...prev.pt1,
          name: session.childName,
          ageBand: session.ageBand || prev.pt1.ageBand,
        },
      }));
    }
  }, [session]);

  // Loop principale di simulazione: avanza ogni device secondo il proprio
  // publishPeriod, come fa il firmware con current_publish_period.
  useEffect(() => {
    if (!isSimulated) return undefined;

    // Pre-popola qualche lettura iniziale per non partire con grafici vuoti.
    setDevices((prev) => {
      const next = { ...prev };
      for (let i = 0; i < 15; i++) {
        Object.keys(next).forEach((key) => {
          next[key] = { ...tickDevice({ ...next[key], alerts: [...next[key].alerts] }) };
        });
      }
      return next;
    });

    const interval = setInterval(() => {
      tickCountRef.current += 1;
      setDevices((prev) => {
        const next = { ...prev };
        Object.keys(next).forEach((key) => {
          const device = next[key];
          if (tickCountRef.current % device.publishPeriod === 0) {
            next[key] = { ...tickDevice({ ...device, alerts: [...device.alerts] }) };
          }
        });
        return next;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Modalita' backend reale: sottoscrizione al canale WebSocket /ws/live.
  useEffect(() => {
    if (isSimulated || !session?.token) return undefined;

    const unsubscribe = api.subscribeLiveTelemetry({
      token: session.token,
      onMessage: (payload) => {
        setDevices((prev) => {
          const matchKey = Object.keys(prev).find(
            (key) => prev[key].deviceId === payload.device_id
          );
          if (!matchKey) return prev;
          return {
            ...prev,
            [matchKey]: {
              ...prev[matchKey],
              state: {
                ...prev[matchKey].state,
                fr: payload.respiration_rate,
                bpm: payload.bpm,
                spo2: payload.spo2,
                temp: payload.skin_temperature,
                battery: payload.battery_pct,
                contact: payload.sensor_contact,
                status: payload.device_status,
              },
              history: [
                {
                  t: new Date(payload.timestamp * 1000),
                  fr: payload.respiration_rate,
                  bpm: payload.bpm,
                  spo2: payload.spo2,
                  temp: payload.skin_temperature,
                  status: payload.device_status,
                },
                ...prev[matchKey].history,
              ].slice(0, 60),
            },
          };
        });
      },
      onError: () => {
        // Connessione realtime non disponibile: l'app resta utilizzabile
        // mostrando l'ultimo stato noto, senza bloccare l'interfaccia.
      },
    });

    return unsubscribe;
  }, [session?.token]);

  /** Invia un comando di riconfigurazione al device (frequenza di
   * pubblicazione + associazione patient_id), come da
   * alvea/devices/<device_id>/commands e main_real_mqtt.py. */
  async function updateDeviceConfig(deviceKey, { publishPeriodS, patientId }) {
    const device = devices[deviceKey];
    if (!device) return;

    await sendCommand(device.deviceId, { publishPeriodS, patientId }, session?.token);

    setDevices((prev) => ({
      ...prev,
      [deviceKey]: {
        ...prev[deviceKey],
        publishPeriod: publishPeriodS || prev[deviceKey].publishPeriod,
        patientId: patientId !== undefined ? patientId : prev[deviceKey].patientId,
      },
    }));
  }

  const caregiverDeviceKey = Object.keys(devices).find((k) => devices[k].isCaregiverPatient) || 'pt1';

  const value = {
    devices,
    deviceList: Object.values(devices),
    caregiverDevice: devices[caregiverDeviceKey],
    updateDeviceConfig,
    deriveStatusInfo,
  };

  return <TelemetryContext.Provider value={value}>{children}</TelemetryContext.Provider>;
}

export function useTelemetry() {
  const ctx = useContext(TelemetryContext);
  if (!ctx) throw new Error('useTelemetry deve essere usato dentro un TelemetryProvider');
  return ctx;
}
