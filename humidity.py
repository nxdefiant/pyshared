#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-

RS = 8314.3 # J/(kmol*K) universelle Gaskonstante
MW = 18.016 # kg/kmol Molekulargewicht des Wasserdampfes

# Openweathermap
STATION=2911298
API_ID="41ff32c10636d35b4c7a46000cb1a6a1"

import urllib
import json

# Sättigungsdampfdruck in hPa
def calc_saturation_vapor_pressure(temp_c):
	if temp_c >= 0:
		a = 7.5
		b = 237.3
	else:
		a = 7.6
		b = 240.7 
	
	return 6.1078 * 10**((a*temp_c)/(b+temp_c))


# https://www.wetterochs.de/wetter/feuchte.html
def calc_humidity_abs(temp_c, humdity_rel):
	temp_k = temp_c + 273.15

	# Dampfdruck in hPa
	SDD = calc_saturation_vapor_pressure(temp_c)
	DD = humdity_rel/100.0 * SDD
	humidity_abs = 10**5 * MW/RS * DD/temp_k
	return humidity_abs


def calc_humidity_rel(temp_c, humidity_abs):
	temp_k = temp_c + 273.15
	SDD = calc_saturation_vapor_pressure(temp_c)
	DD = humidity_abs*temp_k * RS / (10**5*MW)
	
	humdity_rel = DD/SDD*100
	return humdity_rel

def get_weather_current():
	query = urllib.urlencode({'id': STATION, 'APPID': API_ID, 'lang': 'de'})
	url = "http://api.openweathermap.org/data/2.5/weather?units=metric&%s" % query
	response = urllib.urlopen(url)
	results = response.read()
	return json.loads(results)

def check_ventilate(temp_indoor, humdity_rel_indoor):
	dWeatherCurrent = get_weather_current()
	temp_outdoor = dWeatherCurrent["main"]["temp"]
	humdity_rel_outdoor = dWeatherCurrent["main"]["humidity"]

	humdity_abs_indoor = calc_humidity_abs(temp_indoor, humdity_rel_indoor)
	humdity_abs_outdoor = calc_humidity_abs(temp_outdoor, humdity_rel_outdoor)

	print "Wassergehalt Innen: %.2f, Außen: %.2f" % (humdity_abs_indoor, humdity_abs_outdoor)
	return humdity_abs_indoor/humdity_abs_outdoor


if __name__ == "__main__":
	check_ventilate(21, 50)	
