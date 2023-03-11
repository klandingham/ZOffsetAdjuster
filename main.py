# Python script to facilitate setting Z probe offset
# Example temp report from printer: "T:18.12 /0.00 B:34.11 /0.00 @:0 B@:0"

import json
import keyboard
import serial
import serial.tools.list_ports as port_list
import time

DEBUG = False
DEBUG_STRINGS = False


def show_help():
    print("")
    print("\n")
    print("Key Commands:")
    print("\t    - => move nozzle lower and retest")
    print("\t    + => move nozzle higher and retest")
    print("\t    f => toggle fine-tune mode (0.1 or 0.01 increments)")
    print("\t   up => increase move increment")
    print("\t down => decrease move increment")
    print("\t    r => repeat last test from height")
    print("\tenter => accept current offset")
    print("\t  0-9 => enter offset value")
    print("\t    h => display help")
    print("\t    q => quit without saving")
    print("\n")


def clear_prompt_line():
    print("\r                                                                                                \r", end="")


class ZOffsetAdjuster:
    ABORTED = False
    BED_TEMP = 0
    CURRENT_Z_OFFSET = ""
    DISPLAY_DELAY = 3  # length of time to show temporary message (secs)
    EXTRUDER_TEMP = 0
    INTER_CMD_SLEEP = 0.1
    MACHINE_FIRMWARE_NAME = ""
    MACHINE_FIRMWARE_VERSION = ""
    MOVEMENT_SPEED = "F4800"
    OFFSET_VALUE: float = 0.0
    OFFSET_INCREMENT = 0.0
    PRINTER_PORT = ""
    PRINTER = None
    SERIAL_SPEED = 115200
    SERIAL_TIMEOUT = 30
    Z_OFFSET = 0.0

    def init_printer(self):
        if self.PRINTER_PORT != "":
            print("Printer port set to " + self.PRINTER_PORT + " in config file.")
            printer_port = serial.Serial(self.PRINTER_PORT, baudrate=self.SERIAL_SPEED, timeout=self.SERIAL_TIMEOUT)
            self.PRINTER = printer_port
            self.get_firmware_version()
            return True
        print("Searching serial ports for a printer, please wait...", end='')
        printer_found = False
        ports = list(port_list.comports())
        for p in ports:
            test_port = p.device
            try:
                printer_port = serial.Serial(test_port, baudrate=self.SERIAL_SPEED, timeout=self.SERIAL_TIMEOUT)
                # if we reach here, we've found a printer
                printer_found = True
                self.PRINTER = printer_port
                # flush the initial output from the printer
                time.sleep(5)
                for i in range(60):
                    time.sleep(0.05)
                    if printer_port.in_waiting:
                        rsp = printer_port.readline().decode("Ascii").rstrip()
                        if DEBUG_STRINGS:
                            print(str(i) + ": >" + rsp + "<")
                    else:
                        if DEBUG_STRINGS:
                            print(str(i) + ": no more data")
            except serial.SerialException as e:
                continue
        if printer_found:
            print("printer detected on port " + test_port)
            self.get_firmware_version()
        return printer_found

    def send_printer_cmd(self, cmd, msg=None, delay=INTER_CMD_SLEEP, ack=False):
        time.sleep(delay)
        if DEBUG_STRINGS:
            print("Sending: " + cmd)
        cmd_str = b''
        cmd_str += cmd.encode("Ascii")
        cmd_str += b' \r\n'
        self.PRINTER.write(cmd_str)


    def load_config(self):
        print("Loading configuration...", end="")
        with open("config.json", "r") as cfg:
            config = json.load(cfg)
        if DEBUG:  # use lower temps for debugging
            self.BED_TEMP = "25"
            self.EXTRUDER_TEMP = "40"
        else:
            self.BED_TEMP = config["temps"]["bed"]
            self.EXTRUDER_TEMP = config["temps"]["extruder"]
        self.OFFSET_VALUE = config["offset"]["initial"]
        self.OFFSET_INCREMENT = config["offset"]["increment"]
        printer_port = config["printer_port"]["port"]
        if printer_port != "null":
            self.PRINTER_PORT = printer_port
        print("ok.")

    def preheat_bed(self):
        print("Preheating bed...")
        printer = self.PRINTER
        reading = 1
        self.send_printer_cmd("M155 S1")  # enable temp reporting
        self.send_printer_cmd("M140 S" + self.BED_TEMP)
        while reading:
            # Wait until there is data waiting in the serial buffer
            if printer.in_waiting > 0:
                # Read data out of the buffer until a carriage return / new line is found
                prt_response = printer.readline().decode("Ascii").rstrip()
                # split response to get bed heater level (will be >0 while bed is heating)
                if prt_response.startswith("echo:busy"):
                    continue
                tokens1 = prt_response.split()
                if len(tokens1) < 4:  # not a heating report
                    continue
                # extract current bed temp
                tokens2 = tokens1[2].split(sep=":")
                current_bed_temp = tokens2[1]
                print("\r Bed temperature: " + current_bed_temp + " -> " + self.BED_TEMP, end="")
                # extract bed heater level
                tokens2 = tokens1[5].split(sep=":")
                bed_heater_level = tokens2[1]
                if bed_heater_level == '0' and float(current_bed_temp) >= float(self.BED_TEMP):
                    reading = 0
        self.send_printer_cmd("M155 S0")  # disable temp reporting
        print("")
        return

    def preheat_extruder(self):
        print("Preheating extruder...")
        printer = self.PRINTER
        reading = True
        self.send_printer_cmd("M155 S1")
        self.send_printer_cmd("M104 S" + self.EXTRUDER_TEMP)
        while reading:
            # Wait until there is data waiting in the serial buffer
            if printer.in_waiting > 0:
                # Read data out of the buffer until a carriage return / new line is found
                prt_response = printer.readline().decode("Ascii").rstrip()
                if DEBUG_STRINGS:
                    print(prt_response)
                if prt_response.startswith("echo:busy"):
                    continue
                tokens1 = prt_response.split()
                if len(tokens1) < 4:  # not a heating report
                    continue
                # extract current extruder temp
                tokens2 = tokens1[0].split(sep=":")
                current_extruder_temp = tokens2[1]
                print("\r Extruder temperature: " + current_extruder_temp + " -> " + self.EXTRUDER_TEMP, end="")
                # extract extruder heater level
                # Example temp report from printer: "T:18.12 /0.00 B:34.11 /0.00 @:0 B@:0"
                tokens2 = tokens1[4].split(sep=":")
                extruder_heater_level = tokens2[1]
                if float(extruder_heater_level) < 127 and float(current_extruder_temp) >= float(self.EXTRUDER_TEMP):
                    reading = False
        self.send_printer_cmd("M155 S0")  # disable temp reporting
        print("")
        return

    def send_sync_cmd(self, cmd, msg, delay=INTER_CMD_SLEEP, ack=False):
        # To get synchronous command, fills Marlin queue with 4 "no-op" commands,
        # then waits for the correct number of "ok" responses
        print(msg, end="")
        time.sleep(delay)
        num_oks = 0
        printer = self.PRINTER
        self.send_printer_cmd(cmd)
        self.send_printer_cmd("M31")
        self.send_printer_cmd("M31")
        self.send_printer_cmd("M31")
        self.send_printer_cmd("M31")
        while num_oks < 5:
            # Wait until there is data waiting in the serial buffer
            if printer.in_waiting > 0:
                # Read data out of the buffer until a carriage return / new line is found
                prt_response = printer.readline().decode("Ascii").rstrip()
                if DEBUG_STRINGS:
                    print(prt_response)
                if prt_response == "ok":
                    num_oks += 1
        print("OK")

    def home_printer(self):
        # To get synchronous command, fills Marlin queue with 4 "no-op" commands,
        # then waits for the correct number of "ok" responses
        print("Homing printer...", end="")
        num_oks = 0
        prt_response = ""
        printer = self.PRINTER
        self.send_printer_cmd("G28")
        self.send_printer_cmd("M31")
        self.send_printer_cmd("M31")
        self.send_printer_cmd("M31")
        self.send_printer_cmd("M31")
        while num_oks < 5:
            # Wait until there is data waiting in the serial buffer
            if printer.in_waiting > 0:
                # Read data out of the buffer until a carriage return / new line is found
                prt_response = printer.readline().decode("Ascii").rstrip()
                if prt_response == 'ok':
                    num_oks += 1
                else:
                    print(".", end="")
                # print(prt_response)  # debug
        print("OK")

    def adjust_z_offset(self):
        print("\nSetting up for Z-offset measurement...")
        self.send_sync_cmd("M211 S1", "\tenabling software endstops...")
        self.send_sync_cmd("M851 Z0", "\tclearing current Z-offset...")
        self.send_sync_cmd("M500", "\tsaving settings to EEPROM...")
        self.send_sync_cmd("G28", "\thoming printer...")
        self.send_sync_move_cmd("G1 X110 Y110 F1000", "\tmoving nozzle to bed center...", delay=0)
        self.send_sync_cmd("M211 S0", "\tdisabling software endstops...")
        print("Setup complete.")
        self.obtain_z_offset()

    def obtain_z_offset(self):
        print("\nBeginning Z-offset testing...\n")
        print("Insert paper, press any key to continue...", end="")
        event = keyboard.read_event(suppress=True)
        print("")
        fine_tune_mode = False
        offset = self.OFFSET_VALUE
        offset_float = float(offset)
        increment = self.OFFSET_INCREMENT
        offset_accepted = False
        test_from_height = False  # when true, raises nozzle before testing offset
        increment_changed = False  # do not re-measure if only increment change
        while not offset_accepted:
            clear_prompt_line()
            print("\rOffset = {0:.2f}, wait...".format(float(offset)), end="")
            if not increment_changed:
                if test_from_height:
                    test_from_height = False
                    self.send_sync_move_cmd("G0 Z10 " + self.MOVEMENT_SPEED, msg=None, delay=0, ack=False)
                offset_cmd = "G0 Z" + offset + " " + self.MOVEMENT_SPEED
                self.send_sync_move_cmd(offset_cmd, msg=None, delay=0, ack=False)
                print(" Test now then enter a command (h for help): ", end="")
            increment_changed = False
            event = keyboard.read_event()
            if event.event_type == keyboard.KEY_DOWN:
                key = event.name
                if DEBUG_STRINGS:
                    print(f'Pressed: {key}')
                # Note: using if's instead of case for older Pythons
                if key.isdigit():
                    # event = None
                    clear_prompt_line()
                    manual_offset = "-" + key
                    offset_entered = False
                    decimal_point_entered = False
                    print("Enter desired offset -N.NN (esc to abort): " + manual_offset, end="")
                    while not offset_entered:
                        o_event = keyboard.read_event()
                        if o_event.event_type == keyboard.KEY_DOWN:
                            o_key = o_event.name
                            if o_key == "decimal":
                                if not decimal_point_entered:
                                    print(".", end="")
                                    manual_offset += "."
                                    decimal_point_entered = True
                            elif o_key.isdigit():
                                manual_offset += o_key
                                print(o_key, flush=True, end="")
                            if len(manual_offset) == 5:  # 3 digits, a decimal point, and leading minus sign
                                time.sleep(0.5)  # short delay for last digit to be displayed
                                offset_entered = True
                    offset = manual_offset
                elif key == '-':  # move nozzle lower (make offset more negative)
                    offset_float = float(offset)
                    increment_float = float(increment)
                    offset_float -= increment_float
                    offset = str(round(offset_float, 2))
                elif key == '+':  # move nozzle higher (make offset less negative)
                    offset_float = float(offset)
                    increment_float = float(increment)
                    offset_float += increment_float
                    offset = str(round(offset_float, 2))
                elif key == 'r':  # repeat last measurement
                    test_from_height = True
                    continue
                elif key == 'f':  # toggle fine-tune mode
                    clear_prompt_line()
                    if fine_tune_mode:
                        fine_tune_mode = False
                        increment = self.OFFSET_INCREMENT
                        print("Adjustment increment reset to {0:1.1f}".format(float(increment)), end="")
                    else:
                        fine_tune_mode = True
                        increment = 0.01
                        print("Adjustment increment set to {0:1.2f}".format(float(increment)), end="")
                    time.sleep(self.DISPLAY_DELAY)
                    clear_prompt_line()
                    continue
                elif key == 'h':
                    show_help()
                elif key == 'enter':
                    self.Z_OFFSET = offset_float
                    print("\rOffset = {0:.2f}, wait...".format(float(offset)), end="")
                    print("\n\nZ-offset has been set to {0:.2f}".format((round(self.Z_OFFSET, 2))))
                    break
                elif key == 'q':
                    self.ABORTED = True
                    break

    def send_sync_move_cmd(self, move_command, msg=None, delay=INTER_CMD_SLEEP, ack=True):
        if msg is not None:
            print(msg, end="")
        printer = self.PRINTER
        num_oks = 0
        # issue the move command
        self.send_printer_cmd(move_command, delay)
        self.send_printer_cmd("G4 S1", 0)
        self.send_printer_cmd("M31", 0)
        self.send_printer_cmd("M31", 0)
        self.send_printer_cmd("M31", 0)
        while num_oks < 5:
            # Wait until there is data waiting in the serial buffer
            if printer.in_waiting > 0:
                # Read data out of the buffer until a carriage return / new line is found
                prt_response = printer.readline().decode("Ascii").rstrip()
                if prt_response == "ok":
                    num_oks += 1
        if ack:
            print("OK")

    def finish_processing(self):
        if not self.ABORTED:
            print("\nFinishing up...")
            self.send_sync_cmd("M211 S1", "\tre-enabling software endstops...")
            self.send_sync_cmd("G92 Z0", "\tsetting Z = 0 to current Z position...")
            cmd_str = "M851 Z" + str(round(self.Z_OFFSET, 2))
            msg = "\tsetting Z-offset value to {0:.2f}...".format(round(float(self.Z_OFFSET), 2))
            self.send_sync_cmd(cmd_str, msg)
            self.send_sync_cmd("M500", "\tsaving settings to EEPROM...")
            self.send_sync_cmd("M140 S0", "\tturning off bed heater...")
            self.send_sync_cmd("M109 S0", "\tturning off extruder heater...")
            self.send_sync_cmd("G0 Z10", "\traising nozzle...")
            self.send_printer_cmd("M155 S1")  # enable temp reporting
            print("Finished, exiting...")
            exit(0)
        else:
            print("\nProcessing aborted...")
            self.send_sync_cmd("M211 S1", "\tre-enabling software endstops...")
            self.send_sync_cmd("M140 S0", "\tturning off bed heater...")
            self.send_sync_cmd("M109 S0", "\tturning off extruder heater...")
            msg = "\trestoring previous Z-offset (" + self.CURRENT_Z_OFFSET + ")..."
            self.send_sync_cmd("M851 Z-" + self.CURRENT_Z_OFFSET, msg)
            self.send_printer_cmd("M155 S1")  # enable temp reporting
            print("Exiting...")
            exit(1)

    def save_current_z_offset(self):
        print("Saving current Z-offset value: ", end="")
        current_offset = ""
        printer = self.PRINTER
        reading = True
        self.send_printer_cmd("M851")
        while reading:
            # Wait until there is data waiting in the serial buffer
            if printer.in_waiting > 0:
                # Read data out of the buffer until a carriage return / new line is found
                prt_response = printer.readline().decode("Ascii").rstrip()
                if DEBUG_STRINGS:
                    print(prt_response)
                if prt_response == "ok":
                    reading = False
                    continue
                if "Probe Z Offset" in prt_response:  # Marlin 1.1.9
                    tokens = prt_response.split(":")
                    current_offset = tokens[2].strip()
                elif "Probe Offset" in prt_response:  # Marlin 2.0.7.2
                    tokens = prt_response.split()
                    current_offset = tokens[4].split("-")[1]
        self.CURRENT_Z_OFFSET = current_offset
        # if the Z probe offset is already set, start with that instead of the default in config
        if float(current_offset) > 0.5:
            self.OFFSET_VALUE = current_offset
        print(self.CURRENT_Z_OFFSET)

    def preheat(self):
        self.preheat_bed()
        self.preheat_extruder()

    def get_firmware_version(self):
        print("Checking printer firmware version: ", end="")
        prt_response = ""
        printer = self.PRINTER
        reading = True
        self.send_printer_cmd("M115")
        while reading:
            # Wait until there is data waiting in the serial buffer
            if printer.in_waiting > 0:
                # Read data out of the buffer until a carriage return / new line is found
                prt_response = printer.readline().decode("Ascii").rstrip()
                if DEBUG_STRINGS:
                    print(prt_response)
                if prt_response == "ok":
                    reading = False
                    continue
                if prt_response.startswith("FIRMWARE_NAME"):
                    tokens = prt_response.split()
                    self.MACHINE_FIRMWARE_NAME = tokens[0].split(":")[1]
                    self.MACHINE_FIRMWARE_VERSION = tokens[1]
        if self.MACHINE_FIRMWARE_NAME != "":
            print(self.MACHINE_FIRMWARE_NAME + " " + self.MACHINE_FIRMWARE_VERSION)


adjuster = ZOffsetAdjuster()
adjuster.load_config()
# adjuster.find_printer()
status = adjuster.init_printer()
if not status:
    print("could not connect to a printer, no printer found or port busy.  Exiting.")
    exit(1)
adjuster.save_current_z_offset()
adjuster.preheat()
adjuster.adjust_z_offset()
adjuster.finish_processing()
