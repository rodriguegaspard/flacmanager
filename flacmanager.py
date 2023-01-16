import os
import mutagen
import argparse

def printMetadata(audio_files):
    print ("{:<40} {:<20} {:<30} {:<10} {:<30}".format('Album', 'Genre', 'Artist', '#', 'Title'))
    for file in audio_files:
        album = file[0].tags["album"][0] if "album" in file[0].tags else "N/A"
        genre = file[0].tags["genre"][0] if "genre" in file[0].tags else "N/A"
        artist = file[0].tags["artist"][0] if "artist" in file[0].tags else "N/A"
        tracknumber = file[0].tags["tracknumber"][0] if "tracknumber" in file[0].tags else "N/A"
        title = file[0].tags["title"][0] if "title" in file[0].tags else "N/A"
        print("{:<40} {:<20} {:<30} {:<10} {:<30}".format(album, genre, artist, tracknumber, title))

# Creating the parser
parser = argparse.ArgumentParser(description='Manages metadata for multiple audio formats.')
parser.add_argument("input", metavar="files", nargs="+", help='audio file(s)')
parser.add_argument("-l", "--list", action="store_true", default=False, help='Prints the metadata of the audio files.')
args = parser.parse_args()

# Access the input arguments, and removes any unwanted files
audio_files = list(filter(lambda file: file is not None, map(lambda file: (mutagen.File(file), os.path.basename(file)), args.input)))

if args.list:
    printMetadata(audio_files)

if args.check:
