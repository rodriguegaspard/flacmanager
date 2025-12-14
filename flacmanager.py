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
from rich.text import Text

from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.styles import Style

console = Console()


def filterAudioFiles(audio_files,
                     regex=r'',
                     target_tags=["artist",
                                  "album",
                                  "genre",
                                  "tracknumber",
                                  "title"]):
    if not target_tags:
        target_tags = radioSelection("Select tags you wish to filter on",
                                     ["artist",
                                      "album",
                                      "genre",
                                      "tracknumber",
                                      "title"])
    result = []
    for file in audio_files:
        match = False
        for tag in target_tags:
            if tag in file[0].tags:
                if re.search(regex, file[0].tags[tag][0]):
                    match = True
        if match:
            result.append(file)
    if len(result) < 1:
        console.print('[bold red]Filter returned an empty argument list.[/]')
        return None
    else:
        return result


def interactiveHelp():
    console.print('''
------------------------------------
    help - Prints this help.
    list - Lists audio files.
    tweak - Iterates through audio files and prompts for modification.
    modify - Bulk-modifies tags.
    preset - Apply formatting presets.
    order - Prefixes title with tracknumber.
    rename - Renames files to '{tracknumber} - {title}'.
    select - Manual selection of files.
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
                                     "preset",
                                     "order",
                                     "select",
                                     "rename",
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
            modifyMetadata(audio_files)
        elif choice == "preset":
            applyPresets(audio_files)
        elif choice == "order":
            orderAudioFiles(audio_files)
        elif choice == "select":
            filtered = selectAudioFiles(audio_files)
            audio_files = filtered


def tweakAudioFiles(tag, audio_files):
    for file in audio_files:
        if tag in file[0].tags:
            old_value = file[0].tags[tag][0]
        else:
            old_value = ""
        choice = Prompt.ask('[dim italic](c: continue, '
                            'q: quit)[/] '
                            '[{}] -> [?] '
                            .format(old_value),
                            default=old_value)
        if choice == 'q':
            break
        elif choice == 'c':
            continue
        else:
            file[0].tags[tag] = choice
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
        choice = Confirm.ask('{} will be the cover art for {} files. Proceed?'
                             .format(picture, len(audio_files)))
        if choice:
            with console.status("Adding cover art..",
                                spinner="line"):
                for file in audio_files:
                    if type(file) is mutagen.flac.FLAC:
                        file[0].clear_pictures()
                        file[0].add_picture(coverArt)
                    else:
                        b64 = b64encode(coverArt.write())
                        file[0]['metadata_block_picture'] = b64.decode('ascii')
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


def printMetadata(audio_files,
                  regex=None,
                  target_tags=("artist",
                               "album",
                               "genre",
                               "tracknumber",
                               "title"),
                  style=None):
    match = False
    table = Table(show_header=True, box=box.MINIMAL_HEAVY_HEAD)
    tags = ["artist", "album", "genre", "tracknumber", "title"]
    table.add_column("Artist", no_wrap=True, min_width=10, max_width=20)
    table.add_column("Album", no_wrap=True, min_width=10, max_width=20)
    table.add_column("Genre", no_wrap=True, min_width=5, max_width=20)
    table.add_column("#", no_wrap=True, min_width=3, max_width=30)
    table.add_column("Title", no_wrap=True, min_width=10, max_width=40)
    table.add_column("Filename", no_wrap=True, min_width=10, max_width=40)
    for file in audio_files:
        record = []
        for tag in tags:
            if tag in file[0].tags:
                value = file[0].tags[tag][0]
                if (
                        regex is not None
                        and re.search(regex, value)
                        and tag in target_tags):
                    record.append("[{}]{}".format(style, value))
                else:
                    record.append("{}".format(value))
            else:
                record.append("[dim]N/A")
        if match:
            record.append("[{}]{}".format(style, os.path.basename(file[1])))
        else:
            record.append("{}".format(os.path.basename(file[1])))
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
            new_title = "{} - {}".format(
                    file[0].tags["tracknumber"][0],
                    file[0].tags["title"][0])
            file[0].tags["title"] = new_title
            file[0].save()
        else:
            console.print("Could not rename {} : missing tags."
                          .format(os.path.basename(file[1])))


def deleteCoverArtAndLyrics(audio_files):
    choice = Confirm.ask('This will remove ALL cover art and lyrics '
                         'from {} files. Proceed?'
                         .format(len(audio_files)))
    if choice:
        with console.status("Deleting cover art and lyrics..",
                            spinner="line"):
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


def listSelection(message, choices):
    cursor = {"index": 0}
    kb = KeyBindings()

    @kb.add('up')
    def _(event):
        cursor["index"] = (cursor["index"] - 1) % len(choices)

    @kb.add('down')
    def _(event):
        cursor["index"] = (cursor["index"] + 1) % len(choices)

    @kb.add('enter')
    def _(event):
        event.app.exit(result=choices[cursor["index"]])

    style = Style.from_dict({
        "selected": "reverse",
    })

    def get_prompt():
        lines = [f"{message}"
                 "\x1b[3;90m [↑↓, Space: toggle, Enter: confirm] \x1b[0m", ""]
        for i, c in enumerate(choices):
            if i == cursor["index"]:
                pointer = "\x1b[1;36m>\x1b[0m"
                lines.append(f"{pointer} \x1b[7;36m{c}\x1b[0m")
            else:
                lines.append(f"  {c}")
        return ANSI("\n".join(lines) + "\n")

    return prompt(get_prompt, key_bindings=kb, style=style)


def radioSelection(message, choices):
    if len(choices) == 0:
        return []
    if len(choices) == 1:
        return choices[0]

    cursor = {"index": 0}
    selected = set()
    kb = KeyBindings()

    @kb.add("up")
    def _(event):
        cursor["index"] = (cursor["index"] - 1) % len(choices)

    @kb.add("down")
    def _(event):
        cursor["index"] = (cursor["index"] + 1) % len(choices)

    @kb.add(" ")
    def _(event):
        item = choices[cursor["index"]]
        if item in selected:
            selected.remove(item)
        else:
            selected.add(item)

    @kb.add("enter")
    def _(event):
        event.app.exit(result=list(selected))

    def render():
        lines = [f"\n{message}"
                 "\x1b[3;90m [↑↓, Space: toggle, Enter: confirm] \x1b[0m", ""]
        for i, choice in enumerate(choices):
            mark = "[\x1b[1;36m*\x1b[0m]" if choice in selected else "[ ]"
            pointer = ">" if i == cursor["index"] else " "
            if i == cursor["index"]:
                pointer = f"\x1b[1;36m{pointer}\x1b[0m"
            if choice in selected:
                choice_text = f"\x1b[3;96m{choice}\x1b[0m"
            else:
                choice_text = choice
            lines.append(f"{pointer} {mark} {choice_text}")
        return ANSI("\n".join(lines) + "\n")

    return prompt(render, key_bindings=kb)


def printSelectedAudioFiles(audio_files,
                            target_tags=["album",
                                         "artist",
                                         "genre",
                                         "tracknumber",
                                         "title"],
                            title=""):
    table = Table(title=title, show_header=True, box=box.MINIMAL_HEAVY_HEAD)
    if audio_files is None or len(audio_files) < 1:
        return
    for tag in target_tags:
        if tag == "tracknumber":
            table.add_column("#", no_wrap=True, min_width=2, max_width=3)
        else:
            table.add_column(tag.capitalize(),
                             no_wrap=True,
                             min_width=8,
                             max_width=40)
    for file in audio_files:
        record = []
        for tag in target_tags:
            if tag in file[0].tags:
                record.append(file[0].tags[tag][0])
            else:
                record.append("N/A")
        if record:
            table.add_row(*record)

    console.print(table)


def applyRegex(audio_files,
               regex,
               target_tags=["artist",
                            "album",
                            "genre",
                            "tracknumber",
                            "title"],
               replace="",
               dry_run=True):
    for file in audio_files:
        for tag in target_tags:
            if tag in file[0].tags:
                if re.search(regex, file[0].tags[tag][0]):
                    old_value = file[0].tags[tag][0]
                    new_value = re.sub(regex, replace, old_value)
                    file[0].tags[tag] = new_value
                if not dry_run:
                    file[0].save()
    return audio_files


def modifyMetadata(audio_files,
                   regex=None,
                   target_tags=["artist",
                                "album",
                                "genre",
                                "tracknumber",
                                "title"],
                   replace=None,
                   dry_run=True):
    if regex is None:
        prompt = Prompt.ask("Pattern")
        regex = re.compile(prompt)
    if replace is None:
        prompt = Prompt.ask("Replace by")
        replace = prompt
    filter_result = filterAudioFiles(audio_files, regex, target_tags)
    if filter_result is not None:
        printSelectedAudioFiles(filter_result,
                                target_tags)
        console.print("<{}> -> <{}>"
                      .format(regex.pattern, replace),
                      highlight=False)
        preview = applyRegex(filter_result,
                             regex,
                             target_tags,
                             replace)
        printSelectedAudioFiles(preview, target_tags)
        choice = Confirm.ask("Proceed?")
        if choice:
            applyRegex(filter_result,
                       regex,
                       target_tags,
                       replace,
                       False)


def applyPresets(audio_files, presets=None):
    choices = ['A',
               'C',
               'P',
               'W',
               'Z']
    console.print('''
------------------------------------
    A - Only keep the first artist.
    C - Capitalizes every word in the title tag.
    P - Removes everything under parentheses.
    W - Removes wildcards characters.
    Z - Zeropadding of every single-digit tracknumber.
------------------------------------
                  ''')
    if presets is None:
        presets = radioSelection("Select a formatting preset",
                                 choices)
    for preset in presets:
        if preset == 'A':
            modifyMetadata(audio_files,
                           re.compile(r'([^,;]+)[,;].*'),
                           ["artist"],
                           r'\1',
                           False)
        elif preset == 'C':
            modifyMetadata(audio_files,
                           re.compile(r'\b\w+\b'),
                           ["album",
                            "artist",
                            "genre",
                            "title"],
                           lambda m: m.group(0)
                           if m.group(0) == m.group(0).title()
                           else m.group(0).title(),
                           False)
        elif preset == 'P':
            modifyMetadata(audio_files,
                           re.compile(r'\s*\([^()]*\)\s*'),
                           ["artist",
                            "album",
                            "genre",
                            "title"],
                           '',
                           False)
        elif preset == 'W':
            modifyMetadata(audio_files,
                           re.compile(r'[\/\0\*\?\[\]\{\}~!$&;|<>"\'`\\]'),
                           ["artist",
                            "album",
                            "genre",
                            "tracknumber",
                            "title"],
                           '',
                           False)
        elif preset == 'Z':
            modifyMetadata(audio_files,
                           re.compile(r'\b(\d)\b'),
                           ["tracknumber",
                            "title"],
                           r'0\1',
                           False)


def selectAudioFiles(audio_files):
    selection = []
    choices = list(
            map(
                lambda x:
                x[0].tags["album"][0] + " by "
                + x[0].tags["artist"][0] + " ||| "
                + x[0].tags["title"][0],
                audio_files
                ))
    selection = radioSelection("Please select one, or many, audio files",
                               choices)
    titles = list(
            map(
                lambda s:
                re.sub(r'^.*?\s*\|\|\|\s*', '', s),
                selection
                )
            )
    filtered = [x for x in audio_files if x[0].tags["title"][0] in titles]
    return filtered


def printPreview(preview):
    if not preview:
        console.print("[bold green]No changes detected.[/bold green]")
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("Tag", min_width=5, max_width=15)
    table.add_column("Old Value", style="red", max_width=30)
    table.add_column("New Value", style="green", max_width=30)
    table.add_column("Filename",  overflow="fold", max_width=30)
    for file_preview in preview:
        path = file_preview["path"]
        changes = file_preview["changes"]
        for tag, vals in changes.items():
            old = vals["old"]
            new = vals["new"]
            if old != new:
                old_text = Text(old, style="red")
                new_text = Text(new, style="green")
            else:
                old_text = Text(old)
                new_text = Text(new)
            table.add_row(tag, old_text, new_text, os.path.basename(path))
    console.print(table)


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
                    metavar=('PATTERN', 'TAGS'),
                    help='Replaces values in TAGS matched by PATTERN')
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
parser.add_argument("-D",
                    "--delete",
                    action="store_true",
                    help='Deletes cover art and lyrics from the audio files.')
parser.add_argument("-F",
                    "--format",
                    action="store_true",
                    help='Apply one, or several formatting presets.')
args = parser.parse_args()


if args.directory:
    audio_files = parseAudioDirectories(args.input, args.recursive)
else:
    audio_files = parseAudioFiles(args.input)

if args.filter:
    audio_files = filterAudioFiles(audio_files,
                                   re.compile(args.filter[0]),
                                   args.filter[1].split(";"))

if args.interactive:
    interactiveMode(audio_files)
else:
    if args.delete:
        deleteCoverArtAndLyrics(audio_files)

    if args.rename:
        audio_files = renameAudioFiles(audio_files)

    if args.order:
        orderAudioFiles(audio_files)

    if args.modify:
        modifyMetadata(audio_files,
                       re.compile(args.modify[0]),
                       args.modify[1].split(";"),
                       None,
                       False)
    if args.format:
        applyPresets(audio_files, None)

    if args.picture:
        addPicture(args.picture[0], audio_files)

    if args.sort:
        if os.path.isdir(args.sort):
            audio_files = sortAudioFiles(audio_files, args.sort)
        else:
            audio_files = sortAudioFiles(audio_files)

    if args.list:
        printMetadata(audio_files)
