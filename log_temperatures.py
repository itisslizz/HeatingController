import hw_controller
import time
import sqlite3


def main():
    macs = []
    args = []
    
    conn = sqlite3.connect('home/pi/dbs/temperature.db')
    c = conn.cursor()
    create_temp = "CREATE TABLE IF NOT EXISTS heating temperature (timestamp timestamp, mac text, temperature real)"
    c.execute(create_temp)
    query = """INSERT INTO heating_temperature (timestamp, mac, temperature)
               VALUES (?,?,?)""" 
    for mac in macs:
        temp = hw_controller.get_temperature(mac)
        args.push_back((time.time(), mac, temperature,))
    c.executemany(query, args)
    conn.commit()
    conn.close()

