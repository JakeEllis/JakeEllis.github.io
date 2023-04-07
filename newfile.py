from google.cloud import storage
import glob
import os
import os.path
from datetime import datetime
import time
from pijuice import PiJuice # Import pijuice module
from moviepy.editor import *

gcpServiceAccountJsonFile = '/home/pi/Desktop/parking_lot_timelapse_scripts/GCS/date-night-qa-4328ecf6921e.json'
gcpCloudStorageBucket = 'date-night-qa.appspot.com'
videoStorageBucketFolderName = 'parking_lot_timelapse/videos/'
logStorageBucketFolderName = 'parking_lot_timelapse/logs/'
rootScriptFolder = "/home/pi/Desktop/parking_lot_timelapse_scripts"
piLogFileLocation = "/home/pi/Desktop/parking_lot_timelapse_scripts/log_files/"
logFileName = "parking_lot_timelapse_ftp_log"
logBlobName = logStorageBucketFolderName+logFileName
timelapseVideos = []
logFiles = []
maxSdCardFileNum = 10 #maximum number of files we want to store on the camera's SD card at any time
pijuice = PiJuice(1,0x14)
chargeLevel = ""
dateTimeNow = datetime.now()
dateTimeNow_string = dateTimeNow.strftime("%m/%d/%Y %H:%M:%S")
yearMonthDay = dateTimeNow.strftime("%Y")+dateTimeNow.strftime("%m")+dateTimeNow.strftime("%d")
hourMinSec = dateTimeNow.strftime("%H")+dateTimeNow.strftime("%M")+dateTimeNow.strftime("%S")
year = dateTimeNow.strftime("%Y")

#variables for dynamically creating the timelapse folder path. The folder path may change if the SD card is switched out
cameraTimelapseFolderPath = ''

def FindCameraTimelapseFolderPath():
    
    logging("FindCameraTimelapseFolderPath", "Started")
    
    cameraTimelapseFolderPathBase = '/media/pi/'
    folderPath = ''
    for subdir, dirs, files in os.walk(cameraTimelapseFolderPathBase):
        for file in files:
            logging("FindCameraTimelapseFolderPath subdir: ", subdir)
            logging("FindCameraTimelapseFolderPath file: ", file)
            if subdir != '' and 'DCIM' in subdir and ".AVI" in file:
                folderPath = subdir
    if folderPath != '':
        finalPath = folderPath+"/"
    else:
        finalPath = 'NULL'
        
    print("FindCameraTimelapseFolderPath", "cameraTimelapseFolderPath: ",finalPath)
    logging("FindCameraTimelapseFolderPath finalPath: ", finalPath)
    logging("FindCameraTimelapseFolderPath", "Finished")
    return finalPath


def logging(processName, processStatus):

    pathToLoggingFile = "/home/pi/Desktop/parking_lot_timelapse_scripts/detailed_log_files/"+"logging.txt"
    loggingFile = open(pathToLoggingFile,"a") # a gives us access to append to the file
   
    loggingFile.write(processName + " " + processStatus + "\n") 
    loggingFile.close()

    return 

def DisableUsbPorts():
    
    logging("DisableUsbPorts", "Started")

    #----- Ejecting USB Device
    os.system("sudo umount /dev/sda1 /media/pi")


    #using uhubctl to disable power to the usb ports
    os.system("sudo uhubctl -l 2 -a off") # location is hub 2 action off
    os.system("sudo uhubctl -l 2 -r 10") # location is hub 2 retry to turn off 10 times
    os.system("sudo uhubctl -l 1 -a off") # location is hub 1 action off
    os.system("sudo uhubctl -l 1 -r 10") # location is hub 1 retry to turn off 10 times
    
    logging("DisableUsbPorts", "Finished")
    
    return

