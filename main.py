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
from tqdm import tqdm
import binascii

progFolder = getCurrFolder()
sys.path.append(progFolder)
crcHasher = FileHash('crc32')

mainConfigFile = path.join(progFolder, "settings.ini")

updateFromDeviceFolder = path.join(progFolder, "Copied From Device")
noIntroDir = path.join(progFolder, "No-Intro Database")
redumpDir = path.join(progFolder, "Redump Database")
profilesFolder = path.join(progFolder, "Device Profiles")
logFolder = path.join(progFolder, "Logs")

########
# MAIN #
########

def main():
	global isExport
	global recentlyVerified
	prepareMainConfig()
	createDir(noIntroDir)
	createDir(redumpDir)
	createDir(profilesFolder)
	createDir(logFolder)
	recentlyVerified = False
	while True:
		initScreen()
		choice = makeChoice("Select an option.", [
			"Set main ROM folder      (currently "+(mainRomFolder if mainRomFolder != "" else "not set")+")",
			"Set secondary ROM folder (currently "+(secondaryRomFolder if secondaryRomFolder != "" else "not set")+")",
			"Update/audit verified romsets",
			"Create new device profile",
			"Update device profile",
			"Export romset",
			"Test export of romset",
			"Help",
			"Exit"])
		if choice == 1:
			setMainRomFolder()
		elif choice == 2:
			setSecondaryRomFolder()
		elif choice == 3:
			updateAndAuditVerifiedRomsets()
		elif choice == 4:
			createDeviceProfile()
		elif choice == 5:
			isExport = True
			updateDeviceProfile()
		elif choice == 6:
			isExport = True
			mainExport()
		elif choice == 7:
			isExport = False
			mainExport()
		elif choice == 8:
			printHelp()
		else:
			clearScreen()
			sys.exit()

####################
# UPDATE AND AUDIT #
####################

def updateAndAuditVerifiedRomsets():
	global allGameNamesInDAT, romsWithoutCRCMatch, progressBar, recentlyVerified
	initScreen()
	currRomsetFolder = askForDirectory("Select the rom directory you would like to update/audit.\nThis is the directory that contains all of your system folders.")
	if currRomsetFolder == "":
		print("Action cancelled.")
		sleep(1)
		return

	romsetsToVerify = []
	for currSystemName in listdir(currRomsetFolder):
		currSystemFolder = path.join(currRomsetFolder, currSystemName)
		if not path.isdir(currSystemFolder):
			continue
		isNoIntro = True
		currSystemDAT = path.join(noIntroDir, currSystemName+".dat")
		if not path.exists(currSystemDAT):
			isNoIntro = False
			currSystemDAT = path.join(redumpDir, currSystemName+".dat")
			if not path.exists(currSystemDAT):
				for file in listdir(redumpDir):
					if path.splitext(file)[0].split(" - Datfile")[0] == currSystemName:
						currSystemDAT = path.join(redumpDir, file)
						break
				if not path.exists(currSystemDAT):
					continue
		romsetsToVerify.append(currSystemName)
	if len(romsetsToVerify) == 0:
		print("No .DAT files found for any of the system folders in "+currRomsetFolder)
		inputHidden("Press Enter to continue.")
		return
	print("Database (.DAT) files found for the following system(s).")
	sc = makeChoice("Select romset(s). You can select multiple choices by separating them with spaces:", romsetsToVerify+["All", "None"], allowMultiple=True)
	if len(romsetsToVerify)+2 in sc:
		systemChoices = []
	elif len(romsetsToVerify)+1 in sc:
		systemChoices = romsetsToVerify
	else:
		systemChoices = [romsetsToVerify[choice-1] for choice in sc]

	if currRomsetFolder != mainRomFolder:
		moveUnverified = makeChoice("In the event that unverified roms (roms without a matching database CRC) are\nfound, would you like to automatically move these to an \"[Unverified]\"\nsubfolder within the system folder?", ["Yes", "No"])
	else:
		moveUnverified = 2
	for currSystemName in systemChoices:
		currSystemFolder = path.join(currRomsetFolder, currSystemName)
		if not path.isdir(currSystemFolder):
			continue
		print("\n====================\n\n"+currSystemName+"\n")
		isNoIntro = True
		currSystemDAT = path.join(noIntroDir, currSystemName+".dat")
		if not path.exists(currSystemDAT):
			isNoIntro = False
			currSystemDAT = path.join(redumpDir, currSystemName+".dat")
			if not path.exists(currSystemDAT):
				for file in listdir(redumpDir):
					if path.splitext(file)[0].split(" - Datfile")[0] == currSystemName:
						currSystemDAT = path.join(redumpDir, file)
						break
				if not path.exists(currSystemDAT):
					print("Database file not found for "+currSystemName+".")
					continue
		tree = ET.parse(currSystemDAT)
		treeRoot = tree.getroot()
		allGameFields = treeRoot[1:]
		# gameNameToCRC = {}
		crcToGameName = {}
		allGameNames = []
		for game in allGameFields:
			gameName = game.get("name")
			allGameNames.append(gameName)
			try:
				gameCRC = game.find("rom").get("crc").upper()
			except:
				gameCRC = None
			# gameNameToCRC[gameName] = gameCRC
			if gameCRC not in crcToGameName.keys():
				crcToGameName[gameCRC] = []
			crcToGameName[gameCRC].append(gameName)
		try:
			datFileSystemName = treeRoot[0].find("name").text
			headerLength = int(mainConfig["System Header Sizes (Advanced)"][datFileSystemName])
		except:
			headerLength = 0
		allGameNamesInDAT = {}
		for gameName in allGameNames:
			allGameNamesInDAT[gameName] = False
		romsWithoutCRCMatch = []
		numFiles = 0
		for root, dirs, files in walk(currSystemFolder):
			for file in files:
				if path.basename(root) != "[Unverified]":
					numFiles += 1
		progressBar = tqdm(total=numFiles, ncols=80)
		for root, dirs, files in walk(currSystemFolder):
			for file in files:
				if path.basename(root) != "[Unverified]":
					progressBar.update(1)
					foundMatch = renamingProcess(root, file, isNoIntro, headerLength, crcToGameName, allGameNames)
		progressBar.close()
		xmlRomsInSet = [key for key in allGameNamesInDAT.keys() if allGameNamesInDAT[key] == True]
		xmlRomsNotInSet = [key for key in allGameNamesInDAT.keys() if allGameNamesInDAT[key] == False]
		createSystemAuditLog(xmlRomsInSet, xmlRomsNotInSet, romsWithoutCRCMatch, currSystemName)
		numNoCRC = len(romsWithoutCRCMatch)
		if numNoCRC > 0:
			print("\nWarning: "+str(numNoCRC)+pluralize(" file", numNoCRC)+" in this system folder "+pluralize("do", numNoCRC, "es", "")+" not have a matching database entry.")
			print(limitedString("If this system folder is in your main verified rom directory, you should move "+pluralize("", numNoCRC, "this file", "these files")+" to your secondary folder; otherwise, "+pluralize("", numNoCRC, "it", "they")+" may be ignored when exporting this system's romset to another device.",
				80, "", "  "))
			if moveUnverified == 1:
				numMoved = 0
				unverifiedFolder = path.join(currSystemFolder, "[Unverified]")
				createDir(unverifiedFolder)
				for fileName in romsWithoutCRCMatch:
					try:
						rename(path.join(currSystemFolder, fileName), path.join(unverifiedFolder, fileName))
						numMoved += 1
					except:
						pass
				print("Moved "+str(numMoved)+" of these file(s) to \"[Unverified]\" subfolder in system directory.")

	recentlyVerified = True
	inputHidden("\nDone. Press Enter to continue.")

