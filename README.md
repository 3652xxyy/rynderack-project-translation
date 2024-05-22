# Rynderack Project Translation

This is a framework to translate "Rynderack Project" mission packs into English.

## Overview
CSF files for the 3 mission packs are laied out sequentially and build on top of each other. So, if `base` is the content of `ra2md.csf` from the vanilla version of the game.

The file structure of R1 CSF is roughly the following:
```
[base (R1 titles/missions/etc.) | R1 new content]
```

The R2 CSF is build on top of R1 so that some resources can be re used:
```
[base (R2 titles/missions/etc.) | R1 content (R2) | R2 new content]
```

And similarly for R3
```
[base (R3 titles/missions/etc.) | R1 content (R3) | R2 content (R3) | R3 new content]
```

The program will use `base.json` as dependency to build `r1/ra2md.json` (and then use it to build `r1/ra2md.csf`)
- Apply the translations defined in titles (`name.json`) and mission descriptions (`missions.txt`)
- Append the translations of new texts specific to R1 (`data.json`)

To build `r2/ra2md.json`, the program will use `r1/ra2md.json` as base
- Apply the translations defined in titles (`name.json`) and mission descriptions (`missions.txt`)
- Apply the changes in vanilla and R1's section (`from_prev.json`)
- Append the translations of new texts specific to R2 (`data.json`)

Similarly, `r3/ra2md.json` uses `r2/ra2md.json` as a base and repeat the process above.

## Directory Layout

- (`dist`): Output directory, It will be created by running `make`
- `doc`: Documentation source files
- `res`: Resource files that will be copied AS IS to `dist` (or specified output directory)
- `src`: Source files defining the translations
- `scripts`: Various scripts needed to build translations
- `jsons`: Original files (mostly for reference)
- `Makefile`: Script controlling the build process

## Prerequsites
**Linux / macOS**: Python3, GNU Make, `markdown2` python package (if you want to build documentations).

**Windows**: Please use WSL and follow **Linux** prerequsites.

## Workflow / Usage
0. Install all prerequsites
1. Run `make`. It should create a directory called `dist` (or whatever you specified in environment variable `distdir`). All artifacts are contained there. Zip files contains documentation and `ra2md.csf`.
3. Make modifications to files in `src`, `doc`, or `res`
4. Run `make` again to build updated files

### `make` Targets
Build everything (same as `make`)
```
make all
```

Remove all artifacts. This will remove whatever specified by `distdir` in `Makefile`. Be extra careful if you set the environment variable `distdir`.
```
make clean
```

Build only documentations
```
make doc
```

Build only translations (`ra2md.csf`)
```
make csf
```

Build only debug translations (JSON file contains additional information)
```
make debug
```

Build files regarding specific pack (one of below)
```
make r1
make r2
make r3
```

