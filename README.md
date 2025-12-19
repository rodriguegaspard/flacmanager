# FLACMANAGER
Simple Python script for managing .flac audio files (bulk-editing metadata and ordering).

# INSTALLATION
```bash
git clone https://github.com/rodriguegaspard/flacmanager
cd flacmanager
python -m venv .
source bin/activate
pip install -r requirements.txt
```

# USAGE
```
usage: flacmanager [-h] [-d] [-l] [-r] [-s [destination]] [-m TAGS VALUE] [-p IMAGE] [-i] [-f TAGS PATTERN] [-o] [-D] [-F] [-R]
                   files [files ...]

Manages metadata for multiple audio formats.

positional arguments:
  files                 audio file(s)

options:
  -h, --help            show this help message and exit
  -d, --directory       Takes directories as arguments.
  -l, --list            Prints the metadata of the audio files.
  -r, --rename          Renames files using tracknumber and title metadata.
  -s, --sort [destination]
                        Sorts audio files by artist and by album.
  -m, --modify TAGS VALUE
                        Replaces all TAG values by VALUE
  -p, --picture IMAGE   Adds IMAGE as cover art.
  -i, --interactive     Interactive mode.
  -f, --filter TAGS PATTERN
                        Filters audio files using PATTERN on TAG values. Specify multiple tags by separating them with ;
  -o, --order           Appends tracknumber to title.
  -D, --delete          Deletes cover art and lyrics from the audio files.
  -F, --format          Apply one, or several formatting presets.
  -R, --regex           Multi-tag pattern matching and replace
```

