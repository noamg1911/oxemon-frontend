from typing import List, Dict
from icd_converter import icd
from dataclasses import dataclass

def _create_map(conversion_list: List[dict]) -> Dict[int, str]:
    return {
        str(obj["hash"]): obj["string"]
        for obj in conversion_list
    }

# TODO: Handle duplicates
def create_conversion_map(oxemon_dictionary: dict) -> Dict[str, str]:
    module_id_map = _create_map(oxemon_dictionary["module_ids"])
    event_id_map = _create_map(oxemon_dictionary["event_ids"])
    misc_map = _create_map(oxemon_dictionary["misc_conversions"])

    return dict(**module_id_map, **event_id_map, **misc_map)


@dataclass
class EventUpdate:
    module_name: str
    event_name: str
    value: int


def convert_incoming_message(*, message: bytes, conversion_map: Dict[str, str]) -> EventUpdate:
    message = icd.read_message(message)

    body = message[1]
    if isinstance(body, icd.EmitCounter):
        value = body.counter_value.value
    elif isinstance(body, icd.EmitLabel):
        value = body.label.value
    
    try:
        module_name = conversion_map[str(message[icd.EmitHeader].module_id.value)]
    except KeyError as e:
        raise ValueError("Unknown module id") from e
    
    try:
        event_name = conversion_map[str(message[icd.EmitHeader].event_id.value)]
    except KeyError as e:
        raise ValueError("Unknown event id") from e
    
    return EventUpdate(
        module_name=module_name,
        event_name=event_name,
        value=value,
    )

