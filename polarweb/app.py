from flask import Flask, jsonify, render_template, flash, Response
from flask_assets import Environment, Bundle
import time
from polarweb.models.machine import Machines



app = Flask(__name__)
assets = Environment(app)

js = Bundle('../bower_components/jquery/dist/jquery.js',
            '../bower_components/bootstrap/dist/js/bootstrap.js',
            # filters='jsmin',
            output='packed.js')
assets.register('js_all', js)

css = Bundle('../bower_components/bootstrap/dist/css/bootstrap.css',
             output='bootstrap.css')
assets.register('bootstrap', css)

app.debug = True
app.secret_key = '\x1e\x94)\x06\x08\x14Z\x80\xea&O\x8b\xfe\x1eL\x84\xa3<\xec\x83))\xa6\x8f'


@app.before_first_request
def init_machines():
    app.machines = Machines()

# ==================================================================
#    Routes for HTML
# ==================================================================
@app.route('/')
def start():
    flash("Welcome to the Polargraph web service!", 'alert-success')
    return render_template("index.html", machines=app.machines)


# ==================================================================
#    API end points. These are all jsony things used to query
#    or send commands to this app.
# ==================================================================
@app.route('/api/m/<machine_name>/calibrate', methods=['POST'])
def calibrate(machine_name):
    print "Calibrating %s" % machine_name
    result = app.machines[machine_name].calibrate()
    return jsonify(result)


@app.route('/api/m', methods=['GET'])
def get_machines_states():
    result = {name: app.machines[name].state() for name in app.machines.machine_names}
    return jsonify(result)


@app.route('/api/m/<machine_name>/', methods=['GET'])
def get_machine(machine_name):
    return jsonify(app.machines[machine_name].state())


@app.route('/api/m/<machine_name>/connect', methods=['POST'])
def attempt_to_connect(machine_name):
    result = app.machines[machine_name].setup_comm_port()
    return jsonify({'connected': result})

@app.route('/api/m/<machine_name>/page', methods=['GET'])
def get_page(machine_name):
    return jsonify({'name': app.machines[machine_name].current_page['name']})


@app.route('/api/m/<machine_name>/page/<page_name>', methods=['POST'])
def set_page(machine_name, page_name):
    return jsonify(app.machines[machine_name].set_page(page_name=page_name))


@app.route('/api/m/<machine_name>/layout', methods=['GET'])
def get_layout(machine_name):
    print app.machines[machine_name].current_layout['name']
    return jsonify({'name': app.machines[machine_name].current_layout['name']})


@app.route('/api/m/<machine_name>/layout/<layout_name>', methods=['POST'])
def set_layout(machine_name, layout_name):
    return jsonify(app.machines[machine_name].set_layout(layout_name=layout_name))


@app.route('/api/m/<machine_name>/drawing/<command>', methods=['POST'])
def control_drawing(machine_name, command):
    """
    Sends commands to control the drawing: 'pause', 'run', 'cancel_page' etc.
    """
    result = app.machines[machine_name].control_drawing(command)
    return jsonify(result)

@app.route('/api/m/<machine_name>/pen/<command>', methods=['POST'])
def control_pen(machine_name, command):
    """
     Sends pen-type commands to the drawing: 'pen_up', 'pen_down' etc.
    """
    result = app.machines[machine_name].control_pen(command)
    return jsonify(result)


# Control whether machine will acquire a new image immediately
@app.route('/api/m/<machine_name>/acquire/<command>', methods=['POST'])
def control_acquire(machine_name, command):
    """ Send commands to control the image acquire behaviour: 'run', 'pause'
    """
    result = app.machines[machine_name].control_acquire(command)
    return jsonify(result)

@app.route('/api/m/<machine_name>/acquire', methods=['GET'])
def get_loaded_paths(machine_name):
    """ Returns the paths of the current artwork.
    """
    result = app.machines[machine_name].paths
    return jsonify({'paths': result})


@app.route('/api/m/<machine_name>/queue/<response_format>', methods=['GET'])
def queue(machine_name, response_format='json'):
    """  Returns the command queue as a list
    """
    result = {'queue': list(app.machines[machine_name].queue)}
    if response_format == 'html':
        return render_template("queue.html", queue=result['queue'])
    else:
        return jsonify(result)


@app.route('/api/m/<machine_name>/incoming/<response_format>', methods=['GET'])
def incoming(machine_name, response_format='json'):
    """  Returns the command queue as a list
    """
    result = {'queue': list(app.machines[machine_name].received_log)[-20:]}
    if response_format == 'html':
        return render_template("queue.html", queue=result['queue'])
    else:
        return jsonify(result)

if __name__ == '__main__':
    app.run()