def EnableUsbPorts():
    
    logging("EnableUsbPorts", "Started")
    
    os.system("sudo uhubctl -l 1 -a on") # location is hub 1 turn on
    os.system("sudo uhubctl -l 2 -a on") # location is hub 2 turn on
    #time.sleep(5)
    #os.system("sudo udisksctl mount -b /dev/sda1 uid=pi,gid=pi")
    time.sleep(2)
    os.system("sudo udisksctl mount -b /dev/sda1")
    time.sleep(5)
    os.system("sudo mount /dev/sda1 /media/pi -o uid=pi,gid=pi")    

    #waiting 2 seconds to give the Pi time to find the camera
    time.sleep(5)
    
    logging("EnableUsbPorts", "Finished")
    
    return

def UploadTimelapseToGcpBucket(path_to_file):
    
    logging("UploadTimelapseToGcpBucket", "Started")

    # Explicitly use service account credentials by specifying the private key file.
    storage_client = storage.Client.from_service_account_json(gcpServiceAccountJsonFile)
    
    bucket = storage_client.get_bucket(gcpCloudStorageBucket)
    blob = bucket.blob(videoStorageBucketFolderName+latestTimelapseFileName)
    blob.upload_from_filename(path_to_file)
    
    logging("UploadTimelapseToGcpBucket", "Finished")
    
    #returns a public url
    return blob.public_url

def UploadLogfileToGcpBucket():
    
    os.chdir(piLogFileLocation)
    logging("UploadLogfileToGcpBucket: "+ dateTimeNow_string, "Started")
    
    pathToLogFile = piLogFileLocation+logFileName+"_"+yearMonthDay+".txt"
    internetConnection = CheckInternetSource()
    batteryStatus = CheckBatteryStatus()
    
    logFile = open(pathToLogFile,"a") # a gives us access to append to the file
    logFile.write(latestTimelapseFileName+" was loaded on "+dateTimeNow_string+" using "+internetConnection+" with "+batteryStatus+"\n")
    logFile.close()
   
    # Explicitly use service account credentials by specifying the private key file.
    storage_client = storage.Client.from_service_account_json(gcpServiceAccountJsonFile)

    #bucket = storage_client.get_bucket(gcpCloudStorageBucket+"_"+yearMonthDay)
    bucket = storage_client.get_bucket(gcpCloudStorageBucket)
    blob = bucket.blob(logStorageBucketFolderName+logFileName+"_"+yearMonthDay+".txt")
    blob.upload_from_filename(pathToLogFile)
    
    # disabling the usb ports so that the camera is no longer in USB mode and will continue to take photos
    DisableUsbPorts()
    
    logging("UploadLogfileToGcpBucket", "Finished")
    
    #returns a public url
    return blob.public_url

def ConvertToMP4(fileNameToChange):
    
    logging("ConvertToMP4", "Started")
    
    os.chdir(cameraTimelapseFolderPath) # make sure we are in the correct directory
    videoNameBase = fileNameToChange[:8]
    video = VideoFileClip(fileNameToChange)
    newName=videoNameBase+".MP4"
    video.write_videofile(newName)
    logging("ConvertToMP4. fileNameToChange:" + fileNameToChange + ". New file name: " + videoNameBase+".MP4", "Started")
    os.remove(fileNameToChange) # removing the AVI file
    logging("ConvertToMP4", fileNameToChange+" was deleted")



#    try:
#        video = VideoFileClip(fileNameToChange)
#        newName=videoNameBase+".MP4"
#        video.write_videofile(newName)
#        logging("ConvertToMP4. fileNameToChange:" + fileNameToChange + ". New file name: " + videoNameBase+".MP4", "Started")
#    except Exception as e: 
#        logging("ConvertToMP4", "errored")
#                latestTimelapseFileName = "DELETING FILES FROM CAMERA FAILED"        
#                logging("Calling UploadLogfileToGcpBucket as expected", "Started")
#                ######### calling the upload_to_bucket function to send a log file to GCP storage #########
#                UploadLogfileToGcpBucket()
#                turnOffPi()








