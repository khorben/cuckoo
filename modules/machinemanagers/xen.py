# Copyright (c) 2013 Pierre Pronchery <khorben@defora.org>
# This file is contributed to Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import logging
import os.path
import subprocess
from pyparsing import OneOrMore, nestedExpr

from lib.cuckoo.common.abstracts import MachineManager
from lib.cuckoo.common.exceptions import CuckooMachineError

log = logging.getLogger(__name__)

class Xen(MachineManager):
    """Virtualization layer for Xen using the xm utility."""

    def _initialize_check(self):
        """Check for configuration file and Xen setup.
        @raise CuckooMachineError: if configuration is missing or wrong.
        """
        # Consistency checks.
        self._check_xen()
        for machine in self.machines():
            self._check_machine(machine)
        # Base checks.
        super(Xen, self)._initialize_check()

    def _check_xen(self):
        """Checks a xen configuration file
        @param filename: path to the configuration file.
        @raise CuckooMachineError: if the file is not found.
        """
        if not self.options.xen.path:
            self.options.xen.path = '/usr/sbin/xm'
        if not os.path.exists(self.options.xen.path):
            raise CuckooMachineError("%s: Invalid path to Xen xm (file not found)" % self.options.xen.path)

    def _check_machine(self, machine):
        """Checks if a machine exists (including its snapshot).
        @param machine: the virtual machine.
        @raise CuckooMachineError: if the snapshot was not found.
        """
        filename, snapshot = self._parse_label(machine.label)
        host = os.path.basename(filename) #XXX use the section name instead

        if not os.path.exists(filename):
            raise CuckooMachineError("%s: Configuration file not found for machine %s" % (filename, host))
        if not os.path.exists(snapshot):
            raise CuckooMachineError("%s: Snapshot not found for machine %s"
                    % (snapshot, host))

    def start(self, label):
        """Start a virtual machine.
        @param label: virtual machine name.
        @raise CuckooMachineError: if unable to start.
        """
        filename, snapshot = self._parse_label(label)
        host = os.path.basename(filename) #XXX use the section name instead

        # Preventive check
        if self._is_running(host):
            raise CuckooMachineError("%s: Machine already running" % host)

        log.debug("Starting vm %s" % host)

        if not self._command(snapshot, 'restore'):
            raise CuckooMachineError("%s: Could not start the machine" % host)

    def stop(self, label):
        """Stops a virtual machine.
        @param label: virtual machine name.
        @raise CuckooMachineError: if unable to stop.
        """
        filename, snapshot = self._parse_label(label)
        host = os.path.basename(filename) #XXX use the section name instead

        log.debug("Stopping vm %s" % host)

        if not self._command(host, 'shutdown'):
            raise CuckooMachineError("%s: Could not stop the machine" % host)


    def dump_memory(self, label, path):
        """Takes a memory dump.
        @param path: path to where to store the memory dump.
        """
        filename, snapshot = self._parse_label(label)
        host = os.path.basename(filename) #XXX use the section name instead

        #FIXME implement with dump-core
        raise CuckooMachineError("Memory dumps are not implemented")

    def _is_running(self, host):
        """Checks if a virtual machine is running.
        @param host: name of the virtual machine.
        @return: running status.
        """
        #FIXME use domstate instead
        try:
            proc = subprocess.Popen([self.options.xen.path, 'list', '-l',
                host],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, err = proc.communicate()

            if proc.returncode != 0:
                log.debug("Xen returns error checking status for machine %s: %s"
                        % (host, err))
                return False
            data = OneOrMore(nestedExpr()).parseString(output)
            for row in data.asList()[0]:
                if row[0] == 'status' and row[1] == '2':
                    return True
            return False
        except OSError as e:
            log.warning("Xen failed to check status for machine %s: %s"
                    % (label, e))
            return False

    def _parse_label(self, label):
        """Parse the label of a virtual machine.
        @param label: configuration option from the configuration file.
        @return: tuple of path to the configuration file and snapshot.
        """
        opts = label.strip().split(",")
        if len(opts) != 2:
            raise CuckooMachineError("Wrong label syntax for %s in xen.conf: %s" % label)
        filename = opts[0].strip()
        snapshot = opts[1].strip()
        return filename, snapshot

    def _command(self, host, command):
        """Execute a command for a given virtual machine.
        @param host: name of the virtual machine.
        @param command: command to execute.
        @return: if the command was successful
        """
        try:
            proc = subprocess.Popen([self.options.xen.path, command, host],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = proc.communicate()
            if proc.returncode != 0:
                log.debug("%s: Could not execute command %s (error code %s: %s)"
                        % (host, command, proc.returncode, error))
                return False
            return True
        except OSError as e:
            log.warning("%s: Could not execute command %s"
                    % (host, command))
            return False

# vim: et ts=8 sts=4 sw=4
