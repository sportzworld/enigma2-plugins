#######################################################################
#
#    Merlin Programm Guide for Dreambox-Enigma2
#    Coded by Vali (c)2010
#    Support: www.dreambox-tools.info
#
#
#  This plugin is licensed under the Creative Commons 
#  Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#  To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
#  or send a letter to Creative Commons, 559 Nathan Abbott Way, Stanford, California 94305, USA.
#
#  Alternatively, this plugin may be distributed and executed on hardware which
#  is licensed by Dream Multimedia GmbH.
#
#
#  This plugin is NOT free software. It is open source, you are allowed to
#  modify it (if you keep the license), but it may not be commercially 
#  distributed other than under the conditions noted above.
#
#
#######################################################################



from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.EventView import EventViewSimple
from Screens.MessageBox import MessageBox
from Screens.TimerEntry import TimerEntry
from Screens.TimerEdit import TimerSanityConflict
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.EpgList import EPGList, EPG_TYPE_SINGLE, Rect
from Components.config import config, ConfigSubsection, ConfigYesNo, ConfigInteger, getConfigListEntry
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap
from enigma import eServiceReference, eServiceCenter, getDesktop, eTimer, gFont, eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_WRAP
from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT
from ServiceReference import ServiceReference
from ShowMe import ShowMe
from time import localtime



config.plugins.MerlinPG = ConfigSubsection()
config.plugins.MerlinPG.Columns = ConfigYesNo(default=True)
config.plugins.MerlinPG.StartFirst = ConfigYesNo(default=False)
config.plugins.MerlinPG.Primetime  = ConfigInteger(default=20, limits=(0, 23))
config.plugins.MerlinPG.PTlow  = ConfigInteger(default=10, limits=(0, 59))
config.plugins.MerlinPG.PThi  = ConfigInteger(default=20, limits=(0, 59))



def Plugins(**kwargs):
 	list = [(PluginDescriptor(name="Merlin Programm Guide", description="Merlin Programm Guide", where = PluginDescriptor.WHERE_EVENTINFO, fnc=startMerlinPG))]
	list.append(PluginDescriptor(name="Merlin Programm Guide", where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=startMerlinPG))
	return list



def startMerlinPG(session, servicelist, **kwargs):
	if config.plugins.MerlinPG.Columns.value:
		session.open(Merlin_PGII, servicelist)
	else:
		session.open(Merlin_PGd, servicelist)