#        timelapseVideos = glob.glob(cameraTimelapseFolderPath+"*")
#        timelapseVideos.sort(reverse=False)
#        for x in range(len(timelapseVideos)):
#            try:
#                if os.path.basename(timelapseVideos[0+x]):
#                    fileNameToDelete = os.path.basename(timelapseVideos[0+x])
#                    #if FileNameToDelete = maxfilefrom today:
#                        #continue #this skips on the to the next
#                    #print("Deleting file #", (0+x), " ", fileNameToDelete)
#                    logging("CleanupFilesOnCamera", "Deleting file #: "+fileNameToDelete)
#                    os.remove(fileNameToDelete)
#
#            except: 
#                latestTimelapseFileName = "DELETING FILES FROM CAMERA FAILED"        
#                logging("Calling UploadLogfileToGcpBucket as expected", "Started")
#                ######### calling the upload_to_bucket function to send a log file to GCP storage #########
#                UploadLogfileToGcpBucket()
#                turnOffPi()
#            finally:
#                print("")
#        #Manually writing the UploadLogfileToGcpBucket code because global variables were causing it not to work properly
#        os.chdir(piLogFileLocation)      
#        pathToLogFile = piLogFileLocation+logFileName+"_"+yearMonthDay+".txt"
#        internetConnection = CheckInternetSource()
#        batteryStatus = CheckBatteryStatus()
#        
#        logFile = open(pathToLogFile,"a") # a gives us access to append to the file
#        logFile.write("ERROR - CONVERTING TO MP4 FAILED was loaded on "+dateTimeNow_string+" using "+internetConnection+" with "+batteryStatus+"\n")
#        logFile.close()
#       
#        # Explicitly use service account credentials by specifying the private key file.
#        storage_client = storage.Client.from_service_account_json(gcpServiceAccountJsonFile)
#        bucket = storage_client.get_bucket(gcpCloudStorageBucket)
#        blob = bucket.blob(logStorageBucketFolderName+logFileName+"_"+yearMonthDay+".txt")
#        blob.upload_from_filename(pathToLogFile)
#    
#        turnOffPi()
#    finally:
#        os.remove(fileNameToChange) # removing the AVI file
#        logging("ConvertToMP4", fileNameToChange+" was deleted")
#
#        logging("ConvertToMP4", "Finished")

    return 

def AddMinSecToFileNameOnCamera(fileNameToChange):
    
    logging("AddMinSecToFileNameOnCamera", "Started")
    #rename file
    os.chdir(cameraTimelapseFolderPath) # make sure we are in the current directory
    fileNameBase = fileNameToChange[:4]
    newFileName = year+fileNameBase+"_"+hourMinSec+".MP4"
    os.rename(fileNameToChange,newFileName) # change the file name
    logging("AddMinSecToFileNameOnCamera. fileNameToChange:" + fileNameToChange + ". New file name: " + newFileName, "Started")
    testing = glob.glob(cameraTimelapseFolderPath+"*")  
    logging("AddMinSecToFileNameOnCamera", "Finished")
    
    return newFileName

def CleanupFilesOnCamera():
    
    logging("CleanupFilesOnCamera", "Started")
    
    timelapseVideos = glob.glob(cameraTimelapseFolderPath+"*")  
    timelapseVideos.sort(reverse=False)

    for x in range(len(timelapseVideos)):
        try:
            os.chdir(cameraTimelapseFolderPath) # make sure we are in the current directory
            if os.path.basename(timelapseVideos[0+x]):
                fileNameToDelete = os.path.basename(timelapseVideos[0+x])
                #if FileNameToDelete = maxfilefrom today:
                    #continue #this skips on the to the next
                #print("Deleting file #", (0+x), " ", fileNameToDelete)
                logging("CleanupFilesOnCamera", "Deleting file #: "+fileNameToDelete)
                os.remove(fileNameToDelete)
            else:
                logging("CleanupFilesOnCamera", "Finished")
                break

        except: 
            latestTimelapseFileName = "DELETING FILES FROM CAMERA FAILED"

            timelapseVideos = glob.glob(cameraTimelapseFolderPath+"*")  
            timelapseVideos.sort(reverse=False)
    
            logging("Calling UploadLogfileToGcpBucket as expected", "Started")
            ######### calling the upload_to_bucket function to send a log file to GCP storage #########
            UploadLogfileToGcpBucket()
            turnOffPi()

        finally:
            print("") 
    
    logging("CleanupFilesOnCamera", "Finished")

    return
        

