import serial
from serial.tools import list_ports_windows
import ipywidgets as widgets
import binascii
import threading
import time
import math # standard math functions

class control():
    def __init__(self, logger, jump_table):
        self.jump_table=jump_table
        self.logger = logger
        self.valid_packets = 0
        self.corrupt_packets = 0
        self.stop_now = False
        self.lock = threading.Lock()  
        self.read_lock = threading.Lock()
        self.ser = None

    def release_lock(self):
        if self.lock.locked():
            self.lock.release()
            
    def acquire_lock(self):
        self.lock.acquire()
            
    def parse_packet(self, packet):
         global update_sensors
         p = str(packet)
         p = p.replace('b\'', '')
         p = p.replace('\\r\\n', '')
         p = p.replace('\'', '')
         L = p.split(',')
         D = {	'accelX':    float(L[0]), 'accelY':    float(L[1]), 'accelZ': float(L[2]), \
                'gyroX':     float(L[3]), 'gyroY':     float(L[4]), 'gyroZ':  float(L[5]), \
                'magX':      float(L[6]), 'magY':      float(L[7]), 'magZ':   float(L[8]), \
                'pressure':  float(L[9]), 'temp':      float(L[10]), 'rH':    float(L[11]), \
                'proximity': math.floor(float(L[12])), 'maxAudio': math.floor(float(L[13]))}
         #self.logger.info('packet type = %s', str(D))
         process_packet = self.jump_table[0]
         if (process_packet != None):
             with self.lock:
                 try:
                     process_packet(D)
                 except Exception as ex:
                     self.logger.error("ERROR found in parse_packet: %s.", str(ex))            


    def open(self, portName):
        self.logger.info("Starting process to open %s.", portName)
        self.ser = serial.Serial()
        self.ser.baudrate = 9600
        self.ser.port = portName
        self.ser.timeout = 1
        try:
            self.ser.open()
        except Exception as ex:
            self.logger.error("ERROR: Could not open serial port - exception: %s.", str(ex))            
        self.ser.set_buffer_size(rx_size = 32768, tx_size = 4096) # must be called AFTER opening the port
        # see https://stackoverflow.com/questions/12302155/how-to-expand-input-buffer-size-of-pyserial
        self.logger.info("%s port has been opened.", portName)
        return(self.ser.is_open)

    def isOpen(self):
        if self.ser==None:
            return False
        return(self.ser.is_open)
    
    def close(self):
        self.ser.close()
        return(not self.ser.is_open)

    def print_stats(self):
        self.logger.info("Corrupt packets: %s", str(self.corrupt_packets))
        self.logger.info("Valid_packets: %s", str(self.valid_packets))
        return()

    def read(self, num_packets=0, debug=False):
        self.logger.info("Entering the serial port read loop")
        if debug:
            self.logger.debug("control.read() num_packets=%d", num_packets)
            self.logger.debug("control.read() debug=%d", debug)
        i=0
        while (self.stop_now == False) and self.ser.is_open:
            try:
                with self.read_lock:
                    if not ((self.stop_now == False) and self.ser.is_open):
                        break # This check is to defeat possible race condition when button pressed to end serial port reads
                    data = self.ser.readline()
                self.parse_packet(data)
            except Exception as ex:
                self.stop_now = True
                self.logger.info("Problem found on this port.  Please click the \"Close Port\" button and try another port")
                self.close()
                return()
        self.logger.info("Exiting serial port read loop and closing the port")
        self.close()
        return()
                   
    def stop(self):
        self.stop_now = True
        self.logger.info("control.stop() Serial communications thread stopping")

    @staticmethod
    def get_port_names():
        L=list_ports_windows.iterate_comports()
        ports = []
        for x in L:
            ports.append(x.device)
        return(ports)

def object_read(object, num_packets=0, debug=False):
    #print("Entering object read")
    object.stop_now = False
    object.read(num_packets=num_packets, debug=debug)

