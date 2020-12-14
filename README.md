# Rom Organizer 3

This is a program that uses [No-Intro](https://datomatic.no-intro.org/) and/or [Redump](http://redump.org/) database files to create an organized copy of a local romset. The intent is to keep an unorganized collection of verified roms (plus unverified roms such as rom hacks) on one drive, while using this program to create curated sets for each of your individual devices with minimal work required for upkeep. You can create a profile for each device indicating what should/shouldn't be copied so you don't have to remember your preferences every time you update a device. Running time is also low in upkeep since files that already exist on the target drive aren't re-copied.

<img src="https://github.com/GateGuy/RomOrganizer3/blob/main/screenshot%201.png?raw=true" width="500" height="300" />

This is the successor to Rom Organizer and Rom Organizer Deluxe, including many features that aim to make the process of organizing your collection simple and fast:
- Support for multiple romset types (Full, 1G1R, or 1G1R Primary)
- Auto-renaming according to CRC hash (only for No-Intro)
- Header-agnostic hashing; you can verify headered roms using a DAT file for unheadered roms
- Region/language sorting per-game, not just per-rom, with all versions of a game exported to a single game-specific folder
- Define and sort by special categories (compilation, GBA Video, etc), and skip any categories you don't want
- Export your collection using both a main directory (for verified roms) and secondary directory (for rom hacks, homebrew, etc)
- Create multiple device profiles; no need to remember which of your devices can emulate which systems
- Simulate an export; check how much additional disk space your roms would use before attempting to export them
- Detailed log files let you keep track of what's in your collection and what you export

Check the included settings.ini file for a full list of customizable settings.

#### Multiple romset types
Export the following types of romsets on a per-system basis:
- Merged (one folder is created for each game, containing all versions of that game)
- 1G1R (1 Game 1 Rom; one folder is created for each game, containing only the "best" version of a game; ideally, the latest non-demo revision from your region)
- 1G1R Primary (same as 1G1R, but any games that do not have a version from your main region(s) are skipped)

#### Auto-renaming
Misnamed roms are automatically renamed using the matching CRC hash found in the included No-Intro DAT files (you can also download your own DAT files from the links above); this applies to both the rom itself and, if applicable, a ZIP file containing the rom. (Not compatible with Redump due to the common compression methods used for disc-based games)

#### Header-agnostic hashing
For systems that use headered roms (like NES), you have the option to exclude the header during hashing. This allows you to verify headered roms using a DAT file for unheadered roms.

#### Region sorting
Games are sorted by region, in descending order of priority; for example, if your regions are sorted as USA>Europe>Japan, and a game has European and Japanese roms but not USA, that game's folder is placed in the Europe folder. You also have the option of exporting games from your primary region(s) to the root folder instead of a subfolder. See the bottom of this readme for an example.

#### Special categories
Certain games are organized into additional subfolders based on their names, such as "Compilation" and "GBA Video", with the option to skip these folders and their games during export. You can define your own categories in the settings.ini file.

#### Support for unverified roms
In addition to exporting your verified roms following the preferences you've defined, you can also copy all files from a secondary folder onto your device, which is useful if you have a separate folder for things like rom hacks or homebrew.

#### Keep your devices in parity
Additionally, you can also copy any files that only exist in your target device's rom folder (and not in your main or secondary folder) back into a separate folder, which you can manually review and copy back into your main/secondary folder. This way, you won't have to remember what files you've added to each device individually; they'll all stay up to date.

#### Log files
Finally, this will create logs that track what files are missing from your local romset as indicated by the DAT files, along with logs of what files were copied to/from your target drive.

### Device Profile
You can create a device profile that saves settings for that device's curated rom collection. The settings are:
- Which romsets should be copied in Full, 1G1R, 1G1R Primary, or None
- Which folders from your secondary folder should be copied
- Which folders should not be copied (for example, you can skip any file that was originally in a [Homebrew] folder, or skip any roms in the [Japan] region)
- Which regions are set as primary (any roms from these regions will be saved in the root directory instead of a separate region folder)

### Example Output

<img src="https://github.com/GateGuy/RomOrganizer3/blob/main/screenshot%202.png?raw=true" width="300" height="360" /> <img src="https://github.com/GateGuy/RomOrganizer3/blob/main/screenshot%203.png?raw=true" width="237" height="360" />

For example, your local romset containing:
```
C:/Roms/Sega Genesis/My Game 1 (USA).zip
C:/Roms/Sega Genesis/My Game 1 (USA) (Rev 1).zip
C:/Roms/Sega Genesis/My Game 1 (Europe).zip
C:/Roms/Sega Genesis/My Game 1 (Japan).zip
C:/Roms/Sega Genesis/My Game 2 (Europe).zip
C:/Roms/Sega Genesis/My Game 2 (Japan).zip
```
... provided you have a DAT file with the same name as the system:
```
C:/Rom Organizer 3/No-Intro Database/Sega Genesis.dat
```
... will be copied and sorted as:
```
F:/Roms/Sega - Sega Genesis/[USA]/My Game 1/My Game 1 (USA).zip
F:/Roms/Sega - Sega Genesis/[USA]/My Game 1/My Game 1 (USA) (Rev 1).zip
F:/Roms/Sega - Sega Genesis/[USA]/My Game 1/My Game 1 (Europe).zip
F:/Roms/Sega - Sega Genesis/[USA]/My Game 1/My Game 1 (Japan).zip
F:/Roms/Sega - Sega Genesis/[Europe]/My Game 2/My Game 2 (Europe).zip
F:/Roms/Sega - Sega Genesis/[Europe]/My Game 2/My Game 2 (Japan).zip
```
All versions of My Game 1 are stored in the USA folder since a USA version exists, while all versions of My Game 2 are stored in the Europe folder because a USA version does not exist, but a European version does. By default, USA roms are prioritized, followed by Europe, then other English-speaking regions (and any game with an English rom), then Japan, then everything else. Furthermore, if you set USA as a primary region, then these games will be copied and sorted as:
```
F:/Roms/Sega - Sega Genesis/My Game 1/My Game 1 (USA).zip
F:/Roms/Sega - Sega Genesis/My Game 1/My Game 1 (USA) (Rev 1).zip
F:/Roms/Sega - Sega Genesis/My Game 1/My Game 1 (Europe).zip
F:/Roms/Sega - Sega Genesis/My Game 1/My Game 1 (Japan).zip
F:/Roms/Sega - Sega Genesis/[Europe]/My Game 2/My Game 2 (Europe).zip
F:/Roms/Sega - Sega Genesis/[Europe]/My Game 2/My Game 2 (Japan).zip
```
You can define your own region settings in the settings.ini file.

### Disclaimer
This is not a rom downloader, nor does it include any information on how to obtain roms. You are responsible for legally obtaining your own roms for use with this program.
