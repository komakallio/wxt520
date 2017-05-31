# -*- coding: utf-8 -*-
"""
Created on Sat Mar 25 20:06:35 2017

@author: lauri.kangas
"""

import serial
import serial.tools.list_ports as list_ports
import time
import logging
from pprint import pprint
import json

class WXT520:
    bauds = [9600]
    messages = {'r1': 'Wind',
                'r2': 'PTU',
                'r3': 'Rain',
                'r5': 'Status'}

    @staticmethod
    def find_wxt():
        for port in list_ports.comports():
            for baud in WXT520.bauds:
                with serial.Serial(port[0], baud, timeout=1) as ser:
                    time.sleep(.1)
                    ser.flushInput()
                    ser.write(b'?\r\n')
                    response = ser.readline()
                    if response:
                        address = response[:1]
                        if address.isalnum():
                            ser.flushInput()
                            ser.write(address+b'XU\r\n')
                            settings_response = ser.readline()
                            if b'WXT520' in settings_response:
                                return port[0], address.decode()
                            else:
                                logging.debug(settings_response)
        return None

    @staticmethod
    def crc16(msg):
        c = 0
        for a in msg:
            c ^= a
            for _ in range(8):
                if c & 1:
                    c >>= 1
                    c ^= 0xA001
                else:
                    c >>= 1
        bytes_ = [0x40 | (c >> 12), 0x40 | ((c >> 6) & 0x3f), 0x40 | (c & 0x3f)]
        return "".join(map(chr, bytes_)).encode()

    @staticmethod
    def check_crc(message):
        message = message.strip()
        return WXT520.crc16(message[:-3]) == message[-3:]

    @staticmethod
    def message_to_dict(message):
        message = message.strip()[:-3].decode('ascii')
        pieces = message.split(',')
        d = dict()

        message_code = pieces[0][1:]
        try:
            d['Type'] = WXT520.messages[message_code]
        except KeyError:
            return None

        wxt_data = dict()
        for piece in pieces[1:]:
            if '=' in piece:
                label, value = piece.split('=')
                wxt_data[label] = value

        formatted_data = dict()

        def unit_value_pair(label):
            key = label
            value = wxt_data[label]
            try:
                return [float(value[:-1]), parse_unit((key, value))]
            except ValueError:
                raise ValueError("could not convert {}: '{}' to float"
                                 .format(key, value[:-1]))

        if d['Type'] == 'Wind':
            speed = dict()
            direction = dict()

            speed['average'] = unit_value_pair('Sm')
            speed['limits'] = [unit_value_pair('Sn'),
                               unit_value_pair('Sx')]

            direction['average'] = unit_value_pair('Dm')
            direction['limits'] = [unit_value_pair('Dn'),
                                   unit_value_pair('Dx')]

            formatted_data['Speed'] = speed
            formatted_data['Direction'] = direction

        if d['Type'] == 'PTU':
            temperature_ambient = unit_value_pair('Ta')
            temperature_internal = unit_value_pair('Tp')
            humidity = unit_value_pair('Ua')
            pressure = unit_value_pair('Pa')

            formatted_data['Temperature'] = {
                    'Ambient': temperature_ambient,
                    'Internal': temperature_internal}

            formatted_data['Humidity'] = humidity
            formatted_data['Pressure'] = pressure

        if d['Type'] == 'Rain':
            rain = dict()
            hail = dict()

            rain['Intensity'] = unit_value_pair('Ri')
            rain['Peak'] = unit_value_pair('Rp')
            rain['Accumulation'] = unit_value_pair('Rc')
            rain['Duration'] = unit_value_pair('Rd')

            hail['Intensity'] = unit_value_pair('Hi')
            hail['Peak'] = unit_value_pair('Hp')
            hail['Accumulation'] = unit_value_pair('Hc')
            hail['Duration'] = unit_value_pair('Hd')

            formatted_data['Rain'] = rain
            formatted_data['Hail'] = hail

        if d['Type'] == 'Status':
            status = dict()
            voltages = dict()

            voltages['Supply'] = unit_value_pair('Vs')
            voltages['Reference'] = unit_value_pair('Vr')
            heating_voltage, heating_status = unit_value_pair('Vh')
            voltages['Heating'] = [heating_voltage, 'V']

            status['Voltages'] = voltages
            status['Heating'] = {'Temperature': unit_value_pair('Th'),
                                 'Status': heating_status}

            formatted_data = status

        d['Data'] = formatted_data

        return d

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.ser.close()
        pass

    def __init__(self, port, address, baudrate=9600,timeout=1):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.address = address
        time.sleep(.1)
        self.ser.flushInput()
        self.ser.write(b'0XU,M=a\r\n')
        response = self.ser.readline()
        if not b',M=a' in response:
            logging.error('No answer to ASCII automatic mode setting!')
            self.ser.close()
            raise ValueError('No answer to ASCII automatic mode setting!')

    def readline(self):
        line = self.ser.readline()
        if not line:
            return None
        if not WXT520.check_crc(line):
            return None
        return line

def parse_unit(label_value):
    temperature_units = {'C': 'C', 'F': 'F'}
    speed_units = {'M': 'm/s', 'K': 'km/h', 'S': 'mph', 'N': 'kn'}
    direction_units = {'D': 'deg'}
    pressure_units = {'H': 'hPa', 'P': 'Pa', 'B': 'bar', 'M': 'mmHg', 'I': 'inHg'}
    humidity_units = {'P': '%'}
    rain_accumulation_units = {'M': 'mm', 'I': 'in'}
    duration_units = {'S': 's', 's': 's'} # error in doc!
    rain_intensity_units = {'M': 'mm/h', 'I': 'in/h'}
    hail_accumulation_units = {'M': 'hits/cm2', 'I': 'hits/in2', 'H': 'hits'}
    hail_intensity_units = {'M': 'hits/cm2h', 'I': 'hits/in2h', 'H': 'hits/h'}
    voltage_units = {'V': 'V'}
    heating_status = {'N': '0% hi-',
                      'V': '50% mid-hi',
                      'W': '100% lo-mid',
                      'F': '50% -lo'}

    label, value = label_value
    unit_chr = value[-1]
    unit = ''
    try:
        if label == 'Id': # prevent this to reach the duration block
            return None
        elif label[0] == 'T':
            unit = temperature_units[unit_chr]
        elif label[0] == 'S':
            unit = speed_units[unit_chr]
        elif label[0] == 'D':
            unit = direction_units[unit_chr]
        elif label == 'Pa':
            unit = pressure_units[unit_chr]
        elif label == 'Ua':
            unit = humidity_units[unit_chr]
        elif label[-1] == 'd':
            unit = duration_units[unit_chr]
        elif label == 'Ri' or label == 'Rp':
            unit = rain_intensity_units[unit_chr]
        elif label == 'Rc':
            unit = rain_accumulation_units[unit_chr]
        elif label == 'Hi' or label == 'Hp':
            unit = hail_intensity_units[unit_chr]
        elif label == 'Hc':
            unit = hail_accumulation_units[unit_chr]
        elif label == 'Vh':
            unit = heating_status[unit_chr]
        elif label[0] == 'V':
            unit = voltage_units[unit_chr]
    except KeyError:
        if unit_chr == '#':
            unit = 'invalid'
        else:
            raise ValueError('Cannot parse unit character {}'.format(unit_chr))
    return unit
