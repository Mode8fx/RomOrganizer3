from os import path, mkdir, listdir, remove, walk, rename, rmdir
import re
import xml.etree.ElementTree as ET
import zipfile
import numpy
import shutil
from pathlib import Path as plpath
from math import ceil
from time import sleep
from tkinter import filedialog
from tkinter import *
from gatelib import *
from filehash import FileHash
import configparser
from dateutil.parser import parse as dateParse

progFolder = getCurrFolder()
sys.path.append(progFolder)
crcHasher = FileHash('crc32')

mainConfigFile = path.join(progFolder, "settings.ini")

updateFromDeviceFolder = path.join(progFolder, "Copied From Device")
noIntroDir = path.join(progFolder, "No-Intro Database")
redumpDir = path.join(progFolder, "Redump Database")
profilesFolder = path.join(progFolder, "Device Profiles")
logFolder = path.join(progFolder, "Logs")

categoryValues = {
	"Games" : 0,
	"Demos" : 1,
	"Bonus Discs" : 2,
	"Applications" : 3,
	"Coverdiscs" : 4
}

hiddenKeywords = ["Rev", "Disc", "Beta", "Demo", "Sample", "Proto", "Alt", "Earlier", "Download Station"]

########
# MAIN #
########

def main():
	prepareMainConfig()
	createDir(noIntroDir)
	createDir(redumpDir)
	createDir(profilesFolder)
	createDir(logFolder)
	while True:
		initScreen()
		choice = makeChoice("Select an option.", ["Update/audit main romsets", "Create new device profile", "Set main ROM folder", "Set secondary ROM folder", "Export romset", "Help", "Exit"])
		if choice == 1:
			updateAndAuditMainRomsets()
		elif choice == 2:
			createDeviceProfile()
		elif choice == 3:
			setMainRomFolder()
		elif choice == 4:
			setSecondaryRomFolder()
		elif choice == 5:
			exportRomsets()
		elif choice == 6:
			printHelp()
		else:
			clearScreen()
			sys.exit()

####################
# UPDATE AND AUDIT #
####################

def updateAndAuditMainRomsets():
	currRomsetFolder = askForDirectory("Select the ROM directory you would like to update/audit.\nThis is the directory that contains all of your system folders.")
	sleep(1)
	if currRomsetFolder == "":
		print("Action cancelled.")
		sleep(1)
		return
	for currSystemName in listdir(currRomsetFolder):
		print("\n"+currSystemName)
		currSystemFolder = path.join(currRomsetFolder, currSystemName)
		if not path.isdir(currSystemFolder):
			continue
		currSystemDAT = path.join(noIntroDir, currSystemName+".dat")
		if not path.exists(currSystemDAT):
			print("Database file not found for "+currSystemDAT)
			continue
		tree = ET.parse(currSystemDAT)
		root = tree.getroot()
		allGameFields = root[1:]
		allGameNamesInDAT = {}
		for game in allGameFields:
			allGameNamesInDAT[game.get("name")] = False
		romsWithoutCRC = []
		for file in listdir(currSystemFolder):
			finalState = 0 # 0 = 
			currFilePath = path.join(currSystemFolder, file)
			currFileName = path.splitext(file)[0]
			if not path.isfile(currFilePath):
				continue
			if zipfile.is_zipfile(currFilePath):
				with zipfile.ZipFile(currFilePath, 'r', zipfile.ZIP_DEFLATED) as zippedFile:
					if len(zippedFile.namelist()) > 1:
						print("\n"+file+" archive contains more than one file. Skipping.")
						continue
					fileInfo = zippedFile.infolist()[0]
					# currZippedFile = fileInfo.filename
					currFileCRC = format(fileInfo.CRC & 0xFFFFFFFF, '08x').upper() # crc32
			else:
				# currZippedFile = None
				currFileCRC = crcHasher.hash_file(currFilePath).upper()
			foundMatch = False
			for game in allGameFields:
				currDBGameCRC = game.find("rom").get("crc").upper()
				if currDBGameCRC == currFileCRC:
					currDBGameName = game.get("name")
					allGameNamesInDAT[currDBGameName] = True
					if currFileName != currDBGameName:
						currFileExt = path.splitext(currFilePath)[1]
						if path.exists(path.join(currSystemFolder, currDBGameName+currFileExt)): # two of the same file (with different names) exist
							i = 1
							while True:
								incrementedGameName = currDBGameName+" (copy) ("+str(i)+")"
								if not path.exists(path.join(currSystemFolder, incrementedGameName+currFileExt)):
									break
								i += 1
							print("Warning: Multiple copies of the same rom may exist ("+currDBGameName+").")
							currDBGameName = incrementedGameName
						if zipfile.is_zipfile(currFilePath):
							renameArchiveAndContent(currFilePath, currDBGameName)
						else:
							rename(currFilePath, path.join(currSystemFolder, currDBGameName+currFileExt))
							print("Renamed "+currFileName+" to "+currDBGameName)
					foundMatch = True
					break
			if not foundMatch:
				romsWithoutCRC.append(currFileName+" ("+file+")")
		xmlRomsInSet = [key for key in allGameNamesInDAT.keys() if allGameNamesInDAT[key] == True]
		xmlRomsNotInSet = [key for key in allGameNamesInDAT.keys() if allGameNamesInDAT[key] == False]
		createSystemAuditLog(xmlRomsInSet, xmlRomsNotInSet, romsWithoutCRC, currSystemName)
		numNoCRC = len(romsWithoutCRC)
		if numNoCRC > 0:
			print("Warning: "+str(numNoCRC)+pluralize(" file", numNoCRC)+" in this system folder "+pluralize("do", numNoCRC, "es", "")+" not have a matching database entry.")
			print(pluralize("", numNoCRC, "This file", "These files")+" will be ignored when exporting this system's romset to another")
			print("device.")

	inputHidden("\nDone. Press Enter to continue.")

