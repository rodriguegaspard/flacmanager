import os
import mutagen
import argparse
import sys
import re

from mutagen._util import MutagenError

from base64 import b64encode

from pathlib import Path

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
                     target_tags=("artist",
                                  "album",
                                  "genre",
                                  "tracknumber",
                                  "title")):
    if not target_tags:
        target_tags = radioSelection("Select tags you wish to filter on",
                                     ("artist",
                                      "album",
                                      "genre",
                                      "tracknumber",
                                      "title"))
    result = []
    for audio, path in audio_files:
        match = False
        for tag in target_tags:
            if tag in audio.tags:
                if re.search(regex, audio.tags[tag][0]):
                    match = True
        if match:
            result.append((audio, path))
    if len(result) < 1:
        console.print('[bold red]Filter returned an empty argument list.[/]')
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
    rename - Renames files using tracknumber and title.
    exit - Quits the interactive mode.
------------------------------------
                  ''')


def interactiveMode(audio_files):
    console.print("Welcome to the interactive mode.")
    choice = ""
    while choice != "exit":
        choice = Prompt.ask("i>",
                            choices=("help",
                                     "list",
                                     "tweak",
                                     "modify",
                                     "preset",
                                     "order",
                                     "rename",
                                     "exit"),
                            default="help",
                            show_choices=True)
        if choice == "help":
            interactiveHelp()
        elif choice == "list":
            printMetadata(audio_files)
        elif choice == "tweak":
            tag = listSelection("Select a tag to tweak:",
                                ("artist",
                                 "album",
                                 "genre",
                                 "tracknumber",
                                 "title"))
            filtered = selectAudioFiles(audio_files)
            tweakAudioFiles(tag, filtered)
        elif choice == "modify":
            modifyMetadata(audio_files, False, [])
        elif choice == "preset":
            applyPresets(audio_files)
        elif choice == "order":
            orderAudioFiles(audio_files)
        elif choice == "rename":
            audio_files = renameAudioFiles(audio_files)


def tweakAudioFiles(tag, audio_files):
    console.print('[dim italic][Commands : c to continue,'
                  'q to exit tweak mode][/]')
    for audio, path in audio_files:
        if tag in audio.tags:
            old_value = audio.tags[tag][0]
        else:
            old_value = ""
        choice = Prompt.ask(
            f"[italic cyan]{path.name}[/] : "
            f"[[bold]{old_value}[/]] -> [?] ",
            default=old_value
            )
        if choice == 'q':
            break
        elif choice == 'c':
            continue
        else:
            audio.tags[tag] = choice
            audio.save()


def addPicture(picture, audio_files):
    exts = (".jpg", ".jpeg", ".bmp", ".png", ".gif")
    if not os.path.exists(picture) or not os.path.splitext(picture)[1] in exts:
        console.print(f"ERROR: {picture} is not a valid image file.")
    else:
        coverArt = mutagen.flac.Picture()
        with open(picture, "rb") as image_data:
            coverArt.data = image_data.read()
        coverArt.type = mutagen.id3.PictureType.COVER_FRONT
        coverArt.mime = u"image/jpeg"
        coverArt.width = 500
        coverArt.height = 500
        coverArt.depth = 16
        choice = Confirm.ask(f"{picture} will be the cover art for "
                             f"{len(audio_files)} files. Proceed?")
        if choice:
            with console.status("Adding cover art..",
                                spinner="line"):
                for audio, path in audio_files:
                    if type(audio) is mutagen.flac.FLAC:
                        audio.clear_pictures()
                        audio.add_picture(coverArt)
                    else:
                        b64 = b64encode(coverArt.write())
                        audio['metadata_block_picture'] = b64.decode('ascii')
                    audio.save()


def sortAudioFiles(audio_files, base_path=""):
    result = []
    base_path = Path(base_path).resolve()
    for audio, path in audio_files:
        file_path = Path(path)
        artist = audio.tags.get("artist", ["Unknown Artist"])[0]
        album = audio.tags.get("album", ["Unknown Album"])[0]
        album_path = base_path / artist / album
        album_path.mkdir(parents=True, exist_ok=True)
        destination = album_path / file_path.name
        file_path.rename(destination)
        result.append((audio, destination))
    return result


def renameAudioFiles(audio_files):
    new_audio_files = []
    for audio, path in audio_files:
        file_path = Path(path)
        if "tracknumber" in audio.tags and "title" in audio.tags:
            track = audio.tags["tracknumber"][0]
            title = audio.tags["title"][0]
            new_name = f"{track} - {title}{file_path.suffix}"
            destination = file_path.with_name(new_name)
            file_path.rename(destination)
            new_audio_files.append((audio, destination))
        else:
            console.print(
                f"Could not rename {file_path.name} : missing tags."
            )
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
    tags = ("artist", "album", "genre", "tracknumber", "title")
    table.add_column("Artist", no_wrap=True, min_width=10, max_width=20)
    table.add_column("Album", no_wrap=True, min_width=10, max_width=20)
    table.add_column("Genre", no_wrap=True, min_width=5, max_width=20)
    table.add_column("#", no_wrap=True, min_width=3, max_width=30)
    table.add_column("Title", no_wrap=True, min_width=10, max_width=40)
    table.add_column("Filename", no_wrap=True, min_width=10, max_width=40)
    for audio, path in audio_files:
        record = []
        for tag in tags:
            if tag in audio.tags:
                value = audio.tags[tag][0]
                if (
                        regex is not None
                        and re.search(regex, value)
                        and tag in target_tags):
                    record.append(f"[{style}]{value}")
                else:
                    record.append(f"{value}")
        if match:
            record.append(f"[{style}]{path.name}")
        else:
            record.append(f"{path.name}")
        table.add_row(*record)
    console.print(table)


def ensureBasicTags(audio):
    tags = ('artist',
            'album',
            'genre',
            'tracknumber',
            'title')
    for tag in tags:
        if tag not in audio.tags:
            audio.tags[tag] = ""


def parseAudioFiles(arguments):
    audio_files = []
    mutagen_file = None
    sorted_arguments = sorted(list(arguments))
    for audio in sorted_arguments:
        try:
            mutagen_file = mutagen.File(audio)
        except MutagenError:
            console.print('Something went wrong when trying to'
                          'read audio files given as arguments.')
            ensureBasicTags(audio)
        path = Path(audio)
        if mutagen_file is not None:
            audio_files.append((mutagen.File(audio), path))
    if not audio_files:
        console.print('No valid audio files found'
                      'in arguments. Nothing to do.')
        sys.exit()
    return audio_files


def parseAudioDirectories(arguments, is_recursive=False):
    audio_files = []
    paths = []
    for directory in arguments:
        base = Path(directory)
        if is_recursive:
            paths.extend(base.rglob("*"))
        else:
            paths.extend(base.glob("*"))
    for path in sorted(paths):
        if path.is_file():
            try:
                audio = mutagen.File(path)
            except MutagenError:
                console.print(
                    "Something went wrong while trying "
                    "to read audio files given as arguments."
                )
                continue
            if audio is not None:
                ensureBasicTags(audio)
                audio_files.append((audio, path))
    if not audio_files:
        console.print(
            "No valid audio files found in "
            "the directories given as arguments. Nothing to do."
        )
        sys.exit()
    return audio_files


def orderAudioFiles(audio_files):
    for audio, path in audio_files:
        if "tracknumber" in audio.tags and "title" in audio.tags:
            new_title = (
                    f"{audio.tags["tracknumber"][0]}"
                    f" - {audio.tags["title"][0]}"
                    )
            audio.tags["title"] = new_title
            audio.save()
        else:
            console.print(f"Could not rename {path.name} : missing tags.")


def deleteCoverArtAndLyrics(audio_files):
    choice = Confirm.ask(f"This will remove ALL cover art and lyrics"
                         f" from {len(audio_files)} files. Proceed?")
    if choice:
        with console.status("Deleting cover art and lyrics..",
                            spinner="line"):
            for audio, path in audio_files:
                audio.clear_pictures()
                audio.save()
                removeLyrics(audio_files)
    else:
        console.print("No modifications have been made.")


def removeLyrics(audio_files):
    lyric_keys = ("LYRICS", "UNSYNCEDLYRICS", "LYRIC")
    removed = False
    for audio, path in audio_files:
        for key, value in audio.tags.items():
            if key.upper() in lyric_keys:
                del audio.tags[key]
                removed = True
        if removed:
            audio.save()


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


def applyRegex(audio_files,
               regex,
               target_tags=("artist",
                            "album",
                            "genre",
                            "tracknumber",
                            "title"),
               replace="",
               dry_run=True):
    if dry_run:
        preview = []
        for audio, path in audio_files:
            file_preview = {"path": path, "changes": {}}
            for tag in target_tags:
                if tag not in audio.tags:
                    continue
                old_value = audio.tags[tag][0]
                if re.search(regex, old_value):
                    new_value = re.sub(regex, replace, old_value)
                    file_preview["changes"][tag] = {"old": old_value,
                                                    "new": new_value}
            if file_preview["changes"]:
                preview.append(file_preview)
        return preview
    else:
        result = []
        for audio, path in audio_files:
            changed = False
            for tag in target_tags:
                if tag not in audio.tags:
                    continue
                old_value = audio.tags[tag][0]
                if re.search(regex, old_value):
                    new_value = re.sub(regex, replace, old_value)
                    audio.tags[tag] = new_value
                    changed = True
            if changed:
                audio.save()
            result.append((audio, path))
        return result


def modifyMetadata(audio_files,
                   dry_run=True,
                   target_tags=("artist",
                                "album",
                                "genre",
                                "tracknumber",
                                "title"),
                   regex=None,
                   replace=None,
                   ):
    if len(target_tags) < 1:
        target_tags = radioSelection("Select tags to apply modifications to",
                                     ("artist",
                                      "album",
                                      "genre",
                                      "tracknumber",
                                      "title"))
    if regex is None:
        regex = re.compile(Prompt.ask("Pattern"))
    filter_result = filterAudioFiles(audio_files, regex, target_tags)
    if len(filter_result) > 0:
        printMetadata(filter_result, regex, target_tags, "bold green")
    else:
        return
    if replace is None:
        replace = Prompt.ask("Replace by")
    preview = applyRegex(filter_result,
                         regex,
                         target_tags,
                         replace,
                         True)
    printPreview(preview)
    choice = Confirm.ask("Proceed?")
    if choice:
        applyRegex(filter_result,
                   regex,
                   target_tags,
                   replace,
                   False)


def applyPresets(audio_files, presets=None):
    choices = ('A',
               'C',
               'P',
               'W',
               'Z')
    console.print('''
