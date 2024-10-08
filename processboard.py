from flask import Flask, send_from_directory, redirect, current_app, request
from flask_socketio import SocketIO, send, emit
import json, uuid, threading, requests, eventlet, os
from enum import Enum
from typing import Union

# Status types
class Status(Enum):
    COMPLETE = 1
    FAILED = -1
    WAITING = 0
    WORKING = 0.5
    INFORMATION = 2

class Complications(Enum):
    BASIC = "BasicLoading"
    BATCH = "BatchLoading"
    TIMER = "TimeLoading"

# Page item classes
class Loader:
    def __init__(self, name, value: Union[str, int, float] = 0, end: Union[str, int, float] = 0, complication = Complications.BASIC, description = "", tag = "", status = Status.WAITING):
        self.state = {}

        self.state['type'] = complication.value
        self.state['id'] = str(uuid.uuid4())

        # val params
        self.state['value'] = value
        self.state['end'] = end

        # text params
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

class BasicLoading(Loader):
    def __init__(self, name, description = "", tag = "", status = Status.WAITING):
        super(BasicLoading, self).__init__(name, complication = Complications.BASIC, description = description, tag = tag, status = status)

class BatchLoading(Loader):
    def __init__(self, name, value: Union[int, float], end: Union[int, float], description = "", tag = "", status = Status.WAITING):
        super(BatchLoading, self).__init__(name, value, end, complication = Complications.BATCH, description = description, tag = tag, status = status)

class TimeLoading(Loader):
    def __init__(self, name, value: str, end: str, description = "", tag = "", status = Status.WAITING):
        super(TimeLoading, self).__init__(name, value, end, complication = Complications.TIMER, description = description, tag = tag, status = status)

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

    def sendNotification(self, title, description, timeout = 5000):
        self._relay_caller('ev_notification', {'show': 1, 'title': title, 'description': description, 'timeout': timeout})

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

        def next(self, status=Status.COMPLETE, final=Status.WORKING, search=Status.WORKING):
            if len(list(filter(lambda x: x['status'] != Status.WAITING.value, self.elems))) == 0:
                self.elems[0]['status'] = final.value

                self.onChg(self)
                return True

            for idx, item in enumerate(self.elems):
                if item['status'] == search.value:
                    self.elems[idx]['status'] = status.value

                    if idx+1 < len(self.elems):
                        self.elems[idx+1]['status'] = final.value

                    self.onChg(self)
                    return True
            return False

        def __str__(self):
            return json.dumps(self.elems)

        def __obj__(self):
            return self.elems

    # socket.io communication
    @socketio.on('ev_get_items')
    def handle_message(data):
        current_app._self_ref.socketio.emit('ev_update_items', current_app._self_ref.items.__obj__())

    # integrated server stop methods
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

    # circuitous messaging relay
    @app.route('/relay_msg')
    def _relay_handler():
        ev = str(request.args.get('ev'))
        payload = str(request.args.get('content'))

        current_app._self_ref.socketio.emit(ev, json.loads(payload))
        return ""

    def _relay_caller(self, ev, payload):
        try:
            requests.get("http://{}:{}/relay_msg".format(self.host, self.port),
                params={'ev': ev, 'content': json.dumps(payload)})
        except:
            pass

    # static file serving
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
