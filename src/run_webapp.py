#!/usr/bin/env python

import ui


def run():
    app = ui.create_app()
    app.run(host='192.168.8.1', port=5000)
    #app.run(host='192.168.178.33', port=5000)


if __name__ == "__main__":
    run()
