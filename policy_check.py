#########################################################################
# Use: Verify policies on customer facing ports                         #
# Version: 1.0                                                          #
#                                                                       #
# Input: devices.txt file with one device hostname or IP address per    #
#        line. This can include CIDR networks                           #
# Output: Info is output to screen and logged (service_policy_log.txt). #
#                                                                       #
#########################################################################

# Import colorama to colorize output
from colorama import init
from colorama import Fore
# Import getpass so we can easily mask user input for passwords
import getpass
# Import ConnectHandler for SSH connections
from netmiko import ConnectHandler
# Used to convert CIDR to hosts
from netaddr import IPNetwork

# colorama initialization, required for windows
init(autoreset=True)


# Display script name and version
user_message = Fore.YELLOW + "Policy Check - v1.0\n\n" + Fore.WHITE
print(user_message)


# Get user credentials to test
print(Fore.CYAN + "Please enter credentials to check." + Fore.WHITE)
username = input("\nUsername: ")
password = getpass.getpass("Password: ")
enablepw = password



def device_list():
    device_list = []
    # open the devices text file in read-only mode
    with open('devices.txt', 'r') as fn:

        # iterate through the lines in the text file
        for line in fn.read().splitlines():

            # skip empty lines
            if line is '':
                continue

            else:
                # Check if CIDR network was entered
                if "/" in line:
                    # Convert CIDR to individual hosts
                    for ip in IPNetwork(line):
                        # Converted host from CIDR is device
                        device = str(ip)
                        device_list.append(str(device))
                else:
                    # entire line is device
                    device = line
                    device_list.append(str(device))

    return device_list


def run_commands():
    # We use the variables we got from the user earlier
    network_device_param = {
        'device_type': 'cisco_ios_ssh',
        'ip': device,
        'username': username,
        'password': password,
        'secret': enablepw,
        }

    # Connect to device
    net_connect = ConnectHandler(**network_device_param)

    # enter enable mode if required
    if net_connect.find_prompt().endswith('>'):
        net_connect.enable()

    # iterate through the commands list
    for line in commands:
        # assume a normal show command
        out = net_connect.send_command(line.strip())

    # Close session
    net_connect.disconnect()

    return out

# Create device list to populate from devices.txt
device_list = device_list()


# Set log file name and initialize
logname = "service_policy_log.txt"
file = open(logname, 'w')


for device in device_list:
    # Pull and format running config to parse for customer interfaces
    commands = ['sh run']
    print(Fore.MAGENTA + "\nParsing config for " + str(device) + Fore.WHITE)
    file.write(str(device) + " - ")
    out = ''
    out = run_commands()
    config_by_line = out.splitlines()

    # Variable used to list customer line descriptions for further parsing
    line_descriptions = []

    # Customer interface labels that will be used to parse running config
    cust_types = ['CUST','CELL','SLA']

    # Get hostname for reference
    for line in config_by_line:
        if "hostname" in line:
            host = line.split()[1]
    print(Fore.MAGENTA + str(host) + Fore.WHITE)
    file.write(str(host) + "\n")
    
    # Find descriptions containing customer accounts
    for cust_type in cust_types:
        # Search individual lines for applicable descriptions
        for line in config_by_line:
            if cust_type in line:
                # Filter out only lines that are descriptions (some are names)
                word_search = line.split()
                if word_search[0] == 'description':
                    # Add lines to list for indexing
                    line_descriptions.append(line)

    if not line_descriptions:
        print (Fore.RED + " No customer interfaces found." + Fore.WHITE)
        file.write(" No customer interfaces found.\n")
    
    # Find interfaces requiring policy types
    for description in line_descriptions:
        # Variable used to alert on interfaces without any applied policy
        policy_count = 0

        desc_loc = config_by_line.index(description)
        interface = config_by_line[desc_loc - 1].split()[1]

        # Print Interface and description to screen and log
        description = description.split()
        print ("\n " + str(interface) + "\n  " + str(description[1] + "\n"))
        file.write(" " + str(interface) + "\n")
        file.write("  " + str(description[1]) + "\n")

        # Connect to device and pull interface config
        commands = ["sh run int " + interface]
        out = run_commands()

        # Pull applied policies from config
        interface_config = out.splitlines()

        # Parse interface config for applied service policies; print and log
        for line in interface_config:
            if 'service-policy' in line:
                print (str(line))
                file.write(str(line) + "\n")
                policy_count = policy_count + 1
        if policy_count == 0:
            print (Fore.RED + "  No service policies applied!" + Fore.WHITE)
            file.write("  No service policies applied!" + "\n")
        file.write("\n")

# close log
file.close()
