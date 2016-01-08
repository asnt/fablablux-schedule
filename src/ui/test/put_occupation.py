#!/usr/bin/env python

import numpy as np
import requests


n_machines = 7
n_slots = 9
table = np.random.randint(2, size=(n_machines, n_slots)).astype(bool)

def run(host, port):
    address = "http://{:s}:{:d}/api/occupation".format(host, port)
    data = dict(table=table.tolist())
    r = requests.put(address, json=data)
    print(r.text)
    print(r.status_code)


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    i = 0
    host = "192.168.123.100"
    port = 5000
    while i < len(args):
        if args[i] == '-h':
            host = args[i + 1]
            i += 1
        elif args[i] == '-p':
            port = int(args[i + 1])
            i += 1
    run(host=host, port=port)