def createSystemAuditLog(xmlRomsInSet, xmlRomsNotInSet, romsWithoutCRC, currSystemName):
	xmlRomsInSet.sort()
	xmlRomsNotInSet.sort()
	romsWithoutCRC.sort()

	numOverlap = len(xmlRomsInSet)
	numNotInSet = len(xmlRomsNotInSet)
	numNoCRC = len(romsWithoutCRC)
	auditLogFile = open(path.join(logFolder, "Audit ("+currSystemName+") ["+str(numOverlap)+" out of "+str(numOverlap+numNotInSet)+"].txt"), "w", encoding="utf-8", errors="replace")
	auditLogFile.writelines("=== "+currSystemName+" ===\n")
	auditLogFile.writelines("=== This romset contains "+str(numOverlap)+" of "+str(numOverlap+numNotInSet)+" known ROMs ===\n\n")
	if numOverlap > 0:
		auditLogFile.writelines("= CONTAINS =\n")
		for rom in xmlRomsInSet:
			auditLogFile.writelines(rom+"\n")
	if numNotInSet > 0:
		auditLogFile.writelines("\n= MISSING =\n")
		for rom in xmlRomsNotInSet:
			auditLogFile.writelines(rom+"\n")
	if numNoCRC > 0:
		auditLogFile.writelines("\n=== This romset contains "+str(numNoCRC)+pluralize(" file", numNoCRC)+" with no known database match ===\n\n")
		for rom in romsWithoutCRC:
			auditLogFile.writelines(rom+"\n")
	auditLogFile.close()

def renameArchiveAndContent(currArchivePath, newName):
	with zipfile.ZipFile(currArchivePath, 'r', zipfile.ZIP_DEFLATED) as zippedFile:
		zippedFiles = zippedFile.namelist()
		if len(zippedFiles) > 1:
			print("\nThis archive contains more than one file. Skipping.")
			return
		fileExt = path.splitext(zippedFiles[0])[1]
		archiveExt = path.splitext(currArchivePath)[1]
		zippedFile.extract(zippedFiles[0], path.dirname(currArchivePath))
		currExtractedFilePath = path.join(path.dirname(currArchivePath), zippedFiles[0])
		newArchivePath = path.join(path.dirname(currArchivePath), newName+archiveExt)
		newExtractedFilePath = path.splitext(newArchivePath)[0]+fileExt
		rename(currExtractedFilePath, newExtractedFilePath)
	remove(currArchivePath)
	with zipfile.ZipFile(newArchivePath, 'w', zipfile.ZIP_DEFLATED) as newZip:
		newZip.write(newExtractedFilePath, arcname='\\'+newName+fileExt)
	remove(newExtractedFilePath)
	print("Renamed "+path.splitext(path.basename(currArchivePath))[0]+" to "+newName+"\n")

############################
# CONFIG / DEVICE PROFILES #
############################

