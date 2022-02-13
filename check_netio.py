#!/usr/bin/env python3
import sys

import requests
import argparse


class IcingaOutput:
    OK = 0
    WARNING = 1
    CRITICAL = 2
    UNKNOWN = 3

    def __init__(self):
        self._retv = []
        self._debug_data = []
        self._result = self.OK
        self._perfdata = dict()


    def __lshift__(self, s):
        assert type(s) == str
        self._retv.append(s)

    def set_perfdata(self, k, v):
        self._perfdata[k] = v

    def add_debug_data(self, s):
        self._debug_data.append(s)

    def flush(self, verbose=False):
        if self._result == self.CRITICAL:
            print('ERROR - ', end='')
        elif self._result == self.WARNING:
            print('WARNING - ', end='')
        print(''.join(self._retv), end='')

        # do not append perfdata when in UKNOWN in order not to break graphs
        if self._result != self.UNKNOWN:
            if self._perfdata:
                print('|', end='')
                for k,v in self._perfdata.items():
                    print(f"{k}={v}", end=' ')
        #
        print('')
        # add verbose debug dat
        if verbose:
            for ln in self._debug_data:
                sys.stderr.write(f'{ln}\n')
        raise SystemExit(self._result)

    def error(self):
        if self._result in [IcingaOutput.OK, IcingaOutput.WARNING]:
            self._result = IcingaOutput.CRITICAL

    def unknown(self):
        self._result = IcingaOutput.UNKNOWN


class NetioJson:
    def __init__(self, args):
        self.args = args
        self._url = f'http://{args.address}:{args.port}/netio.json'

    def _getStatus(self):
        http_params = dict()
        if args.auth_user:
            http_params['auth'] = (args.auth_user, args.auth_password)
        result = requests.get(self._url, **http_params)
        assert result.status_code == 200
        return result.json()

    def info(self):
        "Get device info"
        output = IcingaOutput()
        data = self._getStatus()
        output.add_debug_data(str(data))

        model = data['Agent']['Model']
        mac = data['Agent']['MAC']
        name = data['Agent']['DeviceName']
        sn = data['Agent']['SerialNumber']

        if 'expect_mac' in self.args:
            if self.args.expect_mac.lower() != mac.lower():
                output << f"Device {name}, with {mac}, expected {self.args.expect_mac}"
                output.error()
                return output
        output << f"Device {name}, (model: {model}, S/N: {sn}, MAC {mac})"
        return output

    def uptime(self):
        "Check device uptime"
        output = IcingaOutput()
        data = self._getStatus()
        output.add_debug_data(str(data))

        uptime = int(data['Agent']['Uptime'])
        name = data['Agent']['DeviceName']
        output.set_perfdata('uptime', f'{uptime}s')

        if self.args.min is not None and uptime < self.args.min:
                output << f"Uptime {uptime}s is lower than expected {self.args.min}s"
                output.error()
        elif self.args.max is not None and uptime > self.args.max:
                output << f"Uptime {uptime}s is larger than expected {self.args.max}s"
                output.error()
        else:
            output << f"Device {name} - uptime is {uptime}s1"
        return output

    def check_output_state(self):
        "Check socket state"
        output = IcingaOutput()
        data = self._getStatus()
        output.add_debug_data(str(data))

        uptime = int(data['Agent']['Uptime'])
        output.set_perfdata('uptime', f'{uptime}s')

        output_id = str(args.output_id)
        output_state = [ k for k in data['Outputs'] if str(k["ID"]) == output_id ]
        if len(output_state) != 1:
            output << f"ERROR - Unable to find output ID '{args.output_id}'"
            output.unknown()
            return output
        output_state = output_state[0]
        output_power_state = output_state['State']
        output_name = output_state['Name']
        output.set_perfdata('state', int(output_power_state))
        #
        current = float(output_state['Current']) / 1000
        load = output_state['Load']
        output.set_perfdata('current', f'{current}A')
        output.set_perfdata('load', f'{load}W')
        output.set_perfdata('power_factor', float(output_state['PowerFactor']))
        #
        if args.expected_state is not None:
            output.add_debug_data(output_state)
            if output_power_state != int(args.expected_state):
                expected_state = int(args.expected_state)
                output << f"Output {output_id}({output_name}) state is {output_power_state}, should be {expected_state}"
                output.error()
            else:
                output << f"Output {output_id}({output_name}) state is {output_power_state}"
        else:
            output << f"Output {output_id}({output_name}) state is {output_power_state}"
        return output

    def check_output_load(self):
        "Check socket load"
        output = IcingaOutput()
        data = self._getStatus()
        output.add_debug_data(str(data))

        uptime = int(data['Agent']['Uptime'])
        output.set_perfdata('uptime', f'{uptime}s')

        output_id = str(args.output_id)
        output_state = [ k for k in data['Outputs'] if str(k["ID"]) == output_id ]
        if len(output_state) != 1:
            output << f"ERROR - Unable to find output ID '{args.output_id}'"
            output.unknown()
            return output
        output_state = output_state[0]
        output_power_state = output_state['State']
        output_name = output_state['Name']
        output.set_perfdata('state', int(output_power_state))
        #
        current = float(output_state['Current']) / 1000
        load = output_state['Load']
        output.set_perfdata('current', f'{current}A')
        output.set_perfdata('load', f'{load}W')
        output.set_perfdata('power_factor', float(output_state['PowerFactor']))
        #
        output << f"Output {output_id}({output_name}) load {current}A, {load}W"
        if args.min_watts is not None and load < args.min_watts:
                output << f', that is lower than {args.min_watts}W'
                output.error()
        elif args.max_watts is not None and load > args.max_watts:
                output << f', that is greater than {args.max_watts}W'
                output.error()
        elif args.min_amps is not None and current > args.min_amps:
                output << f', that is lower than {args.min_amps}A'
                output.error()
        elif args.max_amps is not None and current > args.max_amps:
                output << f', that is greater than {args.max_amps}A'
                output.error()
        return output


