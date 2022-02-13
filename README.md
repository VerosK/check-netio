
# Icinga module for Netio PDUs

Requirements:
  * Python 3.6+ , python-requests 
  * enabled JSON API on the Netio device

### Setup

 * enable JSON API on the Netio device. 
 * install `python3-requests`
 * copy `check_netio.py` to your plugin directory

### Usage

 * help on all commands

       ./check_netio --help

 * help on info command
  
       ./check_netio info --help

 * Get PDU identification 

       ./check_netio -H 192.168.50.220 info

 * check PDU uptime

       ./check_netio -H 192.168.50.220 uptime --min 900 

 * check socket is on or off

       ./check_netio -H 192.168.50.220 output -n 1 --on 
       ./check_netio -H 192.168.50.220 output -n 1 --off

 * check socket current

       ./check_netio -H 192.168.50.220 load -n 1 --min-watts 10 --max-watts 300


## License:

BSD-2


## Thanks

 * Netio for providing me with test device
