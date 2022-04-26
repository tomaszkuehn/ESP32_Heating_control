import os
import time
import ntptime
import sys
import binascii
import socket
import select
import onewire
import ds18x20
#import threading
#from threading import Thread

import machine
import network

import esp
esp.osdebug(None)

import gc

blue_led = machine.Pin(2, machine.Pin.OUT)

ssid = 'NCC'
password = 'password'

station = network.WLAN(network.STA_IF)
station.active(False)
time.sleep(1)
station.active(True)
station.connect(ssid, password)
time.sleep(3)
if station.isconnected() == True:
    print('Connection successful')
    print(station.ifconfig())
    blue_led.value(1)

#opening socket for http
mysocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
mysocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
mysocket.bind(('', 80))
mysocket.listen(5)
mysocket.setblocking(0)


#configuration of 1-wire
dat = machine.Pin(22)
ds = ds18x20.DS18X20(onewire.OneWire(dat))
roms = ds.scan()
print('found devices:', roms)
ds.convert_temp()


#configuration parameters
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
speed_run    = 0
temp_avg = 0        #actual temp

   

def web_page_header():
    header = """<html><head> <title>ESP heating control</title> 
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,"> 
  <style>html{font-family: Helvetica; display:inline-block; margin: 0px auto; text-align: center;}
  h1{color: #8F3376; padding: 2vh;}p{font-size: 1.0rem;}.button{display: inline-block; background-color: #e7bd3b; border: none; 
  border-radius: 4px; color: white; padding: 16px 40px; text-decoration: none; font-size: 20px; margin: 2px; cursor: pointer;}
  .button2{background-color: #4286f4;}</style></head>"""
    return header

def main_page():
  gc.collect()
  memf = gc.mem_free()
  html = web_page_header()
  html = html + """<body> <h1>Heating system</h1>
  <style>
  body {
  font-family: "Fira Sans", sans-serif;
  font-size: 1rem;
  background-color: #192027;
  color: #506678;
  padding: 15px;
}

.wrapper {
  width: 100%;
  max-width: 1024px;
  margin: 0 auto;
}

.canvas {
  position: relative;
  width: 100%;
}

.note {
  width: 100%;
  float: left;
  text-align: center;
  padding: 15px 0;
}

a {
  text-decoration: none;
  color: #506678;
  border-bottom: 1px solid rgba(80, 102, 120, 0.25);
  transition: all 0.35s;
}
a:hover {
  color: #677f93;
  border-bottom: 1px solid rgba(149, 76, 233, 0.5);
}

@media (min-width: 960px) {
  body {
    padding: 25px;
  }

  .note {
    padding: 25px 0;
  }
}
  </style>

  <canvas id="canvas" width="300" height="300"></canvas>
  <p id="diag"></p>
  <script src='https://cdn.jsdelivr.net/npm/chart.js@2.9.3/dist/Chart.min.js'></script>
  <script>
  const colors = {
  purple: {
    default: "rgba(88, 191, 36, 1)",
    half: "rgba(88, 191, 36, 0.5)",
    quarter: "rgba(88, 191, 36, 0.25)",
    zero: "rgba(88, 191, 36, 0)"
  },
  indigo: {
    default: "rgba(80, 102, 120, 1)",
    quarter: "rgba(80, 102, 120, 0.25)"
  }
};

weight = """+str(temp_arr)+""";
heating = """+str(heat_arr[360:])+"""
const labels = [];
temp_max = -10000;
temp_min = 10000;

for(i = 0; i<360; i++) {
    if(weight[i] > temp_max) {temp_max = weight[i];}
    if((weight[i] != 0) && (weight[i] < temp_min)) {temp_min = weight[i];}
}

document.getElementById("diag").innerHTML = '';

temp_max = Math.round(temp_max/10.0);
temp_min = Math.round(temp_min/10.0);
temp_max = 10 * temp_max + 50;
temp_min = 10 * temp_min - 50;
heating_bar_range = temp_min + (temp_max - temp_min)/5;

for(i = 0; i<360; i++) {
    if(heating[i] > 0) {
        heating[i] = heating_bar_range;
    }
}

const ctx = document.getElementById("canvas").getContext("2d");
ctx.canvas.height = 100;

gradient = ctx.createLinearGradient(0, 25, 0, 300);
gradient.addColorStop(0, colors.purple.half);
gradient.addColorStop(0.35, colors.purple.quarter);
gradient.addColorStop(1, colors.purple.zero);

const options = {
  data: {
    labels: weight,
    datasets: [
      {
        type: "line",
        fill: true,
        backgroundColor: gradient,
        pointBackgroundColor: colors.purple.default,
        borderColor: colors.purple.default,
        data: weight,
        lineTension: 0.2,
        borderWidth: 1,
        pointRadius: 0,
        order: 2
      }, {
        type: "bar",
        data: heating,
        backgroundColor: 'rgba(235, 124, 33, 0.8)',
        order: 1
      }
    ]
  },
  options: {
    layout: {
      padding: 10
    },
    responsive: true,
    legend: {
      display: false
    },

    scales: {
      xAxes: [
        {
          gridLines: {
            display: true
          },
          ticks: {
            display: false,
            padding: 10,
            autoSkip: false,
            maxRotation: 15,
            minRotation: 15
          }
        }
      ],
      yAxes: [
        {
          scaleLabel: {
            display: false,
            labelString: "",
            padding: 10
          },
          gridLines: {
            display: true,
            color: colors.indigo.quarter
          },
          ticks: {
            beginAtZero: false,
            max: temp_max,
            min: temp_min,
            padding: 10
          }
        }
      ]
    }
  }
};

window.onload = function () {
  window.myLine = new Chart(ctx, options);
  Chart.defaults.global.defaultFontColor = colors.indigo.default;
  Chart.defaults.global.defaultFontFamily = "Fira Sans";
};
  </script>
  
  <p>TIME/MEM: """+str(time.localtime(time.time()))+""" / """ +str(memf)+ """</p>
  <p>HEATING ON: <strong>HEATING """+str(heating)+"""</strong></p>
  <p>ACTUAL TEMP: <strong>TEMP """+str(temp_avg)+"""</strong></p>
  <p><a href="/control.html"><button class="button">Control page</button></a></p>
  <p><a href="/config.html"><button class="button button2">Config page</button></a></p>
  </body></html>"""
  return html

