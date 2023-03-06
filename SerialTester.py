import serial
import serial.tools.list_ports as port_list
import time


class SerialTester:
    INTER_CMD_SLEEP = 0.1
    PRINTER = None
    PRINTER_PORT = ""
    SERIAL_SPEED = 115200
    SERIAL_TIMEOUT = 30

    def init_printer(self):
        # open printer for I/O
        self.PRINTER = serial.Serial(self.PRINTER_PORT, baudrate=self.SERIAL_SPEED, timeout=self.SERIAL_TIMEOUT)
        # self.send_printer_cmd("M155 S0")  # disable temp reporting
        self.send_printer_cmd("M155 S1")  # enable temp reporting
        print("Printer port has been opened!", flush=True)  # debug

    def send_printer_cmd(self, cmd, delay=INTER_CMD_SLEEP):
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
            max_responses = 50
            response_count = 0
            while response_count < max_responses:
                # Wait until there is data waiting in the serial buffer
                if printer.in_waiting > 0:
                    # Read data out of the buffer until a carriage return / new line is found
                    prt_response = printer.readline().decode("Ascii").rstrip()
                    print(prt_response)
                    response_count += 1
                    # printer should send "ok" when homing has completed
                    # if prt_response == 'ok':
                    #     reading = False

    def find_printer(self):
        print("Searching serial ports for a printer, please wait...", end='')
        printer_found = False
        ports = list(port_list.comports())
        for p in ports:
            print_device = p.device
            try:
                test_port = serial.Serial(print_device, baudrate=self.SERIAL_SPEED, timeout=self.SERIAL_TIMEOUT)
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


serial_tester = SerialTester()
serial_tester.find_printer()
serial_tester.init_printer()
time.sleep(2)
serial_tester.send_printer_cmd("G28")
