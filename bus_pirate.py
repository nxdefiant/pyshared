#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-

import serial
import struct

dPinToBit = {
		"POWER": 6,
		"PULLUP": 5,
		"AUX": 4,
		"MOSI": 3,
		"CLK": 2,
		"MISO": 1,
		"CS": 0
}

# http://dangerousprototypes.com/docs/Bitbang
# http://dangerousprototypes.com/docs/SPI_(binary)
class BP:
	def __init__(self, sDevice):
		self.pSerial = serial.Serial(sDevice, baudrate=115200, timeout=0.1)
		self.mode_bit_bang()
		self.io_state = 0
		self.io_dir = 0

	def command(self, cmd, num_read):
		self.pSerial.write(cmd)
		return self.pSerial.read(num_read)

	def mode_bit_bang(self):
		for i in range(20):
			if self.command(chr(0x0), 5) == "BBIO1":
				return
		raise Exception("Failed to enter bit bang mode")

	def mode_spi(self, mode, speed):
		if self.command(chr(0x1), 4) != "SPI1":
			raise Exception()
		self.spi_set_mode(mode)
		self.spi_set_speed(speed)

	def spi_set_mode(self, mode):
		if mode not in range(0, 4):
			raise Exception("Unknown mode")
		if mode == 0:
			self.spi_command(chr(0b10001000))
		elif mode == 1:
			self.spi_command(chr(0b10001010))
		elif mode == 2:
			self.spi_command(chr(0b10001100))
		elif mode == 3:
			self.spi_command(chr(0b10001110))

	def spi_set_speed(self, speed):
		lSpeeds = ["30kHz", "125kHz", "250kHz", "1MHz", "2MHz", "2.6MHz", "4MHz", "8MHz"]
		val = lSpeeds.index(speed)
		self.spi_command(chr(0b01100000 | val))

	def power_enable(self):
		self.set_io("POWER", True)
	
	def get_adc(self):
		s = self.command(chr(0x14), 2)
		v = struct.unpack(">h", s)
		return v[0]/1024.0*6.6

	# http://codepad.org/qtYpZmIF
	def pwm(self, freq, duty_cycle):
		lPrescaler = {0:1, 1:8 , 2:64, 3:256}
		Fosc = 32e6
		Tcy = 2.0 / Fosc
		period = 1.0 / freq
		prescaler = 1

		# find needed prescaler
		for i in range(4):
			prescaler = lPrescaler[i]
			PRy = period * 1.0 / (Tcy * prescaler)
			PRy = int(PRy - 1)
			OCR = int(PRy * duty_cycle)

			if PRy < (2 ** 16 - 1):
				break # valid value for PRy, keep values

		cmd = struct.pack(">BBHH", 0b00010010, prescaler, duty_cycle, period)
		ret = self.command(cmd, 1)
		if ord(ret) != 0x1:
			raise Exception()

	def spi_command(self, cmd):
		ret = self.command(cmd, 1)
		if ord(ret) != 0x1:
			raise Exception()
	
	def spi_write(self, data, num_read=0):
		if len(data) > 4096:
			raise Exception("SPI Data String too long")
		return self.spi_command(struct.pack(">Bhh%ds" % len(data), 0x04, len(data), num_read, data))

	def set_io_output(self, pin):
		if pin not in dPinToBit.keys():
			raise Exception("Bad output pin")
		self.io_dir &= ~(1 << dPinToBit[pin])
		state = 0b01000000 | self.io_dir
		self.command(chr(state), 1)

	def set_io_input(self, pin):
		if pin not in dPinToBit.keys():
			raise Exception("Bad input pin")
		self.io_dir |= (1 << dPinToBit[pin])
		state = 0b01000000 | self.io_dir
		self.command(chr(state), 1)

	def set_io(self, pin, val):
		if pin not in dPinToBit.keys():
			raise Exception("Bad output pin")
		if val:
			self.io_state |=  (1 << dPinToBit[pin])
		else:
			self.io_state &= ~(1 << dPinToBit[pin])
		state = self.update_io()

	def update_io(self):
		state = self.command(chr(0b10000000 | self.io_state), 1)
		return ord(state)

	def get_io(self, pin):
		if pin not in dPinToBit.keys():
			raise Exception("Bad I/O pin")
		state = self.update_io()
		return state & (1 << dPinToBit[pin])

	def mode_i2c(self, bEnablePower=False, bEnablePullup=False, iSpeedkHz=100):
		if self.command(chr(0x2), 4) != "I2C1":
			raise Exception()

		dSpeeds = {
			5: 0x0,
			50: 0x1,
			100: 0x2,
			400: 0x3,
		}
		if iSpeedkHz not in dSpeeds.keys():
			raise Exception("Invalid I2C speed")
		ret = self.command(chr(0b01100000 | dSpeeds[iSpeedkHz]), 1)
		if ord(ret) != 0x1:
			raise Exception()

		periphals = 0b01000000
		if bEnablePower:
			periphals |= (1<<3)
		if bEnablePullup:
			periphals |= (1<<2)
		ret = self.command(chr(periphals), 1)
		if ord(ret) != 0x1:
			raise Exception()

	def i2c_write(self, addr, reg, s):
		# 1. Write
		# command (1) | number of write bytes (2) | number of read bytes (2) | bytes to write (0..)
		msg = struct.pack(">BHHBB%ds" % len(s), 0x08, 2+len(s), 0, addr, reg, s)
		ret = self.command(msg, 1)

		if ord(ret[0]) != 0x1:
			raise Exception("I2C write error")

	def i2c_read(self, addr, reg, num_read):
		# set reg
		self.i2c_write(addr, reg, "")

		# command (1) | number of write bytes (2) | number of read bytes (2) | bytes to write (0..)
		msg = struct.pack(">BHHB", 0x08, 1, num_read, addr | 0x1)
		ret = self.command(msg, 1 + num_read)

		if ord(ret[0]) != 0x1:
			raise Exception("I2C read error")

		return ret[1:]

	def i2c_search(self):
		for i in range(128):
			msg = struct.pack(">BHHB", 0x08, 1, 1, i)
			ret = self.command(msg, 1)
			if ord(ret) == 0x1:
				print "Found I2C Addr: 0x%x" % (i & ~0x1)
