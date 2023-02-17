# Python script to facilitate setting Z probe offset

import json
import keyboard
import serial
import serial.tools.list_ports as port_list
import time


def show_help():
    print("")
    print("\n")
    print("Key Commands:")
    print("\t    - => move nozzle lower and retest")
    print("\t    + => move nozzle higher and retest")
    print("\t   up => increase move increment")
    print("\t down => decrease move increment")
    print("\t    r => repeat last test from height")
    print("\tenter => accept current offset")
    print("\t    h => display help")
    print("\t    q => quit without saving")
    print("\n")


def modify_increment(increment):
    print("")
    print("Use + and - keys to change increment value, press ENTER when done.")
    modified_increment = increment
    print("increment value = " + modified_increment, end="")
    offset_accepted = False
    while not offset_accepted:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN:
            key = event.name
            if key == "+":
                float_value = float(modified_increment)
                float_value += .01
                modified_increment = str(round(float_value, 2))
                print("\rincrement value = " + modified_increment, end="")
                continue
            elif key == "-":
                float_value = float(modified_increment)
                float_value -= .01
                modified_increment = str(round(float_value, 2))
                print("\rincrement value = " + modified_increment, end="")
                continue
            elif key == 'enter':
                offset_accepted = True
    return modified_increment


class ZOffsetAdjuster:
    ABORTED = False
    BED_TEMP = 0
    EXTRUDER_TEMP = 0
    INTER_CMD_SLEEP = 0.5
    MOVEMENT_SPEED = "F4800"
    OFFSET_VALUE: float = 0.0
    OFFSET_INCREMENT = 0.0
    PRINTER_PORT = ""
    PRINTER = None
    Z_OFFSET = 0.0
    CURRENT_Z_OFFSET = ""

    def init_printer(self):
        # open printer for I/O
        self.PRINTER = serial.Serial(self.PRINTER_PORT)
        print("Printer port has been opened!")  # debug

    def send_printer_cmd(self, cmd, delay=INTER_CMD_SLEEP):
        time.sleep(delay)
        cmd_str = b''
        cmd_str += cmd.encode("Ascii")
        cmd_str += b' \r\n'
        self.PRINTER.write(cmd_str)

    def find_printer(self):
        print("Searching serial ports for a printer, please wait...", end='')
        printer_found = False
        ports = list(port_list.comports())
        for p in ports:
            print_device = p.device
            try:
                test_port = serial.Serial(print_device, timeout=3)
                test_port.write(b"M31 \r\n")
                rsp = test_port.readline().decode("Ascii").rstrip()
                test_port.close()
            except serial.SerialException as e:
                if e.args[0].startswith("could not open"):
                    print("\ncould not open port " + p.name + ", does another program have it open?")
                continue
            if "T:" in rsp:
                printer_found = True
            if rsp.startswith("echo:Print"):
                printer_found = True
            if printer_found:
                print("found a printer at port " + test_port.name + ".")
                self.PRINTER_PORT = test_port.name
                return
        print("no printers found, exiting!")
        exit(1)

    def load_config(self):
        print("Loading configuration...", end="")
        with open("config.json", "r") as cfg:
            config = json.load(cfg)
        self.BED_TEMP = config["temps"]["bed"]
        self.EXTRUDER_TEMP = config["temps"]["extruder"]
        self.OFFSET_VALUE = config["offset"]["initial"]
        self.OFFSET_INCREMENT = config["offset"]["increment"]
        print("ok.")

    def preheat_bed(self):
        # test_string = "T:18.12 /0.00 B:34.11 /0.00 @:0 B@:0"
        print("Preheating bed...")
        printer = self.PRINTER
        reading = 1
        self.send_printer_cmd("M140 S" + self.BED_TEMP)
        time.sleep(3)  # gives printer a chance to power on bed heater
        self.send_printer_cmd("M155 S1")
        while reading:
            # Wait until there is data waiting in the serial buffer
            if printer.in_waiting > 0:
                # Read data out of the buffer until a carriage return / new line is found
                prt_response = printer.readline().decode("Ascii").rstrip()
                # split response to get bed heater level (will be >0 while bed is heating)
                tokens1 = prt_response.split()
                if prt_response.startswith("echo:busy"):
                    continue
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
        self.send_printer_cmd("M155 S0")
        print("")
        return

    def preheat_extruder(self):
        # test_string = "T:18.12 /0.00 B:34.11 /0.00 @:0 B@:0"
        print("Preheating extruder...")
        printer = self.PRINTER
        reading = True
        self.send_printer_cmd("M109 S" + self.EXTRUDER_TEMP)
        time.sleep(5)  # gives printer a chance to power on extruder
        self.send_printer_cmd("M155 S1")
        while reading:
            # Wait until there is data waiting in the serial buffer
            if printer.in_waiting > 0:
                # Read data out of the buffer until a carriage return / new line is found
                prt_response = printer.readline().decode("Ascii").rstrip()
                if prt_response == 'ok':
                    continue
                # split response to get bed heater level (will be >0 while bed is heating)
                tokens1 = prt_response.split()
                if len(tokens1) < 4:  # not a heating report
                    continue
                # extract current extruder temp
                tokens2 = tokens1[0].split(sep=":")
                current_extruder_temp = tokens2[1]
                print("\r Extruder temperature: " + current_extruder_temp + " -> " + self.EXTRUDER_TEMP, end="")
                if current_extruder_temp >= self.EXTRUDER_TEMP:
                    reading = False
        self.send_printer_cmd("M155 S0")
        print("")
        return

    def send_sync_cmd(self, cmd, msg, delay=INTER_CMD_SLEEP):
        print(msg, end="")
        time.sleep(delay)
        printer = self.PRINTER
        reading = True
        self.send_printer_cmd(cmd)
        while reading:
            # Wait until there is data waiting in the serial buffer
            if printer.in_waiting > 0:
                # Read data out of the buffer until a carriage return / new line is found
                prt_response = printer.readline().decode("Ascii").rstrip()
                if prt_response == 'ok':
                    reading = False
        print("OK")

    def home_printer(self):
        print("Homing printer...", end="")
        prt_response = ""
        printer = self.PRINTER
        reading = True
        self.send_printer_cmd("G28")
        while reading:
            # Wait until there is data waiting in the serial buffer
            if printer.in_waiting > 0:
                # Read data out of the buffer until a carriage return / new line is found
                prt_response = printer.readline().decode("Ascii").rstrip()
            # printer should send "ok" when homing has completed
            if prt_response == 'ok':
                reading = False
        print("OK")

    def adjust_z_offset(self):
        print("\nSetting up for Z-offset measurement...")
        self.send_sync_cmd("M211 S1", "\tenabling software endstops...")
        self.send_sync_cmd("M851 Z0", "\tclearing current Z-offset...")
        self.send_sync_cmd("M500", "\tsaving settings to EEPROM...")
        self.send_sync_cmd("G28", "\thoming printer...")
        self.send_sync_move_cmd("G1 X110 Y110 F1000", "\tmoving nozzle to bed center...")
        self.send_sync_cmd("M211 S0", "\tdisabling software endstops...")
        print("Setup complete.")
        self.obtain_z_offset()

    def obtain_z_offset(self):
        print("\nBeginning Z-offset testing...\n")
        print("Insert paper, press any key to continue...", end="")
        print("")
        offset = self.OFFSET_VALUE
        offset_float = float(offset)
        increment = self.OFFSET_INCREMENT
        offset_accepted = False
        test_from_height = False  # when true, raises nozzle before testing offset
        increment_changed = False  # do not re-measure if only increment change
        while not offset_accepted:
            print("\rOffset increment: " + increment + "\tOffset value: " + offset)
            if not increment_changed:
                if test_from_height:
                    test_from_height = False
                    self.send_sync_move_cmd("G0 Z10 " + self.MOVEMENT_SPEED, msg=None, delay=0)
                offset_cmd = "G0 Z" + offset + " " + self.MOVEMENT_SPEED
                self.send_sync_move_cmd(offset_cmd, msg=None, delay=0)
                print("Test paper drag now!\n")
            print("press a command key (h for help): ", end="")
            increment_changed = False
            event = keyboard.read_event()
            if event.event_type == keyboard.KEY_DOWN:
                key = event.name
                print(f'Pressed: {key}')  # debug
                # Note: using if's instead of case for older Pythons
                if key == 'up' or key == 'down':
                    new_increment = modify_increment(increment)
                    if new_increment != increment:
                        increment_changed = True
                        increment = new_increment
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
                elif key == 'h':
                    show_help()
                elif key == 'enter':
                    self.Z_OFFSET = offset_float
                    print("Z-offset value of " + str(round(self.Z_OFFSET, 2)) + " accepted.")
                    break
                elif key == 'q':
                    self.ABORTED = True
                    break

    def send_sync_move_cmd(self, move_command, msg=None, delay=INTER_CMD_SLEEP):
        if msg is not None:
            print(msg, end="")
        printer = self.PRINTER
        # issue the move command
        self.send_printer_cmd(move_command, delay)
        # block further command processing until move has finished
        self.send_printer_cmd("M400", delay)
        # add a command to the queue: get print time
        # will use the response to this command to determine that the move has finished
        self.send_printer_cmd("M31", delay)
        move_finished = False
        while not move_finished:
            time.sleep(0.5)
            # Wait until there is data waiting in the serial buffer
            if printer.in_waiting > 0:
                # Read data out of the buffer until a carriage return / new line is found
                prt_response = printer.readline().decode("Ascii").rstrip()
                if prt_response.startswith("echo:Print"):
                    move_finished = True
        if msg is not None:
            print("OK")

    def finish_processing(self):
        if not self.ABORTED:
            print("\nFinishing up...")
            self.send_sync_cmd("M211 S1", "\tre-enabling software endstops...")
            self.send_sync_cmd("G92 Z0", "\tsetting Z = 0 to current Z position...")
            cmd_str = "M851 Z" + str(round(self.Z_OFFSET, 2))
            self.send_sync_cmd(cmd_str, "\tsaving Z-offset value...")
            self.send_sync_cmd("M500", "\tsaving settings to EEPROM...")
            print("\tturning off bed heater...")
            self.send_printer_cmd("M140 S0")
            print("\tturning off extruder heater...")
            self.send_printer_cmd("M109 S0")
            self.home_printer()
            print("Finished, exiting...")
            exit(0)
        else:
            print("\nProcessing aborted...")
            self.send_sync_cmd("M211 S1", "\tre-enabling software endstops...")
            print("\tturning off bed heater...")
            self.send_printer_cmd("M140 S0")
            print("\tturning off extruder heater...")
            self.send_printer_cmd("M109 S0")
            # TODO: restore old Z-offset here
            print("\trestoring previous Z-offset...")
            self.send_printer_cmd("M851 Z-" + self.CURRENT_Z_OFFSET)
            self.home_printer()
            print("Exiting...")
            exit(1)

    def save_current_z_offset(self):
        print("Saving current Z-offset value: ", end="")
        prt_response = ""
        printer = self.PRINTER
        reading = True
        self.send_printer_cmd("M851")
        while reading:
            # Wait until there is data waiting in the serial buffer
            if printer.in_waiting > 0:
                # Read data out of the buffer until a carriage return / new line is found
                prt_response = printer.readline().decode("Ascii").rstrip()
            # printer should send "ok" when homing has completed
            if prt_response.startswith("Probe Offset"):
                tokens = prt_response.split("Z-")
                self.CURRENT_Z_OFFSET = tokens[1]
                print(self.CURRENT_Z_OFFSET)
                return

    def preheat(self):
        self.preheat_bed()
        self.preheat_extruder()


adjuster = ZOffsetAdjuster()
adjuster.load_config()
adjuster.find_printer()
adjuster.init_printer()
adjuster.save_current_z_offset()
adjuster.preheat()
adjuster.adjust_z_offset()
adjuster.finish_processing()
