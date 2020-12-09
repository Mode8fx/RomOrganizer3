# Rom Organizer 3

This is a program that uses [No-Intro](https://datomatic.no-intro.org/) and/or [Redump](http://redump.org/) database files to create an organized copy of a local romset. The intent is to keep an unorganized collection of verified roms (plus unverified roms such as rom hacks) on one drive, while using this program to create curated sets for each of your individual devices with minimal work required for upkeep. You can create a profile for each device indicating what should/shouldn't be copied so you don't have to remember your preferences every time you update a device. Running time is also low in upkeep since files that already exist on the target drive aren't re-copied.

This is the successor to Rom Organizer and Rom Organizer Deluxe, including many features to (hopefully) make organizing your collection simple and fast:

###### Multiple romset types
It can export the following types of romsets on a per-system basis:
- Merged (one folder is created for each game, containing all versions of that game)
- 1G1R (1 Game 1 Rom; one folder is created for each game, containing only the "best" version of a game; ideally, the latest non-demo/proto revision from your region)
- 1G1R Primary (same as 1G1R, but any games that do not have a version from your region are ignored)

###### Auto-renaming
Misnamed roms are automatically renamed using the matching CRC32 hash found in the included database files (you can also download your own database files from the links above); this applies to both the rom itself and, if applicable, a ZIP file containing the rom.

###### Region sorting
Games are sorted by region, in descending order of priority; for example, if your regions are sorted as USA>Europe>Japan, and a game has European and Japanese roms but not USA, that game's folder is placed in the Europe folder. You also have the option of putting games from your primary region(s) in the root folder instead of a subfolder. See the bottom of this readme for an example.

###### Special categories
Certain games are organized into additional subfolders based on their names, such as "Compilation" and "GBA Video", with the option to skip these folders and their games during export. You can define your own categories in the settings.ini file.

###### Support for unverified roms
After exporting your verified rom following the preferences you've defined, this can also copy all files from a secondary folder onto your device, which is useful if you have a separate folder for things like rom hacks or homebrew.

###### Keep your devices in parity
Additionally, it can also copy any files that only exist in your target device's rom folder (and not in your source drive's main or secondary folder) back onto your source drive. This way, you won't have to remember what files you've added to each device individually; they'll all stay up to date.

###### Log files
Finally, this will create logs that track what files are missing from your local romset as indicated by the database files, along with logs of what files were copied to/from your target drive.

### Device Profile
You can create a device profile that saves settings for that device's curated rom collection. The settings are:
- Which romsets should be copied in Full, 1G1R, 1G1R Primary, or None
- Which folders from your secondary folder should be copied
- Which folders should not be copied (for example, you can ignore any file that was originally in a [Homebrew] folder, or skip any roms in the [Japan] region)
- Which regions are set as primary (any roms from these regions will be saved in the root directory instead of a separate region folder)

### Example Output
For example, your local romset containing:
```
C:/Roms/Sega Genesis/My Game 1 (USA).zip
C:/Roms/Sega Genesis/My Game 1 (USA) (Rev 1).zip
C:/Roms/Sega Genesis/My Game 1 (Europe).zip
C:/Roms/Sega Genesis/My Game 1 (Japan).zip
C:/Roms/Sega Genesis/My Game 2 (Europe).zip
C:/Roms/Sega Genesis/My Game 2 (Japan).zip
```
... provided you have a database file with the same name as the system:
```
D:/Tools/No-Intro Database/Sega Genesis.dat
```
... will be copied and sorted as:
```
F:/Roms/Sega - Sega Genesis/USA/My Game 1/My Game 1 (USA).zip
F:/Roms/Sega - Sega Genesis/USA/My Game 1/My Game 1 (USA) (Rev 1).zip
F:/Roms/Sega - Sega Genesis/USA/My Game 1/My Game 1 (Europe).zip
F:/Roms/Sega - Sega Genesis/USA/My Game 1/My Game 1 (Japan).zip
F:/Roms/Sega - Sega Genesis/Europe/My Game 2/My Game 2 (Europe).zip
F:/Roms/Sega - Sega Genesis/Europe/My Game 2/My Game 2 (Japan).zip
```
All versions of My Game 1 are stored in the USA folder since a USA version exists, while all versions of My Game 2 are stored in the Europe folder because a USA version does not exist, but a European version does. By default, USA roms are prioritized, followed by Europe, then other English-speaking regions (and any game with an English rom), then Japan, then everything else. You can define your own region settings in the settings.ini file.

### Disclaimer
This is not a rom downloader, nor does it include any information on how to obtain roms. You are responsible for legally obtaining your own roms for use with this program.
