# -*- coding: utf-8 -*- 
import os
import sys
import imp
import thread
import threading
import time
import requests
import json
import wiringpi2 as wiringpi

api_url='http://api.yeelink.net/v1.0'
api_key=your_api_key
api_headers={'U-ApiKey':api_key,'content-type': 'application/json'}

sensors = []
datas = []
lcdFD = None
threadLock = threading.Lock()

def logout(str):
    print "[%s]%s"%(time.strftime("%Y-%m-%d %H:%M:%S"), str)
    sys.stdout.flush()


def upload_data_to_yeelink(device, sensor, data):
    url=r'%s/device/%s/sensor/%s/datapoints' % (api_url,device,sensor)
    strftime=time.strftime("%Y-%m-%dT%H:%M:%S")
    data={"timestamp":strftime , "value": data}
    res=requests.post(url,headers=api_headers,data=json.dumps(data),timeout=30)
    if res.status_code != 200:
        return (False, res.status_code)
    else:
        return (True, None)

def load_sensors():
    sensor_path = os.path.abspath("Sensor") + "/"
    sensor_files = os.listdir(sensor_path)

    for filename in sensor_files:
        if filename[-3:] != ".py":
            continue
        try:
            sensor_name = filename[:-3]
            module = imp.load_source(sensor_name, sensor_path + filename)
            class_obj = getattr(module, sensor_name)
            instance = class_obj()
            sensors.append(instance)
        except Exception, e:
            logout("Sensor %s load error:%s"%(filename, e)) 

def run():
    while True:
        global datas
        lst = []
        for sensor in sensors:
            try:                
                logout("Sensor %s fetching data..."%sensor.__class__.__name__) 
                result = sensor.GetData()
                logout("Fetched:%s"%str(result))
                for data in result:
                    lst.append(data)
                    res, err = upload_data_to_yeelink(data["device"], data["sensor"], data["data"])
                    logout("SensorID: %s Uploaed: %s"%(str(data["sensor"]), "Success" if res else "Failed: %s"%err)) 
            except Exception, e:
                logout(str(e))
        threadLock.acquire()
        datas = lst
        threadLock.release()
        logout( "Sleep")
        time.sleep(1*60)

def showSensors():
    global lcdFD
    global datas

    while True:
        ret = False
        threadLock.acquire()
        lst = datas
        threadLock.release()
        for x in xrange(0, len(lst), 2):
            wiringpi.lcdClear(lcdFD)
            data1 = lst[x]
            wiringpi.lcdPosition(lcdFD, 0,0)
            wiringpi.lcdPrintf(lcdFD,"%s:%s%s"%(data1["name"],data1["data"],data1["symbol"]))
    
            if x+1 < len(lst):
                data2 = lst[x+1]            
                wiringpi.lcdPosition(lcdFD, 0,1)
                wiringpi.lcdPrintf(lcdFD,"%s:%s%s"%(data2["name"],data2["data"],data2["symbol"]))
            ret = True
            time.sleep(5)
        if ret != True:
            time.sleep(5)
            

def initLCD():
    global lcdFD

    RS = 3
    EN = 14
    D0 = 4
    D1 = 12
    D2 = 13
    D3 = 6

    wiringpi.wiringPiSetup()
    lcdFD = wiringpi.lcdInit(2, 16, 4, RS, EN, D0, D1, D2, D3, 0, 0, 0, 0);


if __name__ == '__main__':    
    load_sensors()
    initLCD()

    thread.start_new_thread(run, ())
    showSensors()
