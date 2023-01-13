import os
import mutagen
import argparse

def printMetadata(audio_files):
    print ("{:<40} {:<20} {:<30} {:<10} {:<30}".format('Album', 'Genre', 'Artist', '#', 'Title'))
    for file in audio_files:
        album = file.tags["album"][0] if "album" in file.tags else "N/A"
        genre = file.tags["genre"][0] if "genre" in file.tags else "N/A"
        artist = file.tags["artist"][0] if "artist" in file.tags else "N/A"
        tracknumber = file.tags["tracknumber"][0] if "tracknumber" in file.tags else "N/A"
        title = file.tags["title"][0] if "title" in file.tags else "N/A"
        print("{:<40} {:<20} {:<30} {:<10} {:<30}".format(album, genre, artist, tracknumber, title))

def checkMetadata(audio_files):
    for file in audio_files:
        print(len(file.pictures))

# Creating the parser
parser = argparse.ArgumentParser(description='Manages metadata for multiple audio formats.')
parser.add_argument("input", metavar="files", nargs="+", help='audio file(s)')
parser.add_argument("-l", "--list", action="store_true", default=False, help='Prints the metadata of the audio files.')
parser.add_argument("-c", "--check", action="store_true", default=False, help='Checks if audio files have missing metadata tags.')
args = parser.parse_args()

# Access the input arguments, and removes any unwanted files
audio_files = list(filter(lambda file: file is not None, map(lambda file: mutagen.File(file), args.input)))

if args.list:
    printMetadata(audio_files)

if args.check:
    checkMetadata(audio_files)
