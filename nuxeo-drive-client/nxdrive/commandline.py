"""Utilities to operate Nuxeo Drive from the command line"""
import os
import sys
import argparse
from getpass import getpass
import traceback
import threading
try:
    import ipdb
    debugger = ipdb
except ImportError:
    import pdb
    debugger = pdb

from nxdrive.controller import Controller
from nxdrive.daemon import daemonize
from nxdrive.controller import default_nuxeo_drive_folder
from nxdrive.logging_config import configure
from nxdrive.logging_config import get_logger
from nxdrive.protocol_handler import parse_protocol_url
from nxdrive.protocol_handler import register_protocol_handlers
from nxdrive.startup import register_startup
from nxdrive import __version__


DEFAULT_NX_DRIVE_FOLDER = default_nuxeo_drive_folder()
DEFAULT_DELAY = 5.0
DEFAULT_MAX_SYNC_STEP = 10
DEFAULT_HANDSHAKE_TIMEOUT = 60
DEFAULT_TIMEOUT = 20
USAGE = """ndrive [command]

If no command is provided, the graphical application is started along with a
synchronization process.

Possible commands:
- console
- start
- stop
- bind-server
- unbind-server
- bind-root
- unbind-root

To get options for a specific command:

  ndrive command --help

"""

PROTOCOL_COMMANDS = {
    'nxdriveedit': 'edit',
    'nxdrivebind': 'bind_server',
}


