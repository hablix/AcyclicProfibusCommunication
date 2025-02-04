import socket
import struct
from consolemenu import *
from consolemenu.items import *
import re
import time
import elementpath
from xml.etree import ElementTree as et

# Server
ip = "141.76.82.170"
port = 12345
mysocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
mysocket.settimeout
menuValidAdresses = []
menuDevices = []
menu = ConsoleMenu("Azyklisches Lesen - Profibus Kommunikation",
                    "Serveradresse: {}   Serverport: {}".format(ip, port))

class ProfiBus_Device():
    def __init__(self):
        self.physical_blocks = None
        self.transducer_blocks = None
        self.function_blocks = None
        self.link_objects = None


def main():
    valid_addresses = find_valid_addrs()
    devices = []
    for addr in valid_addresses:
        print(f"Device at address {addr}:")
        devices.append(get_device_information(addr))
        print("----------------------------------------------")


def find_valid_addrs():
    valid_addrs = []
    for address in range(0, 10):
        data = sendMessage(1, address, 1, 0)
        if len(data) > 1:
            valid_addrs.append(address)
    print(f"Devices found at bus address: {valid_addrs}")
    return valid_addrs

def findSpecDev():
    print('Finde spezifisches Gerät')
    adress = input('Bus-Adresse: ')

    if adress.isdigit() == False:
        print('Ungültige Adresse')
        time.sleep(3)

    adress_i = int(adress)

    try:
        get_device_information(adress_i)
    except TypeError:
        print('...')
        get_device_information(adress_i)
    print('Enter drücken um zum Menu zurückzukehren')
    input()


def get_device_information(addr):
    framemarker = 1
    slot = 1
    index = 0

    # Get DIRECTORY_OBJECT_HEADER
    response = sendMessage(framemarker, addr, slot, index)
    # maximal 256 Byte lang
    dir_obj_header = response
    pbd = ProfiBus_Device()
    pbd.addr = addr
    pbd.values = []
    pbd.units = []
    pbd.dir_ID = dir_obj_header[1:3]
    pbd.rev_number = dir_obj_header[3:5]
    pbd.num_dir_obj = dir_obj_header[5:7]
    pbd.num_dir_entry = dir_obj_header[7:9]
    pbd.first_comp_list_dir_entry = dir_obj_header[9:11]
    pbd.num_comp_list_dir_entry = dir_obj_header[11:13]
    pbd.num_blocks = int.from_bytes(
        pbd.num_dir_entry, 'big') - int.from_bytes(pbd.num_comp_list_dir_entry, 'big')

    # Get COMPOSITE_LIST_DIRECTORY_ENTRIES
    dir_entries_list = sendMessage(framemarker+1, addr, slot, index+1)
    num_comp = int.from_bytes(pbd.num_comp_list_dir_entry, 'big')

    # Block pointers
    if num_comp >= 1:
        pbd.physical_blocks = {
            "type": "Physical Block",
            "index": dir_entries_list[1],
            "offset": dir_entries_list[2],
            "number": dir_entries_list[3:5],
            "blocks": []
        }

    if num_comp >= 2:
        pbd.transducer_blocks = {
            "type": "Transducer Block",
            "index": dir_entries_list[5],
            "offset": dir_entries_list[6],
            "number": dir_entries_list[7:9],
            "blocks": []
        }

    if num_comp >= 3:
        pbd.function_blocks = {
            "type": "Function Block",
            "index": dir_entries_list[9],
            "offset": dir_entries_list[10],
            "number": dir_entries_list[11:13],
            "blocks": []
        }

    if num_comp >= 4:
        pbd.link_objects = {
            "type": "Link Object",
            "index": dir_entries_list[13],
            "offset": dir_entries_list[14],
            "number": dir_entries_list[15:17],
            "blocks": []
        }

    # Get Composite_Directory_Entries
    blocks_index = dir_entries_list[1]
    if int.from_bytes(pbd.num_dir_obj, 'big') == 1:
        dir_blocks = dir_entries_list[num_comp*4:] # Hole Blöcke aus COMPOSITE_LIST_DIRECTORY_ENTRIES
    else:
        dir_blocks = sendMessage(framemarker+2, addr, slot, blocks_index) #Neuer request für weitere Blöcke
    dir_blocks = [dir_blocks[i:i+4] for i in range(1, len(dir_blocks), 4)]

    relativ_index = pbd.physical_blocks["offset"]

    # Zuordnung der Blöcke zu physical, transducer oder function-Blocks 
    # in abhängigkeit von ihrem index
    for block in dir_blocks:
        info = {
            "slot": block[0],
            "index": block[1],
            "num_para": block[2:4]
        }
        if relativ_index < pbd.transducer_blocks["offset"]:
            pbd.physical_blocks["blocks"].append(info)
        elif relativ_index < pbd.function_blocks["offset"]:
            pbd.transducer_blocks["blocks"].append(info)
        else:
            pbd.function_blocks["blocks"].append(info)
        relativ_index += 1

    # Read physical block information
    for phyBlock in pbd.physical_blocks["blocks"]:
        phyBlock["parent_class"], phyBlock["man_id"], phyBlock["man_name"] = getManufacuter(
            phyBlock, addr)
        print(f"PHYSICAL block information:")
        print(
            f"   Man ID = {phyBlock['man_id']}\n   Man Name = {phyBlock['man_name']}\n   Parent Class = {phyBlock['parent_class']}")
        pbd.manufacturerID = phyBlock['man_id']

    # Read transducer block information
    for tdBlock in pbd.transducer_blocks["blocks"]:
        tdBlock["parent_class"], tdBlock["class"], tdBlock["unit"] = getTranducerBlockInfo(
            tdBlock, addr)
        print(f"   Unit = {tdBlock['unit']}")
        pbd.units.append(tdBlock["unit"])

    # Read function block information
    for fb in pbd.function_blocks["blocks"]:
        fb["parent_class"], fb["class"], fb["value"], fb["status"] = getFunctionBlockInfo(
            fb, addr)
        if fb["value"]:
            pbd.values.append(fb["value"])

    return pbd


