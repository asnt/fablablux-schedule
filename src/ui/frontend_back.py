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


n_machines = 7
n_slots = 9
table = [[False] * n_slots for __ in range(n_machines)]
machines = ['MakerBot 1', 'MakerBot 2', 'RepRap', 'Small CNC',
        'Big CNC', 'Laser cutter', 'Vinyl cutter']
t_end = t_start + n_slots
slots = ['{:02d}:00'.format(h) for h in range(t_start, t_end)]

def data():
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

#     image_fname = 'capture.jpg'
# 
#     # get the latest wall image
#     tmp_fname = image_fname + '.tmp'
#     url = '192.168.123.151/'
#     if simulate_capture:
#         url += '?simulate'
#     args = ['wget', url, '-O', tmp_fname,
#             '--timeout=1', '--tries=1']
#     p = subprocess.run(args)
# 
#     if p.returncode == 0:
#         os.rename(tmp_fname, image_fname)
#     else:
#         if p.stderr is not None:
#             err = p.stderr.decode("utf-8")
#         else:
#             err = ''
#         flash('There was an error retrieving the latest live image. ' \
#                 'The table might be outdated.', 'warning')

#     # process the image
#     if use_test_image:
#         fname = 'test_' + image_fname
#     else:
#         fname = image_fname
#     image = ski.io.imread(fname)
#     if rot180:
#         image = np.flipud(np.fliplr(image))
#     ski.io.imsave('before_processing.jpg', image)
#     try:
#         table = scan_table(image)
#         has_table = True
#     except:
#         has_table = False

#     # format results
#     if has_table:
#         machine_names = ['MakerBot 1', 'MakerBot 2', 'RepRap',
#                 'Small CNC', 'Big CNC',
#                 'Laser cutter', 'Vinyl cutter']
#         n_machines, n_slots = table.shape
#         t_end = t_start + n_slots
#         slots = ['{:02d}:00'.format(h) for h in range(t_start, t_end)]
#         machines = machine_names
#         if len(machines) < n_machines:
#             machines += [''] * (n_machines - len(machines))
#         elif len(machines) > n_machines:
#             machines = machines[:n_machines]
#         matrix = table
#         occupation = dict(slots=slots, machines=zip(machines, matrix))
#     else:
#         occupation = None

    occupation = data()
    machines = zip(occupation['machines'], table)
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
    return jsonify(**data())

@frontend.route('/api/occupation', methods=['PUT'])
def api_update_occupation():
    if request.headers['Content-Type'] != 'application/json':
        return bad_request('Invalid content type')
    table = request.json["table"]
    array = np.array(table)
    if array.dtype != bool or array.shape != (n_machines, n_slots):
        return bad_request('Invalid data')
    return jsonify(request.json)
