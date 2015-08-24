import sqlite3
import urllib
import json

flukso_ip = '0.0.0.0'

def main():
    conn = sqlite3.connect('/home/pi/dbs/electricity.db')
    c = conn.cursor()
    query = "CREATE TABLE IF NOT EXISTS electricity_data (timestamp INTEGER PRIMARY KEY, data INTEGER)"
    c.execute(query)
    data = get_data(0)
    for record in data:
        query = "INSERT INTO electricity_data VALUES (?,?)"
        try:
            c.execute(query, (record[0], record[1],))
        except sqlite3.IntegrityError as e:
            pass
    conn.commit()
    conn.close()


def get_data(try):
    url = "http://" + flukso.ip ":8080/sensor/5c655d0e95b97b23c36775214bf2b875?version=1.0&interval=minute&unit=watt"
    if try > 10:
        return []
    try:
        response = urllib.urlopen(url)
    except e:
        return get_data(try + 1)
    data = json.loads(response.read())
    return data


main()
