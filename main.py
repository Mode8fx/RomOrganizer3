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

progFolder = getCurrFolder()
sys.path.append(progFolder)

mainConfig = configparser.ConfigParser(allow_no_value=True)
mainConfig.optionxform = str
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

crcHasher = FileHash('crc32')

########
# MAIN #
########

def main():
	prepareMainConfig()
	createDir(logFolder)
	while True:
		initScreen()
		choice = makeChoice("Select an option.", ["Update/audit main romsets", "Create new device profile", "Export romset", "Help", "Exit"])
		print()
		if choice == 1:
			updateAndAuditMainRomsets()
		elif choice == 2:
			createDeviceProfile()
		elif choice == 3:
			exportRomsets()
		elif choice == 4:
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
		currSystemXML = path.join(noIntroDir, currSystemName+".dat")
		if not path.exists(currSystemXML):
			print("XML not found for "+currSystemXML)
			continue
		tree = ET.parse(currSystemXML)
		root = tree.getroot()
		allGameFields = root[1:]
		allGameNamesInXML = {}
		for game in allGameFields:
			allGameNamesInXML[game.get("name")] = False
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
					currDBGameName = game.find("description").text
					allGameNamesInXML[currDBGameName] = True
					if currFileName != currDBGameName:
						currFileExt = path.splitext(currFilePath)[1]
						if path.exists(path.join(currSystemFolder, currDBGameName+currFileExt)): # two of the same file (with different names) exist
							i = 1
							while True:
								incrementedGameName = currDBGameName+" (copy) ("+str(i)+")"
								if not path.exists(path.join(currSystemFolder, incrementedGameName+currFileExt)):
									break
								i += 1
							currDBGameName = incrementedGameName
						if zipfile.is_zipfile(currFilePath):
							renameArchiveAndContent(currFilePath, currDBGameName)
						else:
							rename(currFilePath, path.join(currSystemFolder, currDBGameName+currFileExt))
							print("Renamed "+currFileName+" to "+currDBGameName+"\n")
					foundMatch = True
					break
			if not foundMatch:
				romsWithoutCRC.append(currFileName+" ("+file+")")
		xmlRomsInSet = [key for key in allGameNamesInXML.keys() if allGameNamesInXML[key] == True]
		xmlRomsNotInSet = [key for key in allGameNamesInXML.keys() if allGameNamesInXML[key] == False]
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
	global mainConfig, mainRomFolder, secondaryRomFolder, specialFolders, specialAttributes
	if path.exists(mainConfigFile):
		mainConfig.read(mainConfigFile)
	else:
		createMainConfig()
	mainRomFolder = mainConfig["ROM Folders"]["Main ROM Folder"]
	secondaryRomFolder = mainConfig["ROM Folders"]["Secondary ROM Folder"]
	specialFolders = mainConfig["Special Folders"]
	specialAttributes = mainConfig["Special ROM Attributes"]["Keywords"].split("|") + mainConfig["Special ROM Attributes"]["Sources"].split("|")

def createMainConfig():
	global mainConfig
	mainConfig["ROM Folders"] = {}
	mainConfig.set('ROM Folders', '# The directory of the main ROM folder you want to export from, which contains No-Intro verified ROMs. If you leave this blank, the program will ask for this folder when you try to export romsets.')
	mainConfig["ROM Folders"]["Main ROM Folder"] = ""
	mainConfig.set('ROM Folders', '# The directory of the secondary ROM folder you want to export from, which can contain unverified ROMs/other files (this is intended for rom hacks, homebrew, etc). If you leave this blank, the program will ask for this folder when you try to export the secondary folder.')
	mainConfig["ROM Folders"]["Secondary ROM Folder"] = ""
	mainConfig["Special Folders"] = {}
	mainConfig.set('Special Folders', '# Special Folders are folders that are created on your device upon export for verified ROMs cith certain substrings in their filenames.')
	mainConfig.set('Special Folders', '# For example, any ROM with \"2 Games in 1 - \" in its name will be exported to a subfolder called \"Compilation\".')
	mainConfig.set('Special Folders', '# You could then choose to ignore any ROMs marked as \"Compilation\" when exporting to a specific device (see device profiles).')
	mainConfig.set('Special Folders', '# Feel free to add additional Special Folders (or add to existing folders) using the format below (with \"|\" as a delimiter).')
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
	mainConfig["Special ROM Attributes"] = {}
	mainConfig.set('Special ROM Attributes', '# (Advanced) Special ROM Attributes are substrings in verified ROM names (specifically, the parentheses fields in these names) that are ignored when trying to determine the best name for a game.')
	mainConfig.set('Special ROM Attributes', '#            \"Sources\" are also used in determining the best ROM for 1G1R sets (they are given lower priority).')
	mainConfig["Special ROM Attributes"]["Keywords"] = "|".join([
		"Rev", "Beta", "Proto", "Unl", "v", "GB Compatible", "SGB Enhanced", "Demo",
		"Disc", "Promo", "Sample", "DLC", "WiiWare", "Minis", "Club Nintendo",
		"Aftermarket", "Test Program", "Competition Cart", "NES Test", "Promotion Card"
		])
	mainConfig["Special ROM Attributes"]["Sources"] = "|".join([
		"Virtual Console", "Switch Online", "GameCube", "Namcot Collection",
		"Namco Museum Archives"
		])
	with open(mainConfigFile, 'w') as mcf:
		mainConfig.write(mcf)
	print("Created new settings.ini")
	inputHidden("Press Enter to continue.")