def control_page():
  html = web_page_header()
  html = html + """<body> <h1>Heating control</h1>
  <p>Manual_run: 
  <a href="/control.html/?manual_run=1"><button class="button button2">Manual run ON</button></a>
  <strong> Status"""+str(manual_run)+"""</strong></p>
  <p><a href="/"><button class="button button">Go to main page</button></a></p></body></html>"""
  return html 

def config_page():
  html = web_page_header()
  html = html + """<body> <h1>Heating config</h1>
  <p>Speed run:<br>
  <a href="/config.html/?speed_run=1"><button class="button button2">Speed run ON</button></a><br>
  <a href="/config.html/?speed_run=0"><button class="button button2">Speed run OFF</button></a><br>
  <strong> Status"""+str(speed_run)+"""</strong></p>
  <p><a href="/"><button class="button button2">Go to main page</button></a></p></body></html>"""
  return html 

def time_sync():
    try:
        print("Syncing time...")
        ntptime.settime()
        print("Time adjusted: %s" %str(time.localtime()))
    except:
        print("NTP fail")
        

def read_temp(num, out_queue):
    try:
        for rom in roms:
            tt = ds.read_temp(rom)
        ds.convert_temp()
    except:
        tt = temp_avg/100.0
    out_queue.append(tt)
   

    
def heating_switch(heating):
#now control the central heating stove
    """
    #control over wireless
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
    """


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
for i in range (0,360):
    temp_arr.append(0)
heat_arr     = []
for i in range (0,720):
    heat_arr.append(0)

temp_avg_arr = []
for i in range (0,12):
    temp_avg_arr.append(-10000)

hour_arr = []
for i in range (0,24):
    hour_arr.append([1,0])


def read_hour_arr():
#    f = open("/user/hour.txt","r")
#    f1 = f.readlines()
#    for x in f1:
#        if x[0] != '#':
    for x in range(0,24):
        uon,uoff = 1800,1900
        hour_arr[x]=[int(uon), int(uoff)] 
    
    print(hour_arr[7][0]," ",hour_arr[7][1]+1)
    
    
read_hour_arr()
print(hour_arr)
time.sleep(1)

time_sync() 
my_queue = [] #Queue.Queue()
seconds = round(time.time())
read_hour = 0


# MAIN LOOP #

while True:
    systime = time.localtime(time.time())
    print(systime)
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
        if (temp_avg_arr[0] > -10000):
            temp_avg = temp_avg/12
        else:
            temp_avg = temp_avg_arr[11]
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

#check conditions to decide switch heating on                                                        
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
        while True:
            #handle http
            ready = select.select([mysocket], [], [], 1)
            if ready[0]:
                conn, addr = mysocket.accept()
                print('Got a connection')
                try:
                    conn.settimeout(1)
                    try:
                        request=conn.recv(1024).strip()
                    except socket.error:
                        conn.send('0,0:ERROR:UNKNOWN-ERROR\r\n')
                        break
                    #request = conn.recv(1024)
                    request = str(request)
                    print('Content = %s' % request)

                    request = request.split('HTTP')
                    request = request[0]

                    #action control
                    if request.find('/?manual_run') > 0:
                        request_p = request.split('=')
                        fchar = request_p[1][0]
                        if fchar == '1':
                            manual_run = 1
                        if fchar == '0':
                            manual_run = 0
                    if request.find('/?speed_run') > 0:
                        request_p = request.split('=')
                        fchar = request_p[1][0]
                        if fchar == '1':
                            speed_run = 1
                        if fchar == '0':
                            speed_run = 0
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
                gc.collect()
                        
            blue_led.value(1)            
            time.sleep(0.01)
            blue_led.value(0)
            time.sleep(0.08)
            if station.isconnected() == True:
                blue_led.value(1)            
                time.sleep(0.01)
                blue_led.value(0)
            # replace the condition below for accelerated testing
            if speed_run == 0:
                if (round(time.time()) - seconds >= 10):
                    break
            else:
                break
        seconds = round(time.time())
        print (seconds)
        print ("---")
        tick = tick + 1



