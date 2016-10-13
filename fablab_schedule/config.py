import logging
import os
from pkg_resources import resource_filename
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


def get_default_config_file_path():
    return resource_filename("fablab_schedule",
                             "conf/" + example_config_filename)


def get_global_config_file_path():
    path = os.path.join(config_dir, config_filename)
    return path


def parse_float_list(text, delimiter=","):
    return [float(value) for value in text.split(delimiter)]


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


def get():
    global _config
    if _config is None:
        parser = configparser.ConfigParser()
        parser.read_file(open(get_default_config_file_path()))
        parser.read(get_global_config_file_path())
        _config = make_config_dict_from_parser(parser)
    return _config


def from_file(filepath):
    parser = configparser.ConfigParser()
    parser.read_file(open(filepath))
    return make_config_dict_from_parser(parser)
