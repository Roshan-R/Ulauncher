import os
import sys
import logging
import traceback
from threading import Timer
import gi

gi.require_versions({
    "GLib": "2.0",
})
from gi.repository import GLib

from ulauncher.api.shared.event import SystemExitEvent, RegisterEvent
from ulauncher.api.shared.socket_path import get_socket_path
from ulauncher.utils.unix_stream import Client as UnixClient

logger = logging.getLogger(__name__)


class Client:
    """
    Instantiated in extension code and manages data transfer from/to Ulauncher app

    :param ~ulauncher.api.client.Extension extension:
    :param str ws_api_url: uses env. var `ULAUNCHER_WS_API` by default
    """

    def __init__(self, extension):
        self.socket_path = get_socket_path()
        self.extension = extension
        self.unix_client = None

    def connect(self):
        """
        Connects to WS server and blocks thread
        """
        self.unix_client = UnixClient()
        self.unix_client.connect("message_received", self.on_message)
        self.unix_client.connect("closed", self.on_close)
        self.unix_client.set_socket_path(self.socket_path)
        self.send(RegisterEvent(self.extension.extension_id))

        mainloop = GLib.MainLoop.new(None, None)
        mainloop.run()

    # pylint: disable=unused-argument
    def on_message(self, client, framer, event):
        """
        Parses message from Ulauncher and triggers extension event

        :param websocket.WebSocketApp ws:
        :param str message:
        """
        logger.debug('Incoming event %s', type(event).__name__)
        try:
            self.extension.trigger_event(event)
        # pylint: disable=broad-except
        except Exception:
            traceback.print_exc(file=sys.stderr)

    def on_close(self, client):
        """
        Terminates extension process on client disconnect.

        Triggers :class:`~ulauncher.api.shared.event.SystemExitEvent` for graceful shutdown

        :param websocket.WebSocketApp ws:
        """
        logger.warning("Connection closed. Exiting")
        self.extension.trigger_event(SystemExitEvent())
        # extension has 0.5 sec to save it's state, after that it will be terminated
        Timer(0.5, os._exit, args=[0]).start()

    def send(self, response):
        """
        Sends response to Ulauncher

        :param ~ulauncher.api.shared.Response.Response response:
        """
        logger.debug('Send message %s', response)
        self.unix_client.send(response)
