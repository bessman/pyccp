
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

.. |license| image:: http://img.shields.io/badge/license-GPL-blue.svg
   :target: http://opensource.org/licenses/GPL-2.0
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

Currently, information such as CAN IDs and memory addresses must be entered manually.
