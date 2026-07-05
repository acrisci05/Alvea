# shell_log.py - Riga di log compatta e leggibile per la shell di Thonny.

def format_shell_line(reading, status_string):
    """Costruisce una riga compatta leggibile a partire dal dict di
    telemetria """
    bpm = reading.get("bpm", 0.0) or 0.0
    temp = reading.get("skin_temperature", 0.0) or 0.0
    resp = reading.get("respiration_rate", 0.0) or 0.0
    batt = reading.get("battery_pct")
    contact = reading.get("sensor_contact", False)

    batt_str = "{:.0f}%".format(batt) if batt is not None else "N/D"
    contact_str = "OK" if contact else "NO-CONTACT"

    return "BPM:{:5.1f}  Temp:{:5.1f}C  Resp:{:5.1f}  Batt:{:>5}  Contatto:{:<10}  [{}]".format(
        bpm, temp, resp, batt_str, contact_str, status_string
    )

def log_reading(reading, status_string):
    print(format_shell_line(reading, status_string))