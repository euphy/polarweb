from flask import Flask, jsonify, render_template
from polarweb.models.machine import Machines

app = Flask(__name__)
app.debug = True
app.machines = Machines()


@app.route('/')
def start():
    return render_template("index.html", machines=app.machines)


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


@app.route('/api/m/<machine_name>/layout/<layout_name>', methods=['POST'])
def set_page(machine_name, page_name):
    return jsonify(app.machines[machine_name].set_page(page_name=page_name))


@app.route('/api/m/<machine_name>/layout', methods=['GET'])
def get_layout(machine_name):
    print app.machines[machine_name].current_layout['name']
    return jsonify({'name': app.machines[machine_name].current_layout['name']})


@app.route('/api/m/<machine_name>/layout/<layout_name>', methods=['POST'])
def set_layout(machine_name, layout_name):
    return jsonify(app.machines[machine_name].set_layout(layout_name=layout_name))

@app.route('/api/m/<machine_name>/drawing/<state_to_set>', methods=['POST'])
def control_drawing(machine_name, state_to_set):
    result = app.machines[machine_name].control_drawing(state_to_set)
    return result

@app.route('/api/m/<machine_name>/acquire/<state_to_set>', methods=['POST'])
def control_acquire(machine_name, state_to_set):
    result = app.machines[machine_name].control_acquire(state_to_set)
    return result

if __name__ == '__main__':
    app.run()