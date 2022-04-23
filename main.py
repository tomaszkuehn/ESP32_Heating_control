import os
import time
import ntptime
import sys
#import serial
import binascii
import socket
import select
import onewire
import ds18x20
#import threading
#from threading import Thread
#import Queue

import machine
import network

import esp
esp.osdebug(None)

import gc
gc.collect()

ssid = 'NCC'
password = 'password'

station = network.WLAN(network.STA_IF)

station.active(True)
station.connect(ssid, password)
time.sleep(2)
if station.isconnected() == True:
    print('Connection successful')
    print(station.ifconfig())

blue_led = machine.Pin(2, machine.Pin.OUT)
blue_led.value(1)

#opening socket for http
mysocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
mysocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
mysocket.bind(('', 80))
mysocket.listen(5)
mysocket.setblocking(0)
#mysocket.settimeout(0.5)

#configuration of 1-wire
dat = machine.Pin(22)
ds = ds18x20.DS18X20(onewire.OneWire(dat))
roms = ds.scan()
print('found devices:', roms)
ds.convert_temp()
"""
time.sleep(1)
for rom in roms:
    tt = ds.read_temp(rom)
    print(tt)
time.sleep(5)
"""
#os.system('modprobe w1-gpio')
#os.system('modprobe w1-therm')

#configuration parameters
temp_sensor1 = 1 #'/sys/bus/w1/devices/28-0000031bd290/w1_slave'
temp_sensor = 0 #'/sys/bus/w1/devices/28-0000031bc16f/w1_slave'
periodic_run_interval = 240 # in minutes
booster_delay = 48 #in ticks, set 0 to disable

#blobal variables
tick = 0            # 1tick = 10sec
temp_on  = 2000
temp_off = 2030
heating = 0
temp_1w = 0
periodic_run = 0
manual_run   = 0
manual_pause = 0
manual_stop  = 0 
temp_shift = 0
booster      = 0
temp_avg = 0        #actual temp

def web_page_header():
    header = """<html><head> <title>ESP heating control</title> <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,"> <style>html{font-family: Helvetica; display:inline-block; margin: 0px auto; text-align: center;}
  h1{color: #0F3376; padding: 2vh;}p{font-size: 1.5rem;}.button{display: inline-block; background-color: #e7bd3b; border: none; 
  border-radius: 4px; color: white; padding: 16px 40px; text-decoration: none; font-size: 30px; margin: 2px; cursor: pointer;}
  .button2{background-color: #4286f4;}</style></head>"""
    return header

def main_page():
  gc.collect()
  memf = gc.mem_free()
  html = web_page_header()
  html = html + """<body> <h1>Heating system</h1>
  <p>TIME/MEM: """+str(round(time.time()))+""" / """ +str(memf)+ """</p>
  <p>HEATING ON: <strong>HEATING """+str(heating)+"""</strong></p>
  <p>ACTUAL TEMP: <strong>TEMP """+str(temp_avg)+"""</strong></p>
  <p><a href="/control.html"><button class="button">Control page</button></a></p>
  <p><a href="/config.html"><button class="button button2">Config page</button></a></p>
  </body></html>"""
  return html

def control_page():
  html = web_page_header()
  html = html + """<body> <h1>Heating control</h1>
  <p><a href="/"><button class="button button2">Go to main page</button></a></p></body></html>"""
  return html 

def config_page():
  html = web_page_header()
  html = html + """<body> <h1>Heating config</h1>
  <p><a href="/"><button class="button button2">Go to main page</button></a></p></body></html>"""
  return html 

def time_sync():
    try:
        print("Syncing time...")
        ntptime.settime()
        print("Time adjusted: %s" %str(time.localtime()))
    except:
        print("NTP fail")
        
"""
#configure serial port to send messages
ser = serial.Serial (
    port='/dev/ttyAMA0',
    baudrate = 9600,
    parity=serial.PARITY_EVEN,
    stopbits = serial.STOPBITS_TWO,
    bytesize=serial.EIGHTBITS,
    timeout=1
)
"""

"""
def temp_raw():
    try:
        f = open(temp_sensor, 'r')
    except IOError:
        time.sleep(0.1)
        lines = "   :"
        return lines
    lines = f.readlines()
    f.close()
    return lines
"""

def read_temp(num, out_queue):
    try:
        for rom in roms:
            tt = ds.read_temp(rom)
        ds.convert_temp()
    except:
        tt = temp_avg/100.0
    out_queue.append(tt)
