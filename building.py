"""
This module will store and update the model automatically
while providing an interface for desired information
"""
from math import log
import sqlite3
import hw_controller
import numpy as np
import math
import re


class Building:
    def __init__(self, city, country_code):
        # The model on which we do calculations
        self.model = OneROneC()

        # Provides us with information about Temperature
        self.temperature = Temperature()

        # Defines the location of the building
        self.location = Location(city, country_code)

    def get_heat_time(self, ot, dt):
        """
        Uses the Building Model to estimate the time needed to heat to
        dt
        """
        self.it = self.temperature.get_temperature()
        #self.model.update_model(it, ot)
        return self.model.get_heat_time(ot, self.it, dt)

    def get_next_setpoint(self, outdoor_temp, desired_temp, free_time):
        """
        Calculate the optimal next setpoint
        """
        return self.model.get_next_setpoint(outdoor_temp, desired_temp, free_time)

    def set_setpoint(self, setpoint):
        """
        sets the new setpoint
        """
        self.temperature.put_setpoint(setpoint)

    def get_temperature(self):
        """
        returns the current indoor temperature
        """
        return self.temperature.get_temperature(self)

    def get_location(self):
        """
        Returns a location string
        """
        return self.location.get_location()


class Temperature:
    def __init__(self):
        self.current_temp = 0
        self.mac = "221:2eff:ff00:22d0"

    def get_temperature(self):
        # Temperature regex (make sure we only match temperature)
        temp_regex = r'\d{2}\.\d{2}'

        response = hw_controller.get_temperature(self.mac)
        if not re.match(temp_regex, str(response)):
            response = self.fallback_temperature(self.mac)
        return float(response)

    def put_setpoint(self, setpoint):
        hw_controller.put_setpoint(self.mac, setpoint)
        
    def fallback_temperature(self, mac):
        """
        Get the latest temperature from the db
        """
        conn = sqlite3.connect('/home/pi/dbs/heating.db')
        c = conn.cursor()
        query = 'SELECT temperature FROM heating_temperature WHERE mac LIKE ? ORDER BY timestamp DESC LIMIT 1'
        c.execute(query, (mac,))
        temperature = c.fetchone()[0]
        conn.close()
        return temperature


class Location:
    def __init__(self, city, country_code):
        self.longitude = 0
        self.latitude = 0
        self.city = city
        self.country_code = country_code
    
    def get_location(self):
        return self.city + "," + self.country_code


class OneROneC:
    def __init__(self):
        self.r = 0
        self.c = 0
        self.q = 0
        self.load_config()
        self.old_temp = 0

    def get_heat_time(self, outdoor_temp, indoor_temp, desired_temp):
        """
        Calculate time it takes to hate from inddor_temp
        to desired_temp
        """
        if (not self.rc) or (not self.rq):
            return 0
        heat_time = (log((desired_temp - self.rq - outdoor_temp)
                     / (indoor_temp - self.rq - outdoor_temp))
                     * self.rc / (-60.0))
        return heat_time

    def get_next_setpoint(self, outdoor_temp, desired_temp, time_to_heat):
        """
        Calculate how warm the house has to be in order to
        heat it to desired_temp in time_to_heat-15 minutes
        """
        if (not self.rc) or (not self.rq):
            return 0
        temp_result = desired_temp - (self.rq + outdoor_temp)*(1-math.exp(-60.0*(time_to_heat - 15) / self.rc))
        next_sp = temp_result / (math.exp(-60.0*(time_to_heat-15) / self.rc))
        return next_sp

    def update_model(self, it, ot):
        # are we heating?
        if self.old_temp > 0:
            sp = hw_controller.get_setpoint()
            new_rc = self.rc
            heating = (sp > it + 0.5)
            cooling = (sp < it - 1)
            if cooling:
                # not heating
                if self.num_non_heating:
                    avg = -900.0/self.rc
                    new_avg = (avg * self.num_non_heating + (np.log(it-ot)-np.log(self.old_temp-ot))) / (self.num_non_heating + 1)
                    new_rc = -900.0 / new_avg
                else:
                    new_rc = -900.0 / (np.log(it-ot)-np.log(self.old_temp-ot))
                self.num_non_heating = self.num_non_heating + 1
                self.rc = new_rc
                self.update_rq()
            elif heating:
                # heating
                e_rc = math.exp(-900.0/self.rc)
                avg = self.rq * (1 - e_rc)
                new_avg = (avg * self.num_heating + (it - ot) - e_rc * (self.old_temp - ot)) / (self.num_heating + 1)
                new_rq = new_avg / (1-e_rc)
                self.num_heating = self.num_heating + 1
                self.rq = new_rq
            conn = sqlite3.connect('/home/pi/dbs/controller.db')
            c = conn.cursor()
            query = "UPDATE model_config SET value = ? WHERE name = ?"
            c.execute(query, (self.rc, "rc",))
            c.execute(query, (self.rq, "rq",))
            c.execute(query, (self.num_non_heating, "num_non_heating",))
            c.execute(query, (self.num_heating, "num_heating",))
            query = "INSERT INTO intervals VALUES (?, ?, ?)"
            c.execute(query, (self.old_temp-ot, it-ot, heating,))
            conn.commit()
            conn.close()
        self.old_temp = it
        print ("RC:", self.rc, " RQ: ", self.rq)

    def update_rq(self):
        conn = sqlite3.connect('/home/pi/dbs/controller.db')
        c = conn.cursor()
        query = "SELECT first_temp, last_temp FROM intervals WHERE heating = ?"
        c.execute(query, (True, ))
        rows = c.fetchall()
        if (len(rows)):
            arrays = np.array(rows)
            first_temps = arrays[:, 0]
            second_temps = arrays[:, 0]
            e_rc = math.exp(-900/self.rc)
            self.rq = np.average(second_temps - e_rc * first_temps) / (1-e_rc)

    def load_config(self):
        conn = sqlite3.connect('/home/pi/dbs/controller.db')
        c = conn.cursor()
        query = "SELECT m.value FROM model_config m WHERE name = 'rc'"
        c.execute(query)
        self.rc = c.fetchone()[0]
        query = "SELECT m.value FROM model_config m WHERE name = 'rq'"
        c.execute(query)
        self.rq = c.fetchone()[0]
        query = "SELECT m.value FROM model_config m WHERE name = 'num_non_heating'"
        c.execute(query)
        self.num_non_heating = c.fetchone()[0]
        query = "SELECT m.value FROM model_config m WHERE name = 'num_heating'"
        c.execute(query)
        self.num_heating = c.fetchone()[0]
        print("RC:", self.rc, " RQ:", self.rq, " NNH:", self.num_non_heating, " NH:", self.num_heating)
        conn.close()
