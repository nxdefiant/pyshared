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
