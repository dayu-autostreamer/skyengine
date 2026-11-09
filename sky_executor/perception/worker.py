"""A report queue with one consumer, result handles and orderly shutdown."""
from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Lock, Thread
from typing import TYPE_CHECKING, Generic, TypeVar

from sky_executor.perception.contracts import (
    PerceptionReport, PerceptionSnapshot, ReportOutcome, ReportApplicationResult,
)

if TYPE_CHECKING:
    from sky_executor.grid_factory.factory.grid_factory_env import GridFactoryEnv

_Result = TypeVar("_Result")


class ResultHandle(Generic[_Result]):
    """Read a result outside the consumer; no callbacks or cancellation."""

    __slots__ = ("__future",)

    def __init__(self, future: Future[_Result]) -> None:
        self.__future = future

    def done(self) -> bool:
        return self.__future.done()

    def result(self, timeout: float | None = None) -> _Result:
        """Wait for data or raise its error; timeout does not cancel the item."""
        return self.__future.result(timeout=timeout)


@dataclass(frozen=True, slots=True)
class _ReportRequest:
    report: PerceptionReport
    future: Future[ReportApplicationResult]


@dataclass(frozen=True, slots=True)
class _SnapshotRequest:
    future: Future[PerceptionSnapshot]


@dataclass(frozen=True, slots=True)
class _PositionFrameRequest:
    reports: tuple[PerceptionReport, ...]
    future: Future[tuple[ReportOutcome, ...]]


_Request = _ReportRequest | _PositionFrameRequest | _SnapshotRequest


class PerceptionWorker:
    """Serialize report consumption and snapshot boundaries through one handler.

    Producers construct reports before enqueueing. The Worker neither executes
    scene commands nor advances a simulator. Wait and close outside core locks.
    """

    def __init__(
        self,
        env: GridFactoryEnv,
        *,
        required_position_samples: int | None = None,
        temporary_obstacle_source: str | None = None,
    ) -> None:
        self._env = env
        self._handler = env.create_report_handler(
            required_position_samples=required_position_samples,
            temporary_obstacle_source=temporary_obstacle_source,
        )
        self._queue: Queue[_Request | None] = Queue()
        self._admission_lock = Lock()
        self._accepting = True
        self._failure: BaseException | None = None
        self._thread = Thread(target=self._consume, name="perception-worker", daemon=False)
        self._thread.start()

    def submit_report(self, report: PerceptionReport) -> ResultHandle[ReportApplicationResult]:
        """Enqueue input without validating its fields or committing it here."""
        future = Future()
        self._enqueue(_ReportRequest(report, future))
        return ResultHandle(future)

    def request_snapshot(self) -> ResultHandle[PerceptionSnapshot]:
        """Use this request's FIFO position as the snapshot input cutoff."""
        future: Future[PerceptionSnapshot] = Future()
        self._enqueue(_SnapshotRequest(future))
        return ResultHandle(future)

    def submit_position_frame(self, reports) -> ResultHandle[tuple[ReportOutcome, ...]]:
        """Enqueue a complete position frame, not an arbitrary business batch."""
        reports = tuple(reports)
        future = Future()
        self._enqueue(_PositionFrameRequest(reports, future))
        return ResultHandle(future)

    def close(self) -> None:
        """Stop admission, drain queued work and join; do not close the environment."""
        with self._admission_lock:
            if self._accepting:
                self._accepting = False
                self._queue.put(None)
        self._thread.join()

    def __enter__(self) -> PerceptionWorker:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _enqueue(self, request: _Request) -> None:
        # Closing must put the stop marker after every admitted request.
        with self._admission_lock:
            if not self._accepting:
                raise RuntimeError("perception worker is closed or failed") from self._failure
            self._queue.put(request)

    def _consume(self) -> None:
        while True:
            request = self._queue.get()
            try:
                if request is None:
                    return
                try:
                    # A read copies evidence; it neither dispatches work nor resumes a failed run.
                    if isinstance(request, _SnapshotRequest):
                        request_result = self._handler.snapshot()
                    else:
                        with self._env.process_business_chain():
                            request_result = self._process_request(request)
                except BaseException as error:
                    self._stop_after_failure(request, error)
                    return
                # Only this class holds the Future. Callers cannot attach
                # callbacks that would run inline and block this consumer.
                request.future.set_result(request_result)
            finally:
                self._queue.task_done()

    def _process_request(self, request: _ReportRequest | _PositionFrameRequest):
        if isinstance(request, _ReportRequest):
            return self._handler.handle_report(request.report)
        return self._handler.handle_position_frame(request.reports)

    def _stop_after_failure(
        self, current: _Request, error: BaseException
    ) -> None:
        with self._admission_lock:
            self._accepting = False
            self._failure = error
        current.future.set_exception(error)
        while True:
            try:
                pending = self._queue.get_nowait()
            except Empty:
                return
            try:
                if pending is not None:
                    stopped = RuntimeError("perception worker stopped after an internal error")
                    stopped.__cause__ = error
                    pending.future.set_exception(stopped)
            finally:
                self._queue.task_done()
