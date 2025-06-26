from typing import List, Dict
import icd
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


def resolve_log(log: str, params: List[int]) -> str:
    parts = log.split("{}")
    if len(parts) - 1 < len(params):
        raise ValueError("Number of placeholders does not match number of values.")
    elif len(parts) - 1 > len(params):
        # Padding with question marks
        params += ['?'] * len(parts) - 1 - len(params)

    result = ""
    for i in range(len(params)):
        result += parts[i] + f"{{{params[i]}}}"
    result += parts[-1]
    return result


@dataclass
class EventUpdate:
    event_type: str
    module_name: str
    event_name: str  # Or log
    value: int


def convert_incoming_message(*, message: bytes, conversion_map: Dict[str, str]) -> EventUpdate:
    message = icd.read_message(message)

    try:
        module_name = conversion_map[str(message[icd.EmitHeader].module_id.value)]
    except KeyError as e:
        raise ValueError("Unknown module id") from e
    
    try:
        event_name = conversion_map[str(message[icd.EmitHeader].event_id.value)]
    except KeyError as e:
        raise ValueError("Unknown event id") from e
    
    body = message[1]
    if isinstance(body, icd.EmitCounter):
        event_type = "counter"
        value = body.counter_value.value
    elif isinstance(body, icd.EmitLabel):
        event_type = "label"
        value = body.label.value
    elif isinstance(body, icd.EmitLog):
        event_type = "log"
        event_name = resolve_log(log=event_name, params=body.params.value)
        value = 0

    return EventUpdate(
        event_type=event_type,
        module_name=module_name,
        event_name=event_name,
        value=value,
    )

