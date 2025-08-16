import signal
from subprocess import Popen, TimeoutExpired
from typing import Any


class ProcessManager:
    processes: list[Popen]
    """Processes managed by this manager."""

    options: dict[str, Any]
    """Default options for Popen."""

    timeout: float | None
    """Default timeout when stopping processes."""

    def __init__(
            self,
            options: dict[str, Any] = None,
            timeout: float | None = 10.,
    ):
        """
        ProcessManager makes it easy to start and stop numerous processes
        in a coordinated fashion.

        Example:

            with ProcessManager() as pm:
                pm.popen('ls -l', shell=True)
                pm.popen(['rosy', 'topic', 'echo', 'my_topic'])
                pm.popen(['python', 'script.py'])

        Args:
            options:
                Default kwargs to pass to Popen.
            timeout:
                Default timeout when stopping processes.
        """

        self.options = options or {}
        self.timeout = timeout

        self.processes = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def popen(self, args, **kwargs) -> Popen:
        """
        Start a new process.

        Args:
            args: Command arguments passed to Popen.
            **kwargs: Keyword arguments passed to Popen.

        Returns: The Popen object for the new process.
        """

        kwargs = {**self.options, **kwargs}
        return self.add(Popen(args, **kwargs))

    def add(self, process: Popen) -> Popen:
        """Add an existing process to the manager."""
        self.processes.append(process)
        return process

    def stop(
            self,
            process: Popen | None = None,
            timeout: float | None = None,
    ):
        """
        Stop one or all processes managed by this manager.

        First it sends a `SIGTERM` signal to the process, and then waits for it to
        finish. If the process does not finish within the timeout, it sends a
        `SIGKILL` signal to forcefully terminate the process.

        Args:
            process:
                Optional process to stop. By default, all processes will be stopped.
            timeout:
                Optional timeout override. Defaults to `self.timeout`.
        """

        if process is None:
            processes = list(self.processes)
            self.processes.clear()
        else:
            processes = [process]
            self.processes.remove(process)

        if timeout is None:
            timeout = self.timeout

        print(f'Stopping {len(processes)} processes...')
        for process in processes:
            process.send_signal(signal.SIGTERM)

        procs_to_kill = []
        for process in processes:
            try:
                process.wait(timeout)
            except TimeoutExpired:
                print(f'Process {process.pid} did not stop in time.')
                procs_to_kill.append(process)

        for process in procs_to_kill:
            print(f'Killing process {process.pid}')
            process.kill()

        for process in procs_to_kill:
            try:
                process.wait(timeout)
            except TimeoutExpired:
                print(f'Failed to kill process {process.pid}.')

    def wait(self, timeout: float = None) -> None:
        """
        Wait for all processes to finish.

        Args:
            timeout: Optional wait timeout.
        """

        for process in list(self.processes):
            process.wait(timeout)
            self.processes.remove(process)
