# transport_ble.py - Periferica BLE che invia la telemetria via NOTIFY.
#
# Basato su ble_notify_es2.py (versione incapsulata, non bloccante): la logica
# pesante NON va mai dentro l'IRQ, altrimenti il central si disconnette.
from micropython import const
import bluetooth
import json

import config

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)


class BLEPeripheral:
    def __init__(self, name=None):
        self.name = name or config.BLE_NAME
        self.conn_handle = None

        self.SERVICE_UUID = bluetooth.UUID(config.BLE_SERVICE_UUID)
        self.CHAR_UUID = bluetooth.UUID(config.BLE_CHAR_UUID)

        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self._register_services()
        self.ble.irq(self._irq_handler)
        self._start_advertising()

    def _register_services(self):
        char = (self.CHAR_UUID, bluetooth.FLAG_NOTIFY)
        service = (self.SERVICE_UUID, (char,))
        ((self.char_handle,),) = self.ble.gatts_register_services((service,))

    def _irq_handler(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            self.conn_handle, _, _ = data
            print("BLE: central connesso")
        elif event == _IRQ_CENTRAL_DISCONNECT:
            print("BLE: central disconnesso")
            self.conn_handle = None
            self._start_advertising()   # torna visibile

    def _adv_payload(self):
        p = bytearray()
        p += b'\x02\x01\x06'                                  # flags
        p += bytes([len(self.name) + 1, 0x09]) + self.name.encode()  # nome
        return p

    def _start_advertising(self):
        self.ble.gap_advertise(100_000, self._adv_payload())
        print("BLE: advertising come", self.name)

    def is_connected(self):
        return self.conn_handle is not None

    def send_json(self, payload_dict):
        """Invia un dizionario come stringa JSON via NOTIFY (se connesso)."""
        if self.conn_handle is None:
            return False
        msg = json.dumps(payload_dict)
        self.ble.gatts_notify(self.conn_handle, self.char_handle, msg)
        return True