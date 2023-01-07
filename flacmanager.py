import os
import mutagen
import argparse

# Creating the parser
parser = argparse.ArgumentParser(description='Manages metadata for multiple FLAC files.')
parser.add_argument('input', metavar='N', nargs='+', help='audio file(s) or folder containing audio files.')
args = parser.parse_args()

# Access the input arguments
audio_files = map(lambda file: mutagen.File(file),args.input)
for file in audio_files:
    print(file)