def prepareMainConfig():
	global mainConfig, mainRomFolder, secondaryRomFolder, mainSystemDirs, secondarySystemDirs
	# global regions, specialFolders, specialAttributes, ignoredFolders, primaryRegions, doNotCopyFromDevice
	if not path.exists(mainConfigFile):
		createMainConfig()
	mainConfig = configparser.ConfigParser(allow_no_value=True)
	mainConfig.optionxform = str
	mainConfig.read(mainConfigFile)
	mainRomFolder = mainConfig["ROM Folders"]["Main ROM Folder"]
	secondaryRomFolder = mainConfig["ROM Folders"]["Secondary ROM Folder"]
	# regions = [key for key in mainConfig["Regions"]]
	# specialFolders = mainConfig["Special Folders"].split("|")
	# specialAttributes = hiddenKeywords + mainConfig["Special ROM Attributes (Advanced)"]["Keywords"].split("|") + mainConfig["Special ROM Attributes (Advanced)"]["Sources"].split("|")
	# ignoredFolders = deviceConfig["Special Categories"]["Ignored Folders"].split("|")
	# primaryRegions = deviceConfig["Special Categories"]["Primary Regions"].split("|")
	# doNotCopyFromDevice = deviceConfig["Special Categories"]["Do Not Copy From Device"].split("|")
	try:
		mainSystemDirs = [d for d in listdir(mainRomFolder) if path.isdir(path.join(mainRomFolder, d))]
	except:
		mainSystemDirs = []
	try:
		secondarySystemDirs = [d for d in listdir(secondaryRomFolder) if path.isdir(path.join(secondaryRomFolder, d))]
	except:
		secondarySystemDirs = []

