try:
    # Python 3
    import configparser
except ImportError:
    # Python 2
    import ConfigParser as configparser


filename = "schedule.cfg"

_config = None


def get(filename=filename):
    global _config
    if _config is None:
        _config = load(filename)
    return _config


def load(filename):
    parser = configparser.ConfigParser()
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

    config["vertical_flip"] = parser.getbool("camera", "vertical_flip")
    config["horizontal_flip"] = parser.getbool("camera", "horizontal_flip")

    return config


def parse_float_list(text, delimiter=","):
    return [float(value) for value in text.split(delimiter)]