def CleanupLogFilesOnPi(numOfFilesToDelete):
    logging("CleanupLogFilesOnPi", "Started")
    
#    for x in range(numOfFilesToDelete):
    for x in range(numOfFilesToDelete):        
        os.chdir(piLogFileLocation) # make sure we are in the current directory
        logFileNameToDelete = os.path.basename(logFiles[0+x])
        #if FileNameToDelete = maxfilefrom today:
            #continue #this skips on the to the next
        print("Deleting log file #", (0+x), " ", logFileNameToDelete)
        logging("CleanupLogFilesOnPi", "Deleting log file "+logFileNameToDelete)
        os.remove(logFileNameToDelete)
        
    logging("CleanupLogFilesOnPi", "Finished")
    
    return

def CheckBatteryStatus():
    
    logging("CheckBatteryStatus", "Started")

    global chargeLevel 
    
    batteryStatus = pijuice.status.GetStatus() # Read PiJuice status.
    batteryData = batteryStatus['data']
    chargeLevel = pijuice.status.GetChargeLevel()
    batteryTemperature = pijuice.status.GetBatteryTemperature() #The returned value is the temperature in Celsius.
    batteryTemperatureCelsius = batteryTemperature['data']
    batteryTemperatureFahrenheit = (batteryTemperatureCelsius * 1.8) + 32
    
    logText = "Battery status:"+str(batteryData['battery'])+"; Battery percentage:" +str(chargeLevel['data'])+ "%; Battery Temperature:"+str(batteryTemperatureFahrenheit) 
    logging("CheckBatteryStatus", "Finished")
    return logText

def CheckInternetSource():
    logging("CheckInternetSource", "Started")
    
    connectionStatus = ""
    dataConnection = os.system("ping -I usb0 www.google.com -c 1")
    wifiConnection = os.system("ping -I wlan0 www.google.com -c 1")
    if dataConnection == 0 and wifiConnection != 0:
        connectionStatus = "4G/LTE connection"
    elif wifiConnection == 0 and dataConnection != 0:
        connectionStatus = "WIFI connection"
    elif wifiConnection == 0 and dataConnection == 0:
        connectionStatus = "WIFI and 4G/LTE connection"
    else:
        connectionStatus = "No internet connection"
        
    logging("CheckInternetSource", "Finished")
        
    return connectionStatus