def createMainConfig():
	global mainConfig
	mainConfig = configparser.ConfigParser(allow_no_value=True)
	mainConfig.optionxform = str
	# ROM Folders
	mainConfig["ROM Folders"] = {}
	mainConfig.set('ROM Folders', '# The directory of the main ROM folder you want to export from, which contains system folders that contain No-Intro verified ROMs. If you leave this blank, the program will ask for this folder when you try to export romsets.')
	mainConfig["ROM Folders"]["Main ROM Folder"] = ""
	mainConfig.set('ROM Folders', '# The directory of the secondary ROM folder you want to export from, which contains system folders that can contain unverified ROMs/other files (this is intended for rom hacks, homebrew, etc). If you leave this blank, the program will ask for this folder when you try to export the secondary folder.')
	mainConfig["ROM Folders"]["Secondary ROM Folder"] = ""
	# Regions
	mainConfig["Regions"] = {}
	mainConfig.set('Regions', '# The region folder for each ROM is determined by its region/language tag as listed below.')
	mainConfig.set('Regions', '# For example, any ROM with (World), (USA), or (U) in its name will be exported to a [USA] folder')
	mainConfig.set('Regions', '# Additionally, you may set at least one region as primary (see device profiles). Primary regions do not have a subfolder, and are instead exported to the system\'s root folder.')
	mainConfig.set('Regions', '# Regions are listed in order of descending priority, so (to use the default example) if a ROM has both the USA and Fr tags, it will be considered a [USA] ROM. If you want to prioritize Europe over USA, simply move the Europe category above the USA category. You may also create your own region categories.')
	mainConfig.set('Regions', '# Finally, the category with :DEFAULT: (Other (non-English)) is the fallback in the event that a ROM doesn\'t belong in any of the preceding regions. Keep it as the last possible region tag.')
	mainConfig["Regions"]["Test Program"] = "|".join([
		"Test Program"
		])
	mainConfig["Regions"]["USA"] = "|".join([
		"World", "U", "USA"
		])
	mainConfig["Regions"]["Europe"] = "|".join([
		"E", "Europe"
		])
	mainConfig["Regions"]["Other (English)"] = "|".join([
		"En", "A", "Australia", "Ca", "Canada"
		])
	mainConfig["Regions"]["Japan"] = "|".join([
		"J", "Japan", "Ja"
		])
	mainConfig["Regions"]["Other (non-English)"] = "|".join([
		"F", "France", "Fr", "G", "Germany", "De", "S", "Spain", "Es", "I", "Italy",
		"It", "No", "Norway", "Br", "Brazil", "Sw", "Sweden", "Cn", "China", "Zh", "K",
		"Korea", "Ko", "As", "Asia", "Ne", "Netherlands", "Ru", "Russia", "Da",
		"Denmark", "Nl", "Pt", "Sv", "No", "Da", "Fi", "Pl", ":DEFAULT:"
	])
	# Special Folders
	mainConfig["Special Folders"] = {}
	mainConfig.set('Special Folders', '# Special Folders are folders that are created on your device upon export for verified ROMs with filesnames that start with certain strings.')
	mainConfig.set('Special Folders', '# For example, any ROM whose name starts with \"2 Games in 1 - \" will be exported to a subfolder called \"Compilation\".')
	mainConfig.set('Special Folders', '# You could then choose to ignore any ROMs marked as \"Compilation\" when exporting to a specific device (see device profiles).')
	mainConfig.set('Special Folders', '# Feel free to add additional Special Folders (or add to existing folders) using the format below (with \"|\" as a delimiter).')
	mainConfig.set('Special Folders', '# Special Folders are created in order of descending priority, so (to use the default example) if a ROM is in both \"Compilation\" and \"GBA Video\", it will be added to the folder \"SYSTEM/REGION/Compilation/GBA Video/GAME\".')
	mainConfig["Special Folders"]["Compilation"] = "|".join([
		"2 Games in 1 -", "2 Games in 1! -", "2 Disney Games -", "2-in-1 Fun Pack -",
		"2 Great Games! -", "2 in 1 -", "2 in 1 Game Pack -", "2 Jeux en 1",
		"3 Games in 1 -", "4 Games on One Game Pak", "Double Game!",
		"Castlevania Double Pack", "Combo Pack - ", "Crash Superpack",
		"Spyro Superpack", "Crash & Spyro Superpack", "Crash & Spyro Super Pack",
		"Double Pack"
		])
	mainConfig["Special Folders"]["GBA Video"] = "Game Boy Advance Video"
	mainConfig["Special Folders"]["NES & Famicom"] = "|".join([
		"Classic NES Series", "Famicom Mini", "Hudson Best Collection"
		])
	mainConfig["Special Folders"]["BIOS"] = "|".join([
		"[BIOS]"
		])
	# Special ROM Attributes
	mainConfig["Special ROM Attributes (Advanced)"] = {}
	mainConfig.set('Special ROM Attributes (Advanced)', '# Special ROM Attributes are substrings in verified ROM names (specifically, the parentheses fields in these names) that are ignored when trying to determine the best name for a game.')
	mainConfig.set('Special ROM Attributes (Advanced)', '# \"Sources\" are also used in determining the best ROM for 1G1R sets (they are given lower priority).')
	mainConfig["Special ROM Attributes (Advanced)"]["Keywords"] = "|".join([
		"Unl", "Pirate", "PAL", "NTSC", "GB Compatible", "SGB Enhanced",
		"Club Nintendo", "Aftermarket", "Test Program", "Competition Cart",
		"NES Test", "Promotion Card", "Program", "Manual"
		])
	mainConfig["Special ROM Attributes (Advanced)"]["Sources"] = "|".join([
		"Virtual Console", "Switch Online", "GameCube", "Namcot Collection",
		"Namco Museum Archives", "Kiosk", "iQue", "Sega Channel", "WiiWare",
		"DLC", "Minis", "Promo", "Nintendo Channel", "Nintendo Channel, Alt",
		"DS Broadcast", "Wii Broadcast", "DS Download Station", "Dwnld Sttn"
		])
	with open(mainConfigFile, 'w') as mcf:
		mainConfig.write(mcf)
	print("Created new settings.ini")
	inputHidden("Press Enter to continue.")

def selectDeviceProfile():
	global deviceName, deviceConfig
	initScreen()
	deviceProfiles = [prof for prof in listdir(profilesFolder) if path.splitext(prof)[1]== ".ini"]
	if len(deviceProfiles) > 0:
		dp = makeChoice("\nSelect a device profile (which device are you copying to?)", [path.splitext(prof)[0] for prof in deviceProfiles]+["Create new profile", "Back to menu"])
		if dp == len(deviceProfiles)+1:
			createDeviceProfile()
			return False
		elif dp == len(deviceProfiles)+2:
			return False
		else:
			dn = deviceProfiles[dp-1]
			deviceName = path.splitext(dn)[0]
			deviceConfig = path.join(profilesFolder, dn)
			deviceConfig = configparser.ConfigParser(allow_no_value=True)
			deviceConfig.optionxform = str
			deviceConfigFile = path.join(profilesFolder, deviceName+".ini")
			deviceConfig.read(deviceConfigFile)
			return True
	else:
		print("\nNo device profiles found. Go back to the main menu and select \"Create new device profile\".")
		inputHidden("Press Enter to continue.")
		return False

