
|build_travis| |coverage| |code_climate|

|issue_count| |license| |code_style|

.. |build_travis| image:: https://travis-ci.org/bessman/pyccp.svg?branch=master
   :target: https://travis-ci.org/bessman/pyccp
   :alt: Travis build server

.. |coverage| image:: https://coveralls.io/repos/github/bessman/pyccp/badge.svg?branch=master
   :target: https://coveralls.io/github/bessman/pyccp?branch=master
   :alt: Test coverage report

.. |code_climate| image:: https://codeclimate.com/github/bessman/pyccp/badges/gpa.svg
   :target: https://codeclimate.com/github/bessman/pyccp
   :alt: Maintainability grade

.. |issue_count| image:: https://codeclimate.com/github/bessman/pyccp/badges/issue_count.svg
   :target: https://codeclimate.com/github/bessman/pyccp
   :alt: Maintainability issues

.. |license| image:: http://img.shields.io/badge/license-LGPL-blue.svg
   :target: http://opensource.org/licenses/LGPL-3.0
   :alt: GNU General Public License

.. |code_style| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Any color you like


The **C**\ AN **C**\ alibration **P**\ rotocol is a high-level CAN-bus protocol
designed for calibration of and data acquisition from an electronic control unit
(ECU). Via CCP, a master node can read internal variables or set configuration
parameters in one or several slave devices.

CCP communication requires detailed information about the data layout in the
slave device(s). This information is typically distributed in A2L-files, which
are usually automatically generated when building the ECU firmware.


Example usage
-------------

.. code:: python

   import can
   from pya2l import DB, model
   import pyccp
   import logging
   import time

   # Configure logging of received messages
   log = logging.getLogger("ccp_log")
   log.basicConfig(filename="ccp.csv", level=logging.INFO, format="")

   # Configure CAN-bus
   bus = can.Bus(bustype="socketcan", channel="can0", bitrate=500000)

   # Load A2L-file
   db = DB()
   sql_session = db.import_a2l("engine_ecu.a2l")

   # Configure master node
   master = pyccp.Master(transport=bus, cro_id=0x321, dto_id=0x7E1)

   # Configure DAQ session
   daq_session = pyccp.DAQSession(master=master, station_address=0x37)

   # Select some measurement signals to log.
   measurements = sql_session.query(model.Measurement)
   temperatures = measurements.filter(model.Measurement.name.like("%temp%")).all()
   pressures = measurements.filter(model.Measurement.name.like("%pressure%")).all()

   # Start DAQ session
   daq_session.initialize(measurements=temperatures+pressures)
   daq_session.run()

   # Log for 10 seconds
   time.sleep(10)
   daq_session.stop()
   sql_session.close()

Currently, information such as the slave's station address and CAN IDs must be
entered manually.
