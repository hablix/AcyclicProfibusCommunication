import socket

# Server
ip = "141.76.82.170"
port = 12345
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)

class PB_device():
    pass


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

    pbd.directory = []

    if num_comp >= 1:
        pbd.directory.append({
            "type": "Physical Block",
            "index": dir_entries_list[1],
            "offset": dir_entries_list[2],
            "number": dir_entries_list[3:5]
        })
    
    if num_comp >= 2:
        pbd.directory.append({
            "type": "Transducer Block",
            "index": dir_entries_list[5],
            "offset": dir_entries_list[6],
            "number": dir_entries_list[7:9]
        })
    
    if num_comp >= 3:
        pbd.directory.append({
            "type": "Function Block",
            "index": dir_entries_list[9],
            "offset": dir_entries_list[10],
            "number": dir_entries_list[11:13]
        })
    
    if num_comp >= 4:
        pbd.directory.append({
            "type": "Link Object",
            "index": dir_entries_list[13],
            "offset": dir_entries_list[14],
            "number": dir_entries_list[15:17]
        })
    
    # Get Composite_Directory_Entries
    blocks_index = dir_entries_list[1]
    dir_blocks = sendMessage(framemarker+2, addr, slot, blocks_index)
    # TODO: Auslesen der einzelnen Blöcke. PB -> Hersteller, FB -> Funktion und Wert, TB -> Einheit
    
    print(pbd.directory)
    print(f"From bus address {addr} recieved Composite_Directory_Entries: {dir_blocks}")
    
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


if __name__ == "__main__":
    main()
