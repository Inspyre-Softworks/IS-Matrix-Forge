import threading
import queue
from typing import Optional, Any

class ThreadedLEDMatrixController:
    """
    Wraps an LEDMatrixController to execute commands in one or more background threads,
    ensuring no calls are lost when invoked concurrently.

    Usage:
        base = LEDMatrixController(device, default_brightness=50)
        threaded = ThreadedLEDMatrixController(base, max_queue_size=100, num_workers=2)
        # now you can spam commands from any thread, and they’ll all run:
        threaded.draw_grid(grid1)
        threaded.set_brightness(80)
        threaded.animate(True)
        # ...even while a long identify() or Breather is running!

    Parameters:
        controller (LEDMatrixController):
            The controller to wrap.

        max_queue_size (int, optional):
            Maximum number of queued commands. Defaults to infinite.

        num_workers (int, optional):
            Number of worker threads processing the queue. Defaults to 1.
    """

    def __init__(
        self,
        controller: Any,
        max_queue_size: Optional[int] = None,
        num_workers: int = 1
    ):
        self._controller = controller
        # infinite size if you don't care about spam limits
        self._queue = queue.Queue(maxsize=max_queue_size) if max_queue_size else queue.Queue()
        self._workers = []
        for i in range(max(1, num_workers)):
            t = threading.Thread(target=self._worker, daemon=True, name=f"LEDWorker-{i}")
            t.start()
            self._workers.append(t)

    def _worker(self):
        while True:
            method_name, args, kwargs = self._queue.get()
            try:
                getattr(self._controller, method_name)(*args, **kwargs)
            except Exception as e:
                # feel free to hook up your own logger here
                from is_matrix_forge.led_matrix.console import error
                error(f"[ThreadedLEDMatrixController] Error in {method_name}: {e}")
            finally:
                self._queue.task_done()

    def enqueue(self, method_name: str, /, *args, **kwargs):
        """
        Enqueue a method call by name. Raises queue.Full if the queue is full.
        """
        self._queue.put((method_name, args, kwargs))

    def __getattr__(self, name: str):
        """
        Proxy any attribute to the wrapped controller.
        If it’s a callable, return a wrapper that enqueues the call.
        """
        attr = getattr(self._controller, name)
        if callable(attr):
            def wrapper(*args, **kwargs):
                self.enqueue(name, *args, **kwargs)
            return wrapper
        return attr