def getCRC(filePath, headerLength=0):
	if zipfile.is_zipfile(filePath):
		with zipfile.ZipFile(filePath, 'r', zipfile.ZIP_DEFLATED) as zippedFile:
			if len(zippedFile.namelist()) > 1:
				return False
			if headerLength == 0:
				fileInfo = zippedFile.infolist()[0]
				fileCRC = format(fileInfo.CRC & 0xFFFFFFFF, '08x')
				return fileCRC.zfill(8).upper()
			else:
				fileBytes = zippedFile.read(zippedFile.namelist()[0])
				headerlessCRC = str(hex(binascii.crc32(fileBytes[headerLength:])))[2:]
				return headerlessCRC.zfill(8).upper()
	else:
		if headerLength == 0:
			fileCRC = crcHasher.hash_file(filePath)
			return fileCRC.zfill(8).upper()
		with open(filePath, "rb") as unheaderedFile:
			fileBytes = unheaderedFile.read()
			headerlessCRC = str(hex(binascii.crc32(fileBytes[headerLength:])))[2:]
			return headerlessCRC.zfill(8).upper()

def renamingProcess(root, file, isNoIntro, headerLength, crcToGameName, allGameNames):
	global allGameNamesInDAT, romsWithoutCRCMatch
	currFilePath = path.join(root, file)
	currFileName, currFileExt = path.splitext(file)
	if not path.isfile(currFilePath): # this is necessary
		romsWithoutCRCMatch.append(file)
		return
	foundMatch = False
	if isNoIntro:
		currFileCRC = getCRC(currFilePath, headerLength)
		if not currFileCRC:
			progressBar.write(file+" archive contains more than one file. Skipping.")
			romsWithoutCRCMatch.append(file)
			return
		matchingGameNames = crcToGameName.get(currFileCRC)
		if matchingGameNames is not None:
			if not currFileName in matchingGameNames:
				currFileIsDuplicate = True
				for name in matchingGameNames:
					currPossibleMatchingGame = path.join(root, name+currFileExt)
					if not path.exists(currPossibleMatchingGame):
						renameGame(currFilePath, name, currFileExt)
						allGameNamesInDAT[name] = True
						currFileIsDuplicate = False
						break
					elif getCRC(currPossibleMatchingGame, headerLength) != currFileCRC: # If the romset started with a rom that has a name in the database, but with the wrong hash (e.g. it's called "Doom 64 (USA)", but it's actually something else)
						renameGame(currPossibleMatchingGame, name+" (no match)", currFileExt)
						renameGame(currFilePath, name, currFileExt)
						renamingProcess(root, name+" (no match)", isNoIntro, headerLength, crcToGameName, allGameNames)
						allGameNamesInDAT[name] = True
						currFileIsDuplicate = False
						break
				if currFileIsDuplicate:
					dnStart = matchingGameNames[0]+" (copy) ("
					i = 1
					while True:
						duplicateName = path.join(root, dnStart+str(i)+")")
						if not path.exists(duplicateName):
							break
						i += 1
					renameGame(currFilePath, duplicateName, currFileExt)
					progressBar.write("Duplicate found and renamed: "+duplicateName)
			else:
				allGameNamesInDAT[currFileName] = True
			foundMatch = True
	else:
		if currFileName in allGameNames:
			allGameNamesInDAT[currFileName] = True
			foundMatch = True
	if not foundMatch:
		romsWithoutCRCMatch.append(file)

def renameGame(filePath, newName, fileExt):
	if zipfile.is_zipfile(filePath):
		renameArchiveAndContent(filePath, newName)
	else:
		rename(filePath, path.join(path.dirname(filePath), newName+fileExt))
		progressBar.write("Renamed "+path.splitext(path.basename(filePath))[0]+" to "+newName)

def createSystemAuditLog(xmlRomsInSet, xmlRomsNotInSet, romsWithoutCRCMatch, currSystemName):
	xmlRomsInSet.sort()
	xmlRomsNotInSet.sort()
	romsWithoutCRCMatch.sort()

	numOverlap = len(xmlRomsInSet)
	numNotInSet = len(xmlRomsNotInSet)
	numNoCRC = len(romsWithoutCRCMatch)
	auditLogFile = open(path.join(logFolder, "Audit ("+currSystemName+") ["+str(numOverlap)+" out of "+str(numOverlap+numNotInSet)+"] ["+str(numNoCRC)+"].txt"), "w", encoding="utf-8", errors="replace")
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
		for rom in romsWithoutCRCMatch:
			auditLogFile.writelines(rom+"\n")
	auditLogFile.close()

def renameArchiveAndContent(archivePath, newName):
	with zipfile.ZipFile(archivePath, 'r', zipfile.ZIP_DEFLATED) as zippedFile:
		zippedFiles = zippedFile.namelist()
		if len(zippedFiles) > 1:
			progressBar.write("This archive contains more than one file. Skipping.")
			return
		fileExt = path.splitext(zippedFiles[0])[1]
		archiveExt = path.splitext(archivePath)[1]
		zippedFile.extract(zippedFiles[0], path.dirname(archivePath))
		currExtractedFilePath = path.join(path.dirname(archivePath), zippedFiles[0])
		newArchivePath = path.join(path.dirname(archivePath), newName+archiveExt)
		newExtractedFilePath = path.splitext(newArchivePath)[0]+fileExt
		rename(currExtractedFilePath, newExtractedFilePath)
	remove(archivePath)
	with zipfile.ZipFile(newArchivePath, 'w', zipfile.ZIP_DEFLATED) as newZip:
		newZip.write(newExtractedFilePath, arcname='\\'+newName+fileExt)
	remove(newExtractedFilePath)
	progressBar.write("Renamed "+path.splitext(path.basename(archivePath))[0]+" to "+newName)

############################
# CONFIG / DEVICE PROFILES #
############################

