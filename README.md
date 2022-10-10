# buell-logger
A python based logging and data display utility for Buell DDFI-1 ECMs

## Design Brief
Buell DDFI ECMs support runtime data dumps using a serial connection on the DataLink port.

This particular implementation uses an off-the-shelf FTDI-based USB to serial DataLink cable for ECM interfacing since it is very reliable and platform agnostic. In my particular case, I set this up to use a Raspberry Pi Model 3B+ with an Adafruit 2.8" Display.

The workflow is roughly as follows:
1. Turn bike ignition ON and killswitch to RUN
2. ECM initializes and is ready to dump runtime data after a couple seconds
3. Send a byte sequence to the ECM to request data (runtime data header)
4. Wait for a reply on the serial receive buffer
5. Collect the 99-byte reply
6. Process the reply (collect it in a logfile, display it on the screen, etc)
7. Continuously repeat the process from step 3 onward

