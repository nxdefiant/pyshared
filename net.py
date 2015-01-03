#!/usr/bin/python

import sys
import socket
import logging
import traceback
from threading import Thread
from time import sleep
from protocoll import *

logger = logging.getLogger(__name__)

class NetServer(Thread):
	def __init__(self, handler=None, handler_connect=None, handler_disconnect=None):
		Thread.__init__(self)
		self.setDaemon(True)
		self.sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sck.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sck.bind(("", 10001))
		self.sck.listen(1)
		self.sck.setblocking(0)
		self.bRun = False
		self.handler = handler
		self.handler_connect = handler_connect
		self.handler_disconnect = handler_disconnect
		self.start()

	def run(self):
		self.bRun = True
		while(self.bRun):
			sleep(0.01)
			try:
				conn, addr = self.sck.accept()
				#conn.settimeout(0.01)
			except:
				continue
			logger.debug("New Connection")
			proto = Protocoll(NetWrapper(conn))
			if self.handler_connect:
				self.handler_connect(proto)
			while True:
				try:
					addr, msg = proto.receive()
				except socket.error, e:
					if e.errno == 11:
						logger.debug("Connection lost")
					elif e.errno:
						logger.debug("Socket Error %d", e.errno)
						traceback.print_exc(file=sys.stdout)
					break
				except TimeoutException:
					continue
				except ByteError:
					continue
				except NAKReceived:
					continue
				except:
					traceback.print_exc(file=sys.stdout)
					break

				if self.handler:
					try:
						self.handler(addr, msg)
					except:
						traceback.print_exc(file=sys.stdout)
			logger.debug("Connection Ended")
			if self.handler_disconnect:
				self.handler_disconnect(proto)
			conn.close()

	def stop(self):
		self.bRun = False


class NetWrapper:
	def __init__(self, sck):
		self.sck = sck

	def write(self, s):
		return self.sck.send(s)
	
	def read(self, i):
		return self.sck.recv(i)

	def close(self):
		return self.sck.close()

class NetClient(Protocoll, Thread):
	def __init__(self, kTarget, handler=None):
		Thread.__init__(self)
		self.setDaemon(True)
		self.comm = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.comm.connect(kTarget)
		self.comm.setblocking(0)
		self.comm.settimeout(0.01)
		Protocoll.__init__(self, NetWrapper(self.comm))
		self.handler = handler
		self.bRun = False

	def run(self):
		self.bRun = True
		while(self.bRun):
			sleep(0.01)
			try:
				addr, msg = self.receive()
				if self.handler:
					self.handler(addr, msg)
			except socket.error, e:
				if hasattr(e, "errno") and e.errno == 9:
					#print "Connection lost"
					break
				elif e.message == "timed out":
					pass
				else:
					traceback.print_exc(file=sys.stdout)
			except TimeoutException:
				pass
			except:
				traceback.print_exc(file=sys.stdout)
		self.comm.close()

        def receive(self):
                i = 0 
                while True:
                        i+=1
                        try:
                                return Protocoll.receive(self)
                        except:
                                if i > 300:
                                        raise
                        sleep(0.01)

	def stop(self):
		self.bRun = False
	

if __name__ == "__main__":
	def handler(addr, s):
		print addr, s

	if sys.argv[1] == "server":
		pNet = NetServer(handler)
		while(1):
			sleep(1)
	elif sys.argv[1] == "client":
		pNet = NetClient(("192.168.36.14", 10001))
		pNet.send(0, "lights")
