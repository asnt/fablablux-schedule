import logging
import os
from pkg_resources import resource_stream, resource_string
try:
    # Python 3
    import configparser
except ImportError:
    # Python 2
    import ConfigParser as configparser


logger = logging.getLogger(__name__)


config_dir = "/etc/fablab_schedule/"
config_filename = "fablab_schedule.cfg"
example_config_filename = "fablab_schedule.cfg.example"


_config = None


def get_default_config_string():
    return resource_string("fablab_schedule",
                           "conf/" + example_config_filename)


def get_default_config_stream():
    return resource_stream("fablab_schedule",
                           "conf/" + example_config_filename)


def get_config_file_path():
    path = os.path.join(config_dir, config_filename)
    return path


def config_file_exists():
    return os.path.exists(get_config_file_path())


def create_default_config_file(force=False):
    if config_file_exists() and not force:
        return
    config_string = get_default_config_string()
    config_path = os.path.join(config_dir, config_filename)
    with open(config_path, "w") as f:
        f.write(config_string)


def get():
    global _config
    path = get_config_file_path()
    if _config is None:
        _config = load(path)
    return _config


def load_default():
    logger.info("load default config")
    config_string = get_default_config_string().decode("utf-8")
    return load(config_string=config_string)


def load(filename="", config_string=None):
    logger.info("load config")

    parser = configparser.ConfigParser()
    if config_string is not None:
        parser.read_string(config_string)
    parser.read(filename)

    config = {}
    config["username"] = parser.get("api", "username")
    config["password"] = parser.get("api", "password")
    config["base_url"] = parser.get("api", "base_url")

    config["n_machines"] = parser.getint("table", "n_machines")
    config["n_slots"] = parser.getint("table", "n_slots")
    row_offsets = parser.get("table", "row_offsets")
    config["row_offsets"] = parse_float_list(row_offsets)
    column_offsets = parser.get("table", "column_offsets")
    config["column_offsets"] = parse_float_list(column_offsets)
    config["slot_size"] = parser.getint("table", "slot_size")

    config["vertical_flip"] = parser.getboolean("camera", "vertical_flip")
    config["horizontal_flip"] = parser.getboolean("camera", "horizontal_flip")

    return config


def parse_float_list(text, delimiter=","):
    return [float(value) for value in text.split(delimiter)]
