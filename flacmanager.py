import os
import mutagen
import argparse
import sys
import re
import glob
from mutagen._util import MutagenError
from base64 import b64encode
from rich import box
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()


def filterAudioFiles(tag, value, audio_files):
    if tag not in ["album", "artist", "genre", "tracknumber", "title"]:
        console.print('ERROR: Invalid tag.'
                      'Possible values are album, artist, genre,'
                      'tracknumber and title.')
    else:
        filtered_audio_files = [file for file in audio_files
                                if re.match(value, file[0].tags[tag][0])]
        if len(audio_files) < 1:
            console.print('Filter returned an empty argument list.'
                          'Defaulting to whole argument list.')
            return audio_files
        else:
            return filtered_audio_files


def interactiveHelp():
    console.print('''
flacmanager interacive mode commands
------------------------------------
    help - Prints this help.
    list - Lists audio files.
    tweak - Iterates through audio files and prompts for modification.
    zero - Prefixes tracknumbers with a zero if they are a single digit.
    clean - Removes wildcard characters.
    exit - Quits the interactive mode.
------------------------------------
                  ''')


def interactiveMode(audio_files):
    console.print("Welcome to the interactive mode.")
    choice = ""
    while choice != "exit":
        choice = Prompt.ask("i> ",
                            choices=["help",
                                     "list",
                                     "tweak",
                                     "modify",
                                     "zero",
                                     "clean",
                                     "exit"],
                            default="help",
                            show_choices=True)
        if choice == "help":
            interactiveHelp()
        elif choice == "list":
            printMetadata(audio_files)
        elif choice == "tweak":
            tag = Prompt.ask("Choose a tag to tweak",
                             choices=["artist",
                                      "album",
                                      "genre",
                                      "tracknumber",
                                      "title"],
                             show_choices=True)
            tweakAudioFiles(tag, audio_files)
        elif choice == "modify":
            tag = Prompt.ask("Choose a tag to modify",
                             choices=["artist",
                                      "album",
                                      "genre"],
                             show_choices=True)
            value = Prompt.ask("New value?")
            modifyMetadata(tag, value, audio_files)
        elif choice == "zero":
            zeroPadding(audio_files)
        elif choice == "clean":
            cleanMetadata(audio_files)


def zeroPadding(audio_files):
    counter = 0
    for file in audio_files:
        tracknumber = file[0].tags["tracknumber"][0]
        if len(tracknumber) == 1 and tracknumber.isdigit():
            file[0].tags["tracknumber"] = "0" + tracknumber
            file[0].save()
            counter += 1
    if counter == 0:
        console.print("No changes were made.")


def tweakAudioFiles(tag, audio_files):
    for file in audio_files:
        if tag in file[0].tags:
            old_value = " (Old value = " + file[0].tags[tag][0] + ")"
        else:
            old_value = ""
        value = console.input("New value for the "
                              + tag.upper()
                              + " tag of '"
                              + os.path.basename(file[1])
                              + "' ? " + old_value
                              + " - /c to continue, q to exit/ ")
        if value == 'q':
            break
        elif value == 'c':
            continue
        else:
            file[0].tags[tag] = value
            file[0].save()


def addPicture(picture, audio_files):
    exts = [".jpg", ".jpeg", ".bmp", ".png", ".gif"]
    if not os.path.exists(picture) or not os.path.splitext(picture)[1] in exts:
        console.print("ERROR: {} is not a valid image file.".format(picture))
    else:
        coverArt = mutagen.flac.Picture()
        with open(picture, "rb") as image_data:
            coverArt.data = image_data.read()

        coverArt.type = mutagen.id3.PictureType.COVER_FRONT
        coverArt.mime = u"image/jpeg"
        coverArt.width = 500
        coverArt.height = 500
        coverArt.depth = 16

        choice = console.input(picture + " will be the new cover art for "
                               + str(len(audio_files))
                               + " files. Proceed? (Y/n) ")
        if choice == 'Y':
            for file in audio_files:
                if type(file) is mutagen.flac.FLAC:
                    file[0].clear_pictures()
                    file[0].add_picture(coverArt)
                else:
                    b64 = b64encode(coverArt.write())
                    file[0]['metadata_block_picture'] = b64.decode('ascii')
                file[0].save()


