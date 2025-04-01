#version 3.1
import time
import RPi.GPIO as GPIO
import mysql.connector
import schedule
import datetime
import os

# Pin of Input
GPIOpin = -1

# Initial the input pin
def initialInductive(pin):
  global GPIOpin
  GPIOpin = pin
  GPIO.setmode(GPIO.BCM)
  GPIO.setup(GPIOpin,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
  print("Finished Initiation")

# Detect Metal
def detectMetal():
   global oldState
   global count
   if(GPIOpin != -1):
     newState = GPIO.input(GPIOpin)
     if newState != oldState:
       if newState==1:
         count+=1
         print(count)
         oldState=newState
       else:
         oldState=newState
   else:
     print("Please Initial Input Ports")


#sendData
def sendData():
  mysqli=mysql.connector.connect(
        host='192.168.1.54',
        user='webapp',
        password='STUDS2650',
        database='iwt_db')
  global count
  x = datetime.datetime.now()
  myDate = x.strftime("%x")
  myHour = x.hour
  myMin = x.minute
  if myHour>=7 and myHour<=17:
    mycursor=mysqli.cursor()
    sql = "INSERT INTO heading_rates (headName, studCount, updateFullDate, updateDate, updateHour, updateMinute) VALUES (%s, %s, %s, %s, %s, %s)"
    val = ("NATIONAL_1", count, x, myDate, myHour, myMin)
    mycursor.execute(sql,val)
    mysqli.commit()
    if count>0:
      sql2 = "UPDATE heading_data SET headStatus = 'ACTIVE' WHERE headID = 1"
    else:
      sql2 = "UPDATE heading_data SET headStatus = 'INACTIVE' WHERE headID = 1"
    mycursor.execute(sql2)
    mysqli.commit()
    count = 0
    print('Data Sent')
  if myHour==23 and myMin==59:
    os.system('sudo reboot')

# test module
if __name__ == '__main__':
  mysqli=mysql.connector.connect(
    host='192.168.1.6',
    user='webapp',
    password='STUDS2650',
    database='iwt_db')
  mycursor=mysqli.cursor()
  sql = "UPDATE heading_data SET headerAlarm = 'FALSE' WHERE headID = 8"
  mycursor.execute(sql)
  mysqli.commit()
  pin = 17
  count = 0
  oldState = 2
  initialInductive(pin)
  schedule.every(1).minutes.do(sendData)
  while True:
    detectMetal()
    schedule.run_pending()
