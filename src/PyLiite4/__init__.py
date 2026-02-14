"""Complete, typed Python bindings for GTK 4 and libadwaita."""

from PyLiite4 import _bundle

_bundle.setup()

from PyLiite4._runtime import BoundSignal, Property, Signal, SignalMethod, use_asyncio  # noqa: E402

__version__ = "0.1.0"
__all__ = ["BoundSignal", "Property", "Signal", "SignalMethod", "use_asyncio", "__version__"]