def selectDeviceProfile():
	deviceProfiles = listdir(profilesFolder)
	if len(deviceProfiles) > 0:
		dp = makeChoice("\nSelect a device profile (which device are you copying to?)", [path.splitext(prof)[0] for prof in deviceProfiles]+["Create new profile", "Back to menu"])
		if dp == len(deviceProfiles)+1:
			createDeviceProfile()
			return False
		elif dp == len(deviceProfiles)+2:
			return False
		else:
			dn = deviceProfiles[dp-1]
			deviceProfile = path.join(profilesFolder, dn)
			deviceName = path.splitext(dn)[0]
			return True
	else:
		print("\nNo device profiles found. Please create a new one.")
		inputHidden("Press Enter to continue.")
		return False

def createDeviceProfile():
	global deviceName
	global deviceProfile

	print("\nFollow these steps to create a new device profile.")
	deviceName = ""
	while deviceName == "":
		print("\n(1/5) What would you like to name this profile?")
		deviceName = input().strip()
	deviceProfile = path.join(profilesFolder, deviceName+".txt")
	dpFile = open(deviceProfile, "w")
	dpFile.writelines(": Romsets\n")
	print("\n(2/5) Please define how each romset should be copied to this device.")
	for d in systemDirs:
		copyType = makeChoice(d, ["Full (copy all contents)",
			"1G1R (copy only the most significant rom for each game)",
			"1G1R Primary (same as 1G1R, but ignore games that do not have a rom for a primary region (explained in question 4)",
			"None (skip this system)"])
		if copyType == 1:
			copyType = "Full"
		elif copyType == 2:
			copyType = "1G1R"
		elif copyType == 3:
			copyType = "1G1R Primary"
		else:
			copyType = "None"
		dpFile.writelines(d+"\n"+copyType+"\n")
	if otherFolder != "":
		dpFile.writelines("\n\n\n: Other\n")
		print("\nPlease define whether or not each folder in the Other category should be copied to this device.")
		for d in otherDirs:
			copyType = makeChoice(d, ["Yes", "No"])
			if copyType == 1:
				copyType = "True"
			else:
				copyType = "False"
			dpFile.writelines(d+"\n"+copyType+"\n")
	else:
		print("\n(2/5) [You do not have an Other folder. Skipping this question.")
	dpFile.writelines("\n\n\n: Ignore\n")
	print("\n(3/5) Please type the exact names of any folders you would like to skip in copying. Remember that subfolders generated by this program are included in brackets [].")
	print("For example, if you wanted to skip all Japanese roms, you would type [Japan] (including the brackets), followed by Enter.")
	print("Type DONE (in all caps) followed by Enter when you are done.")
	print("Common subfolders are [USA], [Europe], [Japan], [Other (English)], [Other (non-English)],")
	print("[Unlicensed], [Unreleased], [Compilations] (only for 2/3/4 in 1 GBA games), [NES & Famicom] (only for GBA ports of NES/Famicom games), and [GBA Video]")
	while True:
		currChoice = input().strip()
		if currChoice == "DONE":
			break
		if currChoice != "":
			dpFile.writelines(currChoice+"\n")
	dpFile.writelines("\n\n\n: Primary Regions\n")
	print("\n(4/5) Please type the exact names of any folders you would like to prioritize in copying. Remember that subfolders generated by this program are included in brackets [].")
	print("These folders will not be created in romset organization; instead, their contents are added to the root folder of the current system.")
	print("For example, if you wanted all USA roms in the root folder instead of a [USA] subfolder, you would type [USA] (including the brackets), followed by Enter.")
	print("Type DONE (in all caps) followed by Enter when you are done.")
	print("Common subfolders are [USA], [Europe], [Japan], [Other (English)], and [Other (non-English)]")
	while True:
		currChoice = input().strip()
		if currChoice == "DONE":
			break
		if currChoice != "":
			dpFile.writelines(currChoice+"\n")
	dpFile.writelines("\n\n\n: Skipped Folders on Device\n")
	print("\n(5/5) Please type the exact names of any folders in your device's rom folder that you do not want to copy back to the main drive.")
	print("These folders will be skipped; this is useful if you keep roms and non-rom PC games in the same folder.")
	print("For example, if you wanted to ignore anything in the \"Steam\" folder, you would type \"Steam\" (no quotes), followed by Enter.")
	print("Type DONE (in all caps) followed by Enter when you are done.")
	print("Common subfolders are Steam, Windows, and PC Games")
	while True:
		currChoice = input().strip()
		if currChoice == "DONE":
			break
		if currChoice != "":
			dpFile.writelines(currChoice+"\n")
	dpFile.close()
	print("\nDevice Profile saved as "+deviceProfile+".")
	sleep(1)
	inputHidden("Press Enter to continue.")

