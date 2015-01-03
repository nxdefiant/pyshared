#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-

import os
import rlcompleter
import readline
import code
import atexit


class irlcompleter(rlcompleter.Completer):
	def complete(self, text, state):
		if text == "":
			# you could  replace \t to 4 or 8 spaces if you prefer indent via spaces
			return ['\t', None][state]
		else:
			return rlcompleter.Completer.complete(self, text, state)


class HistoryConsole(code.InteractiveConsole):
	def __init__(self, locales=None, filename="<console>", histfile=os.path.expanduser("~/.console-history"), custom_interpreter=None):
		code.InteractiveConsole.__init__(self, locales, filename)
		self.init_history(histfile)
		self.custom_interpreter = custom_interpreter

	def init_history(self, histfile):
		readline.parse_and_bind("tab: complete")
		readline.set_completer(irlcompleter().complete)

		if hasattr(readline, "read_history_file"):
			try:
				readline.read_history_file(histfile)
			except IOError:
				pass
			atexit.register(self.save_history, histfile)

	def save_history(self, histfile):
		readline.write_history_file(histfile)

	def push(self, line):
		line = line.encode("iso-8859-15", "replace")
		if self.custom_interpreter:
			if self.custom_interpreter(line):
				return
		return code.InteractiveConsole.push(self, line)


if __name__ == "__main__":
	con = HistoryConsole(locales=locals())
	con.interact(banner="")
