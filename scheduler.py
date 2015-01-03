#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-

import logging
import threading
from time import sleep


logger = logging.getLogger(__name__)

class Scheduler:
	def __init__(self):
		self.lThreads = []
		self.pause = False
		self.autoclean()

	def autoclean(self):
		logger.debug("Current number of threads: %d" % threading.active_count())
		self.add_thread(10, self.autoclean)
		for t in self.lThreads:
			if not t.isAlive():
				self.lThreads.remove(t)

	def stop(self):
		for t in self.lThreads:
			t.cancel()

	def add_thread(self, time, function, args=[], kwargs={}):
		while(self.pause):
			sleep(1)
		k = [function, None, args, kwargs]
		t = threading.Timer(time, self.dispatch, k)
		t.setDaemon(True)
		t.setName(str(function))
		k[1] = t
		t.start()
		self.lThreads.append(t)

	def dispatch(self, function, timer, args, kwargs):
		timer.timeup = True
		while True:
			still_running = False
			for t in self.lThreads:
				if t.name == str(function) and t.isAlive() and t.ident != timer.ident:
					still_running = True
					break
			if not still_running:
				break
			logger.debug("Delaying execution of Thread %s", t.name)
			# Another Thread still running, delay execution
			sleep(0.1)
		try:
			function(*args, **kwargs)
		except:
			logger.exception("Dispatcher exception of %s:", t.name)
			logger.error("Current number of threads: %d" % threading.active_count())


pScheduler = Scheduler()

if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	def test():
		pScheduler.add_thread(0.1, test)
		print "test"
		sleep(1)
		print "end"
	test()

	while(1):
		sleep(0.1)
