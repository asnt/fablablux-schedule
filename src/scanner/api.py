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


usage_message = """\
Interect with the schedule REST api.

usage: {} [options] <status|get|post>

commands:
    status  get the status of the open access
    get     get the latest schedule
    post    post a random schedule

options:
    --config <filename>
"""

def usage():
    import sys
    message = usage_message.format(sys.argv[0])
    print(message)


def parse_arguments(raw_args):
    args = dict(config_file="schedule.cfg")

    if "--config" in raw_args:
        index = raw_args.index("--config")
        args['config_file'] = raw_args[index + 1]
        del raw_args[index:index + 2]

    args['command'] = raw_args[0]

    return args


def main():
    import sys
    try:
        args = parse_arguments(sys.argv[1:])
    except Exception as e:
        print(e)
        usage()
        sys.exit(1)
        
    import config
    config = config.load(args['config_file'])
    schedule = ScheduleService(config['base_url'], config['username'],
                                                   config['password'])

    command = args['command']
    if command == "status":
        schedule.status()
    elif command == "get":
        schedule.get()
    elif command == "post":
        table = generate_random_table()
        schedule.post(table)
    else:
        print("unknown command: " + str(command))
        print()
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