------------------------------------
    A - Only keep the first artist/genre.
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
                           False,
                           ("artist",
                            "genre"),
                           re.compile(r'([^,;]+)[,;].*'),
                           r'\1')
        elif preset == 'C':
            modifyMetadata(audio_files,
                           False,
                           ("album",
                            "artist",
                            "genre",
                            "title"),
                           re.compile(r'\b\w+\b'),
                           lambda m: m.group(0)
                           if m.group(0) == m.group(0).title()
                           else m.group(0).title())
        elif preset == 'P':
            modifyMetadata(audio_files,
                           False,
                           ("artist",
                            "album",
                            "genre",
                            "title"),
                           re.compile(r'\s*\([^()]*\)\s*'),
                           '')
        elif preset == 'W':
            modifyMetadata(audio_files,
                           False,
                           ("artist",
                            "album",
                            "genre",
                            "tracknumber",
                            "title"),
                           re.compile(r'[\/\0\*\?\[\]\{\}~!$&;|<>"\'`\\]'),
                           '')
        elif preset == 'Z':
            modifyMetadata(audio_files,
                           False,
                           ["tracknumber"],
                           re.compile(r'\b(\d)\b'),
                           r'0\1')


def selectAudioFiles(audio_files):
    selection = []
    choices = list(
            map(
                lambda f:
                (
                    f"{f[0].tags["artist"][0]}"
                    f" by {f[0].tags["album"][0]}"
                    f" <<<>>> {f[0].tags["title"][0]}"
                ),
                audio_files
                ))
    selection = radioSelection("Please select one, or many, audio files",
                               choices)
    titles = list(
            map(
                lambda s:
                re.sub(r'.*<<<>>>\s*', '', s),
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
    table.add_column("Tag", no_wrap=True, min_width=5, max_width=15)
    table.add_column("Old Value", no_wrap=True, style="red", max_width=30)
    table.add_column("New Value", no_wrap=True, style="green", max_width=30)
    table.add_column("Filename",  no_wrap=True, overflow="fold", max_width=30)
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
                    metavar=('TAGS', 'VALUE'),
                    help='Replaces all TAG values by VALUE')
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
                    metavar=('TAGS', 'PATTERN'),
                    help=(
                        'Filters audio files using PATTERN on TAG values. '
                        'Specify multiple tags by separating them with ;')
                    )
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
parser.add_argument("-R",
                    "--regex",
                    action="store_true",
                    help='Multi-tag pattern matching and replace')
args = parser.parse_args()


if args.directory:
    audio_files = parseAudioDirectories(args.input, True)
else:
    audio_files = parseAudioFiles(args.input)

if args.filter:
    audio_files = filterAudioFiles(audio_files,
                                   re.compile(args.filter[1]),
                                   args.filter[0].split(";"))
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
                       False,
                       args.modify[0].split(";"),
                       r'^.*$',
                       args.modify[1])

    if args.regex:
        modifyMetadata(audio_files,
                       False,
                       [],
                       None,
                       None)

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
