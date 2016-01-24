import configparser

import numpy as np
import requests


def load_config(filename):
    parser = configparser.ConfigParser()
    parser.read(filename)

    config = {}
    config["username"] = parser.get("api", "username")
    config["password"] = parser.get("api", "password")
    config["base_url"] = parser.get("api", "base_url")

    return config


class ScheduleService:

    base_route = "?rest_route=/open-access/v1"
    routes = {
            "status": "/",
            "schedule": "/machine-schedule",
    }

    def __init__(self, base_url):
        if not base_url.endswith("/"):
            base_url = base_url + "/"
        self.base_url = base_url + ScheduleService.base_route

    def url_for(self, service):
        if service not in ScheduleService.routes:
            raise ValueError("uknown service {}".format(service))
        route = ScheduleService.routes[service]
        return self.base_url + route


def status(config):
    service = ScheduleService(config["base_url"])
    url = service.url_for("status")
    r = requests.get(url)

    print(url)
    print('status: ', r.status_code)
    print(r.text)


def get_table(config):
    service = ScheduleService(config["base_url"])
    url = service.url_for("schedule")
    params = dict(username=config["username"], password=config["password"])
    r = requests.get(url, params=params)

    print(url)
    print('get schedule: ', r.status_code)
    print(r.text)


def post_table(table, config):
    service = ScheduleService(config["base_url"])
    url = service.url_for("schedule")
    json_data = dict(table=table)
    params = dict(username=config["username"], password=config["password"])
    r = requests.post(url, params=params, json=json_data)

    print(url)
    print('post schedule: ', r.status_code)
    print(r.json())


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
        
    config = load_config(config_filename)

    if len(args) == 0:
        usage()
        sys.exit(1)

    cmd = args[0]
    if cmd == "status":
        status(config)
    elif cmd == "get":
        get_table(config)
    elif cmd == "post":
        table = np.random.randint(2, size=(7, 9)).astype(bool).tolist()
        post_table(table, config)
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
