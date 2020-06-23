import socket
import struct
#from lxml import etree as ET

# Server
ip = "141.76.82.170"
port = 12345
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)

class PB_device():
    def __init__(self):
        self.physical_blocks = None
        self.transducer_blocks = None
        self.function_blocks = None
        self.link_objects = None


def main():    
    valid_addresses = find_valid_addrs()

    devices = []
    for addr in valid_addresses:
        devices.append(get_device_information(addr))


def find_valid_addrs():
    valid_addrs = []
    for address in range(0,10):
        data = sendMessage(1, address, 1, 0)
        if len(data) > 1: valid_addrs.append(address)
    print(f"Devices found at bus address: {valid_addrs}")
    return valid_addrs


def get_device_information(addr):
    framemarker = 1
    slot = 1
    index = 0
    
    # Get DIRECTORY_OBJECT_HEADER
    dir_obj_header = sendMessage(framemarker, addr, slot, index)    

    pbd = PB_device()
    pbd.dir_ID = dir_obj_header[1:3]
    pbd.rev_number = dir_obj_header[3:5]
    pbd.num_dir_obj = dir_obj_header[5:7]
    pbd.num_dir_entry = dir_obj_header[7:9]
    pbd.first_comp_list_dir_entry = dir_obj_header[9:11]
    pbd.num_comp_list_dir_entry = dir_obj_header[11:13]
    pbd.num_blocks = int.from_bytes(pbd.num_dir_entry, 'big') - int.from_bytes(pbd.num_comp_list_dir_entry, 'big')
    
    # Get COMPOSITE_LIST_DIRECTORY_ENTRIES
    dir_entries_list = sendMessage(framemarker+1, addr, slot, index+1)
    num_comp = int.from_bytes(pbd.num_comp_list_dir_entry, 'big')


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
    dir_blocks = sendMessage(framemarker+2, addr, slot, blocks_index)
    dir_blocks = [dir_blocks[i:i+4] for i in range(1, len(dir_blocks), 4)]
    relativ_index = pbd.physical_blocks["offset"]
    
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
        phyBlock["man_id"] = getManufacuter(phyBlock, addr)

    for tdBlock in pbd.transducer_blocks["blocks"]:
        getTranducerBlockInfo(tdBlock, addr)
    
    for fb in pbd.function_blocks["blocks"]:
        fb["parent_class"], fb["class"], fb["value"], fb["status"] = getFunctionBlockInfo(fb, addr)

    
    # TODO: Auslesen der einzelnen Blöcke. PB -> Hersteller, FB -> Funktion und Wert, TB -> Einheit
    return pbd

def sendMessage(framemarker, addr, slot, index):
    framemarker = framemarker.to_bytes(1, 'big')
    addr = addr.to_bytes(1, 'big')          
    slot = slot.to_bytes(1, 'big')    
    index = index.to_bytes(1, 'big')
    msg = framemarker + addr + slot + index
    s.sendto(msg, (ip, port))
    data, _ = s.recvfrom(1024) 
    return data

def getManufacuter(phyBlock, addr):
    # Get Man_ID from physical Block and look up corresponding manufacturer name
    # Relative Index for Man_ID = 110
    device_man_id = sendMessage(1, addr, phyBlock["slot"], phyBlock["index"] + 110)
    device_man_id = int.from_bytes(device_man_id[1:], 'big')
    return device_man_id
    #tree = ET.parse("Man_ID_Table.xml")
    #root = tree.getroot()
    #print(root.xpath(".//Manufacturer[@ID='26']"))
        

def getTranducerBlockInfo(tdBlock, addr):
    slot = tdBlock["slot"]
    index = tdBlock["index"]
    blockinfo = sendMessage(1, addr, slot, index)
    print(f"Found transducer block at Slot {slot} Index {index}: {blockinfo}")

def getFunctionBlockInfo(fBlock, addr):
    slot = fBlock["slot"]
    index = fBlock["index"]
    fbinfo = sendMessage(1, addr, slot, index)
    if(len(fbinfo)>= 5):
        parentClass = fbinfo[3]
        _class = fbinfo[4]
        if parentClass == 1 and _class == 1:
            # Analog Input Function Block
            print(f"Found function block at Slot {slot} Index {index}: Input, Analog Input")
            # Parameter Attributes for the Analog Input Function Block S157: OUT=10
            fb_output = sendMessage(2, addr, slot, index+10)

            try:
                value = struct.unpack('>f', fb_output[1:5])[0]
                status = fb_output[5]
                print(f"With output value = {value} status = {status}")
            except:
                value = None
                status = None

            return "Input", "Analog Input", value, status
        else:
            print(f"Found function block at Slot {slot} Index {index}: Parent Class: {parentClass}, Class: {_class}")
            return parentClass, _class, None, None
    else:
        print(f"Could not find function block at slot {slot} index {index}")
        return None, None, None, None


if __name__ == "__main__":
    main()
