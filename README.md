# FLACMANAGER
Simple Python script for managing .flac audio files (bulk-editing metadata and ordering).

# USAGE & AVAILABLE COMMANDS

```
usage: flacmanager [-h] [-d] [-R] [-l] [-c] [-r] [-s [destination]] [-m TAG VALUE] [-p IMAGE] [-i] [-f TAG VALUE] [-o] [-z] [-D] files [files ...]

Manages metadata for multiple audio formats.

positional arguments:
  files                 audio file(s)

options:
  -h, --help            show this help message and exit
  -d, --directory       Takes directories containing audio files as argument.
  -R, --recursive       Searches recursively in the directories provided as arguments. Can only be used in conjonction with the -d/--directory
                        flag.
  -l, --list            Prints the metadata of the audio files.
  -c, --check           Prints metadata issues (missing tags or album covers).
  -r, --rename          Renames files using tracknumber and title metadata.
  -s [destination], --sort [destination]
                        Sorts audio files by artist and by album in folders at the destination specified.
  -m TAG VALUE, --modify TAG VALUE
                        Modifies TAG value to VALUE.
  -p IMAGE, --picture IMAGE
                        Adds IMAGE as cover art.
  -i, --interactive     Interactive mode.
  -f TAG VALUE, --filter TAG VALUE
                        Filters the input files using tag values.
  -o, --order           Appends the tracknumber (if it exists) to the title tag value, useful for some devices.
  -z, --zeropadding     Automatic left zero-padding for single-digit tracknumbers, so that they're ordered properly.
  -D, --delete          Deletes every metadata tag from the audio files given as arguments.
```