def prepareMainConfig():
	global mainConfig, mainRomFolder, secondaryRomFolder, mainSystemDirs, secondarySystemDirs, keywords, sources, starters
	if not path.exists(mainConfigFile):
		createMainConfig()
	mainConfig = configparser.ConfigParser(allow_no_value=True)
	mainConfig.optionxform = str
	mainConfig.read(mainConfigFile)
	mainRomFolder = mainConfig["ROM Folders"]["Main ROM Folder"]
	secondaryRomFolder = mainConfig["ROM Folders"]["Secondary ROM Folder"]
	keywords = barSplit(mainConfig["Special ROM Attributes (Advanced)"]["Keywords"])
	sources = barSplit(mainConfig["Special ROM Attributes (Advanced)"]["Sources"])
	starters = barSplit(mainConfig["Special ROM Attributes (Advanced)"]["Starters"])
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
	mainConfig.set('ROM Folders', limitedString("The directory of the main ROM folder you want to export from, which contains system folders that contain No-Intro verified ROMs. If you leave this blank, the program will ask for this folder when you try to export romsets.",
		100, "# ", "#    "))
	mainConfig.set('ROM Folders', '###')
	mainConfig["ROM Folders"]["Main ROM Folder"] = ""
	mainConfig.set('ROM Folders', limitedString("The directory of the secondary ROM folder you want to export from, which contains system folders that can contain unverified ROMs/other files (this is intended for rom hacks, homebrew, etc). If you leave this blank, the program will ask for this folder when you try to export the secondary folder.",
		100, "# ", "#    "))
	mainConfig.set('ROM Folders', '###')
	mainConfig["ROM Folders"]["Secondary ROM Folder"] = ""
	# Regions
	mainConfig["Regions"] = {}
	mainConfig.set('Regions', limitedString("The region folder for each ROM is determined by its region/language tag as listed below.",
		100, "# ", "#    "))
	mainConfig.set('Regions', limitedString("For example, any ROM with (World), (USA), or (U) in its name will be exported to a [USA] folder.",
		100, "# ", "#    "))
	mainConfig.set('Regions', limitedString("Additionally, you may set at least one region as primary (see device profiles). Primary regions do not have a subfolder, and are instead exported to the system\'s root folder.",
		100, "# ", "#    "))
	mainConfig.set('Regions', limitedString("Regions are listed in order of descending priority, so (to use the default example) if a ROM has both the USA and Fr tags, it will be considered a [USA] ROM. If you want to prioritize Europe over USA, simply move the Europe category above the USA category. You may also create your own region categories.",
		100, "# ", "#    "))
	mainConfig.set('Regions', limitedString("Finally, the last category (Other (non-English)) is the fallback in the event that a ROM doesn\'t belong in any of the preceding regions.",
		100, "# ", "#    "))
	mainConfig.set('Regions', '###')
	mainConfig["Regions"]["Test Program"] = "|".join([
		"Test Program"
		])
	mainConfig["Regions"]["USA"] = "|".join([
		"World", "U", "USA"
		])
	mainConfig["Regions"]["Europe"] = "|".join([
		"E", "Europe", "United Kingdom"
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
		"Denmark", "Nl", "Pt", "Sv", "No", "Da", "Fi", "Pl"
	])
	# Special Folders
	mainConfig["Special Folders"] = {}
	mainConfig.set('Special Folders', limitedString("Special Folders are folders that are created on your device upon export for verified games with names that contain certain strings.",
		100, "# ", "#    "))
	mainConfig.set('Special Folders', limitedString("For example, any game whose name contains \"2 Games in 1 - \" will be exported to a subfolder called \"Compilation\".",
		100, "# ", "#    "))
	mainConfig.set('Special Folders', limitedString("You could then choose to ignore any games marked as \"Compilation\" when exporting to a specific device (see device profiles).",
		100, "# ", "#    "))
	mainConfig.set('Special Folders', limitedString("Feel free to add additional Special Folders (or add to existing folders) using the format below (with \"|\" as a delimiter).",
		100, "# ", "#    "))
	mainConfig.set('Special Folders', limitedString("Special Folders are created in order of descending priority, so (to use the default example) if a game is in both \"Compilation\" and \"GBA Video\", it will be added to the folder \"SYSTEM/REGION/Compilation/GBA Video/GAME\".",
		100, "# ", "#    "))
	mainConfig.set('Special Folders', limitedString("Note that special folders are created according to the name of a *game*, not the filenames of each rom within the game.",
		100, "# ", "#    "))
	mainConfig.set('Special Folders', '###')
	mainConfig["Special Folders"]["Compilation"] = "|".join([
		"2 Games in 1 -", "2 Games in 1! -", "2 Disney Games -", "2-in-1 Fun Pack -",
		"2 Great Games! -", "2 in 1 -", "2 in 1 Game Pack -", "2 Jeux en 1 -",
		"3 Games in 1 -", "4 Games on One Game Pak", "Castlevania Double Pack",
		"Combo Pack - ", "Crash Superpack -", "Crash & Spyro Superpack",
		"Crash & Spyro Super Pack", "Double Game! -", "Double Pack -", "Spyro Superpack -"
		])
	mainConfig["Special Folders"]["GBA Video"] = "Game Boy Advance Video"
	mainConfig["Special Folders"]["NES & Famicom"] = "|".join([
		"Classic NES Series", "Famicom Mini", "Hudson Best Collection",
		"Kunio-kun Nekketsu Collection"
		])
	mainConfig["Special Folders"]["BIOS"] = "|".join([
		"BIOS"
		])
	# Special ROM Attributes
	mainConfig["Special ROM Attributes (Advanced)"] = {}
	mainConfig.set('Special ROM Attributes (Advanced)', limitedString("Special ROM Attributes are substrings in verified ROM names (specifically, the parentheses fields in these names) that are ignored when trying to determine the best name for a game.",
		100, "# ", "#    "))
	mainConfig.set('Special ROM Attributes (Advanced)', limitedString("\"Sources\" are also used in determining the best ROM for 1G1R sets (they are given lower priority).",
		100, "# ", "#    "))
	mainConfig.set('Special ROM Attributes (Advanced)', limitedString("Parentheses field are also ignored if they start with a \"Starter\". For example, \"Rev\" includes (Rev 1), (Rev 2), (Rev A), ...",
		100, "# ", "#    "))
	mainConfig.set('Special ROM Attributes (Advanced)', '###')
	mainConfig["Special ROM Attributes (Advanced)"]["Keywords"] = "|".join([
		"Unl", "Pirate", "PAL", "NTSC", "GB Compatible", "SGB Enhanced",
		"Club Nintendo", "Aftermarket", "Test Program", "Competition Cart",
		"NES Test", "Promotion Card", "Program", "Manual", "NDSi Enhanced",
		"Wi-Fi Kiosk"
		])
	mainConfig["Special ROM Attributes (Advanced)"]["Sources"] = "|".join([
		"Virtual Console", "Switch Online", "GameCube", "Namcot Collection",
		"Namco Museum Archives", "Kiosk", "iQue", "Sega Channel", "WiiWare",
		"DLC", "Minis", "Promo", "Nintendo Channel", "Nintendo Channel, Alt",
		"DS Broadcast", "Wii Broadcast", "DS Download Station", "Dwnld Sttn",
		"Undumped Japanese Download Station", "WiiWare Broadcast",
		"Disk Writer", "Collection of Mana", "Namco Museum Archives Vol 1",
		"Namco Museum Archives Vol 2", "Castlevania Anniversary Collection",
		"Nintendo Switch", "NP", "Genesis Mini", "Mega Drive Mini"
		])
	mainConfig["Special ROM Attributes (Advanced)"]["Starters"] = "|".join([
		"Rev", "Disc", "Beta", "Demo", "Sample", "Proto", "Alt", "Earlier",
		"Download Station", "FW", "Reprint"
		])
	# System Header Sizes
	mainConfig["System Header Sizes (Advanced)"] = {}
	mainConfig.set('System Header Sizes (Advanced)', limitedString("The size (in bytes) of each system\'s header (0 by default). This is used when comparing a game\'s CRC hash to its system database.",
		100, "# ", "#    "))
	mainConfig.set('System Header Sizes (Advanced)', limitedString("Each system name should match the \"name\" field in the DAT file\'s header.",
		100, "# ", "#    "))
	mainConfig.set('System Header Sizes (Advanced)', '###')
	mainConfig["System Header Sizes (Advanced)"]["Nintendo - Nintendo Entertainment System (Parent-Clone)"] = "16"
	with open(mainConfigFile, 'w') as mcf:
		mainConfig.write(mcf)
	print("Created new settings.ini")
	inputHidden("Press Enter to continue.")

def selectDeviceProfile():
	global deviceName, deviceConfig, deviceConfigFile
	global ignoredFolders, primaryRegions
	initScreen()
	deviceProfiles = [prof for prof in listdir(profilesFolder) if path.splitext(prof)[1] == ".ini"]
	if len(deviceProfiles) > 0:
		dp = makeChoice("Select a device profile (which device are you "+("copying to" if isExport else "testing")+"?)", [path.splitext(prof)[0] for prof in deviceProfiles]+["Create new profile", "Back to menu"])
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
			ignoredFolders = barSplit(deviceConfig["Special Categories"]["Ignored Folders"])
			primaryRegions = barSplit(deviceConfig["Special Categories"]["Primary Regions"])
			# doNotCopyFromDevice = barSplit(deviceConfig["Special Categories"]["Do Not Copy From Device"])
			return True
	else:
		print("\nNo device profiles found. Go back to the main menu and select\n\"Create new device profile\".")
		inputHidden("Press Enter to continue.")
		return False