def make_cli_parser(add_subparsers=True):
    """Parse commandline arguments using a git-like subcommands scheme"""

    common_parser = argparse.ArgumentParser(
        add_help=False,
    )
    common_parser.add_argument(
        "--nxdrive-home",
        default="~/.nuxeo-drive",
        help="Folder to store the Nuxeo Drive configuration."
    )
    common_parser.add_argument(
        "--log-level-file",
        default="DEBUG",
        help="Minimum log level for the file log (under NXDRIVE_HOME/logs)."
    )
    common_parser.add_argument(
        "--log-level-console",
        default="INFO",
        help="Minimum log level for the console log."
    )
    common_parser.add_argument(
        "--log-filename",
        help=("File used to store the logs, default "
              "NXDRIVE_HOME/logs/nxaudit.logs")
    )
    common_parser.add_argument(
        "--debug", default=False, action="store_true",
        help="Fire a debugger (ipdb or pdb) one uncaught error."
    )
    common_parser.add_argument(
        "--delay", default=DEFAULT_DELAY, type=float,
        help="Delay in seconds between consecutive sync operations.")
    common_parser.add_argument(
        "--max-sync-step", default=DEFAULT_MAX_SYNC_STEP, type=int,
        help="Number of consecutive sync operations to perform"
        " without refreshing the internal state DB.")
    common_parser.add_argument(
        "--handshake-timeout", default=DEFAULT_HANDSHAKE_TIMEOUT, type=int,
        help="HTTP request timeout in seconds for the handshake.")
    common_parser.add_argument(
        "--timeout", default=DEFAULT_TIMEOUT, type=int,
        help="HTTP request timeout in seconds for the sync Automation calls.")
    common_parser.add_argument(
        # XXX: Make it true by default as the fault tolerant mode is not yet
        # implemented
        "--stop-on-error", default=True, action="store_true",
        help="Stop the process on first unexpected error."
        "Useful for developers and Continuous Integration.")
    common_parser.add_argument(
        "-v", "--version", action="version", version=__version__,
        help="Print the current version of the Nuxeo Drive client."
    )
    parser = argparse.ArgumentParser(
        parents=[common_parser],
        description="Command line interface for Nuxeo Drive operations.",
        usage=USAGE,
    )

    if not add_subparsers:
        return parser

    subparsers = parser.add_subparsers(
        title='Commands',
    )

    # Link to a remote Nuxeo server
    bind_server_parser = subparsers.add_parser(
        'bind-server', help='Attach a local folder to a Nuxeo server.',
        parents=[common_parser],
    )
    bind_server_parser.set_defaults(command='bind_server')
    bind_server_parser.add_argument(
        "--password", help="Password for the Nuxeo account")
    bind_server_parser.add_argument(
        "--local-folder",
        help="Local folder that will host the list of synchronized"
        " workspaces with a remote Nuxeo server.",
        default=DEFAULT_NX_DRIVE_FOLDER,
    )
    bind_server_parser.add_argument(
        "username", help="User account to connect to Nuxeo")
    bind_server_parser.add_argument("nuxeo_url",
                                    help="URL of the Nuxeo server.")
    bind_server_parser.add_argument(
        "--remote-roots", nargs="*", default=[],
        help="Path synchronization roots (reference or path for"
        " folderish Nuxeo documents such as Workspaces or Folders).")
    bind_server_parser.add_argument(
        "--remote-repo", default='default',
        help="Name of the remote repository.")

    # Unlink from a remote Nuxeo server
    unbind_server_parser = subparsers.add_parser(
        'unbind-server', help='Detach from a remote Nuxeo server.',
        parents=[common_parser],
    )
    unbind_server_parser.set_defaults(command='unbind_server')
    unbind_server_parser.add_argument(
        "--local-folder",
        help="Local folder that hosts the list of synchronized"
        " workspaces with a remote Nuxeo server.",
        default=DEFAULT_NX_DRIVE_FOLDER,
    )

    # Bind root folders
    bind_root_parser = subparsers.add_parser(
        'bind-root',
        help='Attach a local folder as a root for synchronization.',
        parents=[common_parser],
    )
    bind_root_parser.set_defaults(command='bind_root')
    bind_root_parser.add_argument(
        "remote_root",
        help="Remote path or id reference of a folder to synchronize.")
    bind_root_parser.add_argument(
        "--local-folder",
        help="Local folder that will host the list of synchronized"
        " workspaces with a remote Nuxeo server. Must be bound with the"
        " 'bind-server' command.",
        default=DEFAULT_NX_DRIVE_FOLDER,
    )
    bind_root_parser.add_argument(
        "--remote-repo", default='default',
        help="Name of the remote repository.")

    # Unlink from a remote Nuxeo root
    unbind_root_parser = subparsers.add_parser(
        'unbind-root', help='Detach from a remote Nuxeo root.',
        parents=[common_parser],
    )
    unbind_root_parser.set_defaults(command='unbind_root')
    unbind_root_parser.add_argument(
        "local_root", help="Local sub-folder to de-synchronize.")

    # Start / Stop the synchronization daemon
    start_parser = subparsers.add_parser(
        'start', help='Start the synchronization as a GUI-less daemon',
        parents=[common_parser],
    )
    start_parser.set_defaults(command='start')
    stop_parser = subparsers.add_parser(
        'stop', help='Stop the synchronization daemon',
        parents=[common_parser],
    )
    stop_parser.set_defaults(command='stop')
    console_parser = subparsers.add_parser(
        'console',
        help='Start a GUI-less synchronization without detaching the process.',
        parents=[common_parser],
    )
    console_parser.set_defaults(command='console')

    status_parser = subparsers.add_parser(
        'status',
        help='Fetch the status info of the children of a given folder.',
        parents=[common_parser],
    )
    status_parser.set_defaults(command='status')
    status_parser.add_argument(
        "folder", help="Path to a local Nuxeo Drive folder.")

    # embedded test runner base on nose:
    test_parser = subparsers.add_parser(
        'test',
        help='Run the Nuxeo Drive test suite.',
        parents=[common_parser],
    )
    test_parser.set_defaults(command='test')
    test_parser.add_argument(
        "--with-coverage", default=False, action="store_true",
        help="Compute coverage report.")
    test_parser.add_argument(
        "--with-profile", default=False, action="store_true",
        help="Compute profiling report.")

    return parser


