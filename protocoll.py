#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-

import struct
import threading
import math
from pycrc.crc_algorithms import Crc

class ByteError(Exception):
	def __init__(self, value):
		Exception.__init__(self)
		self.value = value
	def __str__(self):
		return "Byte Error, got 0x%x" % self.value

class CRCError(Exception):
	def __str__(self):
		return "CRC Error"

class TimeoutException(Exception):
	def __str__(self):
		return "Timeout"

class NAKReceived(Exception):
	def __str__(self):
		return "NAK received"

class PackageTooBigException(Exception):
	def __str__(self):
		return "Package too long"


class Protocoll:
	ENQ = 0x5
	ACK = 0x6
	DC1 = 0x11
	NAK = 0x21
	MAX_LEN = 128
	STATE_DEFAULT = 0
	STATE_LEN = 1
	STATE_READ = 2
	
	def __init__(self, conn):
		self.conn = conn
		self.lock = threading.Lock()
		self.crc = Crc(width = 8, poly = 0x07, reflect_in = False, xor_in = 0x0, reflect_out = False, xor_out = 0x00)

	def __get_ack(self):
		c = ""
		for i in range(60):
			try:
				c = self.conn.read(1)
			except:
				continue
			if c:
				break
		if not c:
			self.conn.close()
			raise TimeoutException()
		c = ord(c)
		if c not in (self.ACK, self.NAK):
			raise ByteError(c)
		return c == self.ACK

	def send(self, addr, msg, bSlitMsg=False):
		msg_len = 3 + len(msg) + 1
		if bSlitMsg and msg_len > self.MAX_LEN:
			num_per_packet = self.MAX_LEN - 3 - 1
			num_packets = math.ceil(len(msg)/float(num_per_packet))
			self.send(addr, "%cSplit %d" % (self.DC1, num_packets))
			for i in range(0, len(msg), num_per_packet):
				msg_part = msg[i:i+num_per_packet]
				self.send(addr, msg_part)
			return
		self.lock.acquire()
		try:
			if msg_len > self.MAX_LEN:
				raise PackageTooBigException()
			packet = struct.pack("<BBB%ds" % len(msg), self.ENQ, msg_len, addr, msg)
			packet+=chr(self.crc.bit_by_bit_fast(packet))
			self.conn.write(packet)
			if not self.__get_ack():
				raise NAKReceived()
		except:
			raise
		finally:
			self.lock.release()

	def write(self, addr, msg):
		return self.send(addr, msg)

	def __reply_ack(self):
		self.conn.write(chr(self.ACK))
	
	def __reply_nak(self):
		self.conn.write(chr(self.NAK))

	def receive(self):
		packet = ""
		num = 0
		state = self.STATE_DEFAULT
		self.lock.acquire()
		try:
			while(True):
				c = self.conn.read(1)
				if not c:
					raise
				if state == self.STATE_DEFAULT:
					if ord(c) != self.ENQ:
						self.__reply_nak()
						raise ByteError(ord(c))
					state = self.STATE_LEN
					packet = c
				elif state == self.STATE_LEN:
					if ord(c) > self.MAX_LEN:
						self.__reply_nak()
						raise PackageTooBigException()
					state = self.STATE_READ
					packet += c
					num = ord(c)-2
				elif state == self.STATE_READ:
					packet += c
					num-=1
					if num == 0:
						if self.crc.bit_by_bit_fast(packet) == 0:
							self.__reply_ack()
							msgtype, msglen, addr, msg, crc = struct.unpack("<BBB%dsB" % (len(packet)-3-1), packet)
							return addr, msg
						else:
							self.__reply_nak()
							raise CRCError()
		except:
			raise
		finally:
			self.lock.release()
	
	def read(self):
		addr, msg = self.receive()
		if msg[0] == chr(self.DC1) and len(msg) > 1:
			lCmd = msg[1:].split()
			if len(lCmd) == 2 and lCmd[0] == "Split":
				num = int(lCmd[1])
				msg = ""
				for i in range(num):
					addr_part, msg_part = self.receive()
					if addr_part == addr:
						msg+=msg_part
		return addr, msg
