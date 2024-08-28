import os
import mutagen 
import argparse
import sys 
import re
import glob
from mutagen._util import MutagenError
from base64 import b64encode

def filterAudioFiles(tag, value, audio_files):
    if tag not in ["album", "artist", "genre", "tracknumber", "title"]:
        print("ERROR: Invalid tag. Possible values are album, artist, genre, tracknumber and title.")
    else:
        filtered_audio_files = [file for file in audio_files if re.match(value, file[0].tags[tag][0])]
        if len(audio_files) < 1:
            print("Filter returned an empty argument list. Defaulting to whole argument list.")
            return audio_files
        else:
            return filtered_audio_files

def interactiveMode(audio_files):
    choice = ""
    while choice != "exit" and choice != "quit":
        choice = input("flacman> ")
        if choice == "help":
            print(
                '''
flacmanager interacive mode commands
------------------------------------
    help - Prints this help.
    list - Lists audio files.
    check - Checks audio files for errors.
    tweak - Iterates through audio files and prompts the user for tag modification.
    zero-padding - Adds a zero before every single digit, in order to sort the tracks by tracknumber correctly.
    exit or quit - Quits the interactive mode.
------------------------------------
'''
            )
        elif choice == "list":
            printMetadata(audio_files)
        elif choice == "check":
            printMetadataIssues(audio_files)
        elif choice == "zero-padding":
            zeroPadding(audio_files)
        elif choice == "modify":
            tag = input(" What tag do you wish to modify? (album/artist/genre/tracknumber/title)? ")
            value = input(" What is the new value? ")
            modifyMetadata(tag, value, audio_files)
        elif choice == "tweak":
            tweakAudioFiles(audio_files)

def zeroPadding(audio_files):
    counter = 0
    for file in audio_files:
        tracknumber = file[0].tags["tracknumber"][0]
        if len(tracknumber) == 1 and tracknumber.isdigit():
            file[0].tags["tracknumber"] = "0" + tracknumber
            file[0].save()
            counter+=1
    if counter == 0:
        print("No changes were made.")

def tweakAudioFiles(audio_files):
    tag = input(" What tag do you wish to modify (album/artist/genre/tracknumber/title)? ")
    for file in audio_files:
        old_value = "(Old value = " + file[0].tags[tag][0] + ")" if tag in file[0].tags else ""
        value = input(" New value for the " + tag.upper() + " tag of '" + os.path.basename(file[1]) + "' ? " + old_value + " - /c to continue, q to exit/ ")
        if value == 'q':
            break
        elif value == 'c':
            continue
        else:
            file[0].tags[tag] = value
            file[0].save()

def addPicture(picture, audio_files):
    # Checking if the picture provided is valid
    image_exts = [".jpg", ".jpeg", ".bmp", ".png", ".gif"]
    if not os.path.exists(picture) or not os.path.splitext(picture)[1] in image_exts:
        print("ERROR: {} is not a valid image file.".format(picture))
    else:
        # Creating the cover art
        coverArt = mutagen.flac.Picture()
        with open(picture, "rb") as image_data:
            coverArt.data = image_data.read()

        coverArt.type = mutagen.id3.PictureType.COVER_FRONT
        coverArt.mime = u"image/jpeg"
        coverArt.width = 500
        coverArt.height = 500
        coverArt.depth = 16

        # Adding the cover art to each file
        choice = input(picture + " will be the new cover art for " + str(len(audio_files)) + " files. Proceed? (Y/n) ")
        if choice == 'Y':
            for file in audio_files:
                if type(file) is mutagen.flac.FLAC :
                    file[0].clear_pictures()
                    file[0].add_picture(coverArt)
                else :
                    file[0]['metadata_block_picture'] = b64encode(coverArt.write()).decode('ascii')
                file[0].save()


def modifyMetadata(tag, value, audio_files):
    if tag not in ["album", "genre", "artist", "tracknumber", "title"]:
        print("ERROR: {} is not a valid tag. Please provide a valid metadata tag. See -l/--list for a list of all relevant metadata tags.".format(tag))
    else:
        choice = input(value + " will be the new value for the " + tag.upper() + " tag for " + str(len(audio_files)) + " files. Proceed? (Y/n) ")
        if choice == 'Y':
            for file in audio_files:
                file[0].tags[tag.upper()] = value
                file[0].save()