class CliHandler(object):
    """Command Line Interface handler: parse options and execute operation"""

    def parse_cli(self, argv):
        """Parse the command line argument using argparse and protocol URL"""
        # Filter psn argument provided by OSX .app service launcher
        # https://developer.apple.com/library/mac/documentation/Carbon/Reference/LaunchServicesReference/LaunchServicesReference.pdf
        # When run from the .app bundle generated with py2app with
        # argv_emulation=True this is already filtered out but we keep it
        # for running CLI from the source folder in development.
        argv = [a for a in argv if not a.startswith("-psn_")]

        # Preprocess the args to detect protocol handler calls and be more
        # tolerant to missing subcommand
        has_command = False
        protocol_url = None

        filtered_args = []
        for arg in argv[1:]:
            if arg.startswith('nxdrive://'):
                protocol_url = arg
                continue
            if not arg.startswith('-'):
                has_command = True
            filtered_args.append(arg)

        parser = make_cli_parser(add_subparsers=has_command)
        options = parser.parse_args(filtered_args)
        if options.debug:
            # Install Post-Mortem debugger hook

            def info(etype, value, tb):
                traceback.print_exception(etype, value, tb)
                print
                debugger.pm()

            sys.excepthook = info

        # Merge any protocol info into the other parsed commandline
        # parameters
        if protocol_url is not None:
            protocol_info = parse_protocol_url(protocol_url)
            for k, v in protocol_info.items():
                setattr(options, k, v)

        return options

    def _configure_logger(self, options):
        """Configure the logging framework from the provided options"""
        filename = options.log_filename
        if filename is None:
            filename = os.path.join(
                options.nxdrive_home, 'logs', 'nxdrive.log')

        configure(
            filename,
            file_level=options.log_level_file,
            console_level=options.log_level_console,
            command_name=options.command,
        )

    def handle(self, argv):
        """Parse options, setup logs and controller and dispatch execution."""
        options = self.parse_cli(argv)
        # 'start' is the default command if None is provided
        command = options.command = getattr(options, 'command', 'launch')

        # Configure the logging framework
        self._configure_logger(options)

        # Initialize a controller for this process, except for the tests
        # as they initialize their own
        if command != 'test':
            self.controller = Controller(options.nxdrive_home,
                                handshake_timeout=options.handshake_timeout,
                                timeout=options.timeout)

        # Find the command to execute based on the
        handler = getattr(self, command, None)
        if handler is None:
            raise NotImplementedError(
                'No handler implemented for command ' + options.command)

        self.log = get_logger(__name__)
        self.log.debug("Command line: " + ' '.join(argv))

        self._install_faulthandler(options)

        if command == 'launch':
            # Ensure that the protocol handler are registered:
            # this is useful for the edit / open link in the Nuxeo interface
            register_protocol_handlers(self.controller)
            # Ensure that ndrive is registered as a startup application
            register_startup()
        try:
            return handler(options)
        except Exception, e:
            if options.debug:
                # Make it possible to use the postmortem debugger
                raise
            else:
                msg = e.msg if hasattr(e, 'msg') else e
                self.log.error("Error executing '%s': %s", command, msg,
                          exc_info=True)

    def launch(self, options=None):
        """Launch the Qt app in the main thread and sync in another thread."""
        # TODO: use the start method as default once implemented
        from nxdrive.gui.application import Application
        app = Application(self.controller, options)
        app.exec_()
        app.deleteLater()

    def start(self, options=None):
        """Launch the synchronization in a daemonized process (under POSIX)"""
        # Close DB connections before Daemonization
        self.controller.dispose()
        daemonize()

        self.controller = Controller(options.nxdrive_home,
                            handshake_timeout=options.handshake_timeout,
                            timeout=options.timeout)
        self._configure_logger(options)
        self.log.debug("Synchronization daemon started.")
        self.controller.synchronizer.loop(
            delay=getattr(options, 'delay', DEFAULT_DELAY),
            max_sync_step=getattr(options, 'max_sync_step',
                                  DEFAULT_MAX_SYNC_STEP))
        return 0

    def console(self, options):
        self.controller.synchronizer.loop(
            delay=getattr(options, 'delay', DEFAULT_DELAY),
            max_sync_step=getattr(options, 'max_sync_step',
                                  DEFAULT_MAX_SYNC_STEP))
        return 0

    def stop(self, options=None):
        self.controller.stop()
        return 0

    def status(self, options):
        states = self.controller.children_states(options.folder)
        for filename, status in states:
            print status + '\t' + filename
        return 0

    def edit(self, options):
        self.controller.launch_file_editor(
            options.server_url, options.item_id)
        return 0

    def bind_server(self, options):
        if options.password is None:
            password = getpass()
        else:
            password = options.password
        self.controller.bind_server(options.local_folder, options.nuxeo_url,
                                    options.username, password)
        for root in options.remote_roots:
            self.controller.bind_root(options.local_folder, root,
                                      repository=options.remote_repo)
        return 0

    def unbind_server(self, options):
        self.controller.unbind_server(options.local_folder)
        return 0

    def bind_root(self, options):
        self.controller.bind_root(options.local_folder, options.remote_root,
                                  repository=options.remote_repo)
        return 0

    def unbind_root(self, options):
        self.controller.unbind_root(options.local_root)
        return 0

    def test(self, options):
        import nose
        # Monkeypatch nose usage message as it's complicated to include
        # the missing text resource in the frozen binary package
        nose.core.TestProgram.usage = lambda cls: ""
        argv = [
            '',
            '--verbose',
        ]

        if options.with_coverage:
            argv += [
                '--with-coverage',
                '--cover-package=nxdrive',
                '--cover-html',
                '--cover-html-dir=coverage',
            ]

        if options.with_profile:
            argv += [
                '--with-profile',
                '--profile-restrict=nxdrive',
            ]
        # List the test modules explicitly as recursive discovery is broken
        # when the app is frozen.
        argv += [
            "nxdrive.tests.test_integration_concurrent_synchronization",
            "nxdrive.tests.test_integration_copy",
            "nxdrive.tests.test_integration_encoding",
            "nxdrive.tests.test_integration_local_client",
            "nxdrive.tests.test_integration_local_move_and_rename",
            "nxdrive.tests.test_integration_permission_hierarchy",
            "nxdrive.tests.test_integration_remote_changes",
            "nxdrive.tests.test_integration_remote_deletion",
            "nxdrive.tests.test_integration_remote_document_client",
            "nxdrive.tests.test_integration_remote_file_system_client",
            "nxdrive.tests.test_integration_remote_move_and_rename",
            "nxdrive.tests.test_integration_security_updates",
            "nxdrive.tests.test_integration_synchronization",
            "nxdrive.tests.test_integration_versioning",
            "nxdrive.tests.test_integration_windows",
            "nxdrive.tests.test_synchronizer",
        ]
        return 0 if nose.run(argv=argv) else 1

    def _install_faulthandler(self, options):
        """Utility to help debug segfaults"""
        try:
            # Use faulthandler to print python tracebacks in case of segfaults
            import faulthandler
            segfault_filename = os.path.join(
                options.nxdrive_home, 'logs', 'segfault.log')
            segfault_file = open(os.path.expanduser(segfault_filename), 'w')
            self.log.debug("Enabling faulthandler to trace segfaults in %s",
                           segfault_filename)
            faulthandler.enable(file=segfault_file)
        except ImportError:
            self.log.debug("faulthandler is not available: skipped")


def dumpstacks(signal, frame):
    id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
    code = []
    for thread_id, stack in sys._current_frames().items():
        code.append("\n# Thread: %s(%d)" % (id2name.get(thread_id, ""),
                                            thread_id))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s'
                        % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    print "\n".join(code)


def main(argv=None):
    # Print thread dump when receiving SIGUSR1,
    # except under Windows (no SIGUSR1)
    if sys.platform != 'win32':
        import signal
        signal.signal(signal.SIGUSR1, dumpstacks)
    if argv is None:
        argv = sys.argv
    return CliHandler().handle(argv)

if __name__ == "__main__":
    sys.exit(main())
