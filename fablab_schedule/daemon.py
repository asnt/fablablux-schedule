import argparse
import errno
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import os.path
from pkg_resources import resource_filename
import random
import subprocess
import tempfile
import time

import requests

from fablab_schedule import api, config, scanner


def get_log_file_path():
    log_dir = "/var/log/"
    log_file = "fablab_schedule.log"
    path = os.path.join(log_dir, log_file)
    return path


def build_logger():
    log_path = get_log_file_path()

    logger = logging.getLogger("schedule")
    logger.setLevel(logging.DEBUG)
    format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    logging.basicConfig(format=format)

    try:
        file_handler = RotatingFileHandler(log_path, maxBytes=5e6,
                                           backupCount=1)
    except (OSError, IOError) as e:
        # OSError for Python 3
        # IOErro for Python 2
        if e.errno == errno.EACCES:
            logger.warning("cannot open log file %s: %s", log_path, e.strerror)
        else:
            raise(e)
    else:
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(format)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

logger = build_logger()


_config = {}


def grab(image_path):
    """Grab an image with the camera.

    Parameters
    ----------
    image_path: string
        File path where to store the image.

    Raises
    ------
    RuntimeError if the subprocess call fails.
    """
    tmp_image_path = tempfile.TemporaryFile()
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
    return resource_filename("fablab_schedule", "data/wall-reference.jpg")


def get_test_image_path():
    return resource_filename("fablab_schedule", "data/wall-test.jpg")


def process(capture_path):
    reference_path = get_reference_image_path()
    detector = "brisk"
    schedule, unwarped = scanner.scan(reference_path, capture_path, detector)
    return schedule


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
        raise RuntimeError("cannot get open access status")
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
        raise RuntimeError("cannot post schedule: {:s}".format(r.text))


def generate_random_table(n_machines, n_slots):
    def randbool():
        bool(random.randint(0, 1))
    table = [[randbool() for __ in range(n_slots)]
             for __ in range(n_machines)]
    return table


def mainloop():
    iteration_delay_sec = 1.0   # seconds
    while True:
        t0 = time.perf_counter()
        try:
            if not _config['force_scan']:
                if not is_open_access():
                    logger.debug("open access : false")
                    time.sleep(1.0)
                    continue

            message = "open access: true"
            message += " (forced)" if _config['force_scan'] else ""
            logger.debug(message)

            if _config['use_test_image']:
                input_file = get_test_image_path()
            else:
                input_file = "/tmp/capture.png"
                grab(input_file)

            schedule_table = process(input_file)

            if not _config['disable_post']:
                post_table(schedule_table)
        except KeyboardInterrupt:
            logger.info("terminate by keyboard interrupt")
            break
        except Exception as e:
            logger.error(repr(e), exc_info=True)
            pass

        t1 = time.perf_counter()
        elapsed = t1 - t0
        if elapsed < iteration_delay_sec:
            time.sleep(iteration_delay_sec - elapsed)


def run():
    global _config

    description = "Daemon for the FabLab wall schedule scanner"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-c", "--config", help="alternate config file")
    parser.add_argument("-s", "--force-scan", action="store_true",
                        help="force scan even out of open access hours")
    parser.add_argument("-t", "--test-image", action="store_true",
                        help="use bundled test image instead of video capture")
    parser.add_argument("-p", "--disable-post", action="store_true",
                        help="disable posting the table to the remote peer")
    args = parser.parse_args()

    if args.config:
        _config = config.from_file(args.config)
    else:
        _config = config.get()

    _config["force_scan"] = args.force_scan
    _config['use_test_image'] = args.test_image
    _config['disable_post'] = args.disable_post

    mainloop()


if __name__ == "__main__":
    run()