def createDeviceProfile():
	initScreen()
	if not verifyMainRomFolder():
		return
	print("\nFollow these steps to create a new device profile.")
	skipSecondary = False
	if secondaryRomFolder == "":
		choice = makeChoice("Are you using a secondary rom folder containing unverified files such as hacks,\nhomebrew, etc.?", ["Yes, I have a secondary folder", "No, verified roms only"])
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

	print("\n(2/5) Please define how each romset should be exported to this device.")
	for currSystemName in mainSystemDirs:
		addMainSystemToDeviceConfig(currSystemName)
	# Secondary Romsets
	deviceConfig["Secondary Romsets"] = {}
	if not skipSecondary:
		print("\nPlease define whether or not each folder in the secondary rom folder should be")
		print("exported to this device.")
		for currSystemName in secondarySystemDirs:
			addSecondarySystemToDeviceConfig(currSystemName)
	# Special Categories
	deviceConfig["Special Categories"] = {}

	print("\n"+limitedString("(3/5) Please type the names of any Special Folders or Regions you would like to skip in copying. Use \"|\" as a divider.",
		80, "", "  "))
	print("\n"+limitedString("For example, to skip all roms that are either Japan or Compilation, type the following: Japan|Compilation",
		80, "  ", "  "))
	print("According to your settings.ini file, possible Special Folders and Regions are:")
	specialFolders = [folder for folder in mainConfig["Special Folders"]]
	regions = [region for region in mainConfig["Regions"]]
	print(", ".join(["\""+entry+"\"" for entry in specialFolders+regions]))
	print("... along with any exact folder names from your secondary folders.")
	currInput = input().strip()
	currInputParsed = [val.strip() for val in barSplit(currInput)]
	deviceConfig["Special Categories"]["Ignored Folders"] = "|".join(currInputParsed)

	print("\n(4/5) Please type the names of any Primary Regions.")
	print(limitedString("These folders will not be created in romset organization; instead, their contents are added to the root folder of the current system. Use \"|\" as a divider.",
		80, "  ", "  "))
	print(limitedString("For example, if you wanted all USA and Europe roms in the root folder instead of [USA] and [Europe] subfolders, you would type the following: USA|Europe",
		80, "  ", "  "))
	print("According to your settings.ini file, possible Regions are:")
	print(", ".join(["\""+entry+"\"" for entry in regions]))
	currInput = input().strip()
	currInputParsed = [val.strip() for val in barSplit(currInput)]
	deviceConfig["Special Categories"]["Primary Regions"] = "|".join(currInputParsed)

	print("\n"+limitedString("(5/5) When exporting, you have the option to copy contents that exist in this device's rom folder, but not in the main rom folder, into a \"Copied From Device\" folder. This is useful for keeping your devices in parity with each other.",
		80, "", "  "))
	print(limitedString("Please type the exact names of any folders in your device's rom folder that you do not want to copy to this folder. These folders will be skipped; this is useful if you keep roms and non-rom PC games in the same folder. Use \"|\" as a divider.",
		80, "  ", "  "))
	print(limitedString("For example, if you wanted to ignore anything in the \"Steam\" folder, you would type the following: Steam",
		80, "  ", "  "))
	print("Common recommended subfolders are Steam, Windows, and PC Games")
	currInput = input().strip()
	currInputParsed = [val.strip() for val in barSplit(currInput)]
	deviceConfig["Special Categories"]["Do Not Copy From Device"] = "|".join(currInputParsed)

	with open(deviceConfigFile, 'w') as dcf:
		deviceConfig.write(dcf)
	print("\nCreated new profile for "+deviceName+".")
	inputHidden("Press Enter to continue.")

def updateDeviceProfile():
	global deviceConfig
	initScreen()
	if not verifyMainRomFolder():
		return
	if not selectDeviceProfile():
		return
	skipSecondary = False
	if secondaryRomFolder == "":
		choice = makeChoice("Are you using a secondary rom folder containing unverified files such as hacks,\nhomebrew, etc.?", ["Yes, I have a secondary folder", "No, verified roms only"])
		if choice == 1:
			print("Go back to the main menu and select \"Set secondary ROM folder\".")
			inputHidden("Press Enter to continue.")
			return
		else:
			skipSecondary = True

	missingMainSystems = []
	for currSystemName in mainSystemDirs:
		if not currSystemName in list(deviceConfig["Main Romsets"].keys()):
			missingMainSystems.append(currSystemName)
	if len(missingMainSystems) == 0:
		print("\nCurrent device profile is not missing any systems from main rom folder.")
	else:
		print("\nPlease define how each romset should be exported to this device.")
		for currSystemName in missingMainSystems:
			addMainSystemToDeviceConfig(currSystemName)
	if not skipSecondary:
		missingSecondarySystems = []
		for currSystemName in secondarySystemDirs:
			if not currSystemName in list(deviceConfig["Secondary Romsets"].keys()):
				missingSecondarySystems.append(currSystemName)
		if len(missingSecondarySystems) == 0:
			print("\nCurrent device profile is not missing any systems from secondary rom folder.")
		else:
			print("\nPlease define whether or not each folder in the secondary rom folder should be")
			print("exported to this device.")
			for currSystemName in missingSecondarySystems:
				addSecondarySystemToDeviceConfig(currSystemName)
	with open(deviceConfigFile, 'w') as dcf:
		deviceConfig.write(dcf)
	print("\nUpdated profile for "+deviceName+".")
	inputHidden("Press Enter to continue.")

def addMainSystemToDeviceConfig(currSystemName):
	global deviceConfig
	copyType = makeChoice(currSystemName, ["Full (copy all contents)",
		"1G1R (copy only the most significant rom for each game)",
		"1G1R Primary (same as 1G1R, but ignore games that do not have a rom for a primary region",
		"None (skip this system)"])
	if copyType == 1:
		deviceConfig["Main Romsets"][currSystemName] = "Full"
	elif copyType == 2:
		deviceConfig["Main Romsets"][currSystemName] = "1G1R"
	elif copyType == 3:
		deviceConfig["Main Romsets"][currSystemName] = "1G1R Primary"
	elif copyType == 4:
		deviceConfig["Main Romsets"][currSystemName] = "None"

def addSecondarySystemToDeviceConfig(currSystemName):
	global deviceConfig
	copyType = makeChoice(currSystemName, ["Yes", "No"])
	if copyType == 1:
		deviceConfig["Secondary Romsets"][currSystemName] = "Yes"
	else:
		deviceConfig["Secondary Romsets"][currSystemName] = "No"

##########################
# SET/VERIFY ROM FOLDERS #
##########################

def setMainRomFolder():
	global mainConfig, mainSystemDirs, mainRomFolder
	initScreen()
	newMainRomFolder = askForDirectory("Select a main rom folder. This directory should contain system folders, which contain No-Intro verified roms.")
	if newMainRomFolder == "":
		print("Action cancelled.")
		sleep(1)
		return
	mainConfig.read(mainConfigFile)
	mainConfig["ROM Folders"]["Main ROM Folder"] = newMainRomFolder
	mainRomFolder = newMainRomFolder
	mainSystemDirs = [d for d in listdir(mainRomFolder) if path.isdir(path.join(mainRomFolder, d))]
	with open(mainConfigFile, 'w') as mcf:
		mainConfig.write(mcf)

