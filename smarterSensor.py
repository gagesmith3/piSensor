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
   global downTime
   global upTime
   global status
   if(GPIOpin != -1):
     newState = GPIO.input(GPIOpin)
     if newState != oldState:
       if newState==1:
         count+=1
         print(count)
         oldState=newState
         upTime+=1
         status = 'ACTIVE'
       else:
         oldState=newState
     else:
       downTime+=1
       status = 'INACTIVE'
   else:
     print("Please Initial Input Ports")

#sendUpTime
def sendStatus():
  global mysqli
  global mycursor
  global status
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
  val = ("TEST2", count, x, myDate, myHour, myMin)
  mycursor.execute(sql,val)
  mysqli.commit()
  print("Count Record Inserted")
  count = 0



# test module
if __name__ == '__main__':
  pin = 17
  count = -1
  upTime = 0
  downTime = 0
  mysqli = 'mysqli'
  mycursor = 'mycursor'
  status = 'INACTIVE'
  initialInductive(pin)
  oldState = 2
  #schedule.every(1).minutes.do(sendData)
  schedule.every(1).minutes.do(sendStatus)
  print("Count Sequence Started")
  while True:
    detectMetal()
    schedule.run_pending()
