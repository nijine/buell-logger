#!/usr/bin/env python3

import board
import busio
import adafruit_ssd1306
from pylibftdi import Device
from time import sleep
from datetime import datetime
from operator import xor
from sys import argv, exit
from digitalio import DigitalInOut, Direction, Pull
from PIL import Image, ImageDraw, ImageFont


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

RTD_BYTES = bytes(bytearray(runtime_data_header))
RECORD_LENGTH = 99


def checksum(start, end, data, init=0):
    checksum_record = 0

    for i in range(start, end):
        checksum_record = xor(checksum_record, data[i])

    return checksum_record


def initLogFile(file_dir=None):
    current_timestamp = datetime.now().strftime("%d-%m-%y_%H-%M-%S")
    default_location = '/home/pi/buell-logger'

    location = f'{default_location}/{current_timestamp}.log'

    if file_dir is not None:
        location = f'{file_dir}/{current_timestamp}.log'

    log_file = open(location, 'wb')

    # standard bin header for DDFI-1
    log_file.write(b'BUEKA\x00\x00\x00\x01')

    return log_file


def initButtons():
    # Input pins:
    button_A = DigitalInOut(board.D5)
    button_A.direction = Direction.INPUT
    button_A.pull = Pull.UP
    
    button_B = DigitalInOut(board.D6)
    button_B.direction = Direction.INPUT
    button_B.pull = Pull.UP
    
    button_L = DigitalInOut(board.D27)
    button_L.direction = Direction.INPUT
    button_L.pull = Pull.UP
    
    button_R = DigitalInOut(board.D23)
    button_R.direction = Direction.INPUT
    button_R.pull = Pull.UP
    
    button_U = DigitalInOut(board.D17)
    button_U.direction = Direction.INPUT
    button_U.pull = Pull.UP
    
    button_D = DigitalInOut(board.D22)
    button_D.direction = Direction.INPUT
    button_D.pull = Pull.UP
    
    button_C = DigitalInOut(board.D4)
    button_C.direction = Direction.INPUT
    button_C.pull = Pull.UP


def initDrawDevice():
    # Create the I2C interface.
    i2c = busio.I2C(board.SCL, board.SDA)
    # Create the SSD1306 OLED class.
    disp = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)

    # Clear display.
    disp.fill(0)
    disp.show()
    
    # Create blank image for drawing.
    # Make sure to create image with mode '1' for 1-bit color.
    width = disp.width
    height = disp.height
    image = Image.new("1", (width, height))
    
    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)
    
    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    
    # Load font for printing text
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)

    # physical display, renderer, image buffer, and font object for text
    return (disp, draw, image, font)


def getRuntimeData(serial_device):
    serial_device.write(RTD_BYTES)

    # may want a more sophisticated way of doing this so we don't hang up the whole program
    sleep(0.1)

    runtime_data = serial_device.read(RECORD_LENGTH)

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


def checkData(raw_data):
    if len(raw_data) < RECORD_LENGTH:
        return False

    checksum_calculated = checksum(1, RECORD_LENGTH - 1, raw_data)
    checksum_recorded = raw_data[-1]

    return checksum_calculated == checksum_recorded


def drawBasicText(disp, draw, image, font, text="Hello!"):
    # blank rectangle (useful for clearing)
    draw.rectangle((0, 0, disp.width, disp.height), outline=0, fill=0)

    # writing text (coords, text_value, font, fill_color)
    draw.text((1, 1), text, font=font, fill=1)

    # update display buffer with latest image content
    disp.image(image)

    # paint buffer to display
    disp.show()


def main():
    # init everything

    # log file
    log_file_dir = None

    if len(argv) > 1:
        log_file_dir = str(argv[1])

    log_file = initLogFile(log_file_dir)

    # buttons
    initButtons()

    # drawing resources
    draw_res = initDrawDevice()

    # serial device
    try:
        serial = Device()
        serial.baudrate = 9600
        serial.open()
    except:
        drawBasicText(*draw_res, "Serial not found")
        exit(1)

    # error counters
    errors = 0
    recent = 0

    # loop
    while True:
        # get latest data
        data = getRuntimeData(serial)

        # check for data integrity
        record_is_good = checkData(data)

        if record_is_good:
            # record data to file
            recordData(data, log_file)

            # draw it out
            drawBasicText(*draw_res, f"Comm OK!\nBytes: {log_file.tell()}\nErrors: {errors}")

            # reset recent error counter
            recent = 0
        else:
            # increment error counters
            errors += 1
            recent += 1

            # pause after X concurrent errors
            if recent > 5:
                drawBasicText(*draw_res, "Comm error!")
                sleep(10)


main()
