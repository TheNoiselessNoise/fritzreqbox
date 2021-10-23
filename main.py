import sys
import argparse
from requester import FritzReqBox

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description="""
        [WIP] API for Fritz!Box 7581\n
        Working features:
            - Get general information about product
            - Get information about connected devices
    """)
login_group = parser.add_argument_group(title="Login")
login_group.add_argument('--host', help="Host or IP", type=str, required=True)
login_group.add_argument('-u', help="Username to Login", type=str, default="", metavar="USER")
login_group.add_argument('-p', help="Password to Login", type=str, required=True, metavar="PASS")
funcs_group = parser.add_argument_group(title="Functions")
funcs_group.add_argument('--pages', help="Show all available pages", action="store_true")
funcs_group.add_argument('--general', help="Show general information", action="store_true")
funcs_group.add_argument('--devices', help="Show all ever connected devices", action="store_true")
funcs_group.add_argument('--cdevices', help="Show all connected devices", action="store_true")
funcs_group.add_argument('--ncdevices', help="Show all not connected devices", action="store_true")
args = parser.parse_args()

def main():
    fb = FritzReqBox({
        "host": args.host,
        "user": args.u,
        "pass": args.p
    })

    if args.pages:
        print(",".join(fb.get_available_pages().keys()))
    elif args.general:
        print(fb.get_general_information())
    elif args.devices:
        print(fb.get_all_devices())
    elif args.cdevices:
        print(fb.get_connected_devices())
    elif args.ncdevices:
        print(fb.get_not_connected_devices())


if __name__ == "__main__":
    if len(sys.argv[1:]) == 0:
        parser.print_help()
        sys.exit()

    main()
