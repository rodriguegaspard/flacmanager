import os
import mutagen
import argparse

# Creating the parser
parser = argparse.ArgumentParser(description='Manages metadata for multiple audio formats.')
parser.add_argument("input", metavar="N", nargs="+", help='audio file(s) or folder containing audio files.')
parser.add_argument("-l", "--list", action="store_true", default=False, help='Prints the metadata of the audio files.')
args = parser.parse_args()

def printMetaData(audio_files):
    print ("{:<50} {:<15} {:<25} {:<10} {:<30}".format('Album','Genre','Artist','#', 'Title'))
    for file in audio_files:
        print("{:<50} {:<15} {:<25} {:<10} {:<30}".format(file.tags["album"][0], file.tags["genre"][0], file.tags["artist"][0], file.tags["tracknumber"][0], file.tags["title"][0]))

# Access the input arguments
audio_files = map(lambda file: mutagen.File(file),args.input)
if args.list:
        printMetaData(audio_files)
else:
    print("Nothing to do.")
