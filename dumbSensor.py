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
  GPIOpin = pin
  GPIO.setmode(GPIO.BCM)
  GPIO.setup(GPIOpin,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
  print("Finished Initiation")
  print(GPIOpin)

#create counting var
def initiateCount():
  global count
  print("Count Initiated")
  print(count)


# Detect Metal
def detectMetal():
  if(GPIOpin != -1):
    state = GPIO.input(GPIOpin)
    global count
    if state:
      print("Metal Detected")
      count += 1
      print(count)
    else :
      print("Metal Not Detected")
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
  myHour = x.strftime("%H")
  myMin = x.strftime("%M")
  mycursor=mysqli.cursor()
  sql = "INSERT INTO heading_rates (headName, studCount, updateFullDate, updateDate, updateHour, updateMinute) VALUES (%s, %s, %s, %s, %s, %s)"
  val = ("SP11", count, x, myDate, myHour, myMin)
  mycursor.execute(sql,val)
  mysqli.commit()
  print(mycursor.rowcount, "Record Inserted!")
  count = 0


# test module
if __name__ == '__main__':
  pin = 17
  count = 0
  initiateCount()
  initialInductive(pin)
  schedule.every(1).minutes.do(sendData)
  while True:
    detectMetal()
    schedule.run_pending()
    time.sleep(.7)
