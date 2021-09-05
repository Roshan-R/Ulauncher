import sys
import logging
import os
import os.path

import gi

gi.require_versions({
    "Gio": "2.0",
    "GLib": "2.0",
    "GObject": "2.0",
})
from gi.repository import GLib, Gio, GObject

from ulauncher.utils.framer import PickleFramer

log = logging.getLogger(__name__)


class InvalidStateError(RuntimeError):
    """
    Raised if a method is called when the object is in an invalid state for the request.
    """


class Server(GObject.GObject):
    __gsignals__ = {
        "client_connected": (GObject.SignalFlags.RUN_FIRST, None, (PickleFramer,)),
        "client_disconnected": (GObject.SignalFlags.RUN_FIRST, None, (PickleFramer,)),
        "message_received": (GObject.SignalFlags.RUN_FIRST, None, (PickleFramer, object,))
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.socket_path = None

        self.service = Gio.SocketService.new()
        self.service.connect("incoming", self.handle_incoming)

    def set_socket_path(self, socket_path):
        if self.socket_path:
            raise InvalidStateError("Socket already configured for this object, create a new one before calling set_socket_path()")

        self.socket_path = socket_path

        if os.path.exists(socket_path):
            log.debug("Removing existing socket path %s", socket_path)
            os.unlink(socket_path)

        self.service.add_address(
            Gio.UnixSocketAddress.new(socket_path),
            Gio.SocketType.STREAM,
            Gio.SocketProtocol.DEFAULT,
            None
        )
        self.clients = {}

    def handle_incoming(self, service, conn, source):
        log.debug("Incoming: %s %s", conn, source)
        framer = PickleFramer()
        framer.connect("closed", self.handle_close)
        framer.connect("message_parsed", self.handle_message)
        framer.set_connection(conn)
        self.clients[id(framer)] = framer
        self.emit("client_connected", framer)

    def handle_close(self, framer):
        log.debug("Connection closed, cleaning up %s", framer)
        self.clients.pop(id(framer))
        self.emit("client_disconnected", framer)

    def handle_message(self, framer, obj):
        log.debug("Server received %s %s", obj, framer)
        self.emit("message_received", framer, obj)


class Client(GObject.GObject):
    __gsignals__ = {
        "message_received": (GObject.SignalFlags.RUN_FIRST, None, (PickleFramer, object,)),
        "closed": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.client = Gio.SocketClient()
        self.socket_path = None

    def set_socket_path(self, socket_path):
        if self.socket_path:
            raise InvalidStateError("Socket already configured for this object, create a new one before calling set_socket_path()")
        self.socket_path = socket_path
        log.debug("Creating a socket connection for %s", socket_path)
        self.conn = self.client.connect(Gio.UnixSocketAddress.new(socket_path), None)
        if not self.conn:
            raise RuntimeError(f"Failed to connect to socket_path {socket_path}" )
        log.debug("Create the framer")
        self.framer = PickleFramer()
        self.framer.connect("message_parsed", self.handle_message)
        self.framer.set_connection(self.conn)

    def send(self, obj):
        self.framer.send(obj)

    def handle_message(self, framer, obj):
        log.debug("Client received %s", obj)
        self.emit("message_received", framer, obj)

    def handle_close(self, framer):
        self.framer = None
        self.emit("closed")

    def close(self):
        if self.framer:
            self.framer.close()