def createDeviceProfile():
	initScreen()
	if not verifyMainRomFolder():
		return
	print("\nFollow these steps to create a new device profile.")
	skipSecondary = False
	if secondaryRomFolder == "":
		choice = makeChoice("Are you using a secondary rom folder containing unverified roms such as hacks, homebrew, etc.?", ["Yes, I have a secondary folder", "No, verified roms only"])
		if choice == 1:
			print("Go back to the main menu and select \"Set secondary ROM folder\".")
			inputHidden("Press Enter to continue.")
			return
		else:
			skipSecondary = True
	# Device Name
	deviceName = ""
	while deviceName == "":
		print("\n(1/5) What would you like to name this profile?")
		deviceName = input().strip()

	deviceConfig = configparser.ConfigParser(allow_no_value=True)
	deviceConfig.optionxform = str
	deviceConfigFile = path.join(profilesFolder, deviceName+".ini")
	# Main Romsets
	deviceConfig["Main Romsets"] = {}

	print("\n(2/5) Please define how each romset should be copied to this device.")
	for currSystemName in mainSystemDirs:
		copyType = makeChoice(currSystemName, ["Full (copy all contents)",
			"1G1R (copy only the most significant rom for each game)",
			"1G1R Primary (same as 1G1R, but ignore games that do not have a rom for a primary region (explained in question 4)",
			"None (skip this system)"])
		if copyType == 1:
			deviceConfig["Main Romsets"][currSystemName] = "Full"
		elif copyType == 2:
			deviceConfig["Main Romsets"][currSystemName] = "1G1R"
		elif copyType == 3:
			deviceConfig["Main Romsets"][currSystemName] = "1G1R Primary"
	# Secondary Romsets
	deviceConfig["Secondary Romsets"] = {}
	if not skipSecondary:
		print("\nPlease define whether or not each folder in the secondary rom folder should be copied to this device.")
		for currSystemName in secondarySystemDirs:
			copyType = makeChoice(currSystemName, ["Yes", "No"])
			if copyType == 1:
				deviceConfig["Secondary Romsets"][currSystemName] = "Yes"
	# Special Categories
	deviceConfig["Special Categories"] = {}

	print("\n(3/5) Please type the names of any Special Folders or Regions you would like to skip in copying.")
	print("Use \"|\" as a divider.")
	print("For example, to skip all roms that are either Japan or Compilation, type the following: Japan|Compilation")
	print("According to your settings.ini file, possible Special Folders and Regions are:")
	print(", ".join(["\""+entry+"\"" for entry in list(specialFolders.keys())+list(regions.keys())]))
	currInput = input().strip()
	currInputParsed = [val.strip() for val in currInput.split("|")]
	deviceConfig["Special Categories"]["Ignored Folders"] = "|".join(currInputParsed)

	print("\n(4/5) Please type the names of any Primary Regions.")
	print("These folders will not be created in romset organization; instead, their contents are added to the root folder of the current system.")
	print("Use \"|\" as a divider.")
	print("For example, if you wanted all USA and Europe roms in the root folder instead of [USA] and [Europe] subfolders, you would type the following: USA|Europe")
	print("According to your settings.ini file, possible Regions are:")
	print(", ".join(["\""+entry+"\"" for entry in list(regions.keys())]))
	currInput = input().strip()
	currInputParsed = [val.strip() for val in currInput.split("|")]
	deviceConfig["Special Categories"]["Primary Regions"] = "|".join(currInputParsed)

	print("\n(5/5) When exporting, you have the option to copy contents that exist in this device's rom folder, but not in the main rom folder, into a \"Copied From Device\" folder.")
	print("This is useful for keeping your devices in parity with each other.")
	print("Please type the exact names of any folders in your device's rom folder that you do not want to copy to this folder.")
	print("These folders will be skipped; this is useful if you keep roms and non-rom PC games in the same folder.")
	print("Use \"|\" as a divider.")
	print("For example, if you wanted to ignore anything in the \"Steam\" folder, you would type the following: Steam")
	print("Common recommended subfolders are Steam, Windows, and PC Games")
	currInput = input().strip()
	currInputParsed = [val.strip() for val in currInput.split("|")]
	deviceConfig["Special Categories"]["Do Not Copy From Device"] = "|".join(currInputParsed)

	with open(deviceConfigFile, 'w') as dcf:
		deviceConfig.write(dcf)
	print("Created new profile for "+deviceName+".")
	inputHidden("Press Enter to continue.")

