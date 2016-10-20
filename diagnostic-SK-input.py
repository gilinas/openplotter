#!/usr/bin/env python

# This file is part of Openplotter.
# Copyright (C) 2015 by sailoog <https://github.com/sailoog/openplotter>
# 					  e-sailing <https://github.com/e-sailing/openplotter>
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

import json
import logging
import subprocess
import threading
import os
import websocket
import wx

from classes.conf import Conf
from classes.language import Language
from classes.paths import Paths


class MyFrame(wx.Frame):
	def __init__(self):
		self.SK_unit = ''
		self.SK_description = ''
		self.SK_unit_priv = 0
		self.SK_Faktor_priv = 1
		self.SK_Offset_priv = 0
		self.ws = None

		self.thread = threading._DummyThread

		self.private_unit_s = 1
		logging.basicConfig()
		self.buffer = []
		self.list_SK = []
		self.list_SK_unit = []
		self.sortCol = 0

		paths = Paths()
		self.home = paths.home
		self.currentpath = paths.currentpath
		self.conf = Conf(paths)

		Language(self.conf.get('GENERAL', 'lang'))

		wx.Frame.__init__(self, None, title='diagnostic SignalK input', size=(650, 435))
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		panel = wx.Panel(self, wx.ID_ANY)

		self.ttimer = 100
		self.timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.timer_act, self.timer)

		self.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))

		self.icon = wx.Icon(self.currentpath + '/openplotter.ico', wx.BITMAP_TYPE_ICO)
		self.SetIcon(self.icon)

		self.list = wx.ListCtrl(panel, -1, style=wx.LC_REPORT | wx.SUNKEN_BORDER)
		self.list.InsertColumn(0, _('SRC'), width=200)
		self.list.InsertColumn(1, _('SignalK'), width=300)
		self.list.InsertColumn(2, _('Value'), wx.LIST_FORMAT_RIGHT, width=100)
		self.list.InsertColumn(3, _('Unit'), width=40)
		self.list.InsertColumn(4, _('Interval'), wx.LIST_FORMAT_RIGHT, width=55)
		self.list.InsertColumn(5, _('Status'), width=50)
		self.list.InsertColumn(6, _('Description'), width=500)

		sort_SRC = wx.Button(panel, label=_('Sort SRC'))
		sort_SRC.Bind(wx.EVT_BUTTON, self.on_sort_SRC)

		sort_SK = wx.Button(panel, label=_('Sort SK'))
		sort_SK.Bind(wx.EVT_BUTTON, self.on_sort_SK)

		self.private_unit = wx.CheckBox(panel, label=_('private Unit'), pos=(360, 32))
		self.private_unit.Bind(wx.EVT_CHECKBOX, self.on_private_unit)
		self.private_unit.SetValue(self.private_unit_s)

		unit_setting = wx.Button(panel, label=_('Unit Setting'))
		unit_setting.Bind(wx.EVT_BUTTON, self.on_unit_setting)

		vbox = wx.BoxSizer(wx.VERTICAL)
		hlistbox = wx.BoxSizer(wx.HORIZONTAL)
		hbox = wx.BoxSizer(wx.HORIZONTAL)
		hlistbox.Add(self.list, 1, wx.ALL | wx.EXPAND, 5)
		hbox.Add(sort_SRC, 0, wx.RIGHT | wx.LEFT, 5)
		hbox.Add(sort_SK, 0, wx.RIGHT | wx.LEFT, 5)
		hbox.Add((0,0), 1, wx.RIGHT | wx.LEFT, 5)
		hbox.Add(self.private_unit, 0, wx.RIGHT | wx.LEFT, 5)
		hbox.Add(unit_setting, 0, wx.RIGHT | wx.LEFT, 5)
		vbox.Add(hlistbox, 1, wx.ALL | wx.EXPAND, 0)
		vbox.Add(hbox, 0, wx.ALL | wx.EXPAND, 0)
		panel.SetSizer(vbox)

		self.CreateStatusBar()

		self.read()
		self.start()

		self.Show(True)

		self.status = ''
		self.data = []
		self.baudc = 0
		self.baud = 0

		self.timer.Start(self.ttimer)
		self.no_action = 0
		self.no_action_limit = 5000 / self.ttimer

	def timer_act(self, e):
		if len(self.buffer) > 0:
			self.no_action = 0
			for ii in self.buffer:
				if 0 <= ii[0] < self.list.GetItemCount():
					self.list.SetStringItem(ii[0], ii[1], ii[2])
				else:
					self.sorting()
				del self.buffer[0]
				# del ii
		else:
			self.no_action += 1
			if self.no_action > self.no_action_limit:
				if self.ws:
					self.ws.close()
				self.start()
				self.no_action = 0

	def json_interval(self, time_old, time_new):
		sek_n = float(time_new[17:22])
		sek_o = float(time_old[17:22])
		if sek_n >= sek_o:
			dif = sek_n - sek_o
		else:
			dif = sek_n + 60 - sek_o
		return dif

	def read(self):
		self.list_SK_unit = []
		response = subprocess.Popen(
			[self.home + '/.config/signalk-server-node/node_modules/signalk-schema/scripts/extractKeysAndMeta.js'],
			stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		data = json.loads(response.communicate()[0])

		data_sk_unit_private = []
		if os.path.isfile(self.home + '/.config/openplotter/classes/private_unit.json'):
			with open(self.home + '/.config/openplotter/classes/private_unit.json') as data_file:
				data_sk_unit_private = json.load(data_file)

		for i in data:
			if 'units' in data[i].keys():
				if 'description' in data[i].keys():
					self.list_SK_unit.append([str(i), str(data[i]['units']), '', str(data[i]['description'])])
				else:
					self.list_SK_unit.append([str(i), str(data[i]['units']), '', ''])
		for j in data_sk_unit_private:
			for i in self.list_SK_unit:
				if j[0] == i[0]:
					i[2] = j[2]
					break

		self.list_SK_unit.sort(key=lambda tup: tup[0])
		self.list_SK_unit.sort(key=lambda tup: tup[1])

	def lookup_star(self, name):
		skip = -1
		index = 0
		st = ''
		for i in name.split('.'):
			if index > -1:
				if skip == 0:
					st += '.*'
				else:
					if i in ['propulsion', 'inventory']:
						skip = 1
					elif i == 'resources':
						skip = 2
					st += '.' + i
			index += 1
			skip -= 1

		st = st[1:]
		self.SK_unit = ''
		self.SK_unit_priv = ''
		self.SK_description = ''
		for j in self.list_SK_unit:
			exist = False
			if j[0] == st:
				exist = True
				self.SK_unit = j[1]
				self.SK_description = j[3]
				if j[2] != '':
					self.SK_unit_priv = j[2]
				else:
					self.SK_unit_priv = j[1]
				break
		if not exist:
			print 'no unit for ', st

		self.SK_Faktor_priv = 1
		self.SK_Offset_priv = 0
		if self.SK_unit_priv != self.SK_unit:
			if self.SK_unit == 'm':
				if self.SK_unit_priv == 'ft':
					self.SK_Faktor_priv = 0.3048
				elif self.SK_unit_priv == 'nm':
					self.SK_Faktor_priv = 1852
				elif self.SK_unit_priv == 'km':
					self.SK_Faktor_priv = 1000
			elif self.SK_unit == 'Pa':
				if self.SK_unit_priv == 'hPa':
					self.SK_Faktor_priv = 100
				elif self.SK_unit_priv == 'Bar':
					self.SK_Faktor_priv = 100000
			elif self.SK_unit == 'rad' and self.SK_unit_priv == 'deg':
				self.SK_Faktor_priv = 0.0174533
			elif self.SK_unit == 'm/s':
				if self.SK_unit_priv == 'kn':
					self.SK_Faktor_priv = 0.514444444
				elif self.SK_unit_priv == 'kmh':
					self.SK_Faktor_priv = 0, 277778
				elif self.SK_unit_priv == 'mph':
					self.SK_Faktor_priv = 0.44704
			elif self.SK_unit == 'm3':
				if self.SK_unit_priv == 'l':
					self.SK_Faktor_priv = 0.001
				elif self.SK_unit_priv == 'gal':
					self.SK_Faktor_priv = 0.00378541
			elif self.SK_unit == 's':
				if self.SK_unit_priv == 'h':
					self.SK_Faktor_priv = 3600
				elif self.SK_unit_priv == 'd':
					self.SK_Faktor_priv = 86400
				elif self.SK_unit_priv == 'y':
					self.SK_Faktor_priv = 31536000
			elif self.SK_unit == 'K':
				if self.SK_unit_priv == 'C':
					self.SK_Offset_priv = -273.15
				elif self.SK_unit_priv == 'F':
					self.SK_Faktor_priv = 1.8
					self.SK_Offset_priv = -459, 67
		else:
			self.SK_Faktor_priv = 1
			self.SK_Offset_priv = 0
		
	def on_sort_SRC(self, e):
		self.sortCol = 0
		self.sorting()

	def on_sort_SK(self, e):
		self.sortCol = 1
		self.sorting()

	def sorting(self):
		self.list.DeleteAllItems()
		list_new = []
		for i in sorted(self.list_SK, key=lambda item: (item[self.sortCol])):
			list_new.append(i)
		self.list_SK = list_new
		self.init2()

	def init2(self):
		index = 0
		for i in self.list_SK:
			if type(i[2]) is float:
				pass
			else:
				i[2] = 0.0
			self.list.InsertStringItem(index, str(i[0]))
			self.list.SetStringItem(index, 1, str(i[1]))
			if not self.private_unit_s:
				self.buffer.append([index, 2, str('%.3f' % i[2])])
				self.buffer.append([index, 3, i[3]])
			else:
				i[9] = i[2] / i[10] + i[11]
				self.buffer.append([index, 2, str('%.3f' % i[9])])
				self.buffer.append([index, 3, i[8]])
			self.list.SetStringItem(index, 4, str('%.1f' % i[4]))
			self.list.SetStringItem(index, 5, str(i[5]))
			self.list.SetStringItem(index, 6, str(i[6]))
			index += 1

	def on_unit_setting(self, e):
		subprocess.Popen(['python', self.currentpath + '/unit-private.py'])

	def OnClose(self, e):
		if self.ws:
			self.ws.close()
		self.timer.Stop()
		if self.ws:
			self.ws.close()
		self.Destroy()

	def on_message(self, ws, message):
		try:
			js_up = json.loads(message)['updates'][0]
		except:
			return
		label = js_up['source']['label']

		srcExist = False
		src = ''
		try:
			src = js_up['source']['src']
			srcExist = True
		except:
			pass
		if not srcExist:
			try:
				src = js_up['source']['talker']
			except:
				src = 'xx'
		try:
			timestamp = js_up['timestamp']
		except:
			timestamp = '2000-01-01T00:00:00.000Z'

		values_ = js_up['values']
		srclabel2 = ''

		for values in values_:
			path = values['path']
			value = values['value']

			if type(value) is dict:
				if 'timestamp' in value: timestamp = value['timestamp']
				if 'source' in value:
					try:
						src2 = value['source']['talker']
					except:
						src2 = 'xx'
					srclabel2 = label + '.' + src2

				for lvalue in value:
					if lvalue in ['timestamp', 'source']:
						pass
					else:
						path2 = path + '.' + lvalue
						value2 = value[lvalue]
						self.update_add(value2, path2, srclabel2, timestamp)
			else:
				srclabel = label + '.' + src
				self.update_add(value, path, srclabel, timestamp)

	def update_add(self, value, path, src, timestamp):
		# SRC SignalK Value Unit Interval Status Description timestamp	private_Unit private_Value priv_Faktor priv_Offset
		#  0    1      2     3      4        5        6          7           8             9           10          11
		if type(value) is list: value=value[0]

		if type(value) is float: pass
		elif type(value) is int: value = float(value)
		else: value=0.0

		index = 0
		exists = False
		for i in self.list_SK:
			if path == i[1]:
				if src == i[0]:
					exists = True
					i[2] = value
					if type(i[2]) is float:
						pass
					else:
						i[2] = 0.0
					if i[4] == 0.0:
						i[4] = self.json_interval(i[7], timestamp)
					else:
						i[4] = i[4] * .8 + 0.2 * self.json_interval(i[7], timestamp)
					i[7] = timestamp
					self.buffer.append([index, 4, str('%.2f' % i[4])])
					if not self.private_unit_s:
						self.buffer.append([index, 2, str('%.3f' % i[2])])
						self.buffer.append([index, 3, i[3]])
					else:
						i[9] = i[2] / i[10] + i[11]
						self.buffer.append([index, 2, str('%.3f' % i[9])])
						self.buffer.append([index, 3, i[8]])
					break
			index += 1
		if not exists:
			self.lookup_star(path)
			self.list_SK.append(
				[src, path, value, str(self.SK_unit), 0.0, 1, self.SK_description, timestamp, str(self.SK_unit_priv), 0,
				 self.SK_Faktor_priv, self.SK_Offset_priv])
			self.buffer.append([-1, 0, ''])

	def on_private_unit(self, e):
		self.private_unit_s = self.private_unit.GetValue()

	def on_error(self, ws, error):
		print error

	def on_close(self, ws):
		ws.close()

	def on_open(self, ws):
		pass

	def run(self):
		self.ws = websocket.WebSocketApp("ws://localhost:3000/signalk/v1/stream?subscribe=self",
										 on_message=lambda ws, msg: self.on_message(ws, msg),
										 on_error=lambda ws, err: self.on_error(ws, err),
										 on_close=lambda ws: self.on_close(ws))
		self.ws.on_open = lambda ws: self.on_open(ws)
		self.ws.run_forever()
		self.ws = None

	def start(self):
		def run():
			self.run()

		self.thread = threading.Thread(target=run)
		self.thread.start()


app = wx.App()
MyFrame().Show()
app.MainLoop()