def modifyMetadata(tag, value, audio_files):
    if tag not in ["album", "genre", "artist"]:
        console.print('ERROR: {} is not a valid tag.'.format(tag))
    else:
        choice = console.input(value + " will be the new value for the "
                               + tag.upper()
                               + " tag for "
                               + str(len(audio_files))
                               + " files. Proceed? (Y/n) ")
        if choice == 'Y':
            for file in audio_files:
                file[0].tags[tag] = value
                file[0].save()


def sortAudioFiles(audio_files, path=""):
    new_audio_files = []
    for file in audio_files:
        if "artist" in file[0].tags:
            artist = file[0].tags["artist"][0]
            if "album" in file[0].tags:
                album = file[0].tags["album"][0]
            else:
                album = "Unknown Album"
        else:
            artist = "Unknown Artist"
        albumPath = os.path.normpath(os.path.abspath(path)
                                     + "/"
                                     + artist
                                     + "/" + album)
        if not os.path.isdir(albumPath):
            os.makedirs(albumPath)
        os.rename(file[1], os.path.normpath(albumPath
                                            + "/"
                                            + os.path.basename(file[1])))
        new_audio_files.append((file[0], os.path.normpath(albumPath
                                                          + "/"
                                                          + os
                                                          .path
                                                          .basename(file[1]))))
    return new_audio_files


def renameAudioFiles(audio_files):
    new_audio_files = []
    for file in audio_files:
        if "tracknumber" in file[0].tags and "title" in file[0].tags:
            filename = os.path.normpath(os.path.dirname(file[1])
                                        + "/"
                                        + file[0].tags["tracknumber"][0]
                                        + " - "
                                        + file[0].tags["title"][0]
                                        + os.path.splitext(file[1])[1])
            os.rename(file[1], filename)
            new_audio_files.append((file[0], filename))
        else:
            console.print("Could not rename {} : missing tags."
                          .format(os.path.basename(file[1])))
    return new_audio_files


def getAlbum(file):
    return file[0].tags["album"][0] if "album" in file[0].tags else "N/A"


def printMetadata(audio_files):
    table = Table(show_header=True, box=box.MINIMAL_HEAVY_HEAD)
    tags = ["album", "artist", "genre", "tracknumber", "title"]
    table.add_column("Artist", no_wrap=True, min_width=10)
    table.add_column("Album", no_wrap=True, min_width=10)
    table.add_column("Genre", no_wrap=True, min_width=5)
    table.add_column("#", no_wrap=True, min_width=3)
    table.add_column("Title", no_wrap=True, min_width=10)
    table.add_column("Filename", no_wrap=True, min_width=10)
    for file in audio_files:
        record = []
        for tag in tags:
            if tag in file[0].tags:
                record.append(file[0].tags[tag][0])
            else:
                record.append("N/A")
        record.append(os.path.basename(file[1]))
        table.add_row(*record)

    console.print(table)


def parseAudioFiles(arguments):
    audio_files = []
    mutagen_file = None
    sorted_arguments = sorted(list(arguments))
    for file in sorted_arguments:
        try:
            mutagen_file = mutagen.File(file)
        except MutagenError:
            console.print('Something went wrong when trying to'
                          'read audio files given as arguments.')
        if mutagen_file is not None:
            audio_files.append((mutagen.File(file), file))
    if not audio_files:
        console.print('No valid audio files found'
                      'in arguments. Nothing to do.')
        sys.exit()
    return audio_files


def parseAudioDirectories(arguments, is_recursive=False):
    audio_files = []
    sorted_arguments = []
    mutagen_file = None
    glob_regex = "/*" if not is_recursive else "/**/*"
    for directory in arguments:
        for file in glob.glob(directory + glob_regex, recursive=is_recursive):
            sorted_arguments.append(file)

    for file in sorted(sorted_arguments):
        if not os.path.isdir(file):
            try:
                mutagen_file = mutagen.File(file)
            except MutagenError:
                console.print('Something went wrong while trying'
                              'to read audio files given as arguments.')
            if mutagen_file is not None:
                audio_files.append((mutagen.File(file), file))
    if not audio_files:
        console.print('No valid audio files found in'
                      'the directories given as arguments. Nothing to do.')
        sys.exit()

    return audio_files


def orderAudioFiles(audio_files):
    for file in audio_files:
        if "tracknumber" in file[0].tags and "title" in file[0].tags:
            new_title = file[0].tags["tracknumber"][0]
            + " - "
            + file[0].tags["title"][0]
            file[0].tags["title"] = new_title
            file[0].save()
        else:
            console.print("Could not rename {} : missing tags."
                          .format(os.path.basename(file[1])))


