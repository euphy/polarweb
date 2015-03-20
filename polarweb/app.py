import base64
import json
from flask import Flask, jsonify, render_template, flash, Response, \
    send_file, make_response, request
from flask_assets import Environment, Bundle
from flask_socketio import SocketIO, emit
import gevent
import jinja2
from polarweb.models.machines import Machines
from polarweb.visualization import VisualizationThread


app = Flask(__name__)
assets = Environment(app)

js = Bundle('../bower_components/jquery/dist/jquery.js',
            '../bower_components/bootstrap/dist/js/bootstrap.js',
            '../bower_components/socket.io-client/dist/socket.io.min.js',
            output='packed.js')
assets.register('js_all', js)

css = Bundle('../bower_components/bootstrap/dist/css/bootstrap.css',
             '../templates/polarweb.css',
             output='polarweb.css')
assets.register('polarweb_css', css)

# app.debug = True
app.secret_key = '\x1e\x94)\x06\x08\x14Z\x80\xea&O\x8b\xfe\x1eL\x84\xa3<\xec\x83))\xa6\x8f'
app.streaming = False
socketio = SocketIO(app)


def init_machines():
    app.viz = VisualizationThread()  # Greenlet
    app.machines = Machines(outgoing_event_signaller=outgoing_event_signaller,
                            viz_thread=app.viz)


def format_for_web(target, value):
    command = target.split('-')[0]
    if command in ('queue', 'received_log'):
        env = jinja2.Environment(
            loader=jinja2.PackageLoader('polarweb', 'templates'))
        template = env.get_template('queue.html')
        print "Rendering %s" % target
        return template.render(queue=value)
    else:
        return json.dumps(value)


def outgoing_event_signaller(event=None, target=None, value=None):
    if event is None:
        event = dict()
    if target is not None:
        event['target'] = target
    if value is not None:
        event['value'] = value

    print "Event: %s" % event
    if 'target' not in event and 'value' not in event:
        return False

    try:
        html = format_for_web(event['target'], event['value'])
        socketio.emit('status_update',
                      {'target': event['target'],
                       'html': html},
                      namespace='/api')
    except RuntimeError:
        print "Failed."
        return False
    except Exception as e:
        print "Exception in outgoing_event_signaller: %s" % e.message
        return False

    return True



# ==================================================================
#    Routes for HTML
# ==================================================================

@socketio.on('connect', namespace='/api')
def connect():
    print "in connect()"
    emit('my response', {'data': 'Connected', 'count': 0})

@socketio.on('connect', namespace='/stream')
def connect():
    print "in connect stream()"
    emit('my response', {'data': 'Connected', 'count': 0})


@socketio.on('guess', namespace='/api')
def guess_who(message):
    print "In guess... %s" % message


@app.route('/')
def start():
    print "On"
    return render_template("live.html", machines=app.machines)


@app.route('/offline')
def offline():
    return render_template("offline.html", machines=app.machines)


@app.route('/visualize')
def visualize(state='show'):
    if state is "hide":
        app.streaming = False
    else:
        app.streaming = True


@app.route('/video')
def video_feed():
    app.streaming = True
    app.viz.camera_stream(run=True)
    return render_template('video.html')


@socketio.on('feed', namespace='/stream')
def feed(message):
    while app.streaming:
        v = app.viz.get_jpeg_bytes()
        if v is not None:
            emit('feed_response', {'frame': base64.b64encode(v.getvalue())},
                 namespace='/stream')
        gevent.sleep(0.03)


# ==================================================================
#    API end points. These are all jsony things used to query
#    or send commands to this app.
# ==================================================================
@app.route('/api/m/<machine_name>/calibrate', methods=['POST'])
def calibrate(machine_name):
    print "Calibrating %s" % machine_name
    result = app.machines[machine_name].control_movement({'calibrate': True})
    return jsonify(result)


@app.route('/api/m', methods=['GET'])
def get_machines_states():
    result = {name: app.machines[name].state() for name in app.machines.machine_names}
    return jsonify(result)


@app.route('/api/m/<machine_name>/', methods=['GET'])
def get_machine(machine_name):
    return jsonify(app.machines[machine_name].state())


@app.route('/api/m/<machine_name>/svg', methods=['GET'])
def get_machine_svg(machine_name):
    svg_filename = app.machines[machine_name].get_machine_as_svg()
    resp = make_response(send_file(svg_filename, mimetype='image/svg+xml'))
    resp.cache_control.no_cache = True
    return resp


@app.route('/api/m/<machine_name>/connect', methods=['POST'])
def attempt_to_connect(machine_name):
    result = app.machines[machine_name].start_serial_comms()
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


@app.route('/api/m/<machine_name>/layout/svg', methods=['GET'])
def get_layout_svg(machine_name):
    svg_filename = app.machines[machine_name].get_available_panels_as_svg()
    resp = make_response(send_file(svg_filename, mimetype='image/svg+xml'))
    resp.cache_control.no_cache = True
    return resp


@app.route('/api/m/<machine_name>/layout/<layout_name>', methods=['POST'])
def set_layout(machine_name, layout_name):
    result = app.machines[machine_name].set_layout(page=Machines.default_page['extent'],
                                                   layout_name=layout_name)
    return jsonify(app.machines[machine_name].state())


@app.route('/api/m/<machine_name>/move/routine/<routine_name>', methods=['POST'])
def draw_routine(machine_name, routine_name):
    result = app.machines[machine_name].draw_routine(routine_name)
    return jsonify(app.machines[machine_name].state())


@app.route('/api/m/<machine_name>/drawing/<command>', methods=['POST'])
def control_drawing(machine_name, command):
    """
    Sends commands to control the drawing: 'pause', 'run', 'cancel_page' etc.
    """
    result = app.machines[machine_name].control_drawing(command)
    return jsonify(result)


@app.route('/api/m/<machine_name>/speed', methods=['POST'])
def control_speed(machine_name):
    """
    Sends commands to control the drawing: 'pause', 'run', 'cancel_page' etc.
    """
    result = app.machines[machine_name].control_movement(data={'speed': str(request.form['speed-input']),
                                                               'accel': str(request.form['accel-input'])})
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
    code = result.pop('http_code', 200)
    return jsonify(result), code


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

@app.route('/api/m/<machine_name>/restart', methods=['POST'])
def control_machine(machine_name):
    """ Send commands to control the image acquire behaviour: 'run', 'pause'
    """
    result = app.machines[machine_name].control_machine('restart')
    return jsonify(result)


init_machines()
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=80)
