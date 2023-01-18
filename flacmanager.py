import os
import mutagen
import argparse

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
parser.add_argument("-m", "--modify", nargs=2, metavar=('TAG','VALUE'), help='Modifies TAG value to VALUE.')
args = parser.parse_args()


# Access the input arguments, and removes any unwanted files
audio_files = list(filter(lambda file: file is not None, map(lambda file: (mutagen.File(file), file), args.input)))

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