class MerlinPGsetup(ConfigListScreen, Screen):
	skin = """
		<screen position="center,center" size="500,300" title="Merlin Programm Guide">
			<widget name="config" position="10,10" size="480,280" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		clist = []
		clist.append(getConfigListEntry(_("Show EPG in columns:"), config.plugins.MerlinPG.Columns))
		clist.append(getConfigListEntry(_("Start allways on channel 1:"), config.plugins.MerlinPG.StartFirst))
		clist.append(getConfigListEntry(_("Primetime (h):"), config.plugins.MerlinPG.Primetime))
		clist.append(getConfigListEntry(_("Primetime from (m):"), config.plugins.MerlinPG.PTlow))
		clist.append(getConfigListEntry(_("Primetime to (m):"), config.plugins.MerlinPG.PThi))
		ConfigListScreen.__init__(self, clist)
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.set, "cancel": self.exit}, -2)

	def set(self):
		if not config.plugins.MerlinPG.PThi.value > config.plugins.MerlinPG.PTlow.value:
			return
		for x in self["config"].list:
			x[1].save()
		self.close()

	def exit(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()



class MerlinEPGList(EPGList):
	def __init__(self, type=EPG_TYPE_SINGLE, selChangedCB=None, timer = None):
		EPGList.__init__(self, type, selChangedCB, timer)
		self.l.setFont(0, gFont("Regular", 18))
		self.PTpicture = LoadPixmap(cached=True, path="/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/primetime.png")
		self.evCnt = 0

	def recalcEntrySize(self):
		esize = self.l.getItemSize()
		width = esize.width()
		height = esize.height()
		self.weekday_rect = Rect(120, -10, 200, 20)
		self.datetime_rect = Rect(0, 0, 120, 20)
		self.descr_rect = Rect(0, 22, width, height-23)
		self.evCnt = 0

	def buildSingleEntry(self, service, eventId, beginTime, duration, EventName):
		(clock_pic, rec) = self.getPixmapForEntry(service, eventId, beginTime, duration)
		r1=self.weekday_rect
		r2=self.datetime_rect
		r3=self.descr_rect
		t = localtime(beginTime)
		self.evCnt = self.evCnt + 1
		if (t[3]==config.plugins.MerlinPG.Primetime.value) and (t[4]>config.plugins.MerlinPG.PTlow.value) and (t[4]<config.plugins.MerlinPG.PThi.value):
			res = [
				None,
				(eListboxPythonMultiContent.TYPE_TEXT, r1.left(), r1.top(), r1.width(), r1.height(), 0, RT_HALIGN_LEFT, "  _________________"),
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 100, 1, 21, 21, self.PTpicture),
				(eListboxPythonMultiContent.TYPE_TEXT, r2.left(), r2.top(), r2.width(), r1.height(), 0, RT_HALIGN_LEFT, (("%02d:%02d"%(t[3],t[4]))+" - "+self.days[t[6]]))
			]
		else:
			res = [
				None,
				(eListboxPythonMultiContent.TYPE_TEXT, r1.left(), r1.top(), r1.width(), r1.height(), 0, RT_HALIGN_LEFT, "___________________"),
				(eListboxPythonMultiContent.TYPE_TEXT, r2.left(), r2.top(), r2.width(), r1.height(), 0, RT_HALIGN_LEFT, (("%02d:%02d"%(t[3],t[4]))+" - "+self.days[t[6]]))
			]
		if rec:
			res.extend((
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, r3.left(), r3.top(), 21, 21, clock_pic),
				(eListboxPythonMultiContent.TYPE_TEXT, r3.left() + 25, r3.top(), r3.width(), r3.height(), 0, RT_HALIGN_LEFT|RT_WRAP, EventName)
			))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.left(), r3.top(), r3.width(), r3.height(), 0, RT_HALIGN_LEFT|RT_WRAP, EventName))
		return res

	def getBgTime(self):
		tmp = self.l.getCurrentSelection()
		if tmp is None:
			return ( None )
		bt = localtime(tmp[2])
		return ( bt[3], bt[4] )

	def foudPrimetime(self):
		for OneLine in range(0,self.evCnt):
			evBgTime, evBgMin = self.getBgTime()
			if evBgTime is not None:
				if (evBgTime==config.plugins.MerlinPG.Primetime.value) and (evBgMin>config.plugins.MerlinPG.PTlow.value) and (evBgMin<config.plugins.MerlinPG.PThi.value):
					break
				self.moveDown()
			else:
				break



class Merlin_PGII(Screen):
	sz_w = getDesktop(0).size().width()
	if sz_w == 1280:
		skin = """
		<screen flags="wfNoBorder" name="Merlin_PG" position="0,0" size="1280,720" title="Merlin Program Guide">
		<!-- DO NOT CHANGE THIS LINE !!!!!!!!!!!!!!! --><widget enableWrapAround="0" itemHeight="25" name="prg_list" position="-200,-200" size="50,125"/>
			<widget font="Regular;18" halign="center" valign="center" name="currCh1" position="60,40" size="231,24" transparent="1" zPosition="2"/>
			<widget font="Regular;18" halign="center" valign="center" name="currCh2" position="291,40" size="231,24" transparent="1" zPosition="2"/>
			<widget font="Regular;18" halign="center" valign="center" name="currCh3" position="522,40" size="231,24" transparent="1" zPosition="2"/>
			<widget font="Regular;18" halign="center" valign="center" name="currCh4" position="753,40" size="231,24" transparent="1" zPosition="2"/>
			<widget font="Regular;18" halign="center" valign="center" name="currCh5" position="984,40" size="231,24" transparent="1" zPosition="2"/>
			<widget backgroundColor="#10444649" name="Active1" position="60,80" size="225,560" transparent="0" zPosition="3"/>
			<widget backgroundColor="#10444649" name="Active2" position="291,80" size="225,560" transparent="0" zPosition="3"/>
			<widget backgroundColor="#10444649" name="Active3" position="522,80" size="225,560" transparent="0" zPosition="3"/>
			<widget backgroundColor="#10444649" name="Active4" position="753,80" size="225,560" transparent="0" zPosition="3"/>
			<widget backgroundColor="#10444649" name="Active5" position="984,80" size="225,560" transparent="0" zPosition="3"/>
			<widget itemHeight="70" name="epg_list1" position="60,80" scrollbarMode="showOnDemand" size="225,560" transparent="1" zPosition="4"/>
			<widget itemHeight="70" name="epg_list2" position="291,80" scrollbarMode="showOnDemand" size="225,560" transparent="1" zPosition="4"/>
			<widget itemHeight="70" name="epg_list3" position="522,80" scrollbarMode="showOnDemand" size="225,560" transparent="1" zPosition="4"/>
			<widget itemHeight="70" name="epg_list4" position="753,80" scrollbarMode="showOnDemand" size="225,560" transparent="1" zPosition="4"/>
			<widget itemHeight="70" name="epg_list5" position="984,80" scrollbarMode="showOnDemand" size="225,560" transparent="1" zPosition="4"/>
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/buttons.png" position="60,655" size="430,24"/>
			<widget backgroundColor="background" font="Regular;18" foregroundColor="#ffc000" position="500,655" render="Label" size="200,24" source="global.CurrentTime" transparent="1" valign="center" zPosition="3">	
				<convert type="ClockToText">Format:%H:%M  %a %d. %b</convert>
			</widget>
		</screen>"""
	elif sz_w == 1024:
		skin = """
		<screen flags="wfNoBorder" name="Merlin_PG" position="0,0" size="1024,576" title="Merlin Program Guide">
		<!-- DO NOT CHANGE THIS LINE !!!!!!!!!!!!!!! --><widget enableWrapAround="0" itemHeight="25" name="prg_list" position="-200,-200" size="50,100"/>
			<widget font="Regular;18" halign="center" valign="center" name="currCh1" position="50,40" size="231,24" transparent="1" zPosition="2"/>
			<widget font="Regular;18" halign="center" valign="center" name="currCh2" position="281,40" size="231,24" transparent="1" zPosition="2"/>
			<widget font="Regular;18" halign="center" valign="center" name="currCh3" position="512,40" size="231,24" transparent="1" zPosition="2"/>
			<widget font="Regular;18" halign="center" valign="center" name="currCh4" position="743,40" size="231,24" transparent="1" zPosition="2"/>
			<widget backgroundColor="#10444649" name="Active1" position="50,80" size="225,420" transparent="0" zPosition="3"/>
			<widget backgroundColor="#10444649" name="Active2" position="281,80" size="225,420" transparent="0" zPosition="3"/>
			<widget backgroundColor="#10444649" name="Active3" position="512,80" size="225,420" transparent="0" zPosition="3"/>
			<widget backgroundColor="#10444649" name="Active4" position="743,80" size="225,420" transparent="0" zPosition="3"/>
			<widget itemHeight="70" name="epg_list1" position="50,80" scrollbarMode="showOnDemand" size="225,420" transparent="1" zPosition="4"/>
			<widget itemHeight="70" name="epg_list2" position="281,80" scrollbarMode="showOnDemand" size="225,420" transparent="1" zPosition="4"/>
			<widget itemHeight="70" name="epg_list3" position="512,80" scrollbarMode="showOnDemand" size="225,420" transparent="1" zPosition="4"/>
			<widget itemHeight="70" name="epg_list4" position="743,80" scrollbarMode="showOnDemand" size="225,420" transparent="1" zPosition="4"/>
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/buttons.png" position="50,518" size="430,24"/>
			<widget backgroundColor="background" font="Regular;18" foregroundColor="#ffc000" position="490,518" render="Label" size="200,24" source="global.CurrentTime" transparent="1" valign="center" zPosition="3">	
				<convert type="ClockToText">Format:%H:%M  %a %d. %b</convert>
			</widget>
		</screen>"""
	else:
		skin = """
		<screen flags="wfNoBorder" name="Merlin_PG" position="0,0" size="720,576" title="Merlin Program Guide">
		<!-- DO NOT CHANGE THIS LINE !!!!!!!!!!!!!!! --><widget enableWrapAround="0" itemHeight="25" name="prg_list" position="-200,-200" size="50,100"/>
			<widget font="Regular;18" halign="center" valign="center" name="currCh1" position="50,35" size="155,36" transparent="1" zPosition="2"/>
			<widget font="Regular;18" halign="center" valign="center" name="currCh2" position="205,35" size="155,36" transparent="1" zPosition="2"/>
			<widget font="Regular;18" halign="center" valign="center" name="currCh3" position="360,35" size="155,36" transparent="1" zPosition="2"/>
			<widget font="Regular;18" halign="center" valign="center" name="currCh4" position="515,35" size="155,36" transparent="1" zPosition="2"/>
			<widget backgroundColor="#10444649" name="Active1" position="50,90" size="155,420" transparent="0" zPosition="3"/>
			<widget backgroundColor="#10444649" name="Active2" position="205,90" size="155,420" transparent="0" zPosition="3"/>
			<widget backgroundColor="#10444649" name="Active3" position="360,90" size="155,420" transparent="0" zPosition="3"/>
			<widget backgroundColor="#10444649" name="Active4" position="515,90" size="155,420" transparent="0" zPosition="3"/>
			<widget itemHeight="70" name="epg_list1" position="50,90" scrollbarMode="showOnDemand" size="155,420" transparent="1" zPosition="4"/>
			<widget itemHeight="70" name="epg_list2" position="205,90" scrollbarMode="showOnDemand" size="155,420" transparent="1" zPosition="4"/>
			<widget itemHeight="70" name="epg_list3" position="360,90" scrollbarMode="showOnDemand" size="155,420" transparent="1" zPosition="4"/>
			<widget itemHeight="70" name="epg_list4" position="515,90" scrollbarMode="showOnDemand" size="155,420" transparent="1" zPosition="4"/>
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/buttons.png" position="50,518" size="430,24"/>
			<widget backgroundColor="background" font="Regular;18" foregroundColor="#ffc000" position="490,518" render="Label" size="200,24" source="global.CurrentTime" transparent="1" valign="center" zPosition="3">	
				<convert type="ClockToText">Format:%H:%M  %a %d. %b</convert>
			</widget>
		</screen>"""

	def __init__(self, session, servicelist):
		Screen.__init__(self, session)
		self.session = session
		self.srvList = servicelist
		self.myServices = []
		self.myBqts = []
		self.list = []
		self.chCount = 0
		self.ActiveEPG = 1
		if getDesktop(0).size().width() == 1280:
			self.Fields = 6
			self["currCh5"] = Label(" ")
			self["Active5"] = Label(" ")
			self["epg_list5"] = MerlinEPGList(type = EPG_TYPE_SINGLE, selChangedCB = self.onSelectionChanged, timer = session.nav.RecordTimer)
		else:
			self.Fields = 5
		self.CheckForEPG = eTimer()
		self.CheckForEPG.callback.append(self.CheckItNow)
		self["prg_list"] = MenuList(self.getChannels())
		self["currCh1"] = Label(" ")
		self["currCh2"] = Label(" ")
		self["currCh3"] = Label(" ")
		self["currCh4"] = Label(" ")
		self["Active1"] = Label(" ")
		self["Active2"] = Label(" ")
		self["Active3"] = Label(" ")
		self["Active4"] = Label(" ")
		self["epg_list1"] = MerlinEPGList(type = EPG_TYPE_SINGLE, selChangedCB = self.onSelectionChanged, timer = session.nav.RecordTimer)
		self["epg_list2"] = MerlinEPGList(type = EPG_TYPE_SINGLE, selChangedCB = self.onSelectionChanged, timer = session.nav.RecordTimer)
		self["epg_list3"] = MerlinEPGList(type = EPG_TYPE_SINGLE, selChangedCB = self.onSelectionChanged, timer = session.nav.RecordTimer)
		self["epg_list4"] = MerlinEPGList(type = EPG_TYPE_SINGLE, selChangedCB = self.onSelectionChanged, timer = session.nav.RecordTimer)
		self["actions"] = ActionMap(["OkCancelActions", "EPGSelectActions", "DirectionActions", "ColorActions", "MenuActions", "NumberActions", "HelpActions"], {
						"ok": self.showEventInfo, 
						"cancel": self.close,
						"nextBouquet": self.AllUp,
						"prevBouquet": self.AllDown,
						"nextService": self.NextPage,
						"prevService": self.PrevPage,
						"right": self.right,
						"rightRepeated": self.right,
						"left": self.left,
						"leftRepeated": self.left,
						"up": self.up,
						"upRepeated": self.up,
						"down": self.down,
						"downRepeated": self.down,
						"info": self.showEventInfo,
						"red": self.ZapTo,
						"green": self.timerAdd,
						"blue": self.ZapForRefresh,
						"yellow": self.go2Primetime,
						"menu": self.menuClicked,
						"displayHelp": self.myhelp,
						"0": self.go2now,
						"1": self.go2first,
						"7": self.findPrvBqt,
						"9": self.findNextBqt
						},-2)
		self.onLayoutFinish.append(self.onLayoutReady)

	def getChannels(self):
		indx = 0
		serviceHandler = eServiceCenter.getInstance()
		services = serviceHandler.list(eServiceReference('1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 195) || (type == 25) FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
		bouquets = services and services.getContent("SN", True)
		for bouquet in bouquets:
			services = serviceHandler.list(eServiceReference(bouquet[0]))
			channels = services and services.getContent("SN", True)
			for channel in channels:
				if not channel[0].startswith("1:64:"):
					indx = indx + 1
					self.list.append(str(indx) + ". " + channel[1].replace('\xc2\x86', '').replace('\xc2\x87', ''))
					self.myServices.append(channel)
					self.myBqts.append(bouquet)
		self.chCount = indx - 1
		return self.list

	def onLayoutReady(self):
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if (info is not None) and not(config.plugins.MerlinPG.StartFirst.value):
			nameROH = info.getName().replace('\xc2\x86', '').replace('\xc2\x87', '')
			for idx in range(1, len(self.list)):
				name = str(idx) + ". " + nameROH
				if name == self.list[idx-1]:
					break
			self["prg_list"].moveToIndex(idx-1)
		else:
			self["prg_list"].moveToIndex(0)
		self.updateInfos()

	def updateInfos(self):
		self.displayActiveEPG()
		prgIndex = self["prg_list"].getSelectionIndex()
		CurrentPrg = self.myServices[prgIndex]
		self["currCh1"].setText(str(CurrentPrg[1]))
		l = self["epg_list1"]
		l.recalcEntrySize()
		myService = ServiceReference(CurrentPrg[0])
		l.fillSingleEPG(myService)
		prgIndex = prgIndex + 1
		if prgIndex < (self.chCount+1):
			self["epg_list2"].show()
			CurrentPrg = self.myServices[prgIndex]
			self["currCh2"].setText(str(CurrentPrg[1]))
			l = self["epg_list2"]
			l.recalcEntrySize()
			myService = ServiceReference(CurrentPrg[0])
			l.fillSingleEPG(myService)
		else:
			self["currCh2"].setText(str(" "))
			self["epg_list2"].hide()
		prgIndex = prgIndex + 1
		if prgIndex < (self.chCount+1):
			self["epg_list3"].show()
			CurrentPrg = self.myServices[prgIndex]
			self["currCh3"].setText(str(CurrentPrg[1]))
			l = self["epg_list3"]
			l.recalcEntrySize()
			myService = ServiceReference(CurrentPrg[0])
			l.fillSingleEPG(myService)
		else:
			self["currCh3"].setText(str(" "))
			self["epg_list3"].hide()
		prgIndex = prgIndex + 1
		if prgIndex < (self.chCount+1):
			self["epg_list4"].show()
			CurrentPrg = self.myServices[prgIndex]
			self["currCh4"].setText(str(CurrentPrg[1]))
			CurrentPrg = self.myServices[prgIndex]
			self["currCh4"].setText(str(CurrentPrg[1]))
			l = self["epg_list4"]
			l.recalcEntrySize()
			myService = ServiceReference(CurrentPrg[0])
			l.fillSingleEPG(myService)
		else:
			self["currCh4"].setText(str(" "))
			self["epg_list4"].hide()
		if self.Fields == 6:
			prgIndex = prgIndex + 1
			if prgIndex < (self.chCount+1):
				self["epg_list5"].show()
				CurrentPrg = self.myServices[prgIndex]
				self["currCh5"].setText(str(CurrentPrg[1]))
				l = self["epg_list5"]
				l.recalcEntrySize()
				myService = ServiceReference(CurrentPrg[0])
				l.fillSingleEPG(myService)
			else:
				self["currCh5"].setText(str(" "))
				self["epg_list5"].hide()

	def onSelectionChanged(self):
		pass

	def NextPage(self):
		self["prg_list"].pageDown()
		self.ActiveEPG = 1
		self.updateInfos()

	def PrevPage(self):
		self["prg_list"].pageUp()
		self.ActiveEPG = 1
		self.updateInfos()

	def displayActiveEPG(self):
		for xA in range(1,self.Fields):
			if xA == self.ActiveEPG:
				self["Active"+str(xA)].show()
			else:
				self["Active"+str(xA)].hide()

	def getActivePrg(self):
		return self["prg_list"].getSelectionIndex()+(self.ActiveEPG-1)

	def ZapTo(self):
		if self.getActivePrg() > self.chCount:
			return
		CurrentPrg = self.myServices[self.getActivePrg()]
		CurrentBqt = self.myBqts[self.getActivePrg()]
		myService = ServiceReference(CurrentPrg[0])
		myB = ServiceReference(CurrentBqt[0])
		self.srvList.clearPath()
		if self.srvList.bouquet_root != myB.ref:
			self.srvList.enterPath(self.srvList.bouquet_root)
		self.srvList.enterPath(myB.ref)
		self.srvList.setCurrentSelection(myService.ref)
		self.srvList.zap()
		self.close()

	def ZapForRefresh(self):
		if self.getActivePrg() > self.chCount:
			return
		CurrentPrg = self.myServices[self.getActivePrg()]
		myService = ServiceReference(CurrentPrg[0])
		self.session.nav.playService(myService.ref)
		self.CheckForEPG.start(4000, True)

	def CheckItNow(self):
		self.CheckForEPG.stop()
		CurrentPrg = self.myServices[self.getActivePrg()]
		l = self["epg_list"+str(self.ActiveEPG)]
		l.recalcEntrySize()
		myService = ServiceReference(CurrentPrg[0])
		l.fillSingleEPG(myService)

	def up(self):
		self["epg_list"+str(self.ActiveEPG)].moveUp()

	def down(self):
		self["epg_list"+str(self.ActiveEPG)].moveDown()

	def AllUp(self):
		for xU in range(1,self.Fields):
			self["epg_list"+str(xU)].moveUp()

	def AllDown(self):
		for xD in range(1,self.Fields):
			self["epg_list"+str(xD)].moveDown()

	def go2now(self):
		for xD in range(1,self.Fields):
			self["epg_list"+str(xD)].instance.moveSelection(self["epg_list"+str(xD)].instance.moveTop)

	def go2first(self):
		self["prg_list"].moveToIndex(0)
		self.ActiveEPG = 1
		self.updateInfos()

	def left(self):
		if self.ActiveEPG > 1:
			self.ActiveEPG = self.ActiveEPG - 1
			self.displayActiveEPG()
		else:
			self["prg_list"].pageUp()
			self.ActiveEPG = (self.Fields-1)
			self.updateInfos()

	def right(self):
		if self.ActiveEPG < (self.Fields-1):
			self.ActiveEPG = self.ActiveEPG + 1
			self.displayActiveEPG()
		else:
			self.NextPage()

	def showEventInfo(self):
		curEV = self["epg_list"+str(self.ActiveEPG)].getCurrent()
		event = curEV[0]
		service = curEV[1]
		if event is not None:
			self.session.open(EventViewSimple, event, service)

	def timerAdd(self):
		cur = self["epg_list"+str(self.ActiveEPG)].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				cb_func = lambda ret : not ret or self.removeTimer(timer)
				self.session.openWithCallback(cb_func, MessageBox, _("Do you really want to delete %s?") % event.getEventName())
				break
		else:
			newEntry = RecordTimerEntry(serviceref, checkOldTimers = True, *parseEvent(event))
			self.session.openWithCallback(self.finishedAdd, TimerEntry, newEntry)

	def removeTimer(self, timer):
		timer.afterEvent = AFTEREVENT.NONE
		self.session.nav.RecordTimer.removeEntry(timer)

	def finishedAdd(self, answer):
		if answer[0]:
			entry = answer[1]
			simulTimerList = self.session.nav.RecordTimer.record(entry)
			if simulTimerList is not None:
				for x in simulTimerList:
					if x.setAutoincreaseEnd(entry):
						self.session.nav.RecordTimer.timeChanged(x)
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList is not None:
					self.session.openWithCallback(self.finishSanityCorrection, TimerSanityConflict, simulTimerList)
	
	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def menuClicked(self):
		self.session.open(MerlinPGsetup)

	def findNextBqt(self):
		CurrIdx = 0
		CurrBqt = self.myBqts[self.getActivePrg()]
		for CurrIdx in range(self.getActivePrg(),self.chCount):
			NewBqt = self.myBqts[CurrIdx]
			if NewBqt != CurrBqt:
				break
		self["prg_list"].moveToIndex(CurrIdx)
		self.updateInfos()

	def findPrvBqt(self):
		CurrIdx = 0
		CurrBqt = self.myBqts[self.getActivePrg()]
		for CurrIdx in range(self.getActivePrg(),-1,-1):
			NewBqt = self.myBqts[CurrIdx]
			if NewBqt != CurrBqt:
				break
		self["prg_list"].moveToIndex(CurrIdx)
		self.updateInfos()

	def go2Primetime(self):
		for xFL in range(1, self.Fields):
			self["epg_list"+str(xFL)].instance.moveSelection(self["epg_list"+str(xFL)].instance.moveTop)
			for i in range(0,(self.Fields*3)):
				self["epg_list"+str(xFL)].foudPrimetime()

	def myhelp(self):
		self.session.open(ShowMe, "/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/help.jpg")



class Merlin_PGd(Screen):
	try:
		sz_w = getDesktop(0).size().width()
	except:
		sz_w = 720
	if sz_w == 1280:
		skin = """
		<screen backgroundColor="#ffffffff" flags="wfNoBorder" name="Merlin_PG" position="0,0" size="1280,720" title="Merlin Program Guide">
			<widget backgroundColor="#ffffffff" position="0,0" render="Pig" size="520,292" source="session.VideoPicture" zPosition="-1"/>
			<eLabel backgroundColor="#00111112" position="0,292" size="520,450" zPosition="1"/>
			<eLabel backgroundColor="#00111112" position="520,0" size="760,720" zPosition="1"/>
			<ePixmap alphatest="on" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/epg.png" position="1136,105" size="85,77" zPosition="5"/>
			<ePixmap alphatest="on" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/channels.png" position="395,306" size="80,80" zPosition="5"/>
			<ePixmap alphatest="on" name="red" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/red.png" position="70,635" size="35,25" zPosition="2"/>
			<ePixmap alphatest="on" name="green" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/green.png" position="275,635" size="35,25" zPosition="2"/>
			<eLabel backgroundColor="#00111112" font="Regular;18" position="110,635" size="131,24" text="ZAP" transparent="1" zPosition="2"/>
			<eLabel backgroundColor="#00111112" font="Regular;18" position="315,635" size="191,24" text="TIMERS" transparent="1" zPosition="2"/>
			<widget itemHeight="25" name="prg_list" position="75,306" scrollbarMode="showNever" size="400,300" transparent="1" zPosition="4"/>
			<widget itemHeight="27" name="epg_list" position="570,105" scrollbarMode="showNever" size="651,540" transparent="1" zPosition="4"/>
			<widget backgroundColor="#00111112" font="Regular;22" foregroundColor="#fcc000" halign="center" name="currCh" position="555,55" size="651,24" transparent="1" valign="center" zPosition="2"/>
		</screen>"""
	elif sz_w == 1024:
		skin = """
		<screen backgroundColor="#ffffffff" flags="wfNoBorder" name="Merlin_PG" position="0,0" size="1024,576" title="Merlin Program Guide">
			<widget backgroundColor="#ffffffff" position="0,0" render="Pig" size="384,216" source="session.VideoPicture" zPosition="-1"/>
			<eLabel backgroundColor="#00111112" position="0,216" size="384,366" zPosition="1"/>
			<eLabel backgroundColor="#00111112" position="384,0" size="720,576" zPosition="1"/>
			<ePixmap alphatest="on" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/epg.png" position="900,80" size="85,77" zPosition="5"/>
			<ePixmap alphatest="on" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/channels.png" position="292,228" size="80,80" zPosition="5"/>
			<ePixmap alphatest="on" name="red" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/red.png" position="40,520" size="35,25" zPosition="3"/>
			<ePixmap alphatest="on" name="green" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/green.png" position="185,520" size="35,25" zPosition="3"/>
			<eLabel backgroundColor="#00111112" font="Regular;18" position="80,520" size="92,24" text="ZAP" transparent="1" zPosition="2"/>
			<eLabel backgroundColor="#00111112" font="Regular;18" position="230,520" size="141,24" text="TIMERS" transparent="1" zPosition="2"/>
			<widget itemHeight="25" name="prg_list" position="40,228" scrollbarMode="showNever" size="332,275" transparent="1" zPosition="4"/>
			<widget itemHeight="28" name="epg_list" position="395,80" scrollbarMode="showNever" size="590,448" transparent="1" zPosition="4"/>
			<widget backgroundColor="#00111112" font="Regular;21" foregroundColor="#fcc000" halign="center" name="currCh" position="395,40" size="590,24" transparent="1" valign="center" zPosition="4"/>
		</screen>"""
	else:
		skin = """
		<screen flags="wfNoBorder" name="Merlin_PG" position="0,0" size="720,576" title="Merlin Program Guide">
			<ePixmap alphatest="on" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/mpgbgSD-fs8.png" position="0,0" size="720,576" zPosition="1"/>
			<ePixmap alphatest="on" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/red.png" position="165,90" size="35,25" zPosition="2"/>
			<ePixmap alphatest="on" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/green.png" position="165,110" size="35,25" zPosition="2"/>
			<eLabel backgroundColor="#1f1f1f" font="Regular;15" foregroundColor="#f0f0f0" position="205,93" size="70,20" text="ZAP" transparent="1" zPosition="2"/>
			<eLabel backgroundColor="#1f1f1f" font="Regular;15" foregroundColor="#f0f0f0" position="205,113" size="70,20" text="TIMERS" transparent="1" zPosition="2"/>
			<widget name="prg_list" position="342,63" scrollbarMode="showOnDemand" size="327,150" zPosition="2" itemHeight="25"/>
			<widget name="epg_list" position="57,238" scrollbarMode="showOnDemand" size="612,270" zPosition="2" itemHeight="27"/>
			<widget font="Regular;22" foregroundColor="#ffc000" halign="center" name="currCh" position="57,133" size="252,66" transparent="1" valign="center" zPosition="2"/>
			<widget font="LCD;28" halign="left" position="60,95" render="Label" size="91,32" source="global.CurrentTime" transparent="1" zPosition="3">
				<convert type="ClockToText">Default</convert>
			</widget>	
			<widget font="Regular;16" position="60,65" render="Label" size="276,26" source="global.CurrentTime" transparent="1" zPosition="3">
				<convert type="ClockToText">Date</convert>
			</widget>
		</screen>"""

	def __init__(self, session, servicelist):
		Screen.__init__(self, session)
		self.session = session
		self.myServices = []
		self.myBqts = []
		self.list = []
		self.srvList = servicelist
		self.CheckForEPG = eTimer()
		self.CheckForEPG.callback.append(self.CheckItNow)
		self["currCh"] = Label(_("Channel"))
		self["prg_list"] = MenuList(self.getChannels())
		self["epg_list"] = EPGList(type = EPG_TYPE_SINGLE, selChangedCB = self.onSelectionChanged, timer = session.nav.RecordTimer)
		self["actions"] = ActionMap(["OkCancelActions", "EPGSelectActions", "ColorActions", "MenuActions", "HelpActions"], {
									"ok": self.ok, 
									"cancel": self.close,
									"nextBouquet": self.prgDown,
									"prevBouquet": self.prgUp,
									"nextService": self.prgPlus,
									"prevService": self.prgMinus,
									"red": self.ZapTo,
									"green": self.timerAdd,
									"blue": self.ZapForRefresh,
									"yellow": self.go2now,
									"info": self.ok,
									"menu": self.menuClicked,
									"displayHelp": self.myhelp
									},-2)
		self.onLayoutFinish.append(self.onLayoutReady)

	def onLayoutReady(self):
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if (info is not None) and not(config.plugins.MerlinPG.StartFirst.value):
			nameROH = info.getName().replace('\xc2\x86', '').replace('\xc2\x87', '')
			for idx in range(1, len(self.list)):
				name = str(idx) + ". " + nameROH
				if name == self.list[idx-1]:
					break
			self["prg_list"].moveToIndex(idx-1)
		else:
			self["prg_list"].moveToIndex(0)
		self.updateInfos()

	def onSelectionChanged(self):
		pass

	def prgUp(self):
		self["prg_list"].down()
		self.updateInfos()
	
	def prgDown(self):
		self["prg_list"].up()
		self.updateInfos()

	def prgPlus(self):
		self["prg_list"].pageDown()
		self.updateInfos()

	def prgMinus(self):
		self["prg_list"].pageUp()
		self.updateInfos()

	def getChannels(self):
		indx = 0
		serviceHandler = eServiceCenter.getInstance()
		services = serviceHandler.list(eServiceReference('1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 195) || (type == 25) FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
		bouquets = services and services.getContent("SN", True)
		for bouquet in bouquets:
			services = serviceHandler.list(eServiceReference(bouquet[0]))
			channels = services and services.getContent("SN", True)
			for channel in channels:
				if not channel[0].startswith("1:64:"):
					indx = indx + 1
					self.list.append(str(indx) + ". " + channel[1].replace('\xc2\x86', '').replace('\xc2\x87', ''))
					self.myServices.append(channel)
					self.myBqts.append(bouquet)
		return self.list

	def updateInfos(self):
		l = self["epg_list"]
		l.recalcEntrySize()
		CurrentPrg = self.myServices[self["prg_list"].getSelectionIndex()]
		self["currCh"].setText(str(CurrentPrg[1]))
		myService = ServiceReference(CurrentPrg[0])
		l.fillSingleEPG(myService)

	def ok(self):
		curEV = self["epg_list"].getCurrent()
		event = curEV[0]
		service = curEV[1]
		if event is not None:
			self.session.open(EventViewSimple, event, service)
			
	def ZapTo(self):
		CurrentPrg = self.myServices[self["prg_list"].getSelectionIndex()]
		CurrentBqt = self.myBqts[self["prg_list"].getSelectionIndex()]
		myService = ServiceReference(CurrentPrg[0])
		myB = ServiceReference(CurrentBqt[0])
		self.srvList.clearPath()
		if self.srvList.bouquet_root != myB.ref:
			self.srvList.enterPath(self.srvList.bouquet_root)
		self.srvList.enterPath(myB.ref)
		self.srvList.setCurrentSelection(myService.ref)
		self.srvList.zap()
		self.close()

	def ZapForRefresh(self):
		CurrentPrg = self.myServices[self["prg_list"].getSelectionIndex()]
		myService = ServiceReference(CurrentPrg[0])
		self.session.nav.playService(myService.ref)
		self.CheckForEPG.start(4000, True)

	def CheckItNow(self):
		self.CheckForEPG.stop()
		self.updateInfos()

	def timerAdd(self):
		cur = self["epg_list"].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				cb_func = lambda ret : not ret or self.removeTimer(timer)
				self.session.openWithCallback(cb_func, MessageBox, _("Do you really want to delete %s?") % event.getEventName())
				break
		else:
			newEntry = RecordTimerEntry(serviceref, checkOldTimers = True, *parseEvent(event))
			self.session.openWithCallback(self.finishedAdd, TimerEntry, newEntry)

	def removeTimer(self, timer):
		timer.afterEvent = AFTEREVENT.NONE
		self.session.nav.RecordTimer.removeEntry(timer)

	def finishedAdd(self, answer):
		if answer[0]:
			entry = answer[1]
			simulTimerList = self.session.nav.RecordTimer.record(entry)
			if simulTimerList is not None:
				for x in simulTimerList:
					if x.setAutoincreaseEnd(entry):
						self.session.nav.RecordTimer.timeChanged(x)
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList is not None:
					self.session.openWithCallback(self.finishSanityCorrection, TimerSanityConflict, simulTimerList)

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def menuClicked(self):
		self.session.open(MerlinPGsetup)

	def go2now(self):
		self["epg_list"].instance.moveSelection(self["epg_list"].instance.moveTop)

	def myhelp(self):
		self.session.open(ShowMe, "/usr/lib/enigma2/python/Plugins/Extensions/Merlin_PG/help.jpg")






