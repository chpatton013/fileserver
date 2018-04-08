import subprocess

import log


class DryrunPopen():
    def __init__(self, command):
        self.command = command
        self.returncode = 0

    def poll(self):
        pass

    def wait(self):
        pass


class Executor(object):
    def __init__(self, dryrun=False, verbose=False):
        self.dryrun = dryrun
        self.verbose = verbose
        self.log = log.Logger(dryrun=dryrun)

    def debug(self, *args, **kwargs):
        if self.verbose:
            self.log.debug(*args, **kwargs)

    def info(self, *args, **kwargs):
        message = self.log.info(*args, **kwargs)
        return "# {}".format(message)

    def error(self, *args, **kwargs):
        self.log.error(*args, **kwargs)

    def write(self, filepath, content):
        if self.verbose:
            self.log.write(filepath)
            for l in content.splitlines():
                self.log.write("  " + l)

        if not self.dryrun:
            print(content, file=open(filepath, "w"))

        return "echo '{}' > '{}'".format(content, filepath)

    def run(self, command):
        if self.verbose:
            self.log.run(" ".join(map(str, command)))

        if not self.dryrun:
            subprocess.check_call(command)

        return " ".join(command)

    def spawn(self, command):
        if self.verbose:
            self.log.spawn(" ".join(map(str, command)))

        if self.dryrun:
            return DryrunPopen(command)
        else:
            return subprocess.Popen(command)
