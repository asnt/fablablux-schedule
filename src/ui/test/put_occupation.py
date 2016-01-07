#!/usr/bin/env python

import numpy as np
import requests

n_machines = 7
n_slots = 9
table = np.random.randint(2, size=(n_machines, n_slots)).astype(bool)

def run():
    address = "http://localhost:5000/api/occupation"
    data = dict(table=table.tolist())
    r = requests.put(address, json=data)
    print(r.text)
    print(r.status_code)


if __name__ == "__main__":
    run()