##########################
# SET/VERIFY ROM FOLDERS #
##########################

def setMainRomFolder():
	global mainConfig, mainSystemDirs, mainRomFolder
	initScreen()
	newMainRomFolder = askForDirectory("Select a main ROM folder. This directory should contain system folders, which contain No-Intro verified ROMs.")
	if newMainRomFolder == "":
		print("Action cancelled.")
		sleep(1)
		return
	mainConfig.read(mainConfigFile)
	mainConfig["ROM Folders"]["Main ROM Folder"] = newMainRomFolder
	mainRomFolder = newMainRomFolder
	with open(mainConfigFile, 'w') as mcf:
		mainConfig.write(mcf)
	mainSystemDirs = [d for d in listdir(mainRomFolder) if path.isdir(path.join(mainRomFolder, d))]

def setSecondaryRomFolder():
	global mainConfig, secondarySystemDirs, secondaryRomFolder
	initScreen()
	newSecondaryRomFolder = askForDirectory("Select a secondary ROM folder. This directory should contain system folders, which can contain unverified ROMS/other files (rom hacks, homebrew, etc).")
	if newSecondaryRomFolder == "":
		print("Action cancelled.")
		sleep(1)
		return
	mainConfig.read(mainConfigFile)
	mainConfig["ROM Folders"]["Secondary ROM Folder"] = newSecondaryRomFolder
	secondaryRomFolder = newSecondaryRomFolder
	with open(mainConfigFile, 'w') as mcf:
		mainConfig.write(mcf)
	secondarySystemDirs = [d for d in listdir(secondaryRomFolder) if path.isdir(path.join(secondaryRomFolder, d))]

def verifyMainRomFolder():
	if mainRomFolder == "":
		print("You have not set a main ROM folder. Go back to the main menu and select \"Set main ROM folder\".")
		inputHidden("Press Enter to continue.")
		return False
	if not path.isdir(mainRomFolder):
		print("The main ROM folder found in settings.ini is invalid. Go back to the main menu and select \"Set main ROM folder\".")
		inputHidden("Press Enter to continue.")
		return False
	return True

##########
# EXPORT #
##########

def exportRomsets():
	global mainRomFolder, secondaryRomFolder, mainSystemDirs, secondarySystemDirs, systemName
	initScreen()
	if not verifyMainRomFolder():
		return
	if not selectDeviceProfile():
		return

	currProfileMainDirs = [system for system in list(deviceConfig["Main Romsets"].keys()) if deviceConfig["Main Romsets"][system] in ("Full", "1G1R", "1G1R Primary")]
	if len(currProfileMainDirs) == 0:
		if len(mainSystemDirs) > 0:
			print("The current profile does not allow any romsets.")
		systemChoices = []
	else:
		systemChoices = makeChoice("Select romset(s). You can select multiple choices by separating them with spaces:", currProfileMainDirs+["All", "None"], allowMultiple=True)
		if len(currProfileMainDirs)+2 in systemChoices:
			systemChoices = []
		elif len(currProfileMainDirs)+1 in systemChoices:
			systemChoices = list(range(1, len(currProfileMainDirs)+1))
	if secondaryRomFolder != "":
		secondaryFolderName = path.basename(secondaryRomFolder)
		currProfileSecondaryDirs = [system for system in list(deviceConfig["Secondary Romsets"].keys()) if deviceConfig["Secondary Romsets"][system] in ("Full", "1G1R", "1G1R Primary")]
		if len(currProfileMainDirs) == 0:
			if len(secondarySystemDirs) > 0:
				print("The current profile does not allow any "+secondaryFolderName+" folders.")
			otherChoices = []
		else:
			otherChoices = makeChoice("Select system(s) from "+secondaryFolderName+" folder. You can select multiple choices by separating them with spaces:", currProfileSecondaryDirs+["All", "None"], allowMultiple=True)
			if len(currProfileSecondaryDirs)+2 in otherChoices:
				otherChoices = []
			elif len(currProfileSecondaryDirs)+1 in otherChoices:
				otherChoices = list(range(1, len(currProfileSecondaryDirs)+1))
	updateOtherChoice = makeChoice("Update \""+path.basename(updateFromDeviceFolder)+"\" folder by adding any files that are currently exclusive to the ROM folder in "+deviceName+"?", ["Yes", "No"])
	outputFolder = askForDirectory("\nSelect the ROM directory of your "+deviceName+" (example: F:/Roms).")
	initScreen()
	for sc in systemChoices:
		systemName = currProfileMainDirs[sc-1]
		print("\n"+systemName)
		romsetCategory = deviceConfig["Main Romsets"][systemName]
		isNoIntro = True
		currSystemDAT = path.join(noIntroDir, systemName+".dat")
		if not path.exists(currSystemDAT):
			print("Database file not found for "+currSystemDAT)
			print("Skipping current system.")
			continue
		generateGameRomDict()
		# TODO: Start from copyRomset()

