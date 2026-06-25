# Sicurezza e avvertenze

**Alvea è un progetto didattico, NON un dispositivo medico.**

- Non è certificato e **non deve essere usato** per decisioni sulla salute di un
  bambino o di alcuna persona. Non sostituisce la sorveglianza di un adulto né
  un dispositivo medico approvato (es. saturimetro clinico).
- I valori, le soglie per l'asma (frequenza respiratoria via EDR, BPM) e gli allarmi hanno scopo **dimostrativo** (laboratorio).
- **Alimentazione:** usare solo alimentazione a batteria (singola cella LiPo) o power bank a bassa tensione (3.3–5 V).
  Non collegare mai l'elettronica indossata alla rete elettrica 220 V.
- **Sensori (AD8232 per ECG, termistore NTC di precisione per la temperatura):** uso a scopo di esperimento su soggetti
  consenzienti e in salute. Non utilizzare elettrodi ECG su persone con pacemaker o altri
  dispositivi impiantati. Non applicare il prototipo hardware a pazienti pediatrici reali.
- **Privacy (RQ-20):** le credenziali Wi-Fi vanno inserite in `firmware/secrets.py` (copiandolo dal template `firmware/secrets_example.py`, che contiene solo placeholder), mentre le variabili d'ambiente del server vanno in `docker-stack/.env` (copiato da `.env.example`). Entrambi i file (`secrets.py` e `.env`, non i rispettivi template) sono esclusi dal repository tramite `.gitignore`: vanno creati localmente e non vanno mai committati. Tutto il traffico clinico transita nella rete locale: nessun dato sanitario viene inviato a servizi cloud pubblici di terze parti.
