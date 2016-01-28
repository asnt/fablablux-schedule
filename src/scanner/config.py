import configparser


def load(filename):
    parser = configparser.ConfigParser()
    parser.read(filename)

    config = {}
    config["username"] = parser.get("api", "username")
    config["password"] = parser.get("api", "password")
    config["base_url"] = parser.get("api", "base_url")

    return config
