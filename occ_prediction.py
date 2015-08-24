"""
this module provides a prediction for occupancy using
a probabilistic schedule it also returns the estimated
occupancy for the current timeslot
but rather returning predicted occupancy
upon given a timeslot
"""

import sqlite3

MAX_SLOT = 7*96 - 1


def get_free_time(timestamp):
    """
    This function returns the amount of minutes until an occupied timeslot
    is predicted
    @args: timestamp

    @returns free_time in minutes
    """
    conn = sqlite3.connect('/home/pi/dbs/occupancy.db')
    c = conn.cursor()
    current_slot = timestamp.weekday() * 96 + timestamp.hour * 4 + timestamp.minute / 15
    query = "SELECT timeslot FROM prob_schedule WHERE timeslot > ?"
    + " AND probability >= 0.5 ORDER BY timeslot ASC LIMIT 1"
    c.execute(query, current_slot)
    r = c.fetchone()
    if r is not None:
        # A predicted timeslot exists until the end of the week
        next_occupied_slot = r
    else:
        # Start search from the beginning of the week
        query = "SELECT timeslot FROM prob_schedule"
        + " WHERE probability >= 0.5 ORDER BY timeslot ASC LIMIT 1"
        c.execute(query)
        r = c.fetchone()
        if r is not None:
            next_occupied_slot = r
        else:
            next_occupied_slot = (current_slot + 1) % MAX_SLOT
    if next_occupied_slot > current_slot:
        free_time = (next_occupied_slot - current_slot) * 15
    else:
        free_time = ((MAX_SLOT - current_slot) + next_occupied_slot) * 15
    return free_time


def is_pred_occupied(timestamp):
    """
    Given a timestamp this function returns
    whether the home will be occupied at that timestamp
    """
    occupied = False
    current_slot = timestamp.weekday() * 96 + timestamp.hour * 4 + timestamp.minute / 15
    conn = sqlite3.connect('/home/pi/dbs/occupancy.db')
    c = conn.cursor()
    query = "SELECT timeslot FROM prob_schedule WHERE timeslot LIKE ?"
    c.execute(query, current_slot)
    r = c.fetchone()
    if r >= 0.5:
        occupied = True
    return occupied


def set_prediction(is_home, dt):
    """
    enters the current timeslot into the schedule
    """
    timeslot = dt.weekday() * 96 + dt.hour * 4 + dt.minute / 15
    week = dt.isocalendar()[1]
    status = 0
    conn = sqlite3.connect('/home/pi/dbs/occupancy.db')
    c = conn.cursor()
    query = "DELETE FROM schedule WHERE week = ? AND timeslot = ?"
    c.execute(query, (week, timeslot,))
    if is_home:
        status = 1
    query = "INSERT INTO schedule VALUES (?,?,?)"
    c.execute(query, (week, timeslot, status,))
    conn.commit()
    conn.close()
    update_pred_schedule(timeslot)


def update_pred_schedule(timeslot):
    """
    updates the prediction schedule for the current timeslot
    """
    conn = sqlite3.connect('/home/pi/dbs/occupancy.db')
    c = conn.cursor()
    query = "SELECT COUNT(status) FROM schedule WHERE timeslot = ? AND status = ?"
    c.execute(query, (timeslot, 1,))
    num_home = c.fetchone()
    c.execute(query, (timeslot, 0,))
    num_away = c.fetchone()

    prob = 1.0 * num_home[0] / (num_home[0] + num_away[0])
    query = "UPDATE prob_schedule SET probability = ? WHERE timeslot = ?"
    c.execute(query, (prob, timeslot,))
    conn.commit()
    conn.close()
