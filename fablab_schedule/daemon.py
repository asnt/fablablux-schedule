import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import os.path
from pkg_resources import resource_filename
import random
import subprocess
import time

import requests

from fablab_schedule import api, config


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


_config = {}


def run_with_camera():
    while True:
        try:
            if is_open_access() or _config['force_open_access']:
                message = "open access : true"
                message += _config['force_open_access'] and " (forced)" or ""
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


def run_without_camera():
    while True:
        try:
            if is_open_access() or _config['force_open_access']:
                message = "open access : true"
                message += _config['force_open_access'] and " (forced)" or ""
                logger.debug(message)
                n_machines = _config['n_machines']
                n_slots = _config['n_slots']
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
    tmp_image_path = '/tmp/capture.png.tmp'
    image_path = '/tmp/capture.png'
    args = ['/opt/vc/bin/raspistill',
            '--output', tmp_image_path,
            '--encoding', 'png',
            '--timeout', '1',
            '--exposure', 'auto',
            '--width', '648',
            '--height', '486',
            ]
    if _config['vertical_flip']:
        args += ['--vflip']
    if _config['horizontal_flip']:
        args += ['--hflip']
    try:
        subprocess.check_output(args, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.output.decode("utf-8"))
    os.rename(tmp_image_path, image_path)

    return True


def get_reference_image_path():
    return resource_filename("fablab_schedule", "data/wall-reference.png")


def process():
    capture_path = "/tmp/capture.png"
    reference_path = get_reference_image_path()
    processed_path = "/tmp/processed.png"
    args = ["fablab_schedule_scan", "-v", capture_path, reference_path,
            processed_path]
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
    service = api.ScheduleService(_config['base_url'])
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
    service = api.ScheduleService(_config['base_url'])
    url = service.url_for("schedule")
    params = dict(username=_config['username'], password=_config['password'])
    json_data = dict(table=table)
    r = requests.post(url, params=params, json=json_data)
    if r.status_code != 200:
        raise RuntimeError("could not post schedule")


def generate_random_table(n_machines, n_slots):
    def randbool():
        bool(random.randint(0, 1))
    table = [[randbool() for __ in range(n_slots)]
             for __ in range(n_machines)]
    return table


def run():
    global _config

    description = "Daemon for the FabLab wall schedule scanner"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-c", "--config", help="alternate config file")
    parser.add_argument("-d", "--disable-camera", action="store_true",
                        help="disable camera grabbing")
    parser.add_argument("-s", "--force-scanning", action="store_true",
                        help="force scanning even outside open access hours")
    args = parser.parse_args()

    if args.config:
        _config = config.load(args.config)
    else:
        _config = config.load_default()

    if args.force_scanning:
        config["force_open_access"] = True

    if args.disable_camera:
        run_without_camera()
    else:
        run_with_camera()


if __name__ == "__main__":
    run()
