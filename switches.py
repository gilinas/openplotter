#!/usr/bin/env python

# This file is part of Openplotter.
# Copyright (C) 2015 by sailoog <https://github.com/sailoog/openplotter>
#
# Openplotter is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# any later version.
# Openplotter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Openplotter. If not, see <http://www.gnu.org/licenses/>.
import ConfigParser, os, sys, subprocess, time
import RPi.GPIO as GPIO
from classes.twitterbot import TwitterBot
from classes.gmailbot import GmailBot

home = os.path.expanduser('~')
pathname = os.path.dirname(sys.argv[0])
currentpath = os.path.abspath(pathname)

data_conf = ConfigParser.SafeConfigParser()
data_conf.read(currentpath+'/openplotter.conf')

state1=False
state2=False
state3=False
state4=False

#[0]= _('nothing')
#[1]= _('command')
#[2]= _('reset')
#[3]= _('shutdown')
#[4]= _('stop NMEA multiplexer')
#[5]= _('reset NMEA multiplexer')
#[6]= _('stop Signal K server')
#[7]= _('reset Signal K server')
#[8]= _('stop WiFi access point')
#[9]= _('start WiFi access point')
#[10]= _('stop SDR-AIS')
#[11]= _('reset SDR-AIS')
#[12]= _('start Twitter monitoring')
#[13]= _('stop Twitter monitoring')
#[14]= _('publish Twitter')
#[15]= _('start Gmail monitoring')
#[16]= _('stop Gmail monitoring')
#[17]= _('send e-mail')

def switch_options(on_off,switch,option):
	data_conf.read(currentpath+'/openplotter.conf')
	if option=='0': return
	if option=='1':
		command=data_conf.get('SWITCH'+switch, on_off+'_command')
		if command:
			command=command.split(' ')
			subprocess.Popen(command)
	if option=='2': 
		subprocess.Popen(['sudo', 'reboot'])
	if option=='3': 
		subprocess.Popen(['sudo', 'halt'])
	if option=='4': 
		subprocess.Popen(['pkill', '-9', 'kplex'])
	if option=='5':
		subprocess.call(['pkill', '-9', 'kplex'])
		subprocess.Popen('kplex')
	if option=='6': 
		subprocess.Popen(["pkill", '-9', "node"])
	if option=='7':
		subprocess.call(["pkill", '-9', "node"]) 
		subprocess.Popen(home+'/.config/signalk-server-node/bin/nmea-from-10110', cwd=home+'/.config/signalk-server-node') 
	if option=='8':
		wlan=data_conf.get('WIFI', 'device')
		passw2=data_conf.get('WIFI', 'password')
		ssid2=data_conf.get('WIFI', 'ssid')
		subprocess.Popen(['sudo', 'python', currentpath+'/wifi_server.py', '0', wlan, passw2, ssid2])
		data_conf.set('WIFI', 'enable', '0')
		write_conf()
	if option=='9':
		wlan=data_conf.get('WIFI', 'device')
		passw2=data_conf.get('WIFI', 'password')
		ssid2=data_conf.get('WIFI', 'ssid')
		subprocess.Popen(['sudo', 'python', currentpath+'/wifi_server.py', '1', wlan, passw2, ssid2])
		data_conf.set('WIFI', 'enable', '1')
		write_conf()
	if option=='10':
		subprocess.Popen(['pkill', '-9', 'aisdecoder'])
		subprocess.Popen(['pkill', '-9', 'rtl_fm'])
		data_conf.set('AIS-SDR', 'enable', '0')
		write_conf()
	if option=='11':
		gain=data_conf.get('AIS-SDR', 'gain')
		ppm=data_conf.get('AIS-SDR', 'ppm')
		channel=data_conf.get('AIS-SDR', 'channel')
		subprocess.call(['pkill', '-9', 'aisdecoder'])
		subprocess.call(['pkill', '-9', 'rtl_fm'])
		frecuency='161975000'
		if channel=='b': frecuency='162025000'
		rtl_fm=subprocess.Popen(['rtl_fm', '-f', frecuency, '-g', gain, '-p', ppm, '-s', '48k'], stdout = subprocess.PIPE)
		aisdecoder=subprocess.Popen(['aisdecoder', '-h', '127.0.0.1', '-p', '10110', '-a', 'file', '-c', 'mono', '-d', '-f', '/dev/stdin'], stdin = rtl_fm.stdout)
		data_conf.set('AIS-SDR', 'enable', '1')
		write_conf()
	if option=='12':
		subprocess.call(['pkill', '-f', 'monitoring.py'])
		data_conf.set('TWITTER', 'enable', '1')
		write_conf()
		subprocess.Popen(['python', currentpath+'/monitoring.py'])
	if option=='13':
		subprocess.call(['pkill', '-f', 'monitoring.py'])
		data_conf.set('TWITTER', 'enable', '0')
		write_conf()
		if data_conf.get('GMAIL', 'enable')=='1':
			subprocess.Popen(['python', currentpath+'/monitoring.py'])
	if option=='14':
		apiKey = data_conf.get('TWITTER', 'apiKey')
		apiSecret = data_conf.get('TWITTER', 'apiSecret')
		accessToken = data_conf.get('TWITTER', 'accessToken')
		accessTokenSecret = data_conf.get('TWITTER', 'accessTokenSecret')
		now = time.strftime("%H:%M:%S")
		tweetStr=data_conf.get('SWITCH'+switch, on_off+'_command')
		if tweetStr:
			tweetStr = now+' '+tweetStr
			if len(tweetStr)>140: tweetStr=tweetStr[0:140]
			try:
				msg=TwitterBot(apiKey,apiSecret,accessToken,accessTokenSecret)
				msg.send(tweetStr)
			except: pass
	if option=='15':
		subprocess.call(['pkill', '-f', 'monitoring.py'])
		data_conf.set('GMAIL', 'enable', '1')
		write_conf()
		subprocess.Popen(['python', currentpath+'/monitoring.py'])
	if option=='16':
		subprocess.call(['pkill', '-f', 'monitoring.py'])
		data_conf.set('GMAIL', 'enable', '0')
		write_conf()
		if data_conf.get('TWITTER', 'enable')=='1':
			subprocess.Popen(['python', currentpath+'/monitoring.py'])
	if option=='17':
		GMAIL_USERNAME = data_conf.get('GMAIL', 'gmail')
		GMAIL_PASSWORD = data_conf.get('GMAIL', 'password')
		recipient = data_conf.get('GMAIL', 'recipient')
		subject=data_conf.get('SWITCH'+switch, on_off+'_command')
		body = time.strftime("%H:%M:%S")+' '+subject
		if subject:
			try:
				msg=GmailBot(GMAIL_USERNAME,GMAIL_PASSWORD,recipient)
				msg.send(subject,body)
			except: pass

