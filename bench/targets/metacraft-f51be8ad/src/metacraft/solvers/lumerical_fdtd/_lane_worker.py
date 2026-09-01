from __future__ import annotations

import base64
from multiprocessing.connection import Client
from pathlib import Path
import sys
from typing import Any

from .qualification import LumericalUnavailable
from .session import LumericalSession, open_session


def _reply(connection: Any, value: Any = None) -> None:
    connection.send({"ok": True, "value": value})


def _reject(connection: Any, error: BaseException) -> None:
    """
    Preserve typed product absence without classifying exception text.
    """

    if isinstance(error, LumericalUnavailable):
        connection.send(
            {
                "ok": False,
                "unavailable": error.reason,
            }
        )
        return
    connection.send(
        {
            "error": type(error).__name__,
            "message": _reported_error(error),
            "ok": False,
        }
    )


def _reported_error(error: BaseException) -> str:
    """
    Report cleanup notes without changing the exact failure envelope.
    """

    notes = tuple(getattr(error, "__notes__", ()))
    return "\n".join((str(error), *notes))


def _serve(
    connection: Any,
    session: LumericalSession,
) -> None:
    while True:
        request = connection.recv()
        operation = request["operation"]
        arguments = request.get("arguments", ())
        if operation == "close":
            session.close()
            _reply(connection)
            return
        try:
            if operation == "create":
                session.create(*arguments)
                value = None
            elif operation == "read":
                value = dict(session.read(*arguments))
            elif operation == "save":
                session.save(Path(arguments[0]))
                value = None
            elif operation == "solve":
                session.solve(
                    Path(arguments[0]),
                    Path(arguments[1]),
                )
                value = None
            elif operation == "result":
                value = dict(session.result(*arguments))
            elif operation == "optional_result":
                value = session.optional_result(
                    *arguments
                ).as_ipc_mapping()
            elif operation == "prepare_grating_response":
                value = session.prepare_grating_response(
                    *arguments
                ).as_ipc_mapping()
            elif operation == "change_maximum_time":
                session.change_maximum_time(*arguments)
                value = None
            elif operation == "reset":
                session.reset()
                value = None
            else:
                raise RuntimeError(
                    f"native_session_operation_invalid:{operation}"
                )
        except BaseException as error:
            _reject(connection, error)
        else:
            _reply(connection, value)


def main(arguments: list[str] | None = None) -> int:
    """
    Serve one placed native session until its parent closes the channel.
    """

    values = sys.argv[1:] if arguments is None else arguments
    if len(values) != 5:
        raise RuntimeError("native_session_arguments_invalid")
    host, port, encoded_key, python_api, license_server = values
    connection = Client(
        (host, int(port)),
        family="AF_INET",
        authkey=base64.urlsafe_b64decode(encoded_key.encode("ascii")),
    )
    session: LumericalSession | None = None
    failure: BaseException | None = None
    try:
        session = open_session(
            Path(python_api),
            should_hide=True,
            license_server=license_server,
        )
        _reply(connection, "ready")
        _serve(connection, session)
    except BaseException as error:
        failure = error
        if session is not None:
            try:
                session.close()
            except BaseException as cleanup_error:
                error.add_note(
                    "session close failed: "
                    f"{cleanup_error!r}"
                )
        try:
            _reject(connection, error)
        except (EOFError, OSError) as cleanup_error:
            error.add_note(
                "failure reply failed: "
                f"{cleanup_error!r}"
            )
        return 1
    finally:
        try:
            connection.close()
        except BaseException as cleanup_error:
            if failure is None:
                raise
            failure.add_note(
                "connection close failed: "
                f"{cleanup_error!r}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