# Sende Nachrricht, 4 Bytes
def sendMessage(framemarker, addr, slot, index):
    global ip
    global port
    framemarker = framemarker.to_bytes(1, 'big')
    addr = addr.to_bytes(1, 'big')
    slot = slot.to_bytes(1, 'big')
    index = index.to_bytes(1, 'big')
    msg = framemarker + addr + slot + index
    mysocket.sendto(msg, (ip, port))
    mysocket.settimeout(20)
    try:
        data, _ = mysocket.recvfrom(1024) # 1024 bytes max
    except:
        print('TIMEOUT')
        data =[]
    return data


def getManufacuter(phyBlock, addr):
    # Get Man_ID from physical Block and look up corresponding manufacturer name
    # Relative Index for Man_ID = 10 / 110 for device 7
    if addr == 7:
        block_object = sendMessage(
            1, addr, phyBlock["slot"], phyBlock["index"] + 100)
        device_man_id = sendMessage(
            1, addr, phyBlock["slot"], phyBlock["index"] + 110)
    else:
        block_object = sendMessage(
            1, addr, phyBlock["slot"], phyBlock["index"])
        device_man_id = sendMessage(
            1, addr, phyBlock["slot"], phyBlock["index"] + 10)
    device_man_id = int.from_bytes(device_man_id[1:], 'big')
    parent_class = block_object[3]

    print('searching in xml for manufacturer_name ...')

    try:
        tree = et.parse('Man_ID_Table.xml')
        root = tree.getroot()
        for manufacturer in root[1:]:
            if int(manufacturer.attrib['ID']) == device_man_id:
                man_name = manufacturer[0][0].text
                try:
                    man_name = man_name + " " + manufacturer[0][1].attrib['URI']
                except: break
    except:
        man_name = "unknowen"

    return parent_class, device_man_id, man_name


def getTranducerBlockInfo(tdBlock, addr):
    # Read primary value unit
    slot = tdBlock["slot"]
    index = tdBlock["index"]
    block_object = sendMessage(1, addr, slot, index)

    parent_class = block_object[3]
    _class = block_object[4]

    # Unit Codes, Seite 96ff.

    if addr == 7:
        # Hard coded for addr 7 due to defect directory
        _unit = sendMessage(1, addr, 4, 9)[1:]
        _unit = int.from_bytes(_unit, 'big')
        unit = "degree Celsius" if _unit == 1001 else str(_unit)
    elif parent_class == 1:
        # Preassure TB
        _unit = sendMessage(2, addr, slot, index+14)[1:]
        _unit = int.from_bytes(_unit, 'big')
        unit = "mbar" if _unit == 1138 else str(_unit)
        parent_class = "Preassure"
    elif parent_class == 2:
        # Temperature TB
        _unit = sendMessage(2, addr, slot, index+9)[1:]
        _unit = int.from_bytes(_unit, 'big')
        unit = "degree Celsius" if _unit == 1001 else str(_unit)
        parent_class = "Temperature"
    else:
        # All other TBs
        unit = None
    print(
        f"Found TRANSDUCER block at Slot {slot} Index {index}:\n   Parent Class = {parent_class}\n   Class = {_class}")
    return parent_class, _class, unit


