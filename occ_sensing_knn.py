"""
ts | mean | std | soad | est | known
"""
import sqlite3
import numpy as np

SECONDS = 60 * 15
K_FIXED = 19


def knn_search(x, D, K):
    """ find K nearest neighbours of data among D """
    ndata = D.shape[0]
    K = K if K < ndata else ndata
    # euclidean distances from the other points
    sqd = ((D - x)**2).sum(axis=1)
    idx = np.argsort(sqd)
    # return the indexes of K nearest neighbours
    return idx[:K]


def fetch_data(ts):
    conn = sqlite3.connect('/home/pi/dbs/electricity.db')
    c = conn.cursor()
    query = "SELECT data FROM electricity_data WHERE timestamp > ? AND timestamp < ? AND data NOT LIKE 'nan' ORDER BY timestamp ASC"
    c.execute(query, (ts-SECONDS, ts,))
    arr = np.array(c.fetchall())
    conn.close()
    return arr


def create_datapoint(raw_data):
    sda = np.sum(np.absolute(raw_data[:-1]-raw_data[1:]))
    data = np.array([np.average(raw_data), np.std(raw_data), sda])
    return data


def get_all_dp():
    conn = sqlite3.connect('/home/pi/dbs/electricity.db')
    c = conn.cursor()
    query = "SELECT mean, std, sda, occ FROM sample_points_knn WHERE occ NOT LIKE 2"
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
    x = create_datapoint(raw_data)
    full_data = get_all_dp()
    if len(full_data) > 0:
        occ_data = full_data[:, -1]
        D = full_data[:, :-1]
        mean = np.mean(D, axis=0)
        std = np.std(D, axis=0)
        D = (D - mean) / std
        # Do the knn_search on the data
        x_fit = (x - mean) / std
        k_idx = knn_search(x_fit, D, K_FIXED)
        occupied_slots = np.sum(occ_data[k_idx])
        est = 1 if occupied_slots > K_FIXED/2 else 0
    else:
        est = 0
    conn = sqlite3.connect('/home/pi/dbs/electricity.db')
    c = conn.cursor()
    query = "INSERT INTO sample_points_knn (timestamp, mean, std, sda, est_occ, occ) VALUES (?,?,?,?,?,?)"
    try:
        c.execute(query, (ts, x[0], x[1], x[2], est, 2,))
    except sqlite3.IntegrityError:
        print("Already in DB")
    conn.commit()
    conn.close()
    return est
