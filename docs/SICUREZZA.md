# Sicurezza e avvertenze

**Alvea è un progetto didattico, NON un dispositivo medico.**

- Non è certificato e **non deve essere usato** per decisioni sulla salute di un
  bambino o di alcuna persona. Non sostituisce la sorveglianza di un adulto né
  un dispositivo medico approvato (es. saturimetro clinico).
- I valori, le soglie per l'asma (SpO2, frequenza respiratoria) e gli allarmi hanno scopo **dimostrativo** (laboratorio).
- **Alimentazione:** usare solo alimentazione a batteria (singola cella LiPo) o power bank a bassa tensione (3.3–5 V).
  Non collegare mai l'elettronica indossata alla rete elettrica 220 V.
- **Sensori (MAX30102, AD8232, DS18B20):** uso a scopo di esperimento su soggetti
  consenzienti e in salute. Non utilizzare elettrodi ECG su persone con pacemaker o altri
  dispositivi impiantati. Non applicare il prototipo hardware a pazienti pediatrici reali.
- **Privacy (RQ-20):** le credenziali Wi-Fi risiedono in `secrets.py`, mentre le variabili d'ambiente del server in `.env`. Entrambi i file sono esclusi dal repository pubblico. Tutto il traffico clinico transita nella rete locale: nessun dato sanitario viene inviato a servizi cloud pubblici di terze parti.