def turnOffPi():
    # Turning off Pi to conserve battery
    hourMinute = dateTimeNow.strftime("%H%M")
    #hour = dateTimeNow.strftime("%H")
    minuteString = dateTimeNow.strftime("%M")
    minute = int(minuteString)
    logging("turnOffPi: " + dateTimeNow_string, "Started")
    DisableUsbPorts()
    
    date8AM = datetime(9999,12,31,8,0,0) # we don't care about year, month, and day
    time8AM = date8AM.strftime("%H%M") #getting just the hours and minutes in date format
    date10AM = datetime(9999,12,31,10,0,0) # we don't care about year, month, and day
    time10AM = date10AM.strftime("%H%M") #getting just the hours and minutes in date format
    dateNoon = datetime(9999,12,31,12,0,0) # we don't care about year, month, and day
    timeNoon = dateNoon.strftime("%H%M") #getting just the hours and minutes in date format
    date3PM = datetime(9999,12,31,15,0,0) # we don't care about year, month, and day
    time3PM = date3PM.strftime("%H%M") #getting just the hours and minutes in date format
    
    if hourMinute >= time8AM and hourMinute <= time10AM:
        #then turn on every 9 minutes because this process runs every 10 minutes
        pijuice.rtcAlarm.SetWakeupEnabled(True)
        if minute > 0 and minute < 10:
            pijuice.rtcAlarm.SetAlarm({'second':0,'minute':8,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'})
            logging("turnOffPi", "{'second':0,'minute':8,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'}")
        elif minute >= 10 and minute < 20:
            pijuice.rtcAlarm.SetAlarm({'second':0,'minute':18,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'})
            logging("turnOffPi", "{'second':0,'minute':18,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'}")
        elif minute >= 20 and minute < 30:
            pijuice.rtcAlarm.SetAlarm({'second':0,'minute':28,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'})
            logging("turnOffPi", "{'second':0,'minute':8,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'}")
        elif minute >= 30 and minute < 40:
            pijuice.rtcAlarm.SetAlarm({'second':0,'minute':38,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'})
            logging("turnOffPi", "{'second':0,'minute':8,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'}")
        elif minute >= 40 and minute < 50:
            pijuice.rtcAlarm.SetAlarm({'second':0,'minute':48,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'})
            logging("turnOffPi", "{'second':0,'minute':48,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'}")
        elif minute >= 50 and minute < 59:
            pijuice.rtcAlarm.SetAlarm({'second':0,'minute':58,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'})
            logging("turnOffPi", "{'second':0,'minute':58,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'}")
        else:
            pijuice.rtcAlarm.SetAlarm({'second':0,'minute_period':8,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'})
            logging("turnOffPi", "{'second':0,'minute_period':10,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'}")

    elif hourMinute > time10AM and hourMinute <= timeNoon:
        #then turn on every 14 minutes because this process runs every 15 minutes
        pijuice.rtcAlarm.SetWakeupEnabled(True)
        if minute >= 0 and minute < 15:
            pijuice.rtcAlarm.SetAlarm({'second':0,'minute':13,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'})
            logging("turnOffPi", "{'second':0,'minute':13,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'}")
        elif minute >= 15 and minute < 30:
            pijuice.rtcAlarm.SetAlarm({'second':0,'minute':28,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'})
            logging("turnOffPi", "{'second':0,'minute':28,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'}")
        elif minute >= 30 and minute < 45:
            pijuice.rtcAlarm.SetAlarm({'second':0,'minute':43,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'})
            logging("turnOffPi", "{'second':0,'minute':43,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'}")        
        elif minute >= 45 and minute < 59:
            pijuice.rtcAlarm.SetAlarm({'second':0,'minute':58,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'})
            logging("turnOffPi", "{'second':0,'minute':43,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'}")  
        else:
            pijuice.rtcAlarm.SetAlarm({'second':0,'minute_period':13,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'})
            logging("turnOffPi", "{'second':0,'minute_period':13,'hour':'EVERY_HOUR', 'day':'EVERY_DAY'}")

    elif hourMinute > timeNoon:
        #then turn on every 59 minutes because this process runs every 60 minutes
        pijuice.rtcAlarm.SetWakeupEnabled(True)
        pijuice.rtcAlarm.SetAlarm({'second':0,'minute':58,'hour':'EVERY_HOUR','day':'EVERY_DAY'})
        logging("turnOffPi", "{'second':0,'minute':58,'hour':'EVERY_HOUR','day':'EVERY_DAY'}")
    
    logging("turnOffPi", "Finished")
    logging("**********************************************************************", "**********************************"+"\n")

    time.sleep(1)

    #Changing the wakeup settings to that the PI wakes up in the morning
    if chargeLevel['data'] <= 10:
        pijuice.power.SetWakeUpOnCharge(20)
    else:
        pijuice.power.SetWakeUpOnCharge('DISABLED',non_volatile=True)
    
    ##Make sure power to the pi is stopped to not deplete the battery

    pijuice.power.SetSystemPowerSwitch(0)
    pijuice.power.SetPowerOff(10)

    #now turn the system off
    os.system("sudo shutdown -h now")
   
    return 




    
    
    
    







######### Reading Deer Camera folder location to find most recent timelapse video  #############


#emptying this variable in case it contains values from the previous run
DisableUsbPorts()
time.sleep(2)
EnableUsbPorts()
cameraTimelapseFolderPath = FindCameraTimelapseFolderPath()
timelapseVideos = []
timelapseVideos = glob.glob(cameraTimelapseFolderPath+"*")  
logging("Checking for timelapse files", "Started")
if not timelapseVideos: #checking if the camera is found. If not found then we are enabling the usb ports so that the camera is detected and enters USB mode so that we can search the device for the most recent images
    print("Is Empty")
    logging("Checking for timelapse files", "Timelapse files are empty")
    DisableUsbPorts()
    time.sleep(2)
    EnableUsbPorts()
    cameraTimelapseFolderPath = FindCameraTimelapseFolderPath()
    timelapseVideos = glob.glob(cameraTimelapseFolderPath+"*")
    timelapseVideos.sort(reverse=False)

# timelapseVideos = glob.glob(cameraTimelapseFolderPath+"*")  
# timelapseVideos.sort(reverse=False)
print("timelapseVideos Length: ", len(timelapseVideos))
if len(timelapseVideos) > 0:
    logging("Checking for timelapse files. len(timelapseVideos) > 0", "Finished")

    #the camera is plugged in and we found some videos
    latestTimelapseFileName = os.path.basename(timelapseVideos[len(timelapseVideos)-1])
    
    ConvertToMP4(latestTimelapseFileName)
    timelapseVideos = glob.glob(cameraTimelapseFolderPath+"*")  
    timelapseVideos.sort(reverse=False)
    latestTimelapseFileName = os.path.basename(timelapseVideos[len(timelapseVideos)-1])
    
    AddMinSecToFileNameOnCamera(latestTimelapseFileName)
    timelapseVideos = glob.glob(cameraTimelapseFolderPath+"*")  
    timelapseVideos.sort(reverse=False)
    latestTimelapseFileName = os.path.basename(timelapseVideos[len(timelapseVideos)-1])

    ######### Calling the upload_to_bucket function to send the latest timelapse video to the GCP Storage Account #########
    UploadTimelapseToGcpBucket(cameraTimelapseFolderPath+latestTimelapseFileName)
    
    logging("Calling CleanupFilesOnCamera", "Started")
    CleanupFilesOnCamera() #deleting all files after the process runs  
    
    logging("Calling UploadLogfileToGcpBucket as expected", "Started")
    ######### calling the upload_to_bucket function to send a log file to GCP storage #########
    UploadLogfileToGcpBucket()
    
    #In case a new log file was created when loading to GCP bucket, we are pulling them again
    logFiles = glob.glob(piLogFileLocation+"*")
    logFiles.sort(reverse=False)
    if len(logFiles) > maxSdCardFileNum:
        logging("Calling CleanupLogFilesOnPi", "Started")
        CleanupLogFilesOnPi(len(logFiles)-maxSdCardFileNum)
    
    turnOffPi()
    
else:
    logging("Checking for timelapse files. len(timelapseVideos) = 0", "Finished")
    #the camera is not plugged in so we didnt find any videos
    latestTimelapseFileName = "ERROR - NO FILES FOUND"
    
    logging("Calling UploadLogfileToGcpBucket with ERROR message", "Started")
    ######### calling the upload_to_bucket function to send a log file to GCP storage #########
    UploadLogfileToGcpBucket()
    
    logFiles = glob.glob(piLogFileLocation+"*")
    logFiles.sort(reverse=False)
    if len(logFiles) > maxSdCardFileNum:
        logging("Calling CleanupLogFilesOnPi", "Started")
        CleanupLogFilesOnPi(len(logFiles)-maxSdCardFileNum) 
    
    turnOffPi()




