from flask import Flask, send_from_directory, redirect, current_app
from flask_socketio import SocketIO, send, emit
import json, uuid, threading, requests, eventlet, os
from enum import Enum

# Status types
class Status(Enum):
    COMPLETE = 1
    FAILED = -1
    WAITING = 0
    WORKING = 0.5
    INFORMATION = 2

# Page item classes
class BasicLoading:
    def __init__(self, name, description = "", tag = "", status = Status.WAITING):
        self.state = {}

        self.state['type'] = 'BasicLoading'
        self.state['id'] = str(uuid.uuid4())

        # params
        self.state['status'] = status.value
        self.state['name'] = name
        self.state['description'] = description
        self.state['tag'] = tag


    def getId(self):
        return self.state['id']

    def __obj__(self):
        return self.state

    def __str__(self) -> str:
        return json.dumps(self.state)

class BatchLoading:
    def __init__(self, name, value = 0, end = 0, description = "", tag = "", status = Status.WAITING):
        self.state = {}

        self.state['type'] = 'BatchLoading'
        self.state['id'] = str(uuid.uuid4())

        # params
        self.state['value'] = value
        self.state['end'] = end

        self.state['status'] = status.value
        self.state['name'] = name
        self.state['description'] = description
        self.state['tag'] = tag


    def getId(self):
        return self.state['id']

    def __obj__(self):
        return self.state

    def __str__(self) -> str:
        return json.dumps(self.state)

class TimeLoading:
    def __init__(self, name, value: str, end: str, description = "", tag = "", status = Status.WAITING):
        self.state = {}

        self.state['type'] = 'TimeLoading'
        self.state['id'] = str(uuid.uuid4())

        # params
        self.state['value'] = value
        self.state['end'] = end

        self.state['status'] = status.value
        self.state['name'] = name
        self.state['description'] = description
        self.state['tag'] = tag

    def getId(self):
        return self.state['id']

    def __obj__(self):
        return self.state

    def __str__(self) -> str:
        return json.dumps(self.state)

# Background server class
class ProcessBoard:
    # private internals
    app = Flask(__name__)
    socketio = SocketIO(app)
    _proc = None

    def _server(self):
        self.socketio.run(
            self.app,
            host=self.host,
            port=self.port,
            debug=True,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )

    def stop(self):
        if self._proc is not None:
            try:
                requests.get("http://{}:{}/stop".format(self.host, self.port))
            except:
                pass

            self._proc.join()
            self._proc = None

    def start(self):
        self._proc = threading.Thread(target=self._server, args=())
        self._proc.daemon = True
        self._proc.start()

    # web UI routes
    class BoardItems:
        def __init__(self, onChg=lambda: 0):
            self.elems = []
            self.onChg = onChg

        def add(self, elem):
            if isinstance(elem, list):
                ids = []
                for el in elem:
                    obj = el.__obj__()
                    self.elems.append(obj)
                    ids.append(obj['id'])

                self.onChg(self)
                return ids
            else:
                obj = elem.__obj__()
                self.elems.append(obj)

                self.onChg(self)
                return obj['id']

        def remove(self, id):
            for idx, el in enumerate(self.elems):
                if el['id'] == id:
                    del self.elems[idx]

                    self.onChg(self)
                    return True
            return False

        def clear(self):
            self.elems = []

        def setParam(self, id, key, value):
            for idx, el in enumerate(self.elems):
                if el['id'] == id:
                    self.elems[idx][key] = value

                    self.onChg(self)
                    return True
            return False

        def setValue(self, id, value):
            return self.setParam(id, 'value', value)

        def setStatus(self, id, status=Status.COMPLETE):
            return self.setParam(id, 'status', status.value)

        def __str__(self):
            return json.dumps(self.elems)

        def __obj__(self):
            return self.elems

    # socket.io communication
    @socketio.on('ev_get_items')
    def handle_message(data):
        current_app._self_ref.socketio.emit('ev_update_items', current_app._self_ref.items.__obj__())

    # integrated HTTP routes
    @app.route('/stop')
    def _stop_handler():
        current_app._self_ref.socketio.stop()

    @app.route('/stop_all')
    def _stop_all_handler():
        os._exit(1)

    @app.route('/force')
    def _force_handler():
        current_app._self_ref.socketio.emit('ev_update_items', current_app._self_ref.items.__obj__())
        return ""

    def _force_caller(self, _):
        try:
            requests.get("http://{}:{}/force".format(self.host, self.port))
        except:
            pass

    @app.route('/pb/<path:path>')
    def _static_handler(path):
        return send_from_directory('board/public/', path)

    # MUST go last
    def __init__(self, port = 8080, host = '127.0.0.1'):
        self.app.config['SECRET_KEY'] = str(uuid.uuid4())
        self.host = host
        self.port = port
        self.items = self.BoardItems(onChg=self._force_caller)
        self.app._self_ref = self

        # add lambda routes for flask
        self.app.add_url_rule('/', view_func=lambda: redirect('/pb/index.html'))
