# Work in progress: Python script to facilitate setting Z probe offset
# DONE: Automatically determine which port the printer is connected to
# TODO: Timeout procedure that waits for input for a specified time <-- CURRENT WORK
# TODO: Implement settings file
import json
import time

import keyboard
from select import select
from pytimedinput import *
import serial
import serial.tools.list_ports as port_list
import signal


# globals
BED_TEMP = 0
EXTRUDER_TEMP = 0
OFFSET_VALUE = 0.0
OFFSET_INCREMENT = 0.0
# OFFSET_TEST_TIMEOUT = 5         # number of seconds to wait during each Z offset test


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
        test_port.close()
        if len(rsp) > 0:
            print("found a printer at port " + port_name + ".")
            return port_name
    #         printers_discovered.append(port_name)
    # if len(printers_discovered) > 1:
    #     print("\nError: more than one printer found, please connect only one printer.")
    #     exit(1)
        else:
            printers_discovered.append(port_name)
    if len(printers_discovered) < 1:
        print("no printers found, exiting.")
        exit(1)


def send_sync_command(gcode_cmd, console_msg):
    print(console_msg, flush=True)
    reading = 1
    printer_response = ""
    print('Sending gcode: ' + gcode_cmd)
    cmd_str = b''
    cmd_str += gcode_cmd.encode("Ascii")
    cmd_str += b' \r\n'
    printer.write(cmd_str)
    while reading:
        # Wait until there is data waiting in the serial buffer
        if printer.in_waiting > 0:
            # Read data out of the buffer until a carriage return / new line is found
            prt_response = printer.readline().decode("Ascii").rstrip()
            if prt_response == "ok":
                reading = 0
            # Print the contents of the serial data
            if prt_response != "echo:busy: processing":
                print(prt_response) # KIP DEBUG
                printer_response += prt_response
    return printer_response


def test_key_inputs():
    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN:
            key = event.name
            print(f'Pressed: {key}')
            if key == 'q':
                break


def test_timed_input():
    user_text, timed_out = timedKey("Please, press 'y' to accept or 'n' to decline: ", allowCharacters="yn")
    if timed_out:
        print(">>>" + user_text + "<<<")
        print("Timed out when waiting for input. Pester the user later.")
    else:
        print(">>>" + user_text + "<<<")
        if user_text == "y":
            print("User consented to selling their first-born child!")
        else:
            print("User unfortunately declined to sell their first-born child!")


def test_output_overlay():
    inc = 0.1
    offset = -2.00
    for i in range(1, 10):
        print("\r Increment = %.2f , current offset = %.2f" % (inc, offset), end="")
        offset += inc
        inc += 0.01
        time.sleep(1)
    print("")


def load_config():
    with open("config.json", "r") as cfg:
        config = json.load(cfg)
    BED_TEMP = config["temps"]["bed"]
    EXTRUDER_TEMP = config["temps"]["extruder"]
    OFFSET_VALUE = config["offset"]["initial"]
    OFFSET_INCREMENT = config["offset"]["increment"]

    # NEXT: load settings into variables, list each with numbers, offer to edit any, or <ENTER> to accept

# test_key_inputs()
# test_output_overlay()
load_config()
exit(0)
# end of testing code

printer_port = find_printer()
print("Opening printer port...", end="", flush=True)
# printer = serial.Serial("COM4")
printer = serial.Serial(printer_port)
print("ok", flush=True)
response = send_sync_command("M503", "Querying printer settings")
print(response)
response = send_sync_command("G0 Z20", "20")
print(response)
response = send_sync_command("G0 Z40", "40")
print(response)
# printer = serial.Serial(printer_port)
# serialPort = serial.Serial(
#     port="COM4", baudrate=9600, bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE
# )
# print("Querying printer for settings...")
# printer.write(b"M503 \r\n")
# # s.write(b"G28 \r\n")
# response = ""  # Used to hold data coming over UART
# # reading = 1
# # while reading:
#     # Wait until there is data waiting in the serial buffer
#     # if printer.in_waiting > 0:
#     # Read data out of the buffer until a carriage return / new line is found
#     response = printer.readline()
#     sss = response.decode("Ascii").rstrip()
#     if sss == "ok":
#         reading = 0
#     # Print the contents of the serial data
#     print(sss)


# test: home, set relative positioning, raise Z in loop, set absolute positioning
# pending question: if I send printer a command that takes some time to complete,
# how do I tell it finished?
#
# Result: The initial sleep I tried wasn't long enough. The printer seemed to accept more
# commands while it was still homing...when the homing finished, it increased the Z position.
# So the commands in the for loop must have been put in some kind of queue.




# printer.write(b"G28\r\n")
# print("Waiting for home")
# time.sleep(10)
# print("Setting relative positioning")
# printer.write(b"G91\r\n")
# time.sleep(1)
# print("Increasing Z...")
# for i in range(6):
#     printer.write(b"G1 Z5\r\n")
#     time.sleep(1)
#     print(i)
# print("Setting absolute positioning")
# printer.write(b"G91\r\n")

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