def setSecondaryRomFolder():
	global mainConfig, secondarySystemDirs, secondaryRomFolder
	initScreen()
	newSecondaryRomFolder = askForDirectory("Select a secondary rom folder. This directory should contain system folders, which can contain unverified roms/other files (rom hacks, homebrew, etc).")
	if newSecondaryRomFolder == "":
		print("Action cancelled.")
		sleep(1)
		return
	mainConfig.read(mainConfigFile)
	mainConfig["ROM Folders"]["Secondary ROM Folder"] = newSecondaryRomFolder
	secondaryRomFolder = newSecondaryRomFolder
	secondarySystemDirs = [d for d in listdir(secondaryRomFolder) if path.isdir(path.join(secondaryRomFolder, d))]
	with open(mainConfigFile, 'w') as mcf:
		mainConfig.write(mcf)

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

def mainExport():
	global mainRomFolder, secondaryRomFolder, mainSystemDirs, secondarySystemDirs, deviceName, systemName, outputFolder, recentlyVerified
	initScreen()
	if not verifyMainRomFolder():
		return
	if not recentlyVerified:
		choice = makeChoice(limitedString("If you haven't done so already, it is recommended that you update/audit your verified romsets whenever you add new roms (or if this is your first time running this program). This will make sure your rom names match those in the DAT files."), ["I already did this", "Back to menu"])
		if choice == 2:
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
	if path.isdir(secondaryRomFolder) and len(deviceConfig["Secondary Romsets"]) > 0:
		secondaryFolderName = path.basename(secondaryRomFolder)
		currProfileSecondaryDirs = [system for system in list(deviceConfig["Secondary Romsets"].keys()) if deviceConfig["Secondary Romsets"][system] == "Yes"]
		if len(currProfileSecondaryDirs) == 0:
			if len(secondarySystemDirs) > 0:
				print("The current profile does not allow any "+secondaryFolderName+" folders.")
			secondaryChoices = []
		else:
			secondaryChoices = makeChoice("Select system(s) from "+secondaryFolderName+" folder. You can select multiple choices by separating them with spaces:", currProfileSecondaryDirs+["All", "None"], allowMultiple=True)
			if len(currProfileSecondaryDirs)+2 in secondaryChoices:
				secondaryChoices = []
			elif len(currProfileSecondaryDirs)+1 in secondaryChoices:
				secondaryChoices = list(range(1, len(currProfileSecondaryDirs)+1))
	if isExport:
		updateSecondaryChoice = makeChoice("Update \""+path.basename(updateFromDeviceFolder)+"\" folder by adding any files that are currently exclusive to the ROM folder in "+deviceName+"?", ["Yes", "No"])
	else:
		updateSecondaryChoice = makeChoice("Test update of \""+path.basename(updateFromDeviceFolder)+"\" folder by checking which files are currently exclusive to the ROM folder in "+deviceName+"?", ["Yes", "No"])
	outputFolder = askForDirectory("\nSelect the ROM directory of your "+deviceName+" (example: F:/Roms).")
	if outputFolder == "":
		print("Action cancelled.")
		sleep(1)
		return
	initScreen()
	numCopiedBytesMain = 0
	numCopiedBytesSecondary = 0
	for sc in systemChoices:
		systemName = currProfileMainDirs[sc-1]
		print("\n====================\n\n"+systemName)
		romsetCategory = deviceConfig["Main Romsets"][systemName]
		isRedump = False
		currSystemDAT = path.join(noIntroDir, systemName+".dat")
		if not path.exists(currSystemDAT):
			isRedump = True
			currSystemDAT = path.join(redumpDir, systemName+".dat")
			if not path.exists(currSystemDAT):
				for file in listdir(redumpDir):
					if path.splitext(file)[0].split(" - Datfile")[0] == systemName:
						currSystemDAT = path.join(redumpDir, file)
						break
				if not path.exists(currSystemDAT):
					print("Database file not found for "+systemName+".")
					continue
		generateGameRomDict(currSystemDAT)
		numCopiedBytesMain += copyMainRomset(romsetCategory, isRedump)
	print("\n====================\n\nMain Romsets\nExport Size: "+simplifyNumBytes(numCopiedBytesMain))
	if path.isdir(secondaryRomFolder):
		for sc in secondaryChoices:
			systemName = currProfileSecondaryDirs[sc-1]
			print("\n====================\n\n"+systemName)
			secondaryCategory = deviceConfig["Secondary Romsets"][systemName]
			if secondaryCategory == "Yes":
				numCopiedBytesSecondary += copySecondaryRomset()
		print("\n====================\n\nSecondary Romsets\nExport Size: "+simplifyNumBytes(numCopiedBytesSecondary))
	if updateFromDeviceFolder != "":
		if updateSecondaryChoice == 1:
			print("\n====================")
			updateSecondary()
	print("\n====================")
	print("\nTotal Export Size: "+simplifyNumBytes(numCopiedBytesMain+numCopiedBytesSecondary))
	print("\nReview the log files for more information on what files "+("were" if isExport else "would be")+" exchanged between the main drive and "+deviceName+".")
	print("Log files are not created for systems that "+("do" if isExport else "would")+" not receive any new files.")
	sleep(1)
	recentlyVerified = True
	inputHidden("\nPress Enter to return to the main menu.")

def generateGameRomDict(currSystemDAT):
	global gameRomDict
	global newGameRomDict
	global allGameFields
	gameRomDict = {}
	systemFolder = path.join(mainRomFolder, systemName)
	tree = ET.parse(currSystemDAT)
	treeRoot = tree.getroot()
	allGameFields = treeRoot[1:]
	gameNameToCloneOf = {}
	for game in allGameFields:
		gameName = game.get("name")
		try:
			gameCloneOf = game.get("cloneof")
		except:
			gameCloneOf = None
		gameNameToCloneOf[gameName] = gameCloneOf
	for file in listdir(systemFolder):
		_, _, currRegion = getRomsInBestRegion([path.splitext(file)[0]])
		if currRegion in ignoredFolders:
			continue
		romName = path.splitext(file)[0]
		if romName in gameNameToCloneOf:
			parent = gameNameToCloneOf[romName]
			if parent is None:
				addGameAndRomToDict(romName, file)
			else:
				addGameAndRomToDict(parent, file)
	# Rename gameRomDict keys according to best game name
	newGameRomDict = {}
	for game in gameRomDict.keys():
		bestGameName = getBestGameName(gameRomDict[game])
		mergeBoth = False
		if bestGameName in newGameRomDict: # same name for two different games (Pokemon Stadium International vs. Japan)
			finalFirstGameName, finalSecondGameName, renameByAtts = fixDuplicateName(newGameRomDict[bestGameName], gameRomDict[game], bestGameName)
			if renameByAtts: # rename first game according to region
				newGameRomDict[finalFirstGameName] = newGameRomDict.pop(bestGameName)
				newGameRomDict[finalSecondGameName] = gameRomDict[game]
			else: # rename neither (merge the two together); rare, but possible, such as DS demos that have both a DS Download Station and a Nintendo Channel version
				for rom in gameRomDict[game]: # rename one or both games according to 
					newGameRomDict[bestGameName].append(rom)
		else:
			newGameRomDict[bestGameName] = gameRomDict[game]
	gameRomDict = newGameRomDict
	# for game in sorted(gameRomDict.keys()):
	# 	print(game)
	# 	for rom in gameRomDict[game]:
	# 		print(limitedString(rom, 80, "  - ", "    "))
	# inputHidden(" ")
	# sys.exit()

