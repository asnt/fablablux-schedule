#!/usr/bin/env python

import json
import logging
from logging.handlers import RotatingFileHandler
import os
import os.path
import random
import subprocess
import time

import requests

import api
import config


def get_script_dir():
    return os.path.dirname(os.path.realpath(__file__))


def build_logger():
    logfile = os.path.join(get_script_dir(), "schedule.log")

    logger = logging.getLogger("schedule")
    logger.setLevel(logging.DEBUG)

    file_handler = RotatingFileHandler(logfile, maxBytes=5e6, backupCount=1)
    file_handler.setLevel(logging.DEBUG)

    format = '%(asctime)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(format)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger

logger = build_logger()


conf = {}


def run():
    while True:
        try:
            if is_open_access() or conf['force_open_access']:
                message = "open access : true"
                message += conf['force_open_access'] and " (forced)" or ""
                logger.debug(message)
                scan()
            else:
                logger.debug("open access : false")
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("terminate by keyboard interrupt")
            break
        except Exception as e:
            logger.error(repr(e))
            pass


def run_no_camera():
    while True:
        try:
            if is_open_access() or conf['force_open_access']:
                message = "open access : true"
                message += conf['force_open_access'] and " (forced)" or ""
                logger.debug(message)
                n_machines = conf['n_machines']
                n_slots = conf['n_slots']
                post_table(generate_random_table(n_machines, n_slots))
            else:
                logger.debug("open access : false")
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("terminate by keyboard interrupt")
            break
        except Exception as e:
            logger.error("error: " + repr(e))
            pass


def scan():
    logger.debug("grab")
    grab()

    logger.debug("process")
    output = process()

    logger.debug("parse table")
    table = parse_table(output) 

    logger.debug("post table")
    post_table(table)


def grab():
    """Grab an image with the camera.

    Raise RuntimeError if the command failed
    """
    tmp_image_name = '/tmp/capture.png.tmp'
    image_name = '/tmp/capture.png'
    args = ['/opt/vc/bin/raspistill',
            '--output', tmp_image_name,
            '--encoding', 'png',
            '--timeout', '1',
            '--exposure', 'auto',
            '--width', '648',
            '--height', '486',
            ]
    if conf['vertical_flip']:
        args += ['--vflip']
    if conf['horizontal_flip']:
        args += ['--hflip']
    try:
        return_code = subprocess.check_output(args, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.output.decode("utf-8"))
    os.rename(tmp_image_name, image_name)

    return True


def process():
    capture_path = "/tmp/capture.png"
    #capture_path = "/home/alarm/schedule-scanner/data/wall-test.png"
    reference_path = "/home/alarm/schedule-scanner/data/wall-reference.png"
    processed_path = "/tmp/processed.png"
    args = ["python2", "/home/alarm/schedule-scanner/scanner.py", "-d",
            capture_path, reference_path, processed_path]
    output_bytes = subprocess.check_output(args)
    output = output_bytes.decode("ascii")

    return output


def parse_table(table_string): 
    """Parse a table of space-separated boolean values into a 2d list."""
    rows = table_string.split("\n")
    start = rows.index("<table>")
    end = rows.index("</table>")
    rows = rows[start + 1:end]
    table = [[x == 'X' for x in row.strip().split(" ")]
                for row in rows if len(row) > 0]
    return table


def is_open_access():
    """Returns true during open access hours."""
    service = api.ScheduleService(conf['base_url'])
    url = service.url_for("status")
    r = requests.get(url)
    if r.status_code != 200:
        raise RuntimeError("could not get open access status")
    data = r.json()
    # XXX: Needs a second JSON parsing. Does the server return correct JSON?
    data = json.loads(data)
    is_open = data.get('open_access', False)
    return is_open
        

def post_table(table):
    service = api.ScheduleService(conf['base_url'])
    url = service.url_for("schedule")
    params = dict(username=conf['username'], password=conf['password'])
    json_data = dict(table=table)
    r = requests.post(url, params=params, json=json_data)
    if r.status_code != 200:
        raise RuntimeError("could not post schedule")


def generate_random_table(n_machines, n_slots):
    randbool = lambda: bool(random.randint(0, 1))
    table = [[randbool() for __ in range(n_slots)]
             for __ in range(n_machines)]
    return table


def main():
    import sys
    args = sys.argv[1:]

    no_camera = False
    if "--no-camera" in args:
        del args[args.index("--no-camera")]
        no_camera = True
    if "--config" in args:
        index = args.index("--config")
        conf_filename = args[index + 1]
        del args[index + 1]
        del args[index]
    else:
        conf_filename = os.path.join(get_script_dir(), "./conf/schedule.cfg")

    conf = config.load(conf_filename)

    if "--force-open-access" in args:
        del args[args.index("--force-open-access")]
        conf['force_open_access'] = True

    if no_camera:
        run_no_camera()
    else:
        run()


if __name__ == "__main__":
    main()