def generateGameRomDict():
	global gameRomDict
	global newGameRomDict
	gameRomDict = {}
	systemFolder = path.join(mainRomFolder, systemName)
	currSystemDAT = path.join(noIntroDir, systemName+".dat")
	tree = ET.parse(currSystemDAT)
	root = tree.getroot()
	allGameFields = root[1:]
	for file in listdir(systemFolder):
		# currFilePath = path.join(systemFolder, file)
		romName = path.splitext(file)[0]
		for game in allGameFields:
			if game.get("name") == romName:
				parent = game.get("cloneof")
				if parent is None:
					addGameAndRomToDict(romName, romName)
				else:
					addGameAndRomToDict(parent, romName)
				break
	# Rename gameRomDict keys according to best game name
	newGameRomDict = {}
	for game in gameRomDict.keys():
		bestGameName = getBestGameName(gameRomDict[game])
		if bestGameName in newGameRomDict: # same name for two different games (Pokemon Stadium International vs. Japan)
			bestGameName = fixDuplicateName(newGameRomDict[bestGameName], gameRomDict[game], bestGameName)
		newGameRomDict[bestGameName] = gameRomDict[game]
	gameRomDict = newGameRomDict
	for game in sorted(gameRomDict.keys()):
		# print("    ", game, gameRomDict[game])
		print(game)
	inputHidden(" ")

def addGameAndRomToDict(game, rom):
	global gameRomDict
	if game not in gameRomDict.keys():
		gameRomDict[game] = []
	gameRomDict[game].append(rom)

def getBestGameName(roms):
	bestRom = getBestRom(roms)
	atts = getAttributeSplit(bestRom)
	bestGameName = atts[0]
	if len(atts) == 1:
		return bestGameName
	attributes = atts[1:]
	for att in attributes:
		keepAtt = keepAttribute(att)
		if keepAtt:
			bestGameName += " ("+att+")"
	return bestGameName

def keepAttribute(att):
	for keyword in hiddenKeywords:
		if att.startswith(keyword):
			return False
	if att.startswith("v") and len(att) > 1 and att[1].isdigit():
		return False
	for region in mainConfig["Regions"]:
		if att in mainConfig["Regions"][region]:
			return False
	for specialCategory in mainConfig["Special ROM Attributes (Advanced)"]:
		if att in mainConfig["Special ROM Attributes (Advanced)"][specialCategory]:
			return False
	try:
		dateParse(att, False)
		return False
	except:
		return True

def getBestRom(roms):
	romsInBestRegion, _ = getRomsInBestRegion(roms)
	if len(romsInBestRegion) == 1:
		return romsInBestRegion[0]
	bestScore = -500
	bestRom = ""
	for rom in romsInBestRegion:
		currScore = getScore(rom)
		if currScore >= bestScore:
			bestScore = currScore
			bestRom = rom
	return bestRom

def getRomsInBestRegion(roms):
	firstRegionIndex = 99
	romsInBestRegion = []
	for rom in roms:
		attributeSplit = getAttributeSplit(rom)
		i = 0
		foundRegion = False
		for region in mainConfig["Regions"]:
			for regionAtt in mainConfig["Regions"][region].split("|"):
				if regionAtt in attributeSplit or regionAtt == ":DEFAULT:":
					if i < firstRegionIndex:
						firstRegionIndex = i
						romsInBestRegion = [rom]
					elif i == firstRegionIndex:
						romsInBestRegion.append(rom)
					foundRegion = True
				if foundRegion:
					break
			if foundRegion:
				break
			i += 1
	return romsInBestRegion, firstRegionIndex

