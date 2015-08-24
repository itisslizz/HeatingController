"""
Implement MPC
"""
import sched
import time
import weather_service
from building import Building
import occ_prediction
import occ_sensing_knn
import occ_sensing_svm
import datetime
import math
import sqlite3

SETTINGS = {
    "time_interval": 15,
    "comfort_setpoint": 21.0,
    "setback_setpoint": 18.0,
    "classifier": "SVM",
    "algorithm": 1
}


def initialize_dbs():
    # Controller DB storing recorded temperatures
    # and current configurations of the model
    conn = sqlite3.connect('/home/pi/dbs/controller.db')
    c = conn.cursor()
    # Create table for temp recordings if non existant
    query = "CREATE TABLE IF NOT EXISTS 'intervals' (first_temp real, last_temp real, heating integer)"
    c.execute(query)
    # Create table for configuration if non existant
    query = "CREATE TABLE IF NOT EXISTS 'model_config' (value real, name text)"
    c.execute(query)
    # Initialize values for configuration if non existent
    query = "SELECT * FROM model_config"
    c.execute(query)
    if not len(c.fetchall()):
        # No values have been initialized
        print("INITIALIZING VALUES")
        values = [(100000, 'rc'),
                  (40, 'rq'),
                  (0, 'num_heating'),
                  (0, 'num_non_heating'),
                  ]
        query = "INSERT INTO model_config VALUES (?,?)"
        c.executemany(query, values)
    conn.commit()
    conn.close()

    # create electricity db if non existent
    conn = sqlite3.connect('/home/pi/dbs/electricity.db')
    c = conn.cursor()
    query = "CREATE TABLE IF NOT EXISTS electricity_data (timestamp timestamp, data integer)"
    c.execute(query)
    query = """CREATE TABLE IF NOT EXISTS sample_points_knn(
            timestamp timestamp,
            mean real,
            std real,
            sda real,
            est_occ integer,
            occ integer)"""
    c.execute(query)
    query = """CREATE TABLE IF NOT EXISTS sample_points_svm(timestamp timestamp,
            minimum real,
            maximum real,
            mean real,
            std real,
            sda real,
            autocorr real,
            on_off real,
            range_1 real,
            p_time real,
            est_occ integer,
            occ integer)"""
    c.execute(query)
    conn.commit()
    conn.close()

    # occupancy prediction dbs
    conn = sqlite3.connect('/home/pi/dbs/occupancy.db')
    c = conn.cursor()
    create_schedule = "CREATE TABLE IF NOT EXISTS schedule (week integer, timeslot integer, status integer)"
    create_prob_schedule = "CREATE TABLE IF NOT EXISTS prob_schedule (timeslot integer, prob real)"
    c.execute(create_schedule)
    c.execute(create_prob_schedule)


def choose_setpoint(building, sc):
    # Set up the next run
    now = time.time()

    now = now-now % 900

    next_run = (math.floor(now / (60 * SETTINGS["time_interval"])) + 1) * 60 * SETTINGS["time_interval"]
    sc.enter(next_run - now, 1, choose_setpoint, (building, sc,))
    # Decide how Long it takes to heat the house
    # Factors: Current Temperature, Model, Outside
    # Temperature, (Solar Gain) --> heat_time
    if SETTINGS["classifier"] == "SVM":
        is_occupied = occ_sensing_svm.est_occ(now)
    elif SETTINGS["classifier"] == "KNN":
        is_occupied = occ_sensing_knn.est_occ(now)
    else:
        is_occupied = 0
    now_dt = datetime.datetime.fromtimestamp(now)

    if is_occupied:
        free_time = 0
        print("Building seems to be occupied")
    else:
        free_time = occ_prediction.get_free_time(now_dt)
        print("Expecting Occupancy in %i minutes" % free_time)
    outside_temp = weather_service.get_current_temperature(building.get_location())
    print("Current outside temperature is %i degrees Centigrade" % outside_temp)

    if SETTINGS["algorithm"] == 1:
        # Algorithm 1

        heat_time = building.get_heat_time(outside_temp, SETTINGS["comfort_setpoint"])

        if heat_time + 15 >= free_time:
            building.set_setpoint(SETTINGS["comfort_setpoint"])
            print("Setpoint set to %i", SETTINGS["comfort_setpoint"])
        else:
            building.set_setpoint(SETTINGS["setback_setpoint"])
            print("Setpoint set to %i", SETTINGS["setback_setpoint"])
    elif SETTINGS["algorithm"] == 2:
        # Algorithm 2
        if free_time <= 15:
            building.set_setpoint(SETTINGS["comfort_setpoint"])
        else:
            next_setpoint = building.get_next_setpoint(outside_temp, SETTINGS["comfort_setpoint"], free_time)
            next_setpoint = max(next_setpoint, SETTINGS["setback_setpoint"])
            building.set_setpoint(next_setpoint)


if __name__ == "__main__":
    initialize_dbs()
    building = Building("Baden", "ch")
    # get location and models from db?
    s = sched.scheduler(time.time, time.sleep)
    # FIND NEXT 15 minute on clock
    now = time.time()
    next_run = (math.floor(now / (60 * SETTINGS["time_interval"])) + 1) * 60 * SETTINGS["time_interval"]

    s.enter(next_run - now, 1,
            choose_setpoint, (building, s,))
    s.run()
