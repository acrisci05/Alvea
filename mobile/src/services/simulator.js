// src/services/simulator.js
//
// Simulatore di telemetria lato app, usato quando DATA_SOURCE_MODE === 'simulated'
// (vedi src/config.js). Replica fedelmente la logica del firmware:
//   - firmware/sensor_sim.py   -> generazione valori fisiologici e batteria
//   - firmware/alerts.py       -> AlertManager.check_fault / check_battery
//   - main_real_mqtt.py        -> principio anti-panico (sensor_contact=false
//                                  azzera i parametri clinici nel payload)
//
// Nessuna chiamata di rete viene effettuata qui: i dati restano in memoria
// nel dispositivo che esegue l'app, esattamente come fa il simulatore
// firmware quando eseguito in modalita' standalone (main_sim_mqtt.py).

import { THRESHOLDS, DEVICE_DEFAULTS, DEVICE_STATUS } from '../config';

function rand(min, max) {
  return Math.random() * (max - min) + min;
}

export function classify(value, thresholds) {
  if (value <= thresholds.critLow || value >= thresholds.critHigh) return 'critical';
  if (value <= thresholds.warnLow || value >= thresholds.warnHigh) return 'warning';
  return 'ok';
}

/** Crea lo stato iniziale di un device/paziente simulato. */
export function createSimulatedDevice({ id, deviceId, patientId, ageBand = 'prescolare' }) {
  return {
    id,
    deviceId,
    patientId,
    ageBand,
    publishPeriod: DEVICE_DEFAULTS.DEFAULT_PUBLISH_PERIOD_S,
    state: {
      bpm: 98,
      fr: 22,
      spo2: 97.2,
      temp: 36.7,
      battery: 84.5,
      contact: true,
      status: DEVICE_STATUS.OK,
    },
    history: [], // { t: Date, fr, bpm, spo2, temp, status }
    alerts: [],  // { t: Date, parametro, descrizione, gravita }
    faultStreaks: {},
    activeFaults: new Set(),
  };
}

/** Replica AlertManager.check_fault (alerts.py): un alert per transizione,
 * dopo ALERT_FAULT_STREAK_THRESHOLD letture consecutive della stessa
 * condizione, con un alert di risoluzione (INFO) quando la condizione cessa. */
function checkFault(device, conditionName, isFaulty, parametro, descrizione, gravita) {
  if (isFaulty) {
    device.faultStreaks[conditionName] = (device.faultStreaks[conditionName] || 0) + 1;
    if (
      device.faultStreaks[conditionName] >= DEVICE_DEFAULTS.ALERT_FAULT_STREAK_THRESHOLD &&
      !device.activeFaults.has(conditionName)
    ) {
      device.activeFaults.add(conditionName);
      pushAlert(device, parametro, descrizione, gravita);
    }
  } else {
    device.faultStreaks[conditionName] = 0;
    if (device.activeFaults.has(conditionName)) {
      device.activeFaults.delete(conditionName);
      const risolto = descrizione.replace('rilevato', 'risolto') + ' (RISOLTO)';
      pushAlert(device, parametro, risolto, 'INFO');
    }
  }
}

function pushAlert(device, parametro, descrizione, gravita) {
  device.alerts = [{ t: new Date(), parametro, descrizione, gravita }, ...device.alerts].slice(0, 30);
}

