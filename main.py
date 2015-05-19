#========================================================================================================
# Weio Fridge
#========================================================================================================

from weioLib.weio import *
from things.input.environmental.ds18b20 import DS18B20

from multiprocessing import Lock

from time import sleep
import datetime
import urllib2
import json
import inspect

# Log level, the greater the more detail
# -1 always displayed
# 0 should be only fatal errors
# 1 transient errors
# 2 warnings
# 3 info
# 4 debug
maxLogLevel=2    

# Pin no for DHT22 sensor
pinDHT22 = 13  
pinDHT22Power=14

# emoncms properties
emonHostname = "ip or hostname"
emonBaseUrl = "baseurl/"
emonApiKey="emoncms api key"

# Interval between sensor reading
readInterval=60   # in seconds

# Locks to avoid concurrent access to data from requestData() and mainLoop()
readLock=0
requestLock=0

# Storing read values so that they can be used by requestData()
sharedVar['DATA']={}


#========================================================================================================
# WeIO specific setup
#========================================================================================================
def setup():
    attach.process(mainLoop)                    # Main program / loop
    attach.event("requestData", requestData)    # call back for initial data requests from Web clients

#========================================================================================================
# Formats debugging output with date/time & function
#========================================================================================================
def debugPrint(msg,logLevel=3,logFileName="/weioUser/sd/WeIOFridge.log"):
    
    if logLevel<=maxLogLevel:
        
        logFile = open(logFileName,"a")
        
        fullMsg  = time.strftime("%X-%d/%m/%Y")
        fullMsg += "|"
        fullMsg += inspect.stack()[1][3]
        fullMsg += "|"
        fullMsg += str(logLevel)
        fullMsg += "|"
        fullMsg += msg
        
        print fullMsg
        logFile.write(fullMsg + "\n");
        
        logFile.close

#========================================================================================================
# Called whenever a Web client is connecting to 
# update data on first launch (don't want to wait 
# until next sensor reading)
#========================================================================================================
def requestData(forceRead):

    debugPrint("Processing client request",-1)

    #----- Sending data to web client thru web socket (because it asked for it on first load)
    debugPrint("Pushing" + str(sharedVar['DATA']) + " to web clients")
    serverPush("updateData", json.dumps(sharedVar['DATA']))
    

#========================================================================================================
# Reads data from DHT22 and returns a dictionnary
# { temperature: value, humidity: value, retryX: 1 or -1, error: 1}
# 
# In case of reading error, we add a retryX value (X being the retry count) which is set to 
# - 1  if it is a checksum error
# - -1 if humidity = 0
# 
# If after readMaxRetry, still got not valid data, addinh a value error set to 1
#========================================================================================================
def dht22GetData(pin,readMaxRetry):

    dht22Data={}
    rawData={}
    retry=0
    checksum=-1

    # Because I had some trouble reading data from DHT22, I'll retry 3 times before giving up
    while checksum==-1 or ((checksum != rawData[4] or humidity==0) and retry < readMaxRetry):
        
        rawData = dhtRead(pin)

        checksum    = (rawData[0] + rawData[1] + rawData[2] + rawData[3]) & 0xFF
        humidity    = (rawData[0]*256+rawData[1])/10.0
        temperature = ((rawData[2] & 0x80)*256+rawData[3])/10.0

        debugPrint("============================================")
        debugPrint("DHT22 - Raw data -- : " + str(rawData))
        debugPrint("DHT22 - checkSum -- : " + str(checksum) + " | " + str(rawData[4]))
        debugPrint("DHT22 - Temperature : %.2f C"%temperature)
        debugPrint("DHT22 - Humidity -- : %.2f"%humidity + " %")

        if checksum!=rawData[4]:
            debugPrint("Cheksum error (" + str(retry) + " retry). ",2)
            debugPrint("DHT22 Raw data: " + str(rawData),2)
            dht22Data['retry'+str(retry)]=1
            delay(2500)   # Wait AT LEAST 2 secs between readings
        elif humidity==0:
            debugPrint("Humidity = 0 (" + str(retry) + " retry). ",2)
            debugPrint("DHT22 Raw data: " + str(rawData),2)
            dht22Data['retry'+str(retry)]=-1
            delay(2500)   # Wait AT LEAST 2 secs between readings
        else:
            dht22Data['temperature']=temperature
            dht22Data['humidity']=humidity
            debugPrint("Got values")
    
        retry += 1    

    if checksum!=rawData[4] or humidity==0:
        debugPrint("DHT22 checksum error",1)
        debugPrint("Data: " + str(dht22Data))
        dht22Data['error']=1

    return dht22Data
    
#========================================================================================================
# Reads data from all DS18B20 on bus and returns 
# a dictionnary with each sensor : 
# { <id>: value, ... }
#========================================================================================================
def ds18b20GetData(sensorObj,sensorList):
    
    ds12b20Data={}
    
    for sensorId in sensorList:
        ds12b20Data[sensorId]=sensorObj.getTemperature(sensorId)
        debugPrint(sensorId+" - %.2f"%ds12b20Data[sensorId],3)
        
    return ds12b20Data

#========================================================================================================
# Formats dict data to JSON and send to emoncms
#========================================================================================================
def sendJsonEmoncms(jsonString,hostname,baseUrl,apiKey):
    url  = "http://" + hostname + "/" + baseUrl + "input/post.json?node=40&apikey=" + apiKey 
    url += "&json=" + urllib2.quote(jsonString)
    
    response = urllib2.urlopen(url)
    if response.read() != "ok":
        debugPrint("Error while sending to emoncms",1)
    else:
        debugPrint("Sent to emoncms : " + jsonString,-1)

#========================================================================================================
# Main infinite loop
#========================================================================================================
def mainLoop():

    debugPrint("Starting...",-1)
    dhtRead(pinDHT22)         # because on first read, everything is 0...
    delay(1000)               # and wait for a second so sensor gets ready for next read

    # Init DS18B20 sensors and getting a list of all IDs on bus
    dsSensorsObj = DS18B20()
    dsSensorsList = dsSensorsObj.getSensors()
    
    # Prints out sensor details 
    #for dsSensorId in dsSensorsList:
    #    print(dsSensorsObj.sensorInfo(dsSensorId))


    #----------------------------------------------
    # Starting never ending loop
    while True:

        debugPrint("Starting loop...",-1)
    
        #----- Get data from DHT sensor
        dht22Data=dht22GetData(pinDHT22,3)
        
        #----- Get data from DS18B20 sensors
        ds18b20Data=ds18b20GetData(dsSensorsObj,dsSensorsList)
        
        #----- Sending data to emoncms and storing in shared vars (for use by requestData()
        data=dict(dht22Data.items()+ds18b20Data.items())
        sendJsonEmoncms(json.dumps(data),emonHostname,emonBaseUrl,emonApiKey)

        #----- Sharing the data
        sharedVar['DATA']=data

        #----- Sending data to web client thru web socket
        serverPush("updateData", json.dumps(data))
        
        #----- wait until next read
        sleep(readInterval)