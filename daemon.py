#!/usr/bin/env python

#thanks to http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/

import sys, os, time, atexit, subprocess, re
from signal import SIGTERM

class Daemon:
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
#        sys.stderr.write("PID File: %s\n" % (self.pidfile))

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
#                sys.stderr.write("PID Fork 1: %s\n" % (pid))
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
#                sys.stderr.write("PID Fork 2: %s\n" % (pid))
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
#sys.stderr.write("PID File about to be written\n")
#os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
#        sys.stderr.write("PID File written: %s\n" % (pid))
        file(self.pidfile,'w+').write("%s\n" % pid)

    def delpid(self):
        os.remove(self.pidfile)

    def checkStalePid(self, pid):
        #is there a process with this pid?
        try:
            os.kill(pid, 0)
        except OSError:
            #there's no process with that pid, so the pidfile is stale!
            return True
        #there is a process with the given pid. Is it the daemon?
        cmdline = subprocess.Popen("cat /proc/" + str(pid) + "/cmdline", shell=True, stdout=subprocess.PIPE).stdout.read()
        match = re.search(r'rubustat_daemon.py',cmdline)
        if match:
            #the pidfile points to an active instance of the daemon. pidfile is not stale.
            return False
        return True

    def status(self):
        """
        Status of daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        if pid:
            stale = self.checkStalePid(pid)
        if pid and not stale:
            message = "Daemon is running on pid %s\n"
            sys.stderr.write(message % pid)
            sys.exit(1)
        else:
            message = "Daemon is NOT running\n"
            sys.stderr.write(message)
            sys.exit(1)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        if pid:
            stale = self.checkStalePid(pid)
        if pid and not stale:
            message = "pidfile %s already exists. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)
        if pid and stale:
            os.remove(self.pidfile)
            message = "Stale pidfile %s detected. Deleting stale pidfile and starting daemon \n"
            sys.stderr.write(message % self.pidfile)
        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """
