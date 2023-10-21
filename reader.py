#!/usr/bin/env python3

from sys import argv
from operator import xor


def chksum(start, end, data, init=0):
    checksum = 0

    for i in range(start, end):
        checksum = xor(checksum, data[i])

    return checksum


def readRecords(record_filename):
    with open(record_filename, 'rb') as f:
        # read = 0
        consecutive = 0
        last_err = 0
        errors = 0
        records = 0

        header = f.read(9)
        print(header)
        print('\n')

        while True:
            raw_data = f.read(99)
            blank = f.read(4)
            records += 1
            # read += 103

            if len(raw_data) < 99:
                print(f'Record count: {records}')
                print(f'Error count: {errors}')
                break

            chk_calc = chksum(1, 98, raw_data)
            chk_rcrd = raw_data[-1]

            if chk_calc == chk_rcrd:
                temp = (raw_data[31] << 8 | raw_data[30]) * 0.1 - 40  # engine temp in C
                o2 = (raw_data[35] << 8 | raw_data[34]) * 0.004888  # O2 voltage
                ffms = (raw_data[22] << 8 | raw_data[21]) * 0.00133  # Fuel Pulsewidth in ms
                rrms = (raw_data[24] << 8 | raw_data[23]) * 0.00133  # Fuel Pulsewidth in ms
                fftb = (raw_data[18] << 8 | raw_data[17]) * 0.026666  # fuel table reading
                rrtb = (raw_data[20] << 8 | raw_data[19]) * 0.026666  # fuel table reading
                vlts = (raw_data[29] << 8 | raw_data[28]) * 0.01  # battery voltage
                fftm = (raw_data[14] << 8 | raw_data[13]) * 0.0025  # degrees of spark advance
                rrtm = (raw_data[16] << 8 | raw_data[15]) * 0.0025  # degrees of spark advance
                load = raw_data[27] # 1-byte value, engine load as percent * 2.55 (0-255)

                print(f'T: {temp :.2f} | O: {o2 :.2f} | F: {ffms :.2f} | F: {fftb :.0f} | R: {rrms :.2f} | R: {rrtb :.0f} | V: {vlts :.2f} | F: {fftm :.2f} | R: {rrtm :.2f} | L: {load}')

            else:
                errors += 1
                # print(f'Error found at byte: {read}')
                # print(f'{chk_calc} != {chk_rcrd}')

                # if f.tell() - last_err < 104:
                #     consecutive += 1
                # else:
                #     consecutive = 0

                # if consecutive > 5:
                #     break

                # last_err = f.tell()


record_fn = str(argv[1])

readRecords(record_fn)
