import sys
from os import path

def rebuildSettingsFile():
	# the same folder where this program is stored
	if getattr(sys, 'frozen', False):
		mainFolder = path.dirname(sys.executable) # EXE (executable) file
	else:
		mainFolder = path.dirname(path.realpath(__file__)) # PY (source) file
	sys.path.append(mainFolder)

	settingsFile = open(path.join(mainFolder, "settings.py"), "w")
	settingsFile.writelines("""import sys\
\nfrom os import path\
\n\
\n# the same folder where this program is stored\
\nif getattr(sys, 'frozen', False):\
\n	mainFolder = path.dirname(sys.executable) # EXE (executable) file\
\nelse:\
\n	mainFolder = path.dirname(path.realpath(__file__)) # PY (source) file\
\nsys.path.append(mainFolder)\
\n\
\ndriveLetter = path.splitdrive(mainFolder)[0]+\"\\\\\"\
\n\
\n########################\
\n# EDIT BELOW THIS LINE #\
\n########################\
\n\
\n# These are only examples; make sure you replace them with your own directories.\
\n\
\n\"\"\"\
\nA directory can be an absolute path (make sure you put the path in quotes and use two back-slashes to separate folders):\
\nromsetFolder = \"D:\\\\My Files\\\\Verified\"\
\n... or a joined path:\
\nromsetFolder = path.join(\"D:\\\\\", \"My Files\", \"Verified\")\
\n\
\ndriveLetter is the drive where this program is stored (example: \"C:\\\\\"),\
\nand mainFolder is the directory where this program is stored\
\n\"\"\"\
\n\
\n# The folder when your current romsets are stored.\
\nromsetFolder = path.join(driveLetter, \"Roms\", \"Verified\")\
\n\
\n# The folder containing roms that aren't part of a set (rom hacks, homebrew, etc.).\
\n# If you don't have an Other folder, leave this as \"\"\
\notherFolder = path.join(driveLetter, \"Roms\", \"Other\")\
\n\
\n# The folder that will be updated with new files from your target device's rom folder.\
\n# You can set this to be the same as romsetFolder (not recommended) or otherFolder if you'd like.\
\n# If you don't want to copy new files from your device to your main drive,\
\n# set updateFromDeviceFolder = \"\"\
\nupdateFromDeviceFolder = path.join(driveLetter, \"Roms\", \"Copy To Other\")\
\n\
\n# The folder containing your No-Intro XMDB files.\
\n# Similar database formats (like XML) will probably work, but these are untested.\
\nnoIntroDir = path.join(mainFolder, \"No-Intro Database\")\
\n\
\n# The folder containing your Redump DAT files.\
\n# Similar database formats (like XML) will probably work, but these are untested.\
\nredumpDir = path.join(mainFolder, \"Redump Database\")\
\n\
\n# The folder containing profiles for each device (these tell the program which merged/1G1R sets to generate).\
\nprofilesFolder = path.join(mainFolder, \"Romset Profiles\")\
\n\
\n# The folder containing generated log files.\
\n# If you don't want to generate log files, set logFolder = \"\"\
\nlogFolder = path.join(mainFolder, \"Logs\")\
\n""")
	settingsFile.close()