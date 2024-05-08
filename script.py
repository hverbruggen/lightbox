#!/usr/bin/env python3
import datetime
import time
from gpiozero import PWMLED
from rgbstrip import LEDStrip
import Adafruit_DHT
import csv
import schedule
import os
import re

verbose = False

# define input & output files
box_number = 1
in_file = "settings.csv"
log_file = "log.txt"
if verbose: print("starting script - box "+str(box_number))

# set up humidity sensor
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 26

# set up fan
fanPin = 25
fanControl = PWMLED(fanPin)
fanSpeed = .6

# set up white/nir strips (they are controlled as if they were r & g channels of rgb strip)
# there is capacity for another channel on this driver
wnCLKPin = 23
wnDATPin = 24
wnStrip = LEDStrip(wnCLKPin,wnDATPin)
white = 100
nir = 100

# set up rgb strip
rgbCLKPin = 20  #yellow
rgbDATPin = 21  #orange
rgbStrip = LEDStrip(rgbCLKPin, rgbDATPin)
rgbCycle = 1
red = 100
green = 100
blue = 100

# set up the data structure for controlling the LEDs/fan
data = {}

# defining jobs to be run by scheduler
def reload_input():   # reads the instructions from the csv file
	if verbose: print("  loading potential new instructions from file")
	with open(in_file, "r") as reader:
		reader = csv.DictReader(reader)
		for row in reader:
			time = row['time']
			data[time] = row
	if verbose: print("    done")
def store_day_log():   # renames and stores the log file at the end of the day
	if verbose: print("  performing end-of-day log maintenance")
	# rename today's file and store it away
	d = datetime.datetime.now()
	new_name = "box"+str(box_number)+"_"+str(d.year)+str(d.month).zfill(2)+str(d.day).zfill(2)
	os.rename(log_file, new_name)
	# add code here to transfer file to MediaFlux
	# open a new one
	with open(log_file, 'w') as f:
		f.write("box_number\tyear\tmonth\tday\thour\tminute\tsecond\thumidity\ttemperature\twhite\tnir\tred\tgreen\tblue\tfan\n")
	if verbose: print("    done")
def update_settings_and_log():  # updates the LED and fan settings, reads out the temperature and humidity, and writes the values to the log file
	if verbose: print("  updating settings")
	d = datetime.datetime.now()
	time_code_now = str(d.hour).zfill(2)+":"+str(d.minute).zfill(2)
	time_code = time_code_now

	# this entire bit of code is just here to help the program get to the right settings after a crash and reboot
	# it finds the closest instruction before the present time (or the last of the previous day if there are no instructions before present time)
	if not time_code_now in data.keys():
		m = re.split(':',time_code_now)
		cur = int(m[0]) * 60 + int(m[1])
		bestKey = None
		lastKeyOfTheDay = None
		difference = 10000
		lastSumOfTheDay = 0
		for key in data:
			m = re.split(':',key)
			this = int(m[0]) * 60 + int(m[1])
			if this > lastSumOfTheDay:
				lastSumOfTheDay = this
				lastKeyOfTheDay = key
			if this < cur:
				if cur - this < difference:
					difference = cur - this
					bestKey = key
		if bestKey == None:
			bestKey = lastKeyOfTheDay
		time_code = bestKey
	# okay, done with this code to recover from crash

	white = int(data[time_code]['white'])
	red = int(data[time_code]['red'])
	green = int(data[time_code]['green'])
	blue = int(data[time_code]['blue'])
	nir = int(data[time_code]['nir'])
	fanSpeed = data[time_code]['fan']
	fanSpeed = round(float(fanSpeed),2)
	fanControl.value = fanSpeed
	rgbStrip.setcolourrgb(red,green,blue)
	wnStrip.setcolourrgb(white,nir,0)
	if verbose: print("    done")
	if verbose: print("  logging data")
	# get humidity and temperature details
	humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
	if humidity is None:
		humidity = 'NAN'
	else:
		humidity = round(humidity,2)
	if temperature is None:
		temperature = 'NAN'
	else:
		temperature = round(temperature,2)
	# open log file and append data
	with open(log_file, 'a+') as f:
		f.write(str(box_number)+"\t"+str(d.year)+"\t"+str(d.month).zfill(2)+"\t"+str(d.day).zfill(2)+"\t"+str(d.hour).zfill(2)+"\t"+str(d.minute).zfill(2)+"\t"+str(d.second).zfill(2)+"\t"+str(humidity)+"\t"+str(temperature)+"\t"+str(white)+"\t"+str(nir)+"\t"+str(red)+"\t"+str(green)+"\t"+str(blue)+"\t"+str(fanSpeed)+"\n")
	if verbose: print("    done")

# setting the schedules
schedule.every().minute.at(":00").do(update_settings_and_log)
#schedule.every().minute.at(":15").do(update_settings_and_log)
#schedule.every().minute.at(":30").do(update_settings_and_log)
#schedule.every().minute.at(":45").do(update_settings_and_log)
schedule.every().minute.at(":30").do(reload_input)
schedule.every().day.at("23:59:05").do(store_day_log)

if verbose: print("initial loading of instructions")
reload_input()

# the infinite loop
if verbose: print("starting infinite loop")
while True:	
	schedule.run_pending()