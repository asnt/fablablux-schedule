from __future__ import print_function

import argparse
import json
import random

import requests

from fablab_schedule import config


class ScheduleService:

    base_route = "?rest_route=/open-access/v1"
    endpoints = {
        "status": "/",
        "schedule": "/machine-schedule",
    }

    def __init__(self, base_url, username="", password=""):
        if not base_url.endswith("/"):
            base_url = base_url + "/"
        self.base_url = base_url + ScheduleService.base_route
        self.username = username
        self.password = password

    def url_for(self, service):
        if service not in ScheduleService.endpoints:
            raise ValueError("uknown service {}".format(service))
        endpoint = ScheduleService.endpoints[service]
        return self.base_url + endpoint

    def status(self):
        url = self.url_for("status")
        r = requests.get(url)
        print(url)
        print('status: ', r.status_code)
        print(r.text)

    def get(self):
        url = self.url_for("schedule")
        r = requests.get(url)

        print(url)
        print('get schedule: ', r.status_code)
        table = json.loads(r.json()).get("table", None)
        if table is not None:
            print_table(table)
        else:
            print(r.text)

    def post(self, table):
        url = self.url_for("schedule")
        json_data = dict(table=table)
        credentials = dict(username=self.username, password=self.password)
        r = requests.post(url, params=credentials, json=json_data)

        print(url)
        print('post schedule: ', r.status_code)
        data = json.loads(r.json()).get("data", None)
        if data is None:
            table = None
        else:
            table = data.get("table", None)
        if table is not None:
            print_table(table)
        else:
            print(r.text)


def print_table(table):
    for row in table:
        for booked in row:
            symbol = "X" if booked else "-"
            print(symbol, end=" ")
        print()


def generate_random_table():
    n_slots = 9
    n_machines = 7
    table = [
        [bool(round(random.random())) for __ in range(n_slots)]
        for __ in range(n_machines)
    ]
    return table


def main():
    description = "Communicate with the REST API of the FabLab wall schedule" \
                  " WordPress plugin"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("command", choices=["get", "status", "post"])
    parser.add_argument("-c", "--config", help="alternate config file")
    args = parser.parse_args()

    if args.config:
        conf = config.from_file(args.config)
    else:
        conf = config.get()

    url = conf["base_url"]
    user = conf["username"]
    password = conf["password"]
    service = ScheduleService(url, user, password)

    command = args.command
    if command == "status":
        service.status()
    elif command == "get":
        service.get()
    elif command == "post":
        table = generate_random_table()
        service.post(table)


if __name__ == "__main__":
    main()
