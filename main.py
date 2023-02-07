# Work in progress: Python script to facilitate setting Z probe offset
# TODO: Automatically determine which port the printer is connected to <-- CURRENT WORK
# TODO: Timeout procedure that waits for input for a specified time
# TODO: Implement settings file
import time
import serial
import serial.tools.list_ports as port_list

# globals
# printer_port_name = ""      # serial port for printer


def find_printer():
    print("Searching serial ports for a printer, please wait...", end='')
    port_name = ''
    printers_discovered = []
    ports = list(port_list.comports())
    for p in ports:
        port_name = p.device
        test_port = serial.Serial(port_name, timeout=3)
        test_port.write(b"M31 \r\n")
        rsp = test_port.readline().decode("Ascii").rstrip()
        if len(rsp) > 0:
            print("found a printer at port " + port_name + ".")
            printers_discovered.append(port_name)
        test_port.close()
    if len(printers_discovered) > 1:
        print("\nError: more than one printer found, please connect only one printer.")
        exit(1)
    elif len(printers_discovered) < 1:
        print("no printers found, exiting.")
        exit(1)
    return port_name


printer_port = find_printer()
exit(0)
# TODO: Auto-detect printer port (how?)

printer = serial.Serial("COM4")
# serialPort = serial.Serial(
#     port="COM4", baudrate=9600, bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE
# )
printer.write(b"M503 \r\n")
# # s.write(b"G28 \r\n")
response = ""  # Used to hold data coming over UART
reading = 1
while reading:
    # Wait until there is data waiting in the serial buffer
    if printer.in_waiting > 0:
        # Read data out of the buffer until a carraige return / new line is found
        response = printer.readline()
        sss = response.decode("Ascii").rstrip()
        if sss == "ok":
            reading = 0
        # Print the contents of the serial data
        print(sss)

# test: home, set relative positioning, raise Z in loop, set absolute positioning
# pending question: if I send printer a command that takes some time to complete,
# how do I tell it finished?
#
# Result: The initial sleep I tried wasn't long enough. The printer seemed to accept more
# commands while it was still homing...when the homing finished, it increased the Z position.
# So the commands in the for loop must have been put in some kind of queue.
printer.write(b"G28\r\n")
print("Waiting for home")
time.sleep(10)
print("Setting relative positioning")
printer.write(b"G91\r\n")
time.sleep(1)
print("Increasing Z...")
for i in range(6):
    printer.write(b"G1 Z5\r\n")
    time.sleep(1)
    print(i)
print("Setting absolute positioning")
printer.write(b"G91\r\n")

print("End")
# <editor-fold desc="Sample Code">
# s = serial.Serial("COM4")
# s.write(b"M503 \r\n")
# # s.write(b"G28 \r\n")
# out = ''
# # let's wait one second before reading output (let's give device time to answer)
# time.sleep(1)
# # while serial.inWaiting() > 0:
# #   out += ser.read(1)
# read_val = s.read(size=4096)
# s.flush()
# print(read_val.decode("Ascii"))
# # print
# #   read_val
# #         if out != '':
# #             print(">>" + out)
# # res = s.read()
# # print(res.decode("Ascii"))


# configure the serial connections (the parameters differs on the device you are connecting to)
# ser = serial.Serial(
#     # port='/dev/ttyUSB1',
#     port='COM4:',
#     baudrate=9600,
#     parity=serial.PARITY_ODD,
#     stopbits=serial.STOPBITS_TWO,
#     bytesize=serial.SEVENBITS
# )
#
# ser.isOpen()
#
# print('Enter your commands below.\r\nInsert "exit" to leave the application.')
# my_input = 1
# while 1:
#     # get keyboard input
#     my_input: str = input(">> ")
#     # Python 3 users
#     # input = input(">> ")
#     if my_input == 'exit':
#         ser.close()
#         exit()
#     else:
#         # send the character to the device
#         # (note that I happend a \r\n carriage return and line feed to the characters - this is requested by my device)
#         # ser.write(my_input + '\r\n')
#         ser.write(my_input)
#         out = ''
#         # let's wait one second before reading output (let's give device time to answer)
#         time.sleep(1)
#         while ser.inWaiting() > 0:
#             out += ser.read(1)
#
#         if out != '':
#             print(">>" + out)
# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
# import serial
# import io
#
# ser = serial.serial_for_url('loop://', timeout=1)
# sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser, 1), encoding='ascii')
#
# # sio.write(unicode("hello\n"))
# sio.write("hello\n")
# sio.flush()  # it is buffering. required to get the data out *now*
# hello = sio.readline()
# # print(hello == unicode("hello\n"))
# print(hello == "hello\n")

# def print_hi(name):
#     # Use a breakpoint in the code line below to debug your script.
#     print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


# Press the green button in the gutter to run the script.
# if __name__ == '__main__':
#     print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
# </editor-fold>
