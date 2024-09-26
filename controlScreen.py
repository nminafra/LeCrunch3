#!/usr/bin/env python3
# LeCrunch3
# Copyright (C) 2021 Nicola Minafra
#
# based on
#
# LeCrunch2
# Copyright (C) 2014 Benjamin Land
#
# based on
#
# LeCrunch
# Copyright (C) 2010 Anthony LaTorre
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import optparse
import sys
from LeCrunch3 import LeCrunch3


if __name__ == "__main__":
    import sys
    from cli import setup_logging

    usage = "usage: %prog ON/OFF [-i] [-v]"
    parser = optparse.OptionParser(usage, version="%prog 0.1.0")
    parser.add_option("-i", type="str", dest="ip", help="IP address of the scope", default="127.0.0.1")
    parser.add_option(
        "-v",
        action="count",
        dest="verbosity",
        help="increase verbosity (specify multiple times for more verbosity)",
        default=0,
    )
    (options, args) = parser.parse_args(args=sys.argv)

    if len(args) < 1:
        sys.exit(parser.format_help())

    setup_logging(verbosity=options.verbosity)
    print(f"Connecting to {options.ip} ... ", flush=True, end="")
    try:
        scope = LeCrunch3(options.ip)
        print("connected !")
        command = f"DISP {args[1]}"
        print(f"sending command {command}")
        scope.send(command)
        scope.check_last_command()
    except TimeoutError as e:
        print("could not connect to scope")
        print(e)