def getScore(rom):
	attributes = getAttributeSplit(rom)[1:]
	score = 100
	lastVersion = 0
	sources = mainConfig["Special ROM Attributes (Advanced)"]["Sources"].split("|")
	for att in attributes:
		if att.startswith("Rev"):
			try:
				score += 15 + (15 * int(att.split()[1]))
			except:
				score += 30
		elif att.startswith("v"):
			try:
				score += float(att[1:])
				lastVersion = float(att[1:])
			except:
				score += lastVersion
		elif att.startswith("Beta") or att.startswith("Proto"):
			try:
				score -= (50 - int(att.split()[1]))
			except:
				score -= 49
		elif att.startswith("Sample") or att.startswith("Demo") or att.startswith("Promo"):
			try:
				score -= (90 - int(att.split()[1]))
			except:
				score -= 89
		if "Collection" in att:
			score -= 10
		if att in sources:
			score -= 10
	return score

def getAttributeSplit(name):
	mna = [s.strip() for s in re.split('\(|\)', name) if s.strip() != ""]
	mergeNameArray = []
	mergeNameArray.append(mna[0])
	if len(mna) > 1:
		for i in range(1, len(mna)):
			if not ("," in mna[i] or "+" in mna[i]):
				mergeNameArray.append(mna[i])
			else:
				arrayWithComma = [s.strip() for s in re.split('\,|\+', mna[i]) if s.strip() != ""]
				for att2 in arrayWithComma:
					mergeNameArray.append(att2)
	return mergeNameArray

def fixDuplicateName(firstGameRoms, secondGameRoms, sharedName):
	global newGameRomDict
	_, firstRegionNum = getRomsInBestRegion(firstGameRoms)
	_, secondRegionNum = getRomsInBestRegion(secondGameRoms)
	if firstRegionNum <= secondRegionNum:
		newSecondGameName = sharedName+" ("+list(mainConfig["Regions"].keys())[secondRegionNum]+")"
		# print("Renamed "+sharedName+" to "+newSecondGameName)
		return newSecondGameName
	else:
		newFirstGameName = sharedName+" ("+list(mainConfig["Regions"].keys())[firstRegionNum]+")"
		newGameRomDict[newFirstGameName] = newGameRomDict.pop(sharedName)
		# print("Renamed "+sharedName+" to "+newFirstGameName)
		return sharedName

def copyRomset(romsetCategory):
	"""
	Copy roms from mainRomFolder to device according to romsetCategory.
	Do not copy any roms that would be put in a folder that is listed in deviceConfig["Special Categories"]["Ignored Folders"].
	Put roms from primary region in system's root folder.
	Create subfolders according to mainConfig["Special Folders"]
	"""

#########################
# GLOBAL HELPER METHODS #
#########################

def askForDirectory(string):
	print(string)
	sleep(0.5)
	root = Tk()
	root.withdraw()
	outputFolder = filedialog.askdirectory()
	if outputFolder != "":
		isCorrect = makeChoice("Are you sure this is the correct folder?\n"+outputFolder, ["Yes", "No"])
		if isCorrect == 2:
			outputFolder = ""
	return outputFolder

def initScreen():
	clearScreen()
	print()
	printTitle("Rom Organizer 3")
	print()

###############
# HELP SCREEN #
###############

def printHelp():
	clearScreen()
	print("\nUpdate/audit romsets")
	print("- Updates the names of misnamed roms (and the ZIP files containing them, if")
	print("  applicable) according to the rom's entry in the No-Intro Parent/Clone DAT.")
	print("  This is determined by the rom's matching hash code in the DAT.")
	print("- For each system, creates a log file indicating which roms exist in the romset,")
	print("  which roms are missing, and which roms are in the set that don't match")
	print("  anything form the DAT.")
	print("\nExport roms")
	print("- Exports romset according to current device profile. Either all systems or a")
	print("  subset of systems may be chosen, and roms that already exist on the device")
	print("  are not re-exported.")
	print("- May also export contents of secondary folder, according to current device")
	print("  profile.")
	print("\nCreate new device profile")
	print("- Create a new device profile. This is a text file that indicates the following:")
	print("  - Which systems from your rom collection should be copied")
	print("  - Whether each system should include all roms (Full), one rom per game (1G1R),")
	print("    or one rom per game while ignoring games that don't have a version from your")
	print("    primary region(s) (1G1R Primary)")
	print("  - Primary region(s); these folders will not be created in romset organization;")
	print("    instead, their contents are added to the root folder of the current system.")
	print("  - Which folders, if any, exist in your device's rom folder that you do not")
	print("    want to copy back to the main folder.")
	inputHidden("\nPress Enter to continue.")

if __name__ == '__main__':
	main()