def addGameAndRomToDict(game, rom):
	global gameRomDict
	if game not in gameRomDict.keys():
		gameRomDict[game] = []
	gameRomDict[game].append(rom)

def getBestGameName(roms):
	bestRom, _ = getBestRom(roms)
	atts = getAttributeSplit(bestRom)
	# bestGameName = atts[0]
	# if len(atts) == 1:
	# 	return bestGameName.rstrip(".")
	# attributes = atts[1:]
	# for att in attributes:
	# 	keepAtt = keepAttribute(att)
	# 	if keepAtt:
	# 		bestGameName += " ("+att+")"
	# return bestGameName.rstrip(".")
	return atts[0].rstrip(".")

def keepAttribute(att): # unused
	for keyword in starters:
		if att.startswith(keyword):
			return False
	if att.startswith("v") and len(att) > 1 and att[1].isdigit():
		return False
	if att.startswith("b") and (len(att) == 1 or att[1].isdigit()):
		return False
	for region in mainConfig["Regions"]:
		if att in barSplit(mainConfig["Regions"][region]):
			return False
	for specialCategory in mainConfig["Special ROM Attributes (Advanced)"]:
		if att in barSplit(mainConfig["Special ROM Attributes (Advanced)"][specialCategory]):
			return False
	if "Virtual Console" in att:
		return False
	try:
		dateParse(att, False)
		return False
	except:
		return True

def getBestRom(roms):
	romsInBestRegion, _, bestRegion = getRomsInBestRegion(roms)
	if len(romsInBestRegion) == 1:
		return romsInBestRegion[0], bestRegion
	bestScore = -500
	bestRom = ""
	for rom in romsInBestRegion:
		currScore = getScore(rom)
		if currScore >= bestScore:
			bestScore = currScore
			bestRom = rom
	return bestRom, bestRegion

def getRomsInBestRegion(roms):
	romsInBestRegion = []
	bestRegionIndex = 99
	bestRegion = None
	numRegionTypes = len(mainConfig["Regions"])
	for rom in roms:
		attributeSplit = getAttributeSplit(rom)
		for i in range(numRegionTypes):
			region = list(mainConfig["Regions"].keys())[i]
			currRegionAtts = barSplit(mainConfig["Regions"][region])
			if arrayOverlap(attributeSplit, currRegionAtts) or i==numRegionTypes-1:
				if i < bestRegionIndex:
					bestRegionIndex = i
					romsInBestRegion = [rom]
					bestRegion = region
				elif i == bestRegionIndex:
					romsInBestRegion.append(rom)
				break
	return romsInBestRegion, bestRegionIndex, bestRegion

def getScore(rom):
	attributes = getAttributeSplit(rom)[1:]
	score = 100
	lastVersion = 0
	for att in attributes:
		if att.startswith("Rev") or att.startswith("Reprint"):
			try:
				score += 15 + (15 * int(att.split()[1]))
			except:
				score += 30
		elif att.startswith("v") and len(att) > 1 and att[1].isdigit():
			try:
				score += float(att[1:])
				lastVersion = float(att[1:])
			except:
				score += lastVersion
		elif att.startswith("b") and (len(att) == 1 or att[1].isdigit()):
			if len(att) == 1:
				score -= 30
			else:
				try:
					score -= (15 - float(att[1:]))
					lastVersion = float(att[1:])
				except:
					score -= (15 - lastVersion)
		elif att.startswith("Beta") or att.startswith("Proto"):
			try:
				score -= (50 - int(att.split()[1]))
			except:
				score -= 49
		elif att.startswith("Sample") or att.startswith("Demo"):
			try:
				score -= (90 - int(att.split()[1]))
			except:
				score -= 89
		elif "Collection" in att:
			score -= 10
		elif att in sources:
			score -= 10
		elif "DLC" in att:
			score -= 10
		elif att in ["Unl", "Pirate"]:
			score -= 20
		elif not (att in keywords or att in sources or any(att.startswith(starter) for starter in starters)): # a tiebreaker for any new keywords that are later added
			score -= 1
	return score

def getAttributeSplit(name):
	mna = [s.strip() for s in re.split('\(|\)|\[|\]', path.splitext(name)[0]) if s.strip() != ""]
	if name.startswith("[BIOS]") and len(mna) > 1:
		mna[:2] = ["[BIOS] "+mna[1]]
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
	firstBestRoms, firstRegionNum, _ = getRomsInBestRegion(firstGameRoms)
	secondBestRoms, secondRegionNum, _ = getRomsInBestRegion(secondGameRoms)
	if firstRegionNum != secondRegionNum:
		newFirstGameName = sharedName+" ("+list(mainConfig["Regions"].keys())[firstRegionNum]+")"
		newSecondGameName = sharedName+" ("+list(mainConfig["Regions"].keys())[secondRegionNum]+")"
		# print("Renamed "+sharedName+" to "+newFirstGameName)
		return newFirstGameName, newSecondGameName, True
	else:
		firstUniqueAtts, secondUniqueAtts = getUniqueAttributes(getBestRom(firstBestRoms)[0], getBestRom(secondBestRoms)[0])
		if len(firstUniqueAtts) > 0 or len(secondUniqueAtts) > 0:
			newFirstGameName = sharedName
			for att in firstUniqueAtts:
				newFirstGameName += " ("+att+")"
			newSecondGameName = sharedName
			for att in secondUniqueAtts:
				newSecondGameName += " ("+att+")"
			return newFirstGameName, newSecondGameName, True
		else:
			return None, None, False

def getUniqueAttributes(firstRom, secondRom):
	firstAtts = getAttributeSplit(firstRom)
	firstAtts.pop(0)
	secondAtts = getAttributeSplit(secondRom)
	secondAtts.pop(0)
	firstUniqueAtts = []
	tempStarters = starters[:]
	try:
		tempStarters.remove("Proto") # Exerion
	except:
		pass
	for att in firstAtts:
		if att in secondAtts or att in sources:
			continue
		if att.startswith("v") and len(att) > 1 and att[1].isdigit():
			continue
		if att.startswith("b") and (len(att) == 1 or att[1].isdigit()):
			continue
		if not any(att.startswith(starter) for starter in tempStarters):
			firstUniqueAtts.append(att)
	secondUniqueAtts = []
	for att in secondAtts:
		if att in firstAtts or att in sources:
			continue
		if att.startswith("v") and len(att) > 1 and att[1].isdigit():
			continue
		if att.startswith("b") and (len(att) == 1 or att[1].isdigit()):
			continue
		if not any(att.startswith(starter) for starter in tempStarters):
			secondUniqueAtts.append(att)
	if ("Proto" in firstUniqueAtts + secondUniqueAtts) and (len(firstUniqueAtts) + len(secondUniqueAtts) > 1):
		if "Proto" in firstUniqueAtts:
			firstUniqueAtts.remove("Proto")
		elif "Proto" in secondUniqueAtts:
			secondUniqueAtts.remove("Proto")
	return firstUniqueAtts, secondUniqueAtts

