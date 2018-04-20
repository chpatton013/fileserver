import enum
import datetime


__all__ = [
    "InvalidLogStream",
    "LogStream",
    "Logger",
]


class InvalidLogStream(ValueError):
    pass


class LogStream(enum.Enum):
    DEBUG = 1
    INFO = 2
    ERROR = 3
    WRITE = 4
    RUN = 5
    SPAWN = 6


def stream_to_string(stream):
    if stream == LogStream.DEBUG:
        return "DEBUG"
    elif stream == LogStream.INFO:
        return " INFO"
    elif stream == LogStream.ERROR:
        return "ERROR"
    elif stream == LogStream.WRITE:
        return "WRITE"
    elif stream == LogStream.RUN:
        return " RUN "
    elif stream == LogStream.SPAWN:
        return "SPAWN"
    else:
        raise InvalidLogStream()


class Logger(object):
    def __init__(self, dryrun=False):
        self.dryrun = dryrun

    def log(self, stream, message, *args, **kwargs):
        """
        Print a formatted message with dryrun, stream, and timing information as
        a prefix.
        Return the formatted message without the prefix.
        """
        formatted_message = message.format(*args, **kwargs)
        print("[{dryrun}{stream}|{time}]{message}".format(
            dryrun=("DRYRUN|" if self.dryrun else ""),
            stream=stream_to_string(stream),
            time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            message=formatted_message,
        ))
        return formatted_message

    def debug(self, *args, **kwargs):
        return self.log(LogStream.DEBUG, *args, **kwargs)

    def info(self, *args, **kwargs):
        return self.log(LogStream.INFO, *args, **kwargs)

    def error(self, *args, **kwargs):
        return self.log(LogStream.ERROR, *args, **kwargs)

    def write(self, *args, **kwargs):
        return self.log(LogStream.WRITE, *args, **kwargs)

    def run(self, *args, **kwargs):
        return self.log(LogStream.RUN, *args, **kwargs)

    def spawn(self, *args, **kwargs):
        return self.log(LogStream.SPAWN, *args, **kwargs)
