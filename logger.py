#!/usr/bin/env python3

import curses
from pylibftdi import Device
from time import sleep
from datetime import datetime
from operator import xor


# constants
runtime_data_header = [
    0x01,  # SOH
    0x00,  # Emittend
    0x42,  # Recipient
    0x02,  # Data Size
    0xFF,  # EOH
    0x02,  # SOT
    0x43,  # Data 1 -> 0x56 = Get version, 0x43 = Get runttime data
    0x03,  # EOT
    0xFD   # Checksum
]

RTD_BYTES = bytearray(runtime_data_header)
DELAY = 0.1
ERRORS = 0


# test with:
# curses.wrapper(sample)
def sample(screen, *args):
    from random import randrange as rr

    while True:
        rand_x = rr(0, 52)
        rand_y = rr(0, 20)
        screen.addstr(rand_y, rand_x, chr(rr(35,100)))
        screen.refresh()


def chksum(start, end, data, init=0):
    checksum = 0

    for i in range(start, end):
        checksum = xor(checksum, data[i])

    return checksum


def getRuntimeData(serial_device):
    serial_device.write(RTD_BYTES)

    sleep(DELAY)

    runtime_data = serial_device.read(99)

    return runtime_data


def recordData(raw_data, file_obj):
    file_obj.write(raw_data)

    # this emulates the record separator in a Megasquirt-style binary log.
    # usually its an incremental time-ish based record, but I haven't been
    # able to identify what this needs to be exactly. leaving it blank
    # works fine with MegaLogViewer and EcmSpy's log analyzer, it just
    # skews the runtime in MegaLogViewer, which might be fine.
    file_obj.write(int(0).to_bytes(4, "big"))  # b'\x00\x00\x00\x00'

    # making sure to flush anything in the buffer so we don't lose anything
    # when we abruptly turn the bike off
    file_obj.flush()


def printError(screen, error_str):
    screen.clear()
    screen.addstr(0, 6, error_str)


def printEngineTempAndO2(raw_data, screen):
    # screen formatting
    padding = ' '
    width = 3
    location = (0, 0)  # x, y

    # data
    engine_temp = (raw_data[31] << 8 | raw_data[30]) * 0.1 - 40  # engine temp in C
    engine_o2 = (raw_data[35] << 8 | raw_data[34]) * 0.004888  # O2 voltage
    formatted_output = f'T: {engine_temp :{padding}>{width}.0f} C O2: {engine_o2 :.2f} V '

    screen.addstr(location[1], location[0], formatted_output)


def printEngineO2(raw_data, screen):
    # fixed 4-wide field, no need for padding
    location = (0, 1)  # x, y

    # data
    engine_o2 = (raw_data[35] << 8 | raw_data[34]) * 0.004888  # O2 voltage
    formatted_output = f'O2: {engine_o2 :.2f}    '

    screen.addstr(location[1], location[0], formatted_output)


def printEngineFuel(raw_data, screen):
    # readout in ms
    padding = ' '
    width = 5
    location = (0, 1)  # x, y

    # data
    engine_fuel_front = (raw_data[22] << 8 | raw_data[21]) * 0.00133  # Fuel Pulsewidth in ms
    engine_fuel_rear = (raw_data[24] << 8 | raw_data[23]) * 0.00133  # Fuel Pulsewidth in ms
    formatted_output = f'FPW: F {engine_fuel_front :{padding}>{width}.2f} R {engine_fuel_rear :{padding}>{width}.2f}'

    screen.addstr(location[1], location[0], formatted_output)

    # readout in fuel table value
    padding = ' '
    width = 5
    location = (0, 2)  # x, y

    # data
    engine_fuel_front = (raw_data[18] << 8 | raw_data[17]) * 0.026666  # fuel table value
    engine_fuel_rear = (raw_data[20] << 8 | raw_data[19]) * 0.026666  # fuel table value
    formatted_output = f'FTB: F {engine_fuel_front :{padding}>{width}.0f} R {engine_fuel_rear :{padding}>{width}.0f}'

    screen.addstr(location[1], location[0], formatted_output)


def printBatteryVoltage(raw_data, screen):
    padding = ' '
    width = 5
    location = (0, 3)  # x, y

    # data
    engine_volts = (raw_data[29] << 8 | raw_data[28]) * 0.01  # battery voltage
    formatted_output = f'Batt V: {engine_volts :{padding}>{width}.2f}'

    screen.addstr(location[1], location[0], formatted_output)


def printEngineTimingAdvance(raw_data, screen):
    padding = ' '
    width = 5
    location = (0, 4)  # x, y

    # data
    engine_timing_front = (raw_data[14] << 8 | raw_data[13]) * 0.0025  # degrees of spark advance
    engine_timing_rear = (raw_data[16] << 8 | raw_data[15]) * 0.0025  # degrees of spark advance
    formatted_output = f'Adv: F {engine_timing_front :{padding}>{width}.2f} R {engine_timing_rear :{padding}>{width}.2f}'

    screen.addstr(location[1], location[0], formatted_output)


def printEngineLoad(raw_data, screen):
    padding = ' '
    width = 3
    location = (0, 5)  # x, y

    # data
    engine_load = raw_data[27] # 1-byte value, engine load as percent * 2.55 (0-255)
    formatted_output = f'Load: {engine_load :{padding}>{width}}'

    screen.addstr(location[1], location[0], formatted_output)


def main(screen, *args):
    # initializations (one time)

    # serial device
    device = Device('AR0K7VGN')
    device.baudrate = 9600
    device.open()

    # recording file
    current_timestamp = datetime.now().strftime("%d-%m-%y_%H-%M-%S")
    record_file = open(f'/home/pi/buell-logger/{current_timestamp}.log', 'wb')

    # standard bin header for DDFI-1
    record_file.write(b'BUEKA\x00\x00\x00\x01')

    global ERRORS
    global DELAY

    while True:
        # get latest data to draw
        data = getRuntimeData(device)

        if len(data) < 98:
            # error if data isn't complete
            printError(screen, 'Comm error!')
            sleep(1)

        else:
            # check to make sure the data is valid
            chk_calc = chksum(1, 98, data)
            chk_rcrd = data[-1]

            if chk_calc == chk_rcrd:
                # draw it out
                printEngineTempAndO2(data, screen)
                printEngineFuel(data, screen)
                printBatteryVoltage(data, screen)
                printEngineTimingAdvance(data, screen)
                printEngineLoad(data, screen)

                # record data to file
                recordData(data, record_file)

                # reset error counter
                ERRORS = 0
            else:
                # count consecutive errors
                if ERRORS < 3:
                    ERRORS += 1
                    printError(screen, f"ERRORS: {ERRORS}")

                else:
                    # back off the data collection interval
                    DELAY += 0.05
                    ERRORS = 0
                    printError(screen, f"DELAY: {DELAY}")

                    if DELAY > 0.5:
                        printError(screen, f"HIGH ERRORS, PAUSED")
                        sleep(30)
                        DELAY = 0.2

        # refresh the screen
        screen.refresh()


# basically a main() wrapper to cleanly init and de-init curses
curses.wrapper(main)
