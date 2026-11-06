from PyLiite4 import Gio

from demos.workbench import workbench  # noqa: F401

memory_monitor = Gio.MemoryMonitor.dup_default()

cache = {}
cache["a"] = 1
cache["b"] = 2
cache["c"] = 3


def evaluate_memory(_monitor: Gio.MemoryMonitor, level: Gio.MemoryMonitorWarningLevel) -> None:
    # Inequalities rather than equality, since new levels may be added in the future.
    if level >= Gio.MemoryMonitorWarningLevel.LOW:
        # Processes should free up unneeded resources.
        print("Warning Level: Low")
        drop_caches()
    if level >= Gio.MemoryMonitorWarningLevel.MEDIUM:
        # Processes should try harder to free up unneeded resources.
        print("Warning Level: Medium")
    if level >= Gio.MemoryMonitorWarningLevel.CRITICAL:
        # The system will start terminating processes to reclaim memory.
        print("Warning Level: Critical")


memory_monitor.low_memory_warning.connect(evaluate_memory)


def drop_caches() -> None:
    cache.clear()
