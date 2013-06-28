# Copyright (c) 2013 Pierre Pronchery <khorben@defora.org>
# This file is contributed to Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import logging
import subprocess
from pyparsing import OneOrMore, nestedExpr

from lib.cuckoo.common.abstracts import MachineManager
from lib.cuckoo.common.exceptions import CuckooMachineError

log = logging.getLogger(__name__)

class Xen(MachineManager):
    """Virtualization layer for Xen."""

    # VM states.
    RUNNING = "running"
    POWEROFF = "poweroff"
    ABORTED = "aborted"
    ERROR = "machete"

    def start(self, label):
        """Start a virtual machine.
        @param label: virtual machine name.
        @raise CuckooMachineError: if unable to start.
        """
        log.debug("Starting vm %s" % label)

        if self._status(label) == self.RUNNING:
            raise CuckooMachineError("Trying to start an already started vm %s" % label)

        try:
            subprocess.call([self.options.xen.path, 'create',
                self.options.xen.filename, 'name=%s' % label],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc.returncode != 0:
                log.debug("Xen returns error checking status for machine %s: %s"
                                       % (label, err))
                status = self.ERROR
        except OSError as e:
            raise CuckooMachineError("Xen failed starting the machine")
        self._wait_status(label, self.RUNNING)

    def stop(self, label):
        """Stops a virtual machine.
        @param label: virtual machine name.
        @raise CuckooMachineError: if unable to stop.
        """
        log.debug("Stopping vm %s" % label)

        if self._status(label) in [self.POWEROFF, self.ABORTED]:
            raise CuckooMachineError("Trying to stop an already stopped vm %s" % label)

        try:
            proc = subprocess.Popen([self.options.xen.path, 'shutdown',
                label],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc.returncode != 0:
                log.debug("Xen exited with error powering off the machine")
        except OSError as e:
            raise CuckooMachineError("Xen failed powering off the machine: %s" % e)
        self._wait_status(label, [self.POWEROFF, self.ABORTED])

    def _list(self):
        """Lists virtual machines installed.
        @return: virtual machine names list.
        """
        try:
            proc = subprocess.Popen([self.options.xen.path, 'list', '-l'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, err = proc.communicate()
        except OSError as e:
            raise CuckooMachineError("Xen error listing installed machines: %s" % e)
        if proc.returncode != 0:
            log.debug("Xen returns error checking status for machine list: %s"
                    % err)
            status = self.ERROR
            raise CuckooMachineError("Xen error listing installed machines: %s" % err)

        machines = []
        data = OneOrMore(nestedExpr()).parseString(output)
        for row in data.asList():
            if row[0] != 'domain':
                continue
            for prop in row:
                if prop[0] == 'name':
                    machines.append(prop[1])
        return machines

    def _status(self, label):
        """Gets current status of a vm.
        @param label: virtual machine name.
        @return: status string.
        """
        log.debug("Getting status for %s"% label)
        status = None
        try:
            proc = subprocess.Popen([self.options.xen.path, 'list', '-l',
                label],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, err = proc.communicate()

            if proc.returncode != 0:
                log.debug("Xen returns error checking status for machine %s: %s"
                                       % (label, err))
            else:
                data = OneOrMore(nestedExpr()).parseString(output)
                for row in data.asList()[0]:
                    if row[0] == 'status':
                        if row[1] == '2':
                            status = self.RUNNING
                            log.debug("Machine %s status %s" % (label, status))
                        break
        except OSError as e:
            log.warning("Xen failed to check status for machine %s: %s"
                    % (label, e))
        # Report back status.
        if status:
            self.set_status(label, status)
            return status
        else:
            raise CuckooMachineError("Unable to get status for %s" % label)

    def dump_memory(self, label, path):
        """Takes a memory dump.
        @param path: path to where to store the memory dump.
        """
        raise CuckooMachineError("Memory dumps are not implemented")

# vim: et ts=8 sts=4 sw=4
