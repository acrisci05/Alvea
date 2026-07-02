# transport_ble.py - Periferica BLE che invia la telemetria via NOTIFY e riceve comandi/configurazioni via WRITE.

from micropython import const
import bluetooth
import json

import config

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_MTU_EXCHANGED = const(21)

DESIRED_MTU = 256  # payload utile ~182 byte, sufficiente per il JSON attuale
DEFAULT_ATT_MTU = 23


class BLEPeripheral:
    def __init__(self, name=None, command_callback=None):
        self.name = name or config.BLE_NAME
        self.conn_handle = None
        # Funzione chiamata con il payload (bytes) scritto dall'app/medico
        self.command_callback = command_callback
        # MTU negoziato con il central (aggiornato da _IRQ_MTU_EXCHANGED).
        # Finche' non avviene lo scambio, va assunto il default BLE (23 byte).
        self.current_mtu = DEFAULT_ATT_MTU

        self.SERVICE_UUID = bluetooth.UUID(config.BLE_SERVICE_UUID)
        self.CHAR_UUID = bluetooth.UUID(config.BLE_CHAR_UUID)
        self.CHAR_CMD_UUID = bluetooth.UUID(config.BLE_CHAR_CMD_UUID)

        self.ble = bluetooth.BLE()
        self.ble.active(True)
        try:
            self.ble.config(mtu=DESIRED_MTU)
        except Exception as e:
            print("BLE: impossibile impostare MTU esteso, resto sul default:", e)
        self._register_services()
        self.ble.irq(self._irq_handler)
        self._start_advertising()

    def _register_services(self):
        char_tx = (self.CHAR_UUID, bluetooth.FLAG_NOTIFY)
        char_cmd = (self.CHAR_CMD_UUID, bluetooth.FLAG_WRITE)
        service = (self.SERVICE_UUID, (char_tx, char_cmd))
        ((self.char_handle, self.cmd_handle),) = self.ble.gatts_register_services((service,))

    def _irq_handler(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            self.conn_handle, _, _ = data
            print("BLE: central connesso")
        elif event == _IRQ_CENTRAL_DISCONNECT:
            print("BLE: central disconnesso")
            self.conn_handle = None
            self._start_advertising()   # torna visibile
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, attr_handle = data
            if attr_handle == self.cmd_handle and self.command_callback:
                payload = self.ble.gatts_read(self.cmd_handle)
                # La callback viene eseguita fuori dal contesto critico IRQ:
                # deve restare leggera (solo parsing JSON + aggiornamento variabili).
                self.command_callback(payload)
        elif event == _IRQ_MTU_EXCHANGED:
            conn_handle, mtu = data
            self.current_mtu = mtu
            print("BLE: MTU negoziato con il central:", mtu)

    def _adv_payload(self):
        p = bytearray()
        p += b'\x02\x01\x06'                                         # flags
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
        # Spazio utile per il payload ATT = MTU negoziato - 3 byte di header.
        usable_payload = self.current_mtu - 3
        if len(msg) > usable_payload:
            print(
                "BLE: ATTENZIONE - payload di", len(msg),
                "byte supera l'MTU corrente (", usable_payload,
                "byte utili). La notifica potrebbe arrivare troncata."
            )
        self.ble.gatts_notify(self.conn_handle, self.char_handle, msg)
        return True