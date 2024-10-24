# PyCCP

The **C**AN **C**alibration **P**rotocol is a high-level CAN-bus protocol
designed for calibration of and data acquisition from an electronic control unit
(ECU). Via CCP, a master node can read internal variables or set configuration
parameters in one or several slave devices.

CCP communication requires detailed information about the data layout in the
slave device(s). This information is typically distributed in A2L-files, which
are usually automatically generated when building the ECU firmware.


## Example usage

```python
import can
import pyccp
import logging
import time

# Configure logging of received messages
log = logging.getLogger("ccp_log")
log.basicConfig(filename="ccp.csv", level=logging.INFO, format="")

# Configure CAN-bus
bus = can.Bus(bustype="socketcan", channel="can0", bitrate=500000)

# Configure master node
master = pyccp.Master(transport=bus, cro_id=0x321, dto_id=0x7E1)

# Configure DAQ session
session = pyccp.DAQSession(
       master=master,
       station_address=0x37,
       )

# Specify some variables for logging
diff_pressure = pyccp.Element(
       name="diffP",
       size=4,
       address=0x4000AA56,
       scale=0.001,
       )
coolant_temp = pyccp.Element(
       name="cTemp",
       size=2,
       address=0x4000F090,
       is_signed=True,
       )

# Start DAQ session
session.initialize(elements=[diff_pressure, cooland_temp])
session.run()

# Log for 10 seconds
time.sleep(10)
session.stop()
```

Currently, information such as CAN IDs and memory addresses must be entered manually.