def makeParser():
    parser = argparse.ArgumentParser(description='Check Netio PDU status')
    parser.add_argument('--address', '-H', default='192.168.50.220',
                        nargs=1,
                        help='Specify IP address of the device')
    parser.add_argument('--port', '-p', default=80,
                        help='JSON port (default: 80)')
    parser.add_argument('--user', '-k', default=None, dest='auth_user',
                        help='Username used to access the console')
    parser.add_argument('--password', '-K', default='', dest='auth_password',
                        help='Password  used to access the console')
    parser.add_argument('--verbose', '-v', default=0,
                        action='store_const', const=1,
                        dest='verbose', help='Be verbose')

    subparsers = parser.add_subparsers(help="Select sub-command")

    info_parser = subparsers.add_parser('info', help='Get PDU info')
    info_parser.add_argument("--expect-mac", "--mac", default=None, nargs="?",
                             help="Expect MAC address")
    info_parser.set_defaults(action=NetioJson.info)

    uptime_parser = subparsers.add_parser('uptime', help='Check PDU uptime')
    uptime_parser.add_argument("--min", nargs="?", type=int,
                               help="Minimum expected uptime in seconds")
    uptime_parser.add_argument("--max", nargs="?", type=int,
                               help="Maximum expected uptime in seconds")
    uptime_parser.set_defaults(action=NetioJson.uptime)

    state_parser = subparsers.add_parser('output', help='Check output state')
    state_parser.add_argument("--output_id", '-n', dest='output_id',
                              default=1,
                              help="ID of output to check (default: 1)")
    state_parser.add_argument("--on", action='store_true', dest='expected_state',
                              default=None,
                              help="Expect the output to be powered on")
    state_parser.add_argument("--off", action='store_false', dest='expected_state',
                               default=None,
                               help="Expect output to be powered off")
    state_parser.set_defaults(action=NetioJson.check_output_state)

    load_parser = subparsers.add_parser('load', help='Check output load')
    load_parser.add_argument("--output_id", '-n', dest='output_id',
                              default=1,
                              help="ID of output to check (default: 1)")
    load_parser.add_argument("--min-watts", action='store', dest='min_watts',
                              default=None, type=float,
                              help="Expect minimum load in W")
    load_parser.add_argument("--max-watts", action='store', dest='max_watts',
                              default=None, type=float,
                              help="Expect maximum load in W")
    load_parser.add_argument("--min-amps", action='store', dest='min_amps',
                              default=None, type=float,
                              help="Expect minimum load in A")
    load_parser.add_argument("--max-amps", action='store', dest='max_amps',
                              default=None, type=float,
                              help="Expect maximum load in A")
    load_parser.set_defaults(action=NetioJson.check_output_load)


    return parser


def main(args):
    device = NetioJson(args)
    if 'action' not in args:
        result = device.info()
        result.flush(verbose=args.verbose)
    elif args.action:
        result = args.action(self=device)
        result.flush(verbose=args.verbose)
    else:
        print(f"UNKNOWN - action {args.action} is not implemented")
        raise SystemExit(3)


if __name__ == '__main__':
    parser = makeParser()
    args = parser.parse_args()
    main(args)

