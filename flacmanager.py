import os
import mutagen
import argparse

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
    order - Iterates through tracks without track numbers and prompts the user.
    exit or quit - Quits the interactive mode.
------------------------------------
'''
                )
        elif choice == "list":
            printMetadata(audio_files)
        elif choice == "check":
            printMetadataIssues(audio_files)
        elif choice == "order":
            orderTracks(audio_files)
        elif choice == "modify"
            tag = input(" What tag do you wish to modify? ")
            value = input(" What is the new value? ")
            modifyMetadata(tag, value, audio_files)

# This could be improved..
def orderTracks(audio_files):
    unordered_tracks = list(filter(lambda item: item is not None, map(lambda track: track if "tracknumber" not in track[0].tags else None, audio_files)))
    if len(unordered_tracks) < 1:
        print("All tracks have a track number. Nothing to do.")
    else:
        for track in unordered_tracks:
            prompt = input("Track number for " + os.path.basename(track[1]) + "? ")
            track[0].tags["tracknumber"] = prompt
            track[0].save()

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
                file[0].add_picture(coverArt)
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
        issuesList = ""
        for tag in tags:
            if tag not in file[0].tags:
                issues+=1
                issuesList+=tag
        if len(file[0].pictures) < 1:
            issues+=1
            issuesList+="album_cover"
        if issues>0:
            badFiles+=1
            print("{} issue(s) found for \'{}\' ({}).".format(issues, os.path.basename(file[1]), issuesList))
    print("{}/{} file(s) with metadata issues found.".format(badFiles, len(audio_files)))

def printMetadata(audio_files):
    print ("{:<40} {:<20} {:<30} {:<10} {:<30} {:<60}".format('Album', 'Genre', 'Artist', '#', 'Title', 'Filename'))
    for file in audio_files:
        album = file[0].tags["album"][0] if "album" in file[0].tags else "N/A"
        genre = file[0].tags["genre"][0] if "genre" in file[0].tags else "N/A"
        artist = file[0].tags["artist"][0] if "artist" in file[0].tags else "N/A"
        tracknumber = file[0].tags["tracknumber"][0] if "tracknumber" in file[0].tags else "N/A"
        title = file[0].tags["title"][0] if "title" in file[0].tags else "N/A"
        filename = os.path.basename(file[1])
        print("{:<40} {:<20} {:<30} {:<10} {:<30} {:<60}".format(album, genre, artist, tracknumber, title, filename))

# Creating the parser
parser = argparse.ArgumentParser(description='Manages metadata for multiple audio formats.')
parser.add_argument("input", metavar="files", nargs="+", help='audio file(s)')
parser.add_argument("-l", "--list", action="store_true", default=False, help='Prints the metadata of the audio files.')
parser.add_argument("-c", "--check", action="store_true", default=False, help='Prints metadata issues (missing tags or album covers).')
parser.add_argument("-r", "--rename", action="store_true", default=False, help='Renames files using tracknumber and title metadata.')
parser.add_argument("-s", "--sort", metavar="destination", nargs="?", help='Sorts audio files by artist and by album in folders at the destination specified.')
parser.add_argument("-m", "--modify", nargs=2, metavar=('TAG','VALUE'), help='Modifies TAG value to VALUE.')
parser.add_argument("-p", "--picture", nargs=1, metavar="IMAGE", help="Adds IMAGE as cover art.")
parser.add_argument("-i", "--interactive", action="store_true", default=False, help='Interactive mode.')
args = parser.parse_args()


# Access the input arguments, and removes any unwanted files
audio_files = list(filter(lambda file: file is not None, map(lambda file: (mutagen.File(file), file), args.input)))
if args.interactive:
    interactiveMode(audio_files)
else:
    if args.list:
        printMetadata(audio_files)

    if args.check:
        printMetadataIssues(audio_files)

    if args.rename:
        audio_files = renameAudioFiles(audio_files)

    if args.sort:
        # If no directory is found after the -s/--sort flag, default to current directory
        if os.path.isdir(args.sort):
            audio_files = sortAudioFiles(audio_files, args.sort)
        else:
            audio_files = sortAudioFiles(audio_files)

    if args.modify:
        modifyMetadata(args.modify[0], args.modify[1], audio_files)

    if args.picture:
        addPicture(args.picture[0], audio_files)