def sortAudioFiles(audio_files, path=""):
    new_audio_files = []
    for file in audio_files:
        if "artist" in file[0].tags:
            artist = file[0].tags["artist"][0]
            if"album" in file[0].tags:
                album = file[0].tags["album"][0]
            else:
                album = "Unknown Album"
        else:
            artist = "Unknown Artist"
        albumPath = os.path.normpath(os.path.abspath(path) + "/" + artist + "/" + album)
        if not os.path.isdir(albumPath):
            os.makedirs(albumPath)
        os.rename(file[1], os.path.normpath(albumPath + "/" + os.path.basename(file[1])))
        new_audio_files.append((file[0], os.path.normpath(albumPath + "/" + os.path.basename(file[1])))) 
    return new_audio_files

def renameAudioFiles(audio_files):
    new_audio_files = []
    for file in audio_files:
        if "tracknumber" in file[0].tags and "title" in file[0].tags:
            filename = os.path.normpath(os.path.dirname(file[1]) + "/" + file[0].tags["tracknumber"][0] + " - " + file[0].tags["title"][0] + os.path.splitext(file[1])[1])
            os.rename(file[1], filename)
            new_audio_files.append((file[0], filename))
        else:
            print("Could not rename {} : missing tags.".format(os.path.basename(file[1])))
    return new_audio_files


def printMetadataIssues(audio_files):
    tags = ["album" , "genre", "artist", "tracknumber", "title"]
    badFiles = 0
    for file in audio_files:
        issues = 0
        issuesList = " "
        for tag in tags:
            if tag not in file[0].tags:
                issues += 1
                issuesList += tag
            elif tag == "tracknumber" and len(file[0].tags[tag][0]) < 2:
                issues += 1
                issuesList += "bad_tracknumber_format"
            elif file[0].tags[tag][0].count('?') or file[0].tags[tag][0].count('!') or file[0].tags[tag][0].count('/') or file[0].tags[tag][0].count('\\'):
                issues += 1
                issuesList += "bad_characters(" + tag + ")"
            issuesList += " "
        if issues>0:
            badFiles += 1
            print("{} issue(s) found for \'{}\' ({}).".format(issues, os.path.basename(file[1]), issuesList))
    print("{}/{} file(s) with metadata issues found.".format(badFiles, len(audio_files)))

def getAlbum(file):
    return file[0].tags["album"][0] if "album" in file[0].tags else "N/A"

def printMetadata(audio_files):
    audio_files.sort(key=getAlbum)
    print("{:<40} {:<20} {:<30} {:<10} {:<50} {:<50}".format('Album', 'Genre', 'Artist', '#', 'Title', 'Filename'))
    for file in audio_files:
        album = file[0].tags["album"][0] if "album" in file[0].tags else "N/A"
        genre = file[0].tags["genre"][0] if "genre" in file[0].tags else "N/A"
        artist = file[0].tags["artist"][0] if "artist" in file[0].tags else "N/A"
        tracknumber = file[0].tags["tracknumber"][0] if "tracknumber" in file[0].tags else "N/A"
        title = file[0].tags["title"][0] if "title" in file[0].tags else "N/A"
        filename = os.path.basename(file[1])
        print("{:<40} {:<20} {:<30} {:<10} {:<50} {:<50}".format(album, genre, artist, tracknumber, title, filename))

def parseAudioFiles(arguments):
    audio_files = []
    mutagen_file = None
    for file in list(arguments):
        try:
            mutagen_file = mutagen.File(file)
        except MutagenError:
            print("Something went wrong when trying to read some audio files given as arguments.")
        if mutagen_file is not None:
            audio_files.append((mutagen.File(file), file))
    if not audio_files:
        print("No valid audio files found in arguments. Nothing to do.")
        sys.exit()
    return audio_files

