import logging
import os
from pkg_resources import resource_stream, resource_string
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
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
    if _config is None:
        _config = load_default()
        path = get_config_file_path()
        if os.path.exists(path):
            _config.update(load_from_file(path))
    return _config


def load_default():
    logger.info("load default config")
    default_config_string = get_default_config_string().decode("utf-8")
    return load_from_string(default_config_string)


def load_from_string(config_string):
    logger.info("load config from string")
    parser = configparser.ConfigParser()
    try:
        parser.read_string(config_string)
    except AttributeError:
        # Python 2
        config_stream = StringIO(config_string)
        parser.readfp(config_stream)
    return make_config_dict_from_parser(parser)


def load_from_file(filename):
    logger.info("load config file %s", filename)
    parser = configparser.ConfigParser()
    parser.read(filename)
    return make_config_dict_from_parser(parser)


def make_config_dict_from_parser(parser):
    config = {}
    if "api" in parser:
        config["username"] = parser.get("api", "username")
        config["password"] = parser.get("api", "password")
        config["base_url"] = parser.get("api", "base_url")
    if "table" in parser:
        config["n_machines"] = parser.getint("table", "n_machines")
        config["n_slots"] = parser.getint("table", "n_slots")
        row_offsets = parser.get("table", "row_offsets")
        config["row_offsets"] = parse_float_list(row_offsets)
        column_offsets = parser.get("table", "column_offsets")
        config["column_offsets"] = parse_float_list(column_offsets)
        config["slot_size"] = parser.getint("table", "slot_size")
    if "camera" in parser:
        config["vertical_flip"] = parser.getboolean("camera", "vertical_flip")
        config["horizontal_flip"] = parser.getboolean("camera",
                                                      "horizontal_flip")
    return config


def parse_float_list(text, delimiter=","):
    return [float(value) for value in text.split(delimiter)]