"""
    lines = temp_raw()
    timeout = 0
    while ((timeout < 10) and (lines[0].strip()[-3:] != 'YES')):
        timeout = timeout + 1
        time.sleep(0.2)
        lines = temp_raw()

    temp_output = lines[1].find('t=')

    if temp_output != -1:
        temp_string = lines[1].strip()[temp_output+2:]
        temp_c = float(temp_string) / 1000.0
#        temp_f = temp_c * 9.0 / 5.0 + 32.0
        #return temp_c
        print "Read temp TC:%f\n" % temp_c
        out_queue.put(temp_c)
"""    

    
def heating_switch(heating):
#now send over serial
   packet = bytearray()
   if (heating == 1):
      packet.append(0x01)
      packet.append(0x05)
      packet.append(0x00)
      packet.append(0x00)
      packet.append(0xFF)
      packet.append(0x00)
      packet.append(0x8C)
      packet.append(0x3A)
   if (heating == 0):
      packet.append(0x01)
      packet.append(0x05)
      packet.append(0x00)
      packet.append(0x01)
      packet.append(0xFF)
      packet.append(0x00)
      packet.append(0xDD)
      packet.append(0xFA)

   print(packet) #binascii.hexlify(packet)
#comment the line below to avoid any messages sent
#   ser.write(packet)


#heating_switch(0)

#exit()

def process_msg(msg):
    global manual_run
    global manual_stop
    global manual_pause
    global temp_shift
    m = msg.split()
    if (m[0] == '2'):
        if (m[1] == '1'):
            manual_run = 10
        if (m[1] == '0'):
            manual_pause = 10
    if (m[0] == '1'):
        if (m[1] == '1'):
            manual_stop = 0
        if (m[1] == '0'):
            manual_stop = 1
    if (m[0] == '3'):
        if (m[1] == '1'):
            temp_shift = temp_shift + 50
        if (m[1] == '0'):
            temp_shift = temp_shift - 50
        if (m[1] == '2'):
            temp_shift = 0
    if (temp_shift > 200):
        temp_shift = 200
    if (temp_shift < -200):
        temp_shift = -200


temp_arr     = []
for i in range (0,720):
    temp_arr.append(0)
heat_arr     = []
for i in range (0,720):
    heat_arr.append(0)

temp_avg_arr = []
for i in range (0,12):
    temp_avg_arr.append(0)

hour_arr = []
for i in range (0,24):
    hour_arr.append([1,0])


def read_hour_arr():
#    f = open("/user/hour.txt","r")
#    f1 = f.readlines()
#    for x in f1:
#        if x[0] != '#':
    for x in range(0,24):
        uon,uoff = 1500,1600
        hour_arr[x]=[int(uon), int(uoff)] 
    
    print(hour_arr[7][0]," ",hour_arr[7][1]+1)
    
    
read_hour_arr()
print(hour_arr)
time.sleep(1)

time_sync() 
my_queue = [] #Queue.Queue()
seconds = round(time.time())
read_hour = 0

"""
#define system pipe to receive commands
pipe_path = "/tmp/heating_pipe"
if not os.path.exists(pipe_path):
    os.mkfifo(pipe_path)
os.chmod(pipe_path, 0o777)    
pipe_fd = os.open(pipe_path, os.O_RDONLY | os.O_NONBLOCK)
pipe = os.fdopen(pipe_fd)
"""

# MAIN LOOP #

while True:
    systime = time.localtime(time.time())
    #print (systime.tm_hour,':',systime.tm_min, " ", tick, " While loop...")
    print ("Manual RUN:", manual_run, " Manual STOP:", manual_stop, " Periodic RUN:", periodic_run, " PAUSE:", manual_pause, " Booster:", booster)
    if ((systime[4]%5 == 0) and (read_hour == 0)):
        read_hour_arr()
        read_hour = 1
    if (systime[4]%5 != 0):
        read_hour = 0
    temp_on  = hour_arr[systime[3]][0] + temp_shift
    temp_off = hour_arr[systime[3]][1] + temp_shift
    print ("Temp range ", temp_on,"-",temp_off)
#read 1-wire    
    read_temp(1, my_queue)
#read until queue is empty
    tt = my_queue.pop(0)
    while tt:
#current temp in tt
        if (tt < -1000):
            tt = temp_avg_arr[0]
        if (tt > 4000):
            tt = temp_avg_arr[0]
        print(tt)
#update avg temp array
        temp_avg_arr.pop(0)
        temp_avg_arr.append(tt)

        print(temp_avg_arr)
        tt = 0
#calculate average temperature over last minute
        temp_avg = 0
        for i in range (0, 12):
            temp_avg = temp_avg + temp_avg_arr[i]
        temp_avg = temp_avg/12
        temp_avg = temp_avg*100
        temp_avg = round(temp_avg)
        print("(%d): AVG: %d " % (round(time.time()),temp_avg))

