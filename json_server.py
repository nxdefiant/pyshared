#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-

import SocketServer
import json
import threading
import logging
import control
import threading

SocketServer.TCPServer.allow_reuse_address = True

logger = logging.getLogger(__name__)

class TCPServer(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.setDaemon(True)
		self.server = SocketServer.ThreadingTCPServer(('0.0.0.0', 10002), TCPHandler)
		self.server.allow_reuse_address = True
		self.server.daemon_threads = True
		self.start()

	def run(self):
		self.server.serve_forever()

	def stop(self):
		self.server.shutdown()
		self.server.socket.close()


class TCPHandler(SocketServer.BaseRequestHandler):
	def __init__(self, request, client_address, server):
		self.__lock_send = threading.Lock()
		SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)

	def finish(self):
		return SocketServer.BaseRequestHandler.finish(self)

	def send_log(self, s):
		self.send({"log": s})

	def send(self, d):
		with self.__lock_send:
			self.request.sendall(json.dumps(d))

	def handle(self):
		try:
			while True:
				s = self.request.recv(4096)
				if not s:
					return

				data = json.loads(s)
				if data.has_key("command"):
					cmd = data["command"]
					ret = control.handle(cmd)
					self.send({"return": ret, "command_was": cmd})

		except Exception, e:
			logger.debug("Exception wile receiving message: \n%s", e)


if __name__ == "__main__":
	from time import sleep

	logger.setLevel(logging.DEBUG)
	logger.addHandler(logging.StreamHandler())

	pServer = TCPServer()
	while True:
		sleep(1)
