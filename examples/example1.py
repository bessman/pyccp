import time

import can
import ccp

bus = can.Bus(interface="socketcan", channel="can0")
node = ccp.CCPSlave(
    bus=bus,
    station_address=0x10,
    cro_id=0xA,
    dto_id=0x9,
    byte_order="big_endian",
)

# Load internal variables metadata from e.g. a JSON document or an A2L-file.
with open("symbols.json") as f:
    symbols = [
        # A ccp.Element is essentially a pointer; it has a name, an address, a size,
        # and optionally type information (for decoding).
        ccp.Element(
            name=k,
            size=v["size"],
            address=v["address"],
            is_signed=v["is_signed"],
            is_float=v["is_float"],
            scale=v["slope"],
            offset=v["offset"],
            # An Element may also have an optional callback function. It is called every
            # time the element is received.
            on_received=print,
        ) for k, v in json.load(f).items()
    ]

# Using a context manager ensures the connection is closed correctly when we are done.
with node:
    # The Elements can be automatically packed into any available DAQ lists.
    node.daq_lists.pack_elements_into(symbols)
    # Start DAQ session.
    node.daq_lists.start(event_channel=1)

    # Run until cancelled with ^C.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
