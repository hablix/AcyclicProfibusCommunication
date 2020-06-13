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
    dir_entries = sendMessage(framemarker+1, addr, slot, index+1)

    
    
    print(f"From bus address: {addr} recieved: {dir_entries}")
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
