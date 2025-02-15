import json
import re
import logging

from dataclasses import dataclass, field
from typing import List, Optional

import argparse

"""
File format:

<Mission Name blah blah blah>
Location: blah blah blah
<Mission Description blahblah>
<Mission Description line 2 if exist>
<...>
Objective X: blah blah blah
<... other objectives if exist>
Hint: blah blah blah
Note: blah blah blah
Warning: blah blah blah
<... other hints or notes or warnings if exist>

<... another block, same format as above>
<...>

Note:
- each block is separated by more than 1 more line
- empty lines are ignored
- keys are matched based on Patterns in <Mission Name>, therefore some blocks may be ignored
"""

logging.basicConfig(level=logging.DEBUG)

@dataclass
class Block:
    name_: str
    location_str: str # maybe this shouldn't be required
    description: List[str] = field(default_factory=list)
    objectives: List[str] = field(default_factory=list)
    hints: List[str] = field(default_factory=list)

    # Name:All02md
    # Name:All02mdSav
    def name(self):
        return self.name_
    
    # LoadMsg:All02md
    def loadmsg(self):
        return f"{self.name_} - {self.location_str}"
    
    # LoadBrief:All02md
    def loadbrief(self):
        return "\n".join(self.objectives)
    
    # BRIEF:ALL02MD
    def brief(self):
        return "\n\n".join([*self.description, *self.objectives, *self.hints])

class MissionTranslationParser:
    def __init__(self, filename, check_raw_block=None, categorize=None, loglevel=logging.DEBUG):
        self.logger = logging.getLogger("MissionTranslationParser")
        self.logger.setLevel(loglevel)
        with open(filename, "r") as f:
            self.lines = f.readlines()
        self.check_raw_block = check_raw_block
        self.categorize = categorize

    def preprocess(self):
        buffer = []
        self.blocks = []
        for line in self.lines:
            line = line.strip()
            if len(line) == 0:
                # put buffer to blocks
                if len(buffer) > 0:
                    self.blocks.append(buffer)
                    buffer = []
                continue
            buffer.append(line)
        if len(buffer) > 0:
            self.blocks.append(buffer)
            buffer = []
        
        self.logger.info(f"preprocess completed: created {len(self.blocks)} blocks")

    def parse_block(self, block):
        name = block[0]
        idx = 1
        location = ""
        if block[idx].lower().startswith("location:"):
            location = block[idx]
            idx += 1
        description = []
        for x in block[idx:]:
            if x.lower().startswith("hint:") or x.lower().startswith("note:") or x.lower().startswith("warning:") \
                or x.lower().startswith("additional objective") or (x.lower().startswith("objective ") and x.lower()[10:].split(":", 1)[0].isnumeric()):
                break
            description.append(x)
            idx += 1
        objectives = []
        for x in block[idx:]:
            if x.lower().startswith("additional objective") or (x.lower().startswith("objective ") and x.lower()[10:].split(":", 1)[0].isnumeric()):
                objectives.append(x)
                idx += 1
            else:
                break
        hints = []
        for x in block[idx:]:
            if x.lower().startswith("hint:") or x.lower().startswith("note:") or x.lower().startswith("warning:"):
                hints.append(x)
                idx += 1
            else:
                break
        if idx < len(block):
            self.logger.warning(f"block '{block[0]}' has {len(block)} lines, but only {idx} lines get parsed")
        return Block(name, location, description, objectives, hints)
    
    def parse(self):
        self.parsed_blocks = []
        self.categorized_blocks = {}
        for x in self.blocks:
            if self.check_raw_block is None or self.check_raw_block(x):
                pb = self.parse_block(x)
                self.parsed_blocks.append(pb)
                if self.categorize is not None:
                    self.categorized_blocks[self.categorize(pb)] = pb
            else:
                self.logger.debug(f"ignoring raw block '{x[0]} ...' as it fails check_raw_block")

    def generate_dict(self):
        self.dict_ = {}
        for k, v in self.categorized_blocks.items():
            self.dict_[f"Name:{k}"] = v.name()
            self.dict_[f"Name:{k}Sav"] = v.name()
            self.dict_[f"LoadMsg:{k}"] = v.loadmsg()
            self.dict_[f"LoadBrief:{k}"] = v.loadbrief()
            self.dict_[f"Brief:{k}".upper()] = v.brief()

    def generate_output(self):
        output = []
        for k, v in self.dict_.items():
            output.append({
                "label": k,
                "value": v
            })
        return output

def get_prefix(args):
    profiles = {
        "r1": ("eu", "ussr"),
        "r2": ("yuri", "cn"),
        "r3": ("us", "sr"),
    }
    allies_prefix, soviet_prefix = profiles.get(args.profile, (None, None))
    allies_prefix = args.allies_prefix if allies_prefix is None else allies_prefix
    soviet_prefix = args.soviet_prefix if soviet_prefix is None else soviet_prefix
    return allies_prefix, soviet_prefix

def main(args):
    loglevel = logging.DEBUG if args.verbose else logging.INFO
    logger = logging.getLogger("main")
    logger.setLevel(loglevel)
    logger.debug(f"{args}")
    allies_prefix, soviet_prefix = get_prefix(args)
    logger.debug(f"allies_prefix: {allies_prefix}, soviet_prefix: {soviet_prefix}")
    if allies_prefix is None or soviet_prefix is None:
        raise RuntimeError("no prefix set")
    pattern = f"(?:{allies_prefix}|{soviet_prefix})" + r" ([0-9]{2}|final)"

    def check_raw_block(raw_block):
        # for example "(?:yuri|cn) ([0-9]{2})"
        return re.match(pattern, raw_block[0].lower()) is not None
    
    def categorize(parsed_block):
        nums = ["01", "02", "03", "04", "05", "06", "07"]
        names = [f"All{x}md" for x in nums] + [f"Sov{x}md" for x in nums]
        res = re.match(pattern, parsed_block.name().lower())
        num = res.group(1)
        idx = (14 if num == "final" else int(num)) - 1
        return names[idx]

    p = MissionTranslationParser(args.missions, check_raw_block=check_raw_block, categorize=categorize, loglevel=loglevel)
    p.preprocess()
    p.parse()
    # print(p.parsed_blocks)
    # for x in p.categorized_blocks.items():
    #     print(x)

    p.generate_dict()
    # print(p.dict_)

    with open(args.output, "w") as f:
        json.dump(p.generate_output(), f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="makemissions")
    parser.add_argument("missions", help="missions file (txt)")
    parser.add_argument("-p", "--profile", help="the profile to use (r1, r2, r3)")
    parser.add_argument("-a", "--allies-prefix", help="the prefix for allies mission name, overwrite profile if set")
    parser.add_argument("-s", "--soviet-prefix", help="the prefix for soviet mission name, overwrite profile if set")
    parser.add_argument("output", help="output file (JSON)")
    parser.add_argument("-v", "--verbose", action='store_true', help="display debug info")

    args = parser.parse_args()
    main(args)