def write_conf():
	with open(currentpath+'/openplotter.conf', 'wb') as configfile:
		data_conf.write(configfile)

def switch1(channel):
	global state1
	if GPIO.input(channel):
		if not state1:
			switch_options('on', '1', data_conf.get('SWITCH1', 'on_action'))
			state1=True
	else:
		if state1:
			switch_options('off', '1', data_conf.get('SWITCH1', 'off_action'))
			state1=False

def switch2(channel):
	global state2
	if GPIO.input(channel):
		if not state2:
			switch_options('on', '2', data_conf.get('SWITCH2', 'on_action'))
			state2=True
	else:
		if state2:
			switch_options('off', '2', data_conf.get('SWITCH2', 'off_action'))
			state2=False

def switch3(channel):
	global state3
	if GPIO.input(channel):
		if not state3:
			switch_options('on', '3', data_conf.get('SWITCH3', 'on_action'))
			state3=True
	else:
		if state3:
			switch_options('off', '3', data_conf.get('SWITCH3', 'off_action'))
			state3=False

def switch4(channel):
	global state4
	if GPIO.input(channel):
		if not state4:
			switch_options('on', '4', data_conf.get('SWITCH4', 'on_action'))
			state4=True
	else:
		if state4:
			switch_options('off', '4', data_conf.get('SWITCH4', 'off_action'))
			state4=False

GPIO.setmode(GPIO.BCM)

if data_conf.get('SWITCH1', 'enable')=='1':
	channel1=int(data_conf.get('SWITCH1', 'gpio'))
	pull_up_down=GPIO.PUD_DOWN
	if data_conf.get('SWITCH1', 'pull_up_down')=='Pull Up': pull_up_down=GPIO.PUD_UP
	GPIO.setup(channel1, GPIO.IN, pull_up_down=pull_up_down)
	GPIO.add_event_detect(channel1, GPIO.BOTH, callback=switch1)

if data_conf.get('SWITCH2', 'enable')=='1':
	channel2=int(data_conf.get('SWITCH2', 'gpio'))
	pull_up_down=GPIO.PUD_DOWN
	if data_conf.get('SWITCH2', 'pull_up_down')=='Pull Up': pull_up_down=GPIO.PUD_UP
	GPIO.setup(channel2, GPIO.IN, pull_up_down=pull_up_down)
	GPIO.add_event_detect(channel2, GPIO.BOTH, callback=switch2)

if data_conf.get('SWITCH3', 'enable')=='1':
	channel3=int(data_conf.get('SWITCH3', 'gpio'))
	pull_up_down=GPIO.PUD_DOWN
	if data_conf.get('SWITCH3', 'pull_up_down')=='Pull Up': pull_up_down=GPIO.PUD_UP
	GPIO.setup(channel3, GPIO.IN, pull_up_down=pull_up_down)
	GPIO.add_event_detect(channel3, GPIO.BOTH, callback=switch3)

if data_conf.get('SWITCH4', 'enable')=='1':
	channel4=int(data_conf.get('SWITCH4', 'gpio'))
	pull_up_down=GPIO.PUD_DOWN
	if data_conf.get('SWITCH4', 'pull_up_down')=='Pull Up': pull_up_down=GPIO.PUD_UP
	GPIO.setup(channel4, GPIO.IN, pull_up_down=pull_up_down)
	GPIO.add_event_detect(channel4, GPIO.BOTH, callback=switch4)

try:  
	while True:
		time.sleep(1000)
finally:
    GPIO.cleanup()