#version 2.1
import time
import RPi.GPIO as GPIO
import mysql.connector
import schedule
import datetime

# Pin of Input
GPIOpin = -1

# Initial the input pin
def initialInductive(pin):
  global GPIOpin
  global mysqli
  global mycursor
  GPIOpin = pin
  GPIO.setmode(GPIO.BCM)
  GPIO.setup(GPIOpin,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
  print("Finished GPIO Initiation")
  mysqli=mysql.connector.connect(
    host='192.168.1.54',
    user='webapp',
    password='STUDS2650',
    database='iwt_db')
  mycursor = mysqli.cursor()
  print("Finished mySQLi Initiation")

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


#sendStatus
def sendStatus():
  global mysqli
  global mycursor
  global count
  if(count >= 1):
    status='ACTIVE'
  else:
    status='INACTIVE'
  sql = "UPDATE heading_data SET headStatus = %s WHERE headID = %s"
  val = (status, '10')
  mycursor.execute(sql,val)
  mysqli.commit()
  print("Header Status Updated")


#sendData
def sendData():
  global count
  global mysqli
  global mycursor
  x = datetime.datetime.now()
  myDate = x.strftime("%x")
  myHour = x.strftime("%H")
  myMin = x.strftime("%M")
  sql = "INSERT INTO heading_rates (headName, studCount, updateFullDate, updateDate, updateHour, updateMinute) VALUES (%s, %s, %s, %s, %s, %s)"
  val = ("SP11", count, x, myDate, myHour, myMin)
  mycursor.execute(sql,val)
  mysqli.commit()
  print("Count Record Inserted")
  count = 0

# main module
if __name__ == '__main__':
  pin = 17
  count = -1
  upTime = -1
  downTime = -1
  mysqli = 'mysqli'
  mycursor = 'mycursor'
  initialInductive(pin)
  oldState = 2
  schedule.every(1).minutes.do(sendStatus)
  schedule.every(1).minutes.do(sendData)
  print("Count Sequence Started")
  while True:
    detectMetal()
    schedule.run_pending()


