import logging
from functools import partial
from ulauncher.api.server.port_finder import find_unused_port
from ulauncher.api.server.ExtensionController import ExtensionController
from ulauncher.api.shared.socket_path import get_socket_path
from ulauncher.api.shared.event import RegisterEvent
from ulauncher.utils.decorator.singleton import singleton
from ulauncher.utils.unix_stream import Server

logger = logging.getLogger(__name__)


class ExtensionServer:

    @classmethod
    @singleton
    def get_instance(cls):
        return cls()

    def __init__(self):
        self.server = None
        self.socket_path = get_socket_path()
        self.controllers = {}

    def start(self):
        """
        Starts extension server
        """
        if self.server:
            raise ServerIsRunningError()

        self.server = Server()
        self.server.connect("message_received", self.handle_message)
        self.server.set_socket_path(self.socket_path)

    def handle_message(self, server, framer, event):
        if isinstance(event, RegisterEvent):
            ExtensionController(self.controllers, framer, event.extension_id)

    def stop(self):
        """
        Stops extension server
        """
        if not self.is_running():
            raise ServerIsNotRunningError()

        self.server.close()
        self.server = None

    def is_running(self):
        """
        :rtype: bool
        """
        return bool(self.ws_server)

    def get_controller(self, extension_id):
        """
        :param str extension_id:
        :rtype: ~ulauncher.api.server.ExtensionController.ExtensionController
        """
        return self.controllers[extension_id]

    def get_controllers(self):
        """
        :rtype: list of  :class:`~ulauncher.api.server.ExtensionController.ExtensionController`
        """
        return self.controllers.values()

    def get_controller_by_keyword(self, keyword):
        """
        :param str keyword:
        :rtype: ~ulauncher.api.server.ExtensionController.ExtensionController
        """
        for _, ctl in self.controllers.items():
            if keyword in ctl.preferences.get_active_keywords():
                return ctl

        return None


class ServerIsRunningError(RuntimeError):
    pass


class ServerIsNotRunningError(RuntimeError):
    pass


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    server = ExtensionServer.get_instance()
    server.start()