def getFunctionBlockInfo(fBlock, addr):
    slot = fBlock["slot"]
    index = fBlock["index"]
    block_object = sendMessage(1, addr, slot, index)
    if(len(block_object) >= 5):
        parentClass = block_object[3]
        _class = block_object[4]
        if parentClass == 1 and _class == 1:
            # Analog Input Function Block
            print(
                f"Found FUNCTION block at Slot {slot} Index {index}:\n   Input, Analog Input")
            # Parameter Attributes for the Analog Input Function Block s.157: OUT=10
            fb_output = sendMessage(2, addr, slot, index+10)

            try:
                value = struct.unpack('>f', fb_output[1:5])[0]
                status = fb_output[5]
                print(f"   Output value = {value}\n   status = {status}")
            except:
                value = None
                status = None

            return "Input", "Analog Input", value, status
        else:
            print(
                f"Found FUNCTION block at Slot {slot} Index {index}:\n   Parent Class = {parentClass}\n   Class = {_class}")
            return parentClass, _class, None, None
    else:
        print(
            f"Could not find function block at slot {slot} index {index} but there should be one")
        return None, None, None, None


# if __name__ == "__main__":
#     main()


def menuSetIpAdress():
    global ip, port

    print("\nAktuelle Server IP-Adresse: {} und Port: {} \nGeben sie eine neue Adresse ein um diese zu ändern oder Enter um diese zu bestätigen.".format(ip,port))

    re_ipv4 = re.compile(
        '^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
    re_port = re.compile(
        '([0-9]{1,5})')

    ipport = input("Eingabeschema (141.76.82.170:12345): ")
    if ':' not in ipport:
        return

    ip, port = ipport.split(':')

    if not re_ipv4.match(ip):
        print('Ungültige IP_Adresse')
        ip = '141.76.82.170'

    if not ip:
        ip = '141.76.82.170'

    if not re_port.match(port):
        print('Ungültiger Port')
        port = '12345'

    if not port:
        port = '12345'
    
    port = int(port)
    print("\nAktuelle Server IP-Adresse: {} und Port: {}".format(ip,port))
    time.sleep(3)


def menuFindClients():
    global menuValidAdresses
    global menuDevices
    print('Suche nach Endgeräten läuft...')
    menuValidAdresses = find_valid_addrs()
    time.sleep(2)
    for adress in menuValidAdresses:
        global menu
        print(adress)
        device_function_item = FunctionItem(text="Lade Geräteinformationen von Adresse {}".format(
            adress), function=menuGetDeviceInformation, args=[adress])
        menu.append_item(device_function_item)

def menuGetDeviceInformation(addr):
    i = 0
    while True:
        try:
            menuDevices.append(get_device_information(addr))
            break
        except TypeError:
            i = i + 1
            print("Verbindung fehlgeschlagen. Versuche es Erneut... {}".format(i))
            if i > 5:
                raise myError2


def menuGetDeviceInformationOutput():
    global menuDevices
    if not menuDevices:
        print('Keine Gerätedaten gefunden.')
        input("Drücke eine Taste um fortzufahren...")
        return

    for pbd in menuDevices:
        print('Geräteinformationen für Adresse {}:'.format(pbd.addr))
        print('Manifacturer ID: {}'.format(pbd.manufacturerID))
        if len(pbd.units) < len(pbd.values):
            for i in range(len(pbd.values)):
                print('{} {}'.format(pbd.values[i], pbd.units[0]))
        else:
            for i in range(len(pbd.values)):
                print('{} {}'.format(pbd.values[i], pbd.units[i]))

        print('')
    input("Drücke eine Taste um fortzufahren...")



def showMenu():
    global menu
    function_item0 = FunctionItem(
        "Suche alle Geräte", main)
    function_item1 = FunctionItem(
        "Ändern der IP-Adresse und des Ports", menuSetIpAdress)
    function_item2 = FunctionItem(
        "Suche spezielles Gerät", findSpecDev)
    function_item3 = FunctionItem(
        "Suche spezielles Gerät -alt", menuFindClients)

    menu.append_item(function_item0)
    menu.append_item(function_item1)
    menu.append_item(function_item2)
    #menu.append_item(function_item3)
    menu.show()


menuSetIpAdress()
showMenu()
