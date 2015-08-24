"""
This module will provide weather information
"""

import json
import urllib.request as urllib2
import codecs

def get_current_temperature(location):
    url = 'http://api.openweathermap.org/data/2.5/weather?q='+location
    response = urllib2.urlopen(url)
    reader = codecs.getreader("utf-8")
    data = json.load(reader(response))
    return data["main"]["temp"]-273.15

def get_forecast_temperature(location):
    """
    This function provides temperature forecasts
    for the next 5 days in 3 hour resolution
    along with the timestamp
    """
    url = 'http://api.openweathermap.org/data/2.5/forecast?q='+location
    response = urllib2.urlopen(url)
    reader = codecs.getreader("utf-8")
    data = json.load(reader(response))
    temps =[]
    for forecast in data["list"]:
        temps.append((forecast.dt, forecast["main"]["temp"] - 273.15))
    return temps