def deleteCoverArtAndLyrics(audio_files):
    console.print('WARNING : This will remove ALL cover art and lyrics tags'
                  'from the selected files, do you wish to proceed? Y/N ')
    choice = console.input()
    if choice == "Y":
        for file in audio_files:
            file[0].clear_pictures()
            file[0].save()
            removeLyrics(audio_files)
    else:
        console.print("No modifications have been made.")


def removeLyrics(audio_files):
    lyric_keys = ["LYRICS", "UNSYNCEDLYRICS", "LYRIC"]
    removed = False
    for file in audio_files:
        for key in file[0].tags.items():
            if key[0].upper() in lyric_keys:
                del file[0].tags[key[0]]
                removed = True
        if removed:
            file[0].save()


def sanitizeTag(text: str) -> str:
    if text is None:
        return ""
    text = re.sub(r"[\x00-\x1F\x7F]", "", text)
    forbidden = r'[\/\\\*\?<>|"]'
    text = re.sub(forbidden, "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def cleanMetadata(audio_files):
    tags = ["title", "artist", "album"]
    for file in audio_files:
        for tag in tags:
            sanitized_tag = sanitizeTag(file[0].tags[tag][0])
            file[0].tags[tag] = sanitized_tag
            file[0].save()


# Creating the parser
parser = argparse.ArgumentParser(
        description='Manages metadata for multiple audio formats.')
parser.add_argument("input",
                    metavar="files",
                    nargs="+",
                    help='audio file(s)')
parser.add_argument("-d",
                    "--directory",
                    action="store_true",
                    help='Takes directories as arguments.')
parser.add_argument("-R",
                    "--recursive",
                    action="store_true",
                    help='Recursive search. Only words with the -d flag.')
parser.add_argument("-l",
                    "--list",
                    action="store_true",
                    default=False,
                    help='Prints the metadata of the audio files.')
parser.add_argument("-r",
                    "--rename",
                    action="store_true",
                    default=False,
                    help='Renames files using tracknumber and title metadata.')
parser.add_argument("-s",
                    "--sort",
                    metavar="destination",
                    nargs="?",
                    help='Sorts audio files by artist and by album.')
parser.add_argument("-m",
                    "--modify",
                    nargs=2,
                    metavar=('TAG', 'VALUE'),
                    help='Modifies TAG value to VALUE.')
parser.add_argument("-p",
                    "--picture",
                    nargs=1,
                    metavar="IMAGE",
                    help="Adds IMAGE as cover art.")
parser.add_argument("-i",
                    "--interactive",
                    action="store_true",
                    default=False,
                    help='Interactive mode.')
parser.add_argument("-f",
                    "--filter",
                    nargs=2,
                    metavar=('TAG', 'VALUE'),
                    help="Filters the input files using tag values.")
parser.add_argument("-o",
                    "--order",
                    action="store_true",
                    help="Appends tracknumber to title.")
parser.add_argument("-z",
                    "--zeropadding",
                    action="store_true",
                    help="Automatic left zero-padding for tracknumber.")
parser.add_argument("-D",
                    "--delete",
                    action="store_true",
                    help='Deletes cover art and lyrics from the audio files.')
parser.add_argument("-c",
                    "--clean",
                    action="store_true",
                    help='Deletes wildcards characters from tags.')
args = parser.parse_args()

# Access the input arguments

if args.directory:
    audio_files = parseAudioDirectories(args.input, args.recursive)
else:
    audio_files = parseAudioFiles(args.input)

if args.filter:
    audio_files = filterAudioFiles(args.filter[0], args.filter[1], audio_files)

if args.interactive:
    interactiveMode(audio_files)
else:
    if args.delete:
        deleteCoverArtAndLyrics(audio_files)

    if args.zeropadding:
        zeroPadding(audio_files)

    if args.clean:
        cleanMetadata(audio_files)

    if args.rename:
        audio_files = renameAudioFiles(audio_files)

    if args.order:
        orderAudioFiles(audio_files)

    if args.modify:
        modifyMetadata(args.modify[0], args.modify[1], audio_files)

    if args.sort:
        if os.path.isdir(args.sort):
            audio_files = sortAudioFiles(audio_files, args.sort)
        else:
            audio_files = sortAudioFiles(audio_files)

    if args.picture:
        addPicture(args.picture[0], audio_files)

    if args.list:
        printMetadata(audio_files)
