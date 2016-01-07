from datetime import datetime
import os
import subprocess

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request)
from flask_bootstrap import __version__ as FLASK_BOOTSTRAP_VERSION
from flask_nav.elements import Navbar, View, Subgroup, Link, Text, Separator
from markupsafe import escape
import numpy as np

from .nav import nav


frontend = Blueprint('frontend', __name__)

nav.register_element('frontend_top', Navbar(
    View('FabLab Luxembourg', '.index'),
))


weekday = 4 # Thursday
t_start = 14
t_end = 22

def is_open():
    now = datetime.now()
    if now.weekday() == weekday and now.hour >= t_start and now.hour < t_end:
        return True
    return False


data_filename = "data.txt"
n_machines = 7
n_slots = 9
default_table = np.zeros((n_machines, n_slots), dtype=bool)
machines = ['MakerBot 1', 'MakerBot 2', 'RepRap', 'Small CNC',
        'Big CNC', 'Laser cutter', 'Vinyl cutter']
t_end = t_start + n_slots
slots = ['{:02d}:00'.format(h) for h in range(t_start, t_end)]

def create_table():
    global default_table
    save_table(default_table)
    return default_table

def load_table():
    if os.path.exists(data_filename):
        table = np.loadtxt(data_filename, dtype=bool)
    else:
        table = create_table()
    return table.tolist()

def save_table(table):
    np.savetxt(data_filename, table, fmt='%d')

def occupation_data():
    table = load_table()
    occupation = dict(slots=slots, machines=machines, table=table)
    return occupation


@frontend.route('/')
def index():
    use_test_image = 'test_image' in request.args
    rot180 = 'rot180' in request.args
    force_open = 'force_open' in request.args
    simulate_capture = 'simulate_capture' in request.args

    if force_open:
        status = True
    else:
        status = is_open()

    occupation = occupation_data()
    machines = zip(occupation['machines'], occupation['table'])
    occupation = dict(slots=occupation['slots'], machines=machines)

    return render_template('index.html', status=status,
                            occupation=occupation)


@frontend.route('/main-site')
def main_site():
    return redirect('http://www.fablablux.org')


def bad_request(message="Bad request"):
    data = dict(status=400, message=message)
    resp = jsonify(**data)
    resp.status_code = 400
    return resp


@frontend.route('/api/status', methods=['GET'])
def api_get_status():
    return jsonify(status=is_open)

@frontend.route('/api/occupation', methods=['GET'])
def api_get_occupation():
    return jsonify(**occupation_data())

@frontend.route('/api/occupation', methods=['PUT'])
def api_update_occupation():
    if request.headers['Content-Type'] != 'application/json':
        return bad_request('Invalid content type')
    table = request.json["table"]
    array = np.array(table)
    if array.dtype != bool or array.shape != (n_machines, n_slots):
        return bad_request('Invalid data')
    save_table(table)
    return jsonify(request.json)
