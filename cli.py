import logging
import sys
import optparse
import time


def parse_options(args: list[str]) -> tuple[optparse.Values, list[str]]:
    """
    Parse command line options
    """

    usage = "usage: %prog <filename/prefix> [-i] [-n] [-s]"
    parser = optparse.OptionParser(usage, version="%prog 0.1.0")
    parser.add_option("-i", type="str", dest="ip", help="IP address of the scope", default="127.0.0.1")
    parser.add_option(
        "-n",
        type="int",
        dest="nevents",
        help="number of events to capture in total",
        default=1000,
    )
    parser.add_option(
        "-s",
        type="int",
        dest="nsequence",
        help="number of sequential events to capture at a time",
        default=1,
    )
    parser.add_option(
        "--time",
        action="store_true",
        dest="time",
        help="append time string to filename",
        default=False,
    )
    parser.add_option(
        "-v",
        action="count",
        dest="verbosity",
        help="increase verbosity (specify multiple times for more verbosity)",
        default=0,
    )
    parser.add_option(
        "-q",
        action="count",
        dest="quiet",
        help="be quiet and do not print progress during data aquisition, suppress logging",
        default=0,
    )
    (options, args) = parser.parse_args(args=args)

    if len(args) < 1:
        sys.exit(parser.format_help())

    if options.nevents < 1 or options.nsequence < 1:
        sys.exit("Arguments to -s or -n must be positive")

    if options.nevents % options.nsequence != 0:
        sys.exit(f"#events {options.nevents} must be a multiplicity of #sequences {options.nsequence}")

    if options.quiet > 0 and options.verbosity > 0:
        sys.exit("Cannot use quiet and verbose option at the same time, use only one of them")

    return options, args


def setup_logging(verbosity: int = 0):
    log_level = logging.WARNING
    if verbosity == 1:
        print("Setting log level to INFO")
        log_level = logging.INFO
    elif verbosity == 2:
        print("Setting log level to DEBUG")
        log_level = logging.DEBUG

    logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

    start_time = time.time()

    def elapsed_time():
        """Function to calculate time elapsed since the start of the program"""
        return time.time() - start_time

    class ElapsedTimeFormatter(logging.Formatter):
        def format(self, record):
            record.elapsed_time = elapsed_time()
            return super(ElapsedTimeFormatter, self).format(record)

    elapsed_formatter = ElapsedTimeFormatter("%(asctime)s - %(levelname)s - [%(elapsed_time).3f seconds] - %(message)s")

    # Set all StreamHandlers to WARNING level, deeper levels will go to files, as set below
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setLevel(logging.WARNING)

    if log_level == logging.DEBUG:
        debug_filename = "debug.log"
        print(f"Saving DEBUG level logs to {debug_filename}")
        debug_handler = logging.FileHandler(debug_filename)
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(elapsed_formatter)
        logging.getLogger().addHandler(debug_handler)

    if log_level in (logging.DEBUG, logging.INFO):
        info_filename = "info.log"
        print(f"Saving INFO level logs to {info_filename}")
        info_handler = logging.FileHandler(info_filename)
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(elapsed_formatter)
        logging.getLogger().addHandler(info_handler)