def parseAudioDirectories(arguments, is_recursive=False):
    audio_files = []
    mutagen_file = None
    glob_regex = "/*" if not is_recursive else "/**/*"
    for directory in arguments:
        for file in glob.glob(directory + glob_regex, recursive=is_recursive):
            if not os.path.isdir(file):
                try:
                    mutagen_file = mutagen.File(file)
                except MutagenError:
                    print("Something went wrong while trying to read some audio files in the directories given as arguments.")
                if mutagen_file is not None:
                    audio_files.append((mutagen.File(file), file))
    if not audio_files:
        print("No valid audio files found in the directories given as arguments. Nothing to do.")
        sys.exit()
    return audio_files

def orderAudioFiles(audio_files):
    for file in audio_files:
        if "tracknumber" in file[0].tags and "title" in file[0].tags:
            new_title = file[0].tags["tracknumber"][0] + " - " + file[0].tags["title"][0]
            file[0].tags["TITLE"] = new_title
            file[0].save()
        else:
            print("Could not rename {} : missing tags.".format(os.path.basename(file[1])))

def deleteMetadataTags(audio_files):
    print("WARNING : This will remove ALL metadata from the selected files, do you want to proceed? Y/N")
    choice = input()
    if choice == "Y":
        for file in audio_files:
            file[0].delete()
            file[0].clear_pictures()
            file[0].save()
        print("The selected files have successfully had their metadata deleted.")
    else:
        print("No modifications have been made.")


# Creating the parser
parser = argparse.ArgumentParser(description='Manages metadata for multiple audio formats.')
parser.add_argument("input", metavar="files", nargs="+", help='audio file(s)')
parser.add_argument("-d", "--directory", action="store_true", help='Takes directories containing audio files as argument.')
parser.add_argument("-R", "--recursive", action="store_true", help='Searches recursively in the directories provided as arguments. Can only be used in conjonction with the -d/--directory flag.')
parser.add_argument("-l", "--list", action="store_true", default=False, help='Prints the metadata of the audio files.')
parser.add_argument("-c", "--check", action="store_true", default=False, help='Prints metadata issues (missing tags or album covers).')
parser.add_argument("-r", "--rename", action="store_true", default=False, help='Renames files using tracknumber and title metadata.')
parser.add_argument("-s", "--sort", metavar="destination", nargs="?", help='Sorts audio files by artist and by album in folders at the destination specified.')
parser.add_argument("-m", "--modify", nargs=2, metavar=('TAG','VALUE'), help='Modifies TAG value to VALUE.')
parser.add_argument("-p", "--picture", nargs=1, metavar="IMAGE", help="Adds IMAGE as cover art.")
parser.add_argument("-i", "--interactive", action="store_true", default=False, help='Interactive mode.')
parser.add_argument("-f", "--filter", nargs=2, metavar=('TAG', 'VALUE'), help="Filters the input files using tag values.")
parser.add_argument("-o", "--order", action="store_true", help="Appends the tracknumber (if it exists) to the title tag value, useful for some devices.")
parser.add_argument("-z", "--zeropadding", action="store_true", help="Automatic left zero-padding for single-digit tracknumbers, so that they're ordered properly.")
parser.add_argument("-D", "--delete", action="store_true", help='Deletes every metadata tag from the audio files given as arguments.')
args = parser.parse_args()

# Access the input arguments

if args.directory:
    audio_files = parseAudioDirectories(args.input, args.recursive) 
else:
    audio_files = parseAudioFiles(args.input)

if args.filter:
    audio_files=filterAudioFiles(args.filter[0], args.filter[1], audio_files)

if args.interactive:
    interactiveMode(audio_files)
else:
    if args.delete:
        deleteMetadataTags(audio_files)

    if args.zeropadding:
        zeroPadding(audio_files)

    if args.rename:
        audio_files = renameAudioFiles(audio_files)

    if args.order:
        orderAudioFiles(audio_files)

    if args.modify:
        modifyMetadata(args.modify[0], args.modify[1], audio_files)

    if args.sort:
        # If no directory is found after the -s/--sort flag, default to current directory
        if os.path.isdir(args.sort):
            audio_files = sortAudioFiles(audio_files, args.sort)
        else:
            audio_files = sortAudioFiles(audio_files)

    if args.picture:
        addPicture(args.picture[0], audio_files)

    if args.list:
        printMetadata(audio_files)

    if args.check:
        printMetadataIssues(audio_files)
