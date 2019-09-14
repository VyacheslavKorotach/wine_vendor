import json
from typing import Optional

from paho.mqtt.client import MQTTMessage


# TODO: move 'give_out_goods' here
class WineMQTTClient:
    def __init__(self):
        pass

    @staticmethod
    def decode(msg: MQTTMessage) -> Optional[dict]:
        try:
            json_string = msg.payload.decode('utf8')
            try:
                json_object = json.loads(json_string)
                return json_object
            except ValueError:
                return None
        except UnicodeDecodeError:
            return None