/** Avanza la simulazione di un tick (un ciclo di pubblicazione telemetria). */
export function tickDevice(device) {
  const roll = Math.random();
  const contactDrop = roll < 0.012; // ~1.2% di probabilita' di distacco per tick
  const clinicalEvent = roll >= 0.012 && roll < 0.045; // ~3.3% finestra di episodio lieve

  const wasContactLost = device.faultStreaks['sensor_contact_lost'] > 0 &&
    device.faultStreaks['sensor_contact_lost'] < 3;

  device.state.contact = !(contactDrop || wasContactLost);

  if (!device.state.contact) {
    // Principio anti-panico (Relazione, Sez. 5.4): azzeramento dei parametri
    // clinici, nessun falso allarme di distress da letture nulle.
    device.state.fr = 0;
    device.state.bpm = 0;
    device.state.spo2 = 0;
    device.state.temp = 0;
    device.state.status = DEVICE_STATUS.ERR_PPG_NO_CONTACT;
  } else if (clinicalEvent) {
    device.state.fr = rand(31, 36);
    device.state.bpm = rand(131, 145);
    device.state.spo2 = rand(91, 94);
    device.state.temp = rand(37.3, 38.0);
    device.state.status = DEVICE_STATUS.OK;
  } else {
    device.state.fr = rand(20, 26);
    device.state.bpm = rand(88, 108);
    device.state.spo2 = rand(96, 99);
    device.state.temp = rand(36.3, 37.0);
    device.state.status = DEVICE_STATUS.OK;
  }

  // Scarica batteria lineare con rollover, come sensor_sim.py.
  device.state.battery -= 0.08;
  if (device.state.battery < 0) device.state.battery = 100;

  checkFault(
    device, 'sensor_contact_lost', !device.state.contact,
    'sensor_contact', 'Caduta di contatto del sensore rilevata', 'WARNING'
  );
  checkFault(
    device, 'battery_low', device.state.battery < THRESHOLDS.batteryMinPct,
    'battery', `Batteria scarica rilevata (${device.state.battery.toFixed(0)}%)`, 'WARNING'
  );

  if (device.state.contact) {
    const frClass = classify(device.state.fr, THRESHOLDS.fr);
    const bpmClass = classify(device.state.bpm, THRESHOLDS.bpm);
    const tempClass = classify(device.state.temp, THRESHOLDS.temp);

    checkFault(
      device, 'fr_out_of_range', frClass !== 'ok', 'respiration_rate',
      frClass === 'critical'
        ? 'Distress respiratorio critico: frequenza respiratoria fuori soglia critica'
        : 'Scostamento della frequenza respiratoria oltre la soglia di warning',
      frClass === 'critical' ? 'CRITICAL' : 'WARNING'
    );
    checkFault(
      device, 'bpm_out_of_range', bpmClass !== 'ok', 'bpm',
      bpmClass === 'critical'
        ? 'Anomalia cardiaca critica (bradicardia/tachicardia severa)'
        : 'Scostamento della frequenza cardiaca oltre la soglia di warning',
      bpmClass === 'critical' ? 'CRITICAL' : 'WARNING'
    );
    checkFault(
      device, 'spo2_low', device.state.spo2 < THRESHOLDS.spo2Min,
      'spo2', 'Desaturazione: SpO2 sotto la soglia di allerta', 'WARNING'
    );
    checkFault(
      device, 'temp_out_of_range', tempClass !== 'ok', 'skin_temperature',
      tempClass === 'critical'
        ? 'Stato febbrile critico rilevato'
        : 'Temperatura cutanea fuori range di riferimento',
      tempClass === 'critical' ? 'CRITICAL' : 'WARNING'
    );
  }

  device.history = [
    {
      t: new Date(),
      fr: device.state.fr,
      bpm: device.state.bpm,
      spo2: device.state.spo2,
      temp: device.state.temp,
      status: device.state.status,
    },
    ...device.history,
  ].slice(0, 60);

  return device;
}

/** Calcola lo stato sintetico (verde/giallo/rosso) di un device, coerente
 * con la classificazione a 3 severita' effettivamente implementata
 * (Relazione, Sez. 5.3). */
export function deriveStatusInfo(device) {
  if (!device.state.contact) {
    return { level: 'warning', label: 'GIALLO · ' + device.state.status };
  }
  const frClass = classify(device.state.fr, THRESHOLDS.fr);
  const bpmClass = classify(device.state.bpm, THRESHOLDS.bpm);
  const tempClass = classify(device.state.temp, THRESHOLDS.temp);
  const spo2Low = device.state.spo2 < THRESHOLDS.spo2Min;

  if (frClass === 'critical' || bpmClass === 'critical' || tempClass === 'critical') {
    return { level: 'critical', label: 'ROSSO · CRITICAL' };
  }
  if (frClass === 'warning' || bpmClass === 'warning' || tempClass === 'warning' || spo2Low) {
    return { level: 'warning', label: 'ARANCIO · WARNING' };
  }
  return { level: 'ok', label: 'VERDE · SYSTEM_OK' };
}
