import web
import sqlite3
import json
import time
import occ_prediction
from datetime import datetime
from math import floor

urls = (
    '/', 'index',
    '/phonelog', 'home',
    '/last_update', 'last_update'
)


class index:
    def GET(self):
        return "Hello, world!"


class home:
    def POST(self):
        i = web.data()
        i = json.loads(i)
        conn = sqlite3.connect('occupancy.db')
        c = conn.cursor()
        datestring = "%Y-%m-%d %H:%M:%S"

        query = "SELECT timestamp, status FROM phone_reports ORDER BY timestamp DESC LIMIT 1"
        c.execute(query)
        last_ts = c.fetchone()
        db_query = "INSERT INTO phone_reports (status, timestamp) VALUES (?,?)"
        status = 0 if i[u'state'] == "away" else 1
        c.execute(db_query,(status, i[u'timestamp'],))
        conn.commit()
        conn.close()
        # Fill in the occupancy states that can be defined
        if not last_ts:
            return
        new_ts = time.mktime(time.strptime(i[u'timestamp'],datestring))
        home = 0
        if last_ts[1]:
            home = 1
        last_ts = time.mktime(time.strptime(last_ts[0], datestring))
        conn_elec = sqlite3.connect('(/home/pi/dbs/electricity.db')
        c_elec = conn_elec.cursor()
        if new_ts - last_ts > 1800:
            # Fill in the covered time slots with the right status
            print "BIG GAP"
            current_ts  = new_ts - new_ts%900
            while current_ts > last_ts + 900:
                # set knn_data for current_ts to status
                query = "UPDATE sample_points SET occ = ? WHERE timestamp LIKE ?"
                #c_elec.execute(query, (home, current_ts,))
                # calc timeslot for current_ts
                dt = datetime.fromtimestamp(current_ts - 900)
                print(dt, " in the big gap")
                occ_prediction.set_prediction(home, dt)
                current_ts = current_ts - 900
        if floor(last_ts/900) < floor(new_ts/900):
            
            conn = sqlite3.connect('/home/pi/dbs/occupancy.db')
            c = conn.cursor()
            beginning = floor(last_ts/900)
            end = floor(new_ts/900)
            query = "SELECT status, timestamp FROM phone_reports WHERE timestamp > ? AND timestamp < ? ORDER BY timestamp DESC"
            c.execute(query, (beginning, end,))
            reports = c.fetchall()
            query = "SELECT status FROM phone_reports WHERE timestamp < ? ORDER BY timestamp DESC LIMIT 1"
            c.execute(query, (beginning,))
            status = c.fetchone()
            conn.close()
            if not status:
                status = 0
            else:
                status = status[0]
            time_away = 0
            time_home = 0
            curr = beginning
            for report in reports:
                if status:
                    time_home = time_home - curr + report[1]
                else:
                    time_away = time_away - curr + report[1]
                    curr = report[1]
                    status = report[0]
            if status:
                time_home = time_home - curr + end
            else:
                time_away = time_away - curr + end

            if time_away > time_home:
                home = 0
                
            query = "UPDATE ? SET occ = ? WHERE timestamp = ?"
            try:
            	c_elec.execute(query, ('sample_points_knn', home, beginning))
            	c_elec.execute(query, ('sample_points_svm', home, beginning))
            except Exception as e:
                print(e)
            dt = datetime.fromtimestamp(end*900)
            print dt
            occ_prediction.set_prediction(home, dt)
        conn_elec.commit()
        conn_elec.close()

        

class last_update:
    def GET(self):
        conn = sqlite3.connect('/home/pi/dbs/occupancy.db')
        c = conn.cursor()
        query = "SELECT timestamp FROM phone_reports ORDER BY timestamp DESC LIMIT 1"
        c.execute(query)
        timestamp = c.fetchone()
        
        
        if timestamp:
            return json.dumps({'timestamp':timestamp[0]})
        else:
            return json.dumps({'timestamp':0})

if __name__ == "__main__":
    # Setup the database
    conn = sqlite3.connect('/home/pi/dbs/occupancy.db')
    c = conn.cursor()
    create_table_phone = "CREATE TABLE IF NOT EXISTS 'phone_reports' (status integer, timestamp timestamp)"
    create_table_sched = "CREATE TABLE IF NOT EXISTS 'schedule' (week integer, timeslot integer, status integer)"
    create_table_prob = "CREATE TABLE IF NOT EXISTS 'prob_schedule' (timeslot integer, probability real)"
    c.execute(create_table_phone)
    c.execute(create_table_sched)
    c.execute(create_table_prob)
    conn.commit()
    conn.close()
    
    app = web.application(urls, globals())
    
    app.run()
