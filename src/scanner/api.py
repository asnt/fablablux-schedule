import json
import random

import requests


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
        for cell in row:
            print(cell and "X" or "-", end=" ")
        print()


def generate_random_table():
    n_slots = 9
    n_machines = 7
    table = [
        [bool(round(random.random())) for __ in range(n_slots)]
        for __ in range(n_machines)
    ]
    return table


def usage():
    import sys
    usage_message = """\
Utility for interacting with the machine schedule api.

usage: {} [options] <status|get|post>

commands:
    status  get the status of the open access
    get     get the latest machine schedule
    post    post a random machine schedule

options:
    --config <filename>
""".format(sys.argv[0])
    print(usage_message)


def main():
    import sys
    args = sys.argv[1:]

    if "--config" in args:
        index = args.index("--config")
        config_filename = args[index + 1]
        del args[index + 1]
        del args[index]
    else:
        config_filename = "schedule.cfg"

    if len(args) == 0:
        usage()
        sys.exit(1)
        
    import config
    config = config.load(config_filename)
    schedule = ScheduleService(config['base_url'], config['username'],
                                                   config['password'])

    cmd = args[0]
    if cmd == "status":
        schedule.status()
    elif cmd == "get":
        schedule.get()
    elif cmd == "post":
        table = generate_random_table()
        schedule.post(table)
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
