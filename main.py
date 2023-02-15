# Work in progress: Python script to facilitate setting Z probe offset
# DONE: Automatically determine which port the printer is connected to
# DONE: Implement settings file
import json
import time
import serial
import serial.tools.list_ports as port_list


class ZOffsetAdjuster:
    BED_TEMP = 0
    EXTRUDER_TEMP = 0
    OFFSET_VALUE = 0.0
    OFFSET_INCREMENT = 0.0
    PRINTER_PORT = ""
    PRINTER = None
    INTER_CMD_SLEEP = 3

    def init_printer(self):
        # open printer for I/O
        self.PRINTER = serial.Serial(self.PRINTER_PORT)
        print("Printer port has been opened!")  # debug
        # self.preheat_bed()
        # self.preheat_extruder()
        self.send_sync_cmd("G28")

    def send_printer_cmd(self, cmd):
        time.sleep(self.INTER_CMD_SLEEP)
        cmd_str = b''
        cmd_str += cmd.encode("Ascii")
        cmd_str += b' \r\n'
        self.PRINTER.write(cmd_str)

    def find_printer(self):
        print("Searching serial ports for a printer, please wait...", end='')
        printers_discovered = []
        ports = list(port_list.comports())
        for p in ports:
            print_device = p.device
            test_port = serial.Serial(print_device, timeout=3)
            test_port.write(b"M31 \r\n")
            rsp = test_port.readline().decode("Ascii").rstrip()
            test_port.close()
            if len(rsp) > 0:
                print("found a printer at port " + test_port.name + ".")
                self.PRINTER_PORT = test_port.name
                return
            else:
                printers_discovered.append(test_port)
        if len(printers_discovered) < 1:
            print("No printers found, exiting!")
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
                if len(tokens1) < 4:  # not a heating report
                    continue
                # extract current bed temp
                tokens2 = tokens1[2].split(sep=":")
                current_bed_temp = tokens2[1]
                print("\r Bed temperature: " + current_bed_temp + " -> " + self.BED_TEMP, end="")
                # extract bed heater level
                tokens2 = tokens1[5].split(sep=":")
                bed_heater_level = tokens2[1]
                if bed_heater_level == '0':
                    reading = 0
        self.send_printer_cmd("M155 S0")
        self.send_printer_cmd("M140 S0")  # TODO: remove this line after testing, turn heaters off on exit
        print("")
        return

    def preheat_extruder(self):
        # test_string = "T:18.12 /0.00 B:34.11 /0.00 @:0 B@:0"
        print("Preheating extruder...")
        printer = self.PRINTER
        reading = 1
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
                    reading = 0
        self.send_printer_cmd("M155 S0")
        self.send_printer_cmd("M109 S0")  # TODO: remove this line after testing, turn heaters off on exit
        print("")
        return

    def send_sync_cmd(self, cmd):
        printer = self.PRINTER
        reading = 1
        self.send_printer_cmd("M155 S1")
        self.send_printer_cmd(cmd)
        # while reading:
        for i in range(0, 50):
            # Wait until there is data waiting in the serial buffer
            if printer.in_waiting > 0:
                # Read data out of the buffer until a carriage return / new line is found
                prt_response = printer.readline().decode("Ascii").rstrip()
                print(prt_response)
                reading = 0
        self.send_printer_cmd("M155 S1")


adjuster = ZOffsetAdjuster()
adjuster.load_config()
adjuster.find_printer()
adjuster.init_printer()
