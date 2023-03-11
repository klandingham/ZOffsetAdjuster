import serial
import serial.tools.list_ports as port_list
import time

DEBUG_STRINGS = True


class SerialTester:
    INTER_CMD_SLEEP = 0.1
    PRINTER = None
    PRINTER_PORT = ""
    SERIAL_SPEED = 115200
    SERIAL_TIMEOUT = 30

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

    def send_printer_cmd(self, cmd, msg=None, delay=INTER_CMD_SLEEP, ack=False):
        # TODO: DELETE following code is nice to have but causes infinite recursion
        # cmd_tokens = cmd.split()
        # if DEBUG_STRINGS:
        #     print(cmd_tokens)
        # if cmd_tokens[0] in 'G0''G1':
        #     self.send_sync_move_cmd(cmd, msg, delay, True)
        #     return
        time.sleep(delay)
        if DEBUG_STRINGS:
            print("Sending: " + cmd)
        cmd_str = b''
        cmd_str += cmd.encode("Ascii")
        cmd_str += b' \r\n'
        self.PRINTER.write(cmd_str)

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

        # printer = self.PRINTER
        # time.sleep(delay)
        # cmd_str = b''
        # cmd_str += cmd.encode("Ascii")
        # cmd_str += b' \r\n'
        # printer.write(cmd_str)

    def send_printer_cmd_loop(self, cmd, delay=INTER_CMD_SLEEP):
        active = True
        printer = self.PRINTER
        while active:
            print("Enter a printer command (q to quit): ", end="")
            prt_cmd = input()
            if prt_cmd == 'q':
                print("Goodbye")
                exit()
            else:
                print("You entered " + prt_cmd)
            cmd_str = b''
            cmd_str += prt_cmd.upper().encode("Ascii")
            cmd_str += b' \r\n'
            printer.write(cmd_str)
            printer_command_finished = False
            while not printer_command_finished:
                # Wait until there is data waiting in the serial buffer
                if printer.in_waiting > 0:
                    # Read data out of the buffer until a carriage return / new line is found
                    prt_response = printer.readline().decode("Ascii").rstrip()
                    if DEBUG_STRINGS:
                        print(prt_response)
                    # printer should send "ok" when homing has completed
                    if prt_response == 'ok':
                        printer_command_finished = True

    # Rename this function to init_printer() and implement as follows:
    #   - list ports
    #   - attempt to open port
    #   - if port opens
    #   -   flush output
    #   -   set class printer to port
    #   -   return true
    #   - else
    #   -   try next port
    #   - if no ports open
    #   -   output msg and quit
    def init_printer(self):
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
            print("OK")
        return printer_found

    # def find_printer(self):
    #     print("Searching serial ports for a printer, please wait...", end='')
    #     printer_found = False
    #     ports = list(port_list.comports())
    #     for p in ports:
    #         print_device = p.device
    #         try:
    #             test_port = serial.Serial(print_device, baudrate=self.SERIAL_SPEED, timeout=self.SERIAL_TIMEOUT)
    #             test_port.write(b"M31 \r\n")
    #             rsp = test_port.readline().decode("Ascii").rstrip()
    #             test_port.close()
    #         except serial.SerialException as e:
    #             if e.args[0].startswith("could not open"):
    #                 print("\ncould not open port " + p.name + ", does another program have it open?")
    #             continue
    #         if len(rsp) > 0:
    #             printer_found = True
    #         if "T:" in rsp:
    #             printer_found = True
    #         if rsp.startswith("echo:Print"):
    #             printer_found = True
    #         if printer_found:
    #             print("found a printer at port " + test_port.name + ".")
    #             self.PRINTER_PORT = test_port.name
    #             return
    #     print("no printers found, exiting!")
    #     exit(1)


serial_tester = SerialTester()
status = serial_tester.init_printer()
if not status:
    print("could not find a connected printer, exiting.")
    exit(1)
serial_tester.send_sync_cmd("G28", "Homing printer...")
serial_tester.send_sync_move_cmd("G0 Z10", "Moving Z to 10...")
# serial_tester.send_sync_move_cmd("G0 Z20", "Moving Z to 100...", ack=True)
