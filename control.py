import serial
from serial.tools import list_ports_windows
import ipywidgets as widgets
import binascii
import threading
import time

class control():
    def __init__(self, logger, jump_table):
        self.logger = logger
        self.jump_table = jump_table
        self.spec1 = b'\x7d\x5e'
        self.spec2 = b'\x7e'
        self.spec3 = b'\x7d\x5d'
        self.spec4 = b'\x7d'
        self.terminator = b'\x7e\x7e'
        self.expected_lengths=[0, 34, 8, 12, 12, 12, 16, 46, 45, 18, 18, 24, 114, 66, 38 ]
        self.max_packet_id = len(self.expected_lengths)-1
        self.valid_packets = [0] * 15
        self.corrupt_packets = [0] * 15
        self.escapes_found = 0
        self.stop_now = False
        self.lock = threading.Lock()  
        self.read_lock = threading.Lock()
        self.ser = None

    def release_lock(self):
        if self.lock.locked():
            self.lock.release()
            
    def acquire_lock(self):
        self.lock.acquire()
            
    def parse_packet(self,i,packet,debug=False):
        pl=len(packet)
        #print("Entering parse_packet")
        if (pl<3):
            self.corrupt_packets[0]+=1
            if debug:
                self.logger.debug("control.read_packet() Discarded incomplete (too short) packet")
            return(0,pl)
        else:
            packet_type = packet[0]
            if (packet_type<=self.max_packet_id):
                b = packet[:-2]
                b = b.replace(self.spec1, self.spec2)
                b = b.replace(self.spec3, self.spec4)
                pl2=len(b)
                sub_found = (pl2!=pl-2)
                if sub_found:
                    self.escapes_found+=1
                ok = (pl2==self.expected_lengths[packet_type])
                if ok:
                    self.valid_packets[packet_type] += 1
                    # process packet here
                    try:
                        process_packet = self.jump_table[packet_type-1]
                        if (process_packet != None):
                            with self.lock:
                                #self.logger.debug("serial port lock acquired")
                                process_packet(b)
                                #self.logger.debug("serial port lock released")
                    except Exception as ex:
                        self.logger.error("ERROR: Packet handling exception found: %s", str(ex))
                else:
                    if debug:
                        self.logger.debug("Iteration %d : len=%d, ptype=%d : %s", \
                            i, pl2, packet_type, binascii.hexlify(bytearray(packet)))
                        self.logger.debug("Incorrect packet type %d length found! Expected %d, got %d", \
                            packet_type, self.expected_lengths[packet_type], pl2)
                    self.corrupt_packets[packet_type] += 1
                    packet_type = 0
                    pl2 = 0
                return(packet_type, pl2)
            else:
                self.corrupt_packets[0]+=1
                if debug:
                    self.logger.debug("control.read_packet() Discarded packet with packet ID > %d", self.max_packet_id)
                return(0,pl)

    def open(self, portName):
        self.logger.info("Starting process to open %s.", portName)
        self.ser = serial.Serial()
        self.ser.baudrate = 115200
        self.ser.port = portName
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
        self.logger.info("Corrupt packet summary: %s", str(self.corrupt_packets))
        self.logger.info("Valid_packet summary: %s", str(self.valid_packets))
        self.logger.info("Packets processed for escapes: %d", self.escapes_found)
        valid_packets = sum(self.valid_packets)
        corrupt_packets = sum(self.corrupt_packets)
        total = corrupt_packets + valid_packets
        if valid_packets>0:
            rate = 100*valid_packets/total
            self.logger.info("%d packets counted, %f%% successful", total, rate)
            rate = 100*self.escapes_found/valid_packets
            self.logger.info("{0:2.2f}% of valid packets included escape sequences".format(rate))
        else:
            self.logger.info("NO TRAFFIC RECORDED")
        return()

    def read(self, num_packets=0, debug=False):
        #print("read entered")
        if debug:
            self.logger.debug("control.read() num_packets=%d", num_packets)
            self.logger.debug("control.read() debug=%d", debug)
        if num_packets>0:
            for i in range(0,num_packets):
                data = self.ser.read_until(self.terminator)
                #print("serial port data type: ", type(data))
                self.parse_packet(i,data,debug)
        else:
            #print("about to enter read while loop")
            i=0
            while (self.stop_now == False) and self.ser.is_open:
                i+=1
                try:
                    #print("self.ser.read_until")
                    with self.read_lock:
                        if not ((self.stop_now == False) and self.ser.is_open):
                            break # This check is to defeat possible race condition when button pressed to end serial port reads
                        data = self.ser.read_until(self.terminator)
                    #print("serial port data type: ", type(data))
                except Exception as ex:
                    self.logger.error("ERROR: control.ser.read_until() exception: %s. self.terminator=%s", str(ex), str(self.terminator))
                try:
                    #print("self.parse_packet")
                    self.parse_packet(i,data,debug)
                except Exception as ex:
                    self.logger.error("ERROR: control.parse_packet() exception: %s", str(ex))
            self.logger.debug("Exiting serial port read loop")
        return()
            
#    def run(self, num_packets=0, debug=False):
#        self.logger.info("control.run() Starting Serial Port Thread")
#        self.object_read(num_packets=0, debug=False)
#        #p = threading.Thread(target=object_read, kwargs=dict(object=self, debug=debug, num_packets=num_packets))
#        #p.start()
       
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