def copyMainRomset(romsetCategory, isRedump):
	global gameRomDict, progressBar
	print("Main Romset\n")
	currSystemSourceFolder = path.join(mainRomFolder, systemName)
	currSystemTargetFolder = path.join(outputFolder, systemName)
	numGames = len(gameRomDict.keys())
	romsCopied = []
	numRomsSkipped = 0
	romsFailed = []
	currNumCopiedBytes = 0
	progressBar = tqdm(total=numGames, ncols=80)
	for game in gameRomDict.keys():
		progressBar.update(1)
		currSpecialFolders = getSpecialFoldersForGame(game)
		if arrayOverlap(currSpecialFolders, ignoredFolders):
			continue
		currGameFolder = currSystemTargetFolder
		bestRom, bestRegion = getBestRom(gameRomDict[game])
		bestRegionIsPrimary = bestRegion in primaryRegions
		if not bestRegionIsPrimary:
			currGameFolder = path.join(currGameFolder, "["+bestRegion+"]")
		if "(Unl" in bestRom or "(Pirate" in bestRom:
			currGameFolder = path.join(currGameFolder, "[Unlicensed]")
		if "(Proto" in bestRom:
			currGameFolder = path.join(currGameFolder, "[Unreleased]")
		for folder in currSpecialFolders:
			currGameFolder = path.join(currGameFolder, "["+folder+"]")
		if isRedump:
			redumpCategory = "Games"
			currRomName = path.splitext(gameRomDict[game][0])[0] # Redump doesn't have clones, so each game only has one rom
			for gameField in allGameFields:
				if gameField.get("name") == currRomName:
					redumpCategory = gameField.find("category").text
					break
			if redumpCategory != "Games":
				currGameFolder = path.join(currGameFolder, "["+redumpCategory+"]")
		elif "(Sample" in bestRom or "(Demo" in bestRom:
			currGameFolder = path.join(currGameFolder, "[Demos]")
		currGameFolder = path.join(currGameFolder, game)
		if romsetCategory == "Full":
			for rom in gameRomDict[game]:
				sourceRomPath = path.join(currSystemSourceFolder, rom)
				targetRomPath = path.join(currGameFolder, rom)
				if not path.exists(targetRomPath):
					try:
						if isExport:
							createdFolder = createDir(currGameFolder)
							shutil.copy(sourceRomPath, targetRomPath)
						currNumCopiedBytes += path.getsize(sourceRomPath)
						romsCopied.append(rom)
					except:
						# progressBar.write("\nFailed to copy: "+rom)
						if createdFolder and len(listdir(createdFolder)) == 0:
							rmdir(createdFolder)
						romsFailed.append(rom)
				else:
					numRomsSkipped += 1
		elif romsetCategory == "1G1R" or bestRegionIsPrimary:
			sourceRomPath = path.join(currSystemSourceFolder, bestRom)
			targetRomPath = path.join(currGameFolder, bestRom)
			if not path.isfile(targetRomPath):
				try:
					if isExport:
						createdFolder = createDir(currGameFolder)
						shutil.copy(sourceRomPath, targetRomPath)
					currNumCopiedBytes += path.getsize(sourceRomPath)
					romsCopied.append(bestRom)
				except:
					# progressBar.write("\nFailed to copy: "+bestRom)
					if createdFolder and len(listdir(createdFolder)) == 0:
						rmdir(createdFolder)
					romsFailed.append(bestRom)
			else:
				numRomsSkipped += 1
	progressBar.close()
	createMainCopiedLog(romsCopied, romsFailed, "Export" if isExport else "Test")
	if isExport:
		print("\nCopied "+str(len(romsCopied))+" new files.")
		print("Skipped "+str(numRomsSkipped)+" files that already exist on this device.")
		print("Failed to copy "+str(len(romsFailed))+" new files.")
	else:
		print("\n"+str(len(romsCopied))+" new files would be copied.")
		print(str(numRomsSkipped)+" old files would be skipped.")
	print("Export Size: "+simplifyNumBytes(currNumCopiedBytes))
	return currNumCopiedBytes

def getSpecialFoldersForGame(game):
	currSpecialFolders = []
	for folder in mainConfig["Special Folders"]:
		for keyword in barSplit(mainConfig["Special Folders"][folder]):
			if keyword in game:
				currSpecialFolders.append(folder)
				break
	return currSpecialFolders

def createMainCopiedLog(romsCopied, romsFailed, logType="Export"):
	if len(romsCopied) + len(romsFailed) > 0:
		romsCopied.sort()
		romsFailed.sort()
		romsetLogFile = open(path.join(logFolder, logType+" Main ("+systemName+") ("+deviceName+") ["+str(len(romsCopied))+"] ["+str(len(romsFailed))+"].txt"), "w", encoding="utf-8", errors="replace")
		romsetLogFile.writelines("=== Copied "+str(len(romsCopied))+" new ROMs from "+systemName+" to "+deviceName+" ===\n\n")
		for file in romsCopied:
			romsetLogFile.writelines(file+"\n")
		if len(romsFailed) > 0:
			romsetLogFile.writelines("\n= FAILED TO COPY =\n")
			for file in romsFailed:
				romsetLogFile.writelines(file+"\n")
		romsetLogFile.close()

def copySecondaryRomset():
	print("Secondary Romset\n")
	currSystemSourceFolder = path.join(secondaryRomFolder, systemName)
	currSystemTargetFolder = path.join(outputFolder, systemName)
	numFiles = 0
	for root, dirs, files in walk(currSystemSourceFolder):
		for file in files:
			numFiles += 1
	filesCopied = []
	numFilesSkipped = 0
	filesFailed = []
	currNumCopiedBytes = 0
	progressBar = tqdm(total=numFiles, ncols=80)
	for root, dirs, files in walk(currSystemSourceFolder):
		for fileName in files:
			progressBar.update(1)
			currRoot = root.split(currSystemSourceFolder)[1][1:]
			oldFileDirPathArray = getPathArray(root)
			if arrayOverlap(ignoredFolders, oldFileDirPathArray):
				continue
			sourceRomPath = path.join(root, fileName)
			targetRomDir = path.join(currSystemTargetFolder, currRoot)
			targetRomPath = path.join(targetRomDir, fileName)
			if not path.isfile(targetRomPath):
				try:
					if isExport:
						createdFolder = createDir(targetRomDir)
						shutil.copy(sourceRomPath, targetRomPath)
					currNumCopiedBytes += path.getsize(sourceRomPath)
					filesCopied.append(targetRomPath)
				except:
					# print("\nFailed to copy: "+sourceRomPath)
					if createdFolder and listdir(targetRomDir) == 0:
						rmdir(targetRomDir)
					filesFailed.append(sourceRomPath)
			else:
				numFilesSkipped += 1
	progressBar.close()
	createSecondaryCopiedLog(filesCopied, filesFailed, "Export" if isExport else "Test")
	if isExport:
		print("\nCopied "+str(len(filesCopied))+" new "+pluralize("file", len(filesCopied))+".")
		print("Skipped "+str(numFilesSkipped)+pluralize(" file", numFilesSkipped)+" that already exist on this device.")
		print("Failed to copy "+str(len(filesFailed))+" new "+pluralize("file", len(filesFailed))+".")
	else:
		print("\n"+str(len(filesCopied))+" new files would be copied.")
		print(str(numFilesSkipped)+" old files would be skipped.")
	print("Export Size: "+simplifyNumBytes(currNumCopiedBytes)+" of new files.")
	return currNumCopiedBytes

def createSecondaryCopiedLog(filesCopied, filesFailed, logType="Export"):
	updateFolderName = path.basename(updateFromDeviceFolder)
	if len(filesCopied) + len(filesFailed) > 0:
		filesCopied.sort()
		otherLogFile = open(path.join(logFolder, logType+" Secondary ("+systemName+") ("+deviceName+") ["+str(len(filesCopied))+"] ["+str(len(filesFailed))+"].txt"), "w", encoding="utf-8", errors="replace")
		otherLogFile.writelines("=== Copied "+str(len(filesCopied))+" new "+pluralize("file", len(filesCopied))+" from "+updateFolderName+" to "+deviceName+" ===\n\n")
		for file in filesCopied:
			otherLogFile.writelines(file+"\n")
		if len(filesFailed) > 0:
			otherLogFile.writelines("\n= FAILED TO COPY =\n")
			for file in filesFailed:
				otherLogFile.writelines(file+"\n")
		otherLogFile.close()