#drive heating based on temperature reading
        if temp_avg <= temp_on:
            heating = 1
    
        if temp_avg >= temp_off:
            if heating == 1 and booster == 0:
                booster =  booster_delay
            heating = 0

#check heating rule to avoid continuous usage
        hh = 0
        if(heating - heat_arr[719] == 1): #heating switched on
            for i in range (705,720):
                hh = hh + heat_arr[i]
                if ( hh > 0 ):
                    heating = 0
                    print("HH:%d Heating postponed - over usage\n" % hh)
        if( heat_arr[719] == 1):	#heating was on
            for i in range (698,720):
                hh = hh + heat_arr[i]
                if ( hh > 19 ):
                    heating = 0
                    print("HH:%d Heating stopped - over usage\n" % hh)

#run heating periodically
        hh = 0
        if(heating == 0):
            ppi = round(720 - periodic_run_interval / 2)
            for i in range (ppi,720):
                hh = hh + heat_arr[i]
            if ( hh == 0 ):
                periodic_run = 1
        hh = 0
        if ( periodic_run == 1 ):
            for i in range (714,720):
                hh = hh + heat_arr[i]
            if ( hh >= 4 ):
                periodic_run = 0

#check booster
        if booster > 0:
            booster = booster - 1
        if booster == 2:
            heating = 1
        if booster == 1:
            heating = 0
                            
        heating = heating or periodic_run or manual_run
        if(manual_pause or manual_stop):
            heating = 0
        if(heating > 1):
            heating = 1
        print("Heating switch:%d " % heating)
        heating_switch(heating)

#every two minutes    
        if tick%12 == 0: #shift data in array
            temp_arr.pop(0)
            temp_arr.append(temp_avg)
            heat_arr.pop(0)
            if((heating!=0) and (heating!=1)):
                heating = 0
            heat_arr.append(heating)
            
#every minute
        if tick%6 == 0:
        #manual override
            if(manual_run > 0):
                manual_run = manual_run - 1 
            if(manual_pause > 0):
                manual_pause = manual_pause -1               

#create www
        """
        ff = open("/var/www/html/temp.json","w+")
        ff.write("{\n")
        ff.write("\"TEMP_ARR\":[0")
        for item in temp_arr:
            ff.write(",%d" % item)
        ff.write("],")
        ff.write("\"HEAT_ARR\":[0")
        for item in heat_arr:
            ff.write(",%d" % item)
        ff.write("],")
        ff.write("\"LAST_AVG\":%d," % temp_avg)
        ff.write("\"HEAT_ON\":%d," % temp_on)
        ff.write("\"HEAT_OFF\":%d," % temp_off)
        ff.write("\"TEMP_SHIFT\":%d" % temp_shift)
        ff.write("\n}\n")
        ff.write
        ff.close
    
        print "\n"
        sys.stdout.flush()
        """            
        while True:
            #handle http
            ready = select.select([mysocket], [], [], 1)
            if ready[0]:
                #data = mysocket.recv(4096)
                conn, addr = mysocket.accept()
                print('Got a connection')
                try:
                    request = conn.recv(1024)
                    request = str(request)
                    print('Content = %s' % request)
                    """
                    led_on = request.find('/?led=on')
                    led_off = request.find('/?led=off')
                    if led_on == 6:
                        print('LED ON')
                        #led.value(1)
                    if led_off == 6:
                        print('LED OFF')
                        #led.value(0)
                    """
                    request = request.split('HTTP')
                    request = request[0]

                    response = ""
                    if request.find('config') > 0:
                        response = config_page()
                    if request.find('control') > 0:
                        response = control_page()    
                    if response == "":
                        response = main_page()    
                    conn.send('HTTP/1.1 200 OK\n')
                    conn.send('Content-Type: text/html\n')
                    conn.send('Connection: close\n\n')
                    conn.sendall(response)
                    conn.close()
                except:                    
                    conn.close()
            # check command over pipe
            # to send command use: echo "command" > /tmp/heating_pipe
            """
            message = pipe.read()
            if message:
                print("Received command(s): '%s'" % message)
                msgs = message.split('#')
                for msg in msgs:
                    if msg:
                        process_msg(msg)
            """            
            blue_led.value(1)            
            time.sleep(0.01)
            blue_led.value(0)
            time.sleep(0.08)
            if station.isconnected() == True:
                blue_led.value(1)            
                time.sleep(0.01)
                blue_led.value(0)
            # replace the condition below for accelerated testing
            #if True:
            if (round(time.time()) - seconds >= 10):
                break
        seconds = round(time.time())
        print (seconds)
        print ("---")
        tick = tick + 1



