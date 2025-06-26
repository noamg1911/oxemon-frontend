from hydration import Struct, UInt8, UInt32, UInt64, Enum, OpcodeField, Endianness, Vector


class EmitCounter(Struct):
    counter_value = UInt64


class EmitLabel(Struct):
    label = UInt32


class EmitLog(Struct):
    param_count = UInt8
    params = Vector("param_count", UInt64)


OPCODE_DICTIONARY = {
    EmitCounter: 0,
    EmitLabel: 1,
    EmitLog: 2,
}


class EmitHeader(Struct, endianness=Endianness.NativeEndian):
    module_id = UInt32
    event_id = UInt32
    event_type = OpcodeField(UInt8, OPCODE_DICTIONARY)


def read_message(data: bytes):
    header = EmitHeader.from_bytes(data)

    opposite_map = {value: struct for (struct, value) in OPCODE_DICTIONARY.items()}
    if header.event_type.value not in opposite_map:
        raise ValueError(f"Unexpected event type: {header.event_type}")
    
    body = opposite_map[header.event_type.value].from_bytes(data[len(header):])

    return header / body