def updateSecondary():
	updateFolderName = path.basename(updateFromDeviceFolder)
	print("\nUpdating "+updateFolderName+" folder from "+deviceName+".\n")
	createDir(updateFromDeviceFolder)
	filesCopied = []
	numFilesSkipped = 0
	filesFailed = []
	currNumCopiedBytes = 0
	for root, dirs, files in walk(outputFolder):
		dirs[:] = [d for d in dirs if d not in barSplit(deviceConfig["Special Categories"]["Do Not Copy From Device"])]
		currRoot = root.split(outputFolder)[1][1:]
		try:
			currSystem = getPathArray(currRoot)[0]
		except:
			currSystem = ""
		for file in files:
			fileInOutput = path.join(root, file)
			fileInRomset = path.join(mainRomFolder, currSystem, file)
			fileInSecondary = path.join(secondaryRomFolder, currRoot, file)
			updateFolder = path.join(updateFromDeviceFolder, currRoot)
			fileInUpdate = path.join(updateFolder, file)
			if not (path.isfile(fileInRomset) or path.isfile(fileInSecondary) or path.isfile(fileInUpdate)):
				try:
					if isExport:
						createDir(updateFolder)
						shutil.copy(fileInOutput, fileInUpdate)
					# print("From "+deviceName+" to "+updateFolderName+": "+fileInUpdate)
					currNumCopiedBytes += path.getsize(fileInOutput)
					filesCopied.append(fileInUpdate)
				except:
					# print("Failed to copy: "+fileInOutput)
					filesFailed.append(fileInOutput)
	# print("\nUpdated "+updateFolderName+" folder with "+str(len(filesCopied))+" new files.")
	# print("\nRemoving empty folders from "+updateFolderName+"...")
	removeEmptyFolders(updateFromDeviceFolder)
	createUpdateToSecondaryLog(filesCopied, filesFailed, "Update" if isExport else "Test Update")
	if isExport:
		print("\nCopied "+str(len(filesCopied))+" new "+pluralize("file", len(filesCopied))+".")
		print("Skipped "+str(numFilesSkipped)+pluralize(" file", numFilesSkipped)+" that already exist on this device.")
		print("Failed to copy "+str(len(filesFailed))+" new "+pluralize("file", len(filesFailed))+".")
	else:
		print("\n"+str(len(filesCopied))+" new files would be copied.")
		print(str(numFilesSkipped)+" old files would be skipped.")
	print("Export Size: "+simplifyNumBytes(currNumCopiedBytes)+" of new files.")
	return currNumCopiedBytes

def createUpdateToSecondaryLog(filesCopied, filesFailed, logType="Update"):
	updateFolderName = path.basename(updateFromDeviceFolder)
	if len(filesCopied) + len(filesFailed) > 0:
		filesCopied.sort()
		otherLogFile = open(path.join(logFolder, logType+" ("+deviceName+") ["+str(len(filesCopied))+"] ["+str(len(filesFailed))+"].txt"), "w", encoding="utf-8", errors="replace")
		otherLogFile.writelines("=== Copied "+str(len(filesCopied))+" new "+pluralize("file", len(filesCopied))+" from "+deviceName+" to "+updateFolderName+" ===\n\n")
		for file in filesCopied:
			otherLogFile.writelines(file+"\n")
		if len(filesFailed) > 0:
			otherLogFile.writelines("\n= FAILED TO COPY =\n")
			for file in filesFailed:
				otherLogFile.writelines(file+"\n")
		otherLogFile.close()

#########################
# GLOBAL HELPER METHODS #
#########################

def askForDirectory(string):
	print(string)
	sleep(0.5)
	root = Tk()
	root.withdraw()
	directory = filedialog.askdirectory()
	if directory != "":
		isCorrect = makeChoice("Are you sure this is the correct folder?\n"+directory, ["Yes", "No"])
		if isCorrect == 2:
			directory = ""
	return directory

def initScreen():
	clearScreen()
	print()
	printTitle("Rom Organizer 3")
	print()

def barSplit(string):
	if string.strip() == "":
		return []
	return string.split("|")

###############
# HELP SCREEN #
###############

def printHelp():
	clearScreen()
	print("\nSet main ROM folder")
	print(limitedString("Allows you to set a main rom folder. This is the directory that contains system folders, which contain No-Intro verified roms.",
		80, "- ", "  "))
	print(limitedString("Example: MAINFOLDER/Sega Genesis/Sonic the Hedgehog (USA, Europe).zip",
		80, "- ", "  "))
	print("\nSet secondary ROM folder")
	print(limitedString("(Optional) Allows you to set a secondary rom folder. This is a directory that contains system folders, which can contain unverified roms/other files (rom hacks, homebrew, etc).",
		80, "- ", "  "))
	print(limitedString("Example: SECONDARYFOLDER/Sega Genesis/[Hacks]/Sonic/Sonic 2 Delta.zip",
		80, "- ", "  "))
	print("\nUpdate/audit verified romsets")
	print(limitedString("Updates the names of misnamed roms (and the ZIP files containing them, if applicable) according to the rom's entry in the No-Intro Parent/Clone DAT. This is determined by the rom's matching hash code in the DAT, so the original name doesn't matter.",
		80, "- ", "  "))
	print(limitedString("For each system, creates a log file indicating which roms exist in the romset, which roms are missing, and which roms are in the set that don't match anything from the DAT.",
		80, "- ", "  "))
	print(limitedString("Note: Only systems with a No-Intro database can have their rom names updated, as disc-based systems often use a compression method that changes the file's hash, making hash verification impossible.",
		80, "- ", "  "))
	print("\nCreate new device profile")
	print(limitedString("Create a new device profile. This is a text file that indicates the following:",
		80, "- ", "  "))
	print(limitedString("Which systems from your rom collection should be copied",
		80, "  - ", "    "))
	print(limitedString("Whether each system should include all roms (Full), one rom per game (1G1R), or one rom per game while ignoring games that don't have a version from your primary region(s) (1G1R Primary)",
		80, "  - ", "    "))
	print(limitedString("Primary region(s); these folders will not be created in romset organization; instead, their contents are added to the root folder of the current system.",
		80, "  - ", "    "))
	print(limitedString("Which folders, if any, exist in your device's rom folder that you do not want to copy back to the main folder.",
		80, "  - ", "    "))
	print("\nUpdate device profile")
	print(limitedString("Update an existing device profile for newly-added folders in your main and secondary rom folders.",
		80, "- ", "  "))
	print("\nExport romset")
	print(limitedString("Exports romset according to current device profile. Either all systems or a subset of systems may be chosen, and roms that already exist on the device are not re-exported, allowing you to simply update a device with newly-added roms.",
		80, "- ", "  "))
	print(limitedString("May also export contents of the secondary folder, according to current device profile.",
		80, "- ", "  "))
	print("\nTest export of romset")
	print(limitedString("Same as \"Export romset\", except files are not actually exported; instead, you are shown how many files would be exported per system and how much additional space they would use on your device.",
		80, "- ", "  "))
	print(limitedString("This is useful if you want to know how much space an export would require before exporting to a device with little free space.",
		80, "- ", "  "))
	inputHidden("\nPress Enter to continue.")

if __name__ == '__main__':
	main()
