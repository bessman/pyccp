import enum
import logging
import platform
import struct
import sys
import time

import can

from pyccp import CCPSlave, Element, SessionStatus

_logger = logging.getLogger(__name__)
# _logger.handlers = []
# _logger.filters = []
# _logger.setLevel(logging.DEBUG)
# loghand = logging.StreamHandler(sys.stdout)
# loghand.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
# # loghand.addFilter(lambda record: record.name.startswith(__name__))
# # loghand.addFilter(lambda record: record.name.startswith("pyccp"))
# _logger.addHandler(loghand)
# logging.basicConfig(level=logging.DEBUG)


class ActionService(enum.IntFlag):
    METADATA0 = 0x0010
    METADATA1 = 0x0011
    METADATA2 = 0x0012
    METADATA3 = 0x0013
    METADATA4 = 0x0014
    METADATA5 = 0x0015
    METADATA6 = 0x0016
    METADATA7 = 0x0017
    METADATA8 = 0x0018
    METADATA9 = 0x0019
    FIRST_SYMBOL = 0x0020
    SYMBOL_NEXT = 0x0030


class SignalType(enum.IntFlag):
    SIGNED = 1 << 0
    HEXADECIMAL = 1 << 1
    READABLE = 1 << 2
    WRITEABLE = 1 << 3
    LITTLE_ENDIAN = 1 << 4
    CAN_SIGNAL = 1 << 5
    FLOAT = 1 << 6
    ACTION = 1 << 7


def decode(
    data: bytes,
    byteorder: str = "big",
    is_signed: bool = False,
    is_float: bool = False,
    is_str: bool = False,
):
    if is_float:
        fmt = ">f" if byteorder == "big" else "<f"
        return struct.unpack(fmt, data)[0]
    if is_str:
        return data.decode()
    return int.from_bytes(data, byteorder=byteorder, signed=is_signed)


class Symbol:
    __slots__ = (
        "address",
        "size",
        "type",
        "segment_start",
        "segment_length",
        "demux_start",
        "demux_length",
        "demux_value",
        "group",
        "slope",
        "offset",
        "decimals",
        "event",
        "unit",
        "name",
    )

    def __init__(self, data, metadata, byteorder="big"):
        self.address = decode(data[metadata.fields["address"]])
        self.size = decode(data[metadata.fields["size"]])
        self.type = decode(data[metadata.fields["type"]])
        self.segment_start = decode(data[metadata.fields["segment_start"]])
        self.segment_length = decode(data[metadata.fields["segment_length"]])
        self.demux_start = decode(data[metadata.fields["demux_start"]])
        self.demux_length = decode(data[metadata.fields["demux_length"]])
        self.demux_value = decode(data[metadata.fields["demux_value"]])
        self.group = decode(data[metadata.fields["group"]])
        self.slope = decode(data[metadata.fields["slope"]], is_float=True)
        self.offset = decode(data[metadata.fields["offset"]], is_float=True)
        self.decimals = decode(data[metadata.fields["decimals"]])
        self.event = decode(data[metadata.fields["event"]])
        self.unit = decode(data[metadata.fields["unit"]], is_str=True)
        self.name = decode(data[metadata.fields["name"]], is_str=True)
        _logger.debug(f"Received symbol: {self.name}")


class MetaData:
    SIZE_START = 6
    SIZE_END = 21
    LENGTH_START = 21
    LENGTH_END = 36

    def __init__(self, data: bytes):
        self.n_symbols = int.from_bytes(data[:2], byteorder="big")
        _logger.debug(f"Received metadata: {self.n_symbols} symbols")
        self.version_address = int.from_bytes(data[2:6], byteorder="big")
        self.fields = {
            k: slice(data[i], data[i] + data[j])
            for k, (i, j) in zip(
                Symbol.__slots__,
                zip(
                    range(MetaData.SIZE_START, MetaData.SIZE_END),
                    range(MetaData.LENGTH_START, MetaData.LENGTH_END),
                ),
            )
        }


class SymbolTable:
    def __init__(self, node: CCPSlave, number: int):
        _logger.debug(f"Requesting action service: METADATA{number}")
        size = node.action_service(ActionService[f"METADATA{number}"]).length
        self.metadata = MetaData(node.upload_block(size))
        _logger.debug("Requesting action service: FIRST_SYMBOL")
        node.action_service(ActionService.FIRST_SYMBOL)
        self.symbols = []
        for i in range(self.metadata.n_symbols):
            _logger.debug("Requesting action service: SYMBOL_NEXT")
            size = node.action_service(ActionService.SYMBOL_NEXT).length
            self.symbols.append(Symbol(node.upload_block(size), self.metadata))


if platform.system() == "Windows":
    bus = can.Bus(interface="kvaser", channel=0, bitrate=500000, single_handle=True)
elif platform.system() == "Linux":
    bus = can.Bus(interface="socketcan", channel="can0")
else:
    raise RuntimeError(f"Unsupported platform: {platform.system()}.")

print("Connecting")
node = CCPSlave(
    bus=bus,
    station_address=0x10,
    cro_id=0xA,
    dto_id=0x9,
    byte_order="big_endian",
)

with node:
    table = SymbolTable(node, 4)

    daq_symbols = []
    poll_symbols = []
    for symbol in table.symbols:
        if symbol.type & SignalType.CAN_SIGNAL:
            continue
        if symbol.type & SignalType.READABLE: 
            element = Element(
                name=symbol.name,
                size=symbol.size,
                address=symbol.address,
                is_signed=symbol.type & SignalType.SIGNED,
                is_float=symbol.type & SignalType.FLOAT,
                scale=symbol.slope,
                offset=symbol.offset,
                on_received=print
            )
            if symbol.event: # event channel 0 is query only.
                daq_symbols.append(element)
            else:
                poll_symbols.append(element)
                
    for s in poll_symbols:
        print(node.poll(s))

    node.daq_lists.pack_elements_into(daq_symbols)
    print("Running DAQ")
    node.session_status |= SessionStatus.RUN
    node.daq_lists.start(event_channel=1)
    print("Temporary disconnect")
    node.disconnect(permanent=0)

    try:
        while True:
            time.sleep(5)
            break
    except KeyboardInterrupt:
        pass

    print("Disconnecting")

# _logger.handlers.clear()
# _logger.filters.clear()