##########
# EXPORT #
##########

def exportRomsets():
	initScreen()
	if not selectDeviceProfile():
		return

	currProfileSystemDirs = [d for d in systemDirs if getRomsetCategory(d) != "None"]
	if len(currProfileSystemDirs) == 0:
		if len(systemDirs) > 0:
			print("The current profile does not allow any romsets.")
		systemChoices = []
	else:
		systemChoices = makeChoice("Select romset(s). You can select multiple choices by separating them with spaces:", currProfileSystemDirs+["All", "None"], allowMultiple=True)
		if len(currProfileSystemDirs)+2 in systemChoices:
			systemChoices = []
		elif len(currProfileSystemDirs)+1 in systemChoices:
			systemChoices = list(range(1, len(currProfileSystemDirs)+1))
	if otherFolder != "":
		otherFolderName = path.basename(otherFolder)
		currProfileOtherDirs = [d for d in otherDirs if getOtherCategory(d) == "True"]
		if len(currProfileSystemDirs) == 0:
			if len(otherDirs) > 0:
				print("The current profile does not allow any "+otherFolderName+" folders.")
			otherChoices = []
		else:
			otherChoices = makeChoice("Select system(s) from "+otherFolderName+" folder. You can select multiple choices by separating them with spaces:", currProfileOtherDirs+["All", "None"], allowMultiple=True)
			if len(currProfileOtherDirs)+2 in otherChoices:
				otherChoices = []
			elif len(currProfileOtherDirs)+1 in otherChoices:
				otherChoices = list(range(1, len(currProfileOtherDirs)+1))
		if updateFromDeviceFolder != "":
			updateOtherChoice = makeChoice("Update \""+path.basename(updateFromDeviceFolder)+"\" folder by adding any files that are currently exclusive to "+deviceName+"?", ["Yes", "No"])
		else:
			updateOtherChoice = 2
	ignoredAttributes = getIgnoredAttributes()
	primaryRegions = getPrimaryRegions()
	skippedFoldersOnDevice = getSkippedOtherFolders()

##################
# HELPER METHODS #
##################

def askForDirectory(string):
	print("\n"+string)
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

###############
# HELP SCREEN #
###############

def printHelp():
	clearScreen()
	print("\n")
	print("Update/audit romsets")
	print("- Updates the names of misnamed roms (and the ZIP files containing them, if")
	print("  applicable) according to the rom's entry in the No-Intro Parent/Clone XML.")
	print("  This is determined by the rom's matching hash code in the XML.")
	print("- For each system, creates a log file indicating which roms exist in the romset,")
	print("  which roms are missing, and which roms are in the set that don't match")
	print("  anything form the XML.")
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
