"""
ts | mean | std | soad | est | known
"""
import sqlite3
from datetime import datetime
import numpy as np

from sklearn.decomposition import PCA
from sklearn import svm

SECONDS = 60 * 15


def fetch_data(ts):
    conn = sqlite3.connect('/home/pi/dbs/electricity.db')
    c = conn.cursor()
    query = "SELECT data FROM electricity_data WHERE timestamp > ? AND timestamp < ? AND data NOT LIKE 'nan' ORDER BY timestamp ASC"
    c.execute(query, (ts-SECONDS, ts,))
    arr = np.array(c.fetchall())
    conn.close()
    return arr


def create_datapoint(raw_data, orig_data):
    minimum = np.amin(raw_data)
    maximum = np.amax(raw_data)
    mean = np.average(raw_data)
    std = np.std(raw_data)
    sda = np.sum(np.absolute(raw_data[:-1]-raw_data[1:]))
    autocorr = np.correlate(raw_data[:-1, 0], raw_data[1:, 0])
    on_off = num_onoff(orig_data)
    range_1 = maximum - minimum
    data_point = np.array([minimum,
                           maximum,
                           mean,
                           std,
                           sda,
                           autocorr,
                           on_off,
                           range_1])
    return data_point


def num_onoff(raw_data):
    ThA = 90
    ThT = 90
    old_value = raw_data[0]
    on_offs = 0
    pending = []
    for value in raw_data[1:]:
        if value >= old_value + ThA:
            pending.append([old_value + ThA, 0])
        for sample in pending:
            if value >= sample[0]:
                sample[1] = sample[1] + 1
                if sample[1] == ThT:
                    on_offs = on_offs + 1
                    pending.remove(sample)
            else:
                pending.remove(sample)
    return on_offs


def get_all_dp():
    conn = sqlite3.connect('/home/pi/dbs/electricity.db')
    c = conn.cursor()
    query = """SELECT
    minimum,
    maximum,
    mean,
    std,
    sda,
    autocorr,
    on_off,
    range_1,
    p_time,
    occ FROM sample_points_svm WHERE occ NOT LIKE 2"""
    c.execute(query)
    arr = np.array(c.fetchall())
    conn.close()
    return arr


def est_occ(ts):
    orig_data = fetch_data(ts)
    if not len(orig_data):
        # No Electricity Data Available
        # return true
        return 1
    orig_data[orig_data < 1] = 1
    raw_data = np.log10(orig_data)
    x = create_datapoint(raw_data, orig_data)
    dt = datetime.fromtimestamp(ts)
    p_time = dt.hour * 4 + dt.minute / 15 - 23
    x = np.append(x, p_time)
    full_data = get_all_dp()
    if len(full_data) > 0:
        occ_data = full_data[:, -1]
        D = full_data[:, :-1]
        mean = np.mean(D, axis=0)
        std = np.std(D, axis=0)
        D = (D - mean) / std
        pca = PCA(n_components=5)
        pca.fit(D)
        D = pca.transform(D)
        x_fit = (x - mean) / std
        x_fit = pca.transform(x_fit)
        clf = svm.SVC()
        clf.fit(D, occ_data)
        pred = clf.predict(x_fit)
        pred = pred[0]
    else:
        pred = 0
    conn = sqlite3.connect('/home/pi/dbs/electricity.db')
    c = conn.cursor()
    query = """INSERT INTO sample_points_svm (
    timestamp,
    minimum,
    maximum,
    mean,
    std,
    sda,
    autocorr,
    on_off,
    range_1,
    p_time,
    est_occ,
    occ
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"""
    try:
        c.execute(query,
                  (ts,
                   x[0],
                   x[1],
                   x[2],
                   x[3],
                   x[4],
                   x[5],
                   x[6],
                   x[7],
                   x[8],
                   pred,
                   2, ))
    except sqlite3.IntegrityError:
        print("Already in DB")
    conn.commit()
    conn.close()
    return pred
