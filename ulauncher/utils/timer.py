import math
from functools import partial
import gi

gi.require_versions({
    "GLib": "2.0",
})
from gi.repository import GLib

class TimerContext:
    def __init__(self, source, func, repeat=False):
        self.source = source
        self.repeat = repeat
        self.func = func
        self.source.set_callback(self.trigger)
        self.source.attach(None)

    def cancel(self):
        if self.source:
            self.source.destroy()
            self.source = None

    def trigger(self, user_data):
        self.func()
        return self.repeat


def timer(delay_sec, func, repeat=False):
    frac, whole = math.modf(delay_sec)
    if frac == 0.0:
        source = GLib.timeout_source_new_seconds(delay_sec)
    else:
        source = GLib.timeout_source_new(delay_sec*1000)

    return TimerContext(source, func, repeat)


if __name__ == "__main__":
    def test_1(one, two):
        print("One: %s two: %s" % (one, two))

    def test_cancel(source_to_cancel):
        print("Canceling %s" % source_to_cancel)
        source_to_cancel.cancel()

    loop = GLib.MainLoop.new(None, None)

    timer(1.1, partial(test_1, "this is one", "this is two"), True)
    timer(1.5, partial(test_1, "The second one", "The second two"))
    timer(2, partial(test_1, "this is one-3", "this is two -3"))
    to_cancel = timer(5, partial(test_1, "Should be canceled", "Not shown"))
    timer(3, partial(test_cancel, to_cancel))

    loop.run()
