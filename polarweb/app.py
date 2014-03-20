from flask import Flask, jsonify, render_template
from flask_assets import Environment, Bundle
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

@app.before_first_request
def init_machines():
    app.machines = Machines()

# ==================================================================
#    Routes for HTML
# ==================================================================
@app.route('/')
def start():
    return render_template("index.html", machines=app.machines)


# ==================================================================
#    API end points. These are all jsony things used to query
#    or send commands to this app.
# ==================================================================
@app.route('/api/m/<machine_name>/calibrate')
def calibrate(machine_name):
    print "Calibrating %s" % machine_name
    result = app.machines[machine_name].send_calibrate()
    return jsonify(result)


@app.route('/api/m', methods=['GET'])
def get_machines_states():
    result = {name: app.machines[name].state() for name in app.machines.machine_names}
    return jsonify(result)


@app.route('/api/m/<machine_name>/', methods=['GET'])
def get_machine(machine_name):
    return jsonify(app.machines[machine_name].state())


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
    return result


# Control whether machine will acquire a new image immediately
@app.route('/api/m/<machine_name>/acquire/<command>', methods=['POST'])
def control_acquire(machine_name, command):
    """ Send commands to control the image acquire behaviour: 'run', 'pause'
    """
    result = app.machines[machine_name].control_acquire(command)
    return result


if __name__ == '__main__':
    app.run()