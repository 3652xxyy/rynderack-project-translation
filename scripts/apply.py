import json
import logging
from collections import OrderedDict

import argparse

logging.basicConfig(level=logging.DEBUG)

class CSFData:
    def __init__(self, jsondata, case_sensitive=False, keep_fields=False, loglevel=logging.DEBUG):
        self.logger = logging.getLogger("CSFData")
        self.logger.setLevel(loglevel)
        self.jsondata = jsondata
        self.case_sensitive = case_sensitive
        self.keep_fields = keep_fields
        if self.case_sensitive:
            self.map = OrderedDict((v["label"], dict(v)) for v in self.jsondata["content"])
        else:
            self.map = OrderedDict((v["label"].lower(), dict(v)) for v in self.jsondata["content"])
        if len(self.map) < len(self.jsondata["content"]):
            self.logger.warning(f"duplicated keys detected in base, the latest values are used for duplicated keys")

    def data(self):
        self.jsondata["content"] = list(self.map.values())
        return self.jsondata

    def apply(self, toapply, append=False):
        append_count = 0
        apply_count = 0
        for x in toapply:
            xlabel = x["label"] if self.case_sensitive else x["label"].lower()
            if xlabel in self.map:
                if append:
                    self.logger.warning(f"ignoring duplicated key '{x['label']}' in append mode")
                else:
                    if self.case_sensitive:
                        assert self.map[xlabel]["label"] == xlabel
                    else:
                        assert self.map[xlabel]["label"].lower() == xlabel
                    self.logger.debug(f"applied '{x['label']}': '{self.map[xlabel]['value']}' -> '{x['value']}'")
                    self.map[xlabel]["value"] = x["value"]
                    if self.keep_fields:
                        for y in x:
                            if y not in ["label", "value"]:
                                self.map[xlabel][y] = x[y]
                    apply_count += 1
            else:
                self.map[xlabel] = {
                    "label": x["label"],
                    "value": x["value"],
                }
                if self.keep_fields:
                    for y in x:
                        if y not in ["label", "value"]:
                            self.map[xlabel][y] = x[y]
                self.logger.debug(f"appended {self.map[xlabel]}")
                append_count += 1
        return apply_count, append_count

    def remove(self, toremove):
        remove_count = 0
        for x in toremove:
            xlabel = x["label"] if self.case_sensitive else x["label"].lower()
            if xlabel in self.map:
                self.logger.debug(f"removed {self.map[x['label']]}")
                del self.map[xlabel]
                remove_count += 1
            else:
                self.logger.debug(f"ignoring '{x['label']}' as it is not present in base")
        return remove_count

def main(args):
    loglevel = logging.DEBUG if args.verbose else logging.INFO
    logger = logging.getLogger("main")
    logger.setLevel(loglevel)
    logger.debug(f"{args}")
    with open(args.base, "r") as f:
        data = CSFData(json.loads(f.read()), case_sensitive=args.case_sensitive, keep_fields=args.keep_fields, loglevel=loglevel)
    for type_, path_ in args.actions:
        if type_ == "apply":
            with open(path_, "r") as f:
                apply_count, append_count = data.apply(json.loads(f.read()), append=False)
                logger.info(f"apply '{path_}' complete, applied {apply_count}, appended {append_count}")
        elif type_ == "extend":
            with open(path_, "r") as f:
                _, append_count = data.apply(json.loads(f.read()), append=True)
                logger.info(f"extend '{path_}' complete, appended {append_count}")
        elif type_ == "remove":
            with open(path_, "r") as f:
                remove_count = data.remove(json.loads(f.read()), append=False)
                logger.info(f"remove '{path_}' complete, removed {remove_count}")
        else:
            logger.error(f"unknown operation '{type_}' ignored")
    with open(args.output, "w") as f:
        json.dump(data.data(), f, indent=4, ensure_ascii=False)

def apply_type(path):
    return ("apply", path)

def extend_type(path):
    return ("extend", path)

def remove_type(path):
    return ("remove", path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="apply")
    parser.add_argument("base", help="base file (JSON, csftool compatible)")
    parser.add_argument("-a", "--apply", action='append', dest="actions", metavar="FILE", type=apply_type, help="file containing values to apply (JSON, list of objects containing 'label' and 'value', other fields are permitted but ignored)")
    parser.add_argument("-e", "--extend", action='append', dest="actions", metavar="FILE", type=extend_type, help="file containing values to append (JSON, list of objects containing 'label' and 'value', other fields are permitted but ignored)")
    parser.add_argument("-r", "--remove", action='append', dest="actions", metavar="FILE", type=remove_type, help="file containing keys to remove (JSON, list of objects containing 'label', other fields are permitted but ignored)")
    parser.add_argument("-c", "--case-sensitive", action='store_true', help="use case sensitive match for labels")
    parser.add_argument("-k", "--keep-fields", action='store_true', help="keep additional fields (during apply/extend)")
    # TODO support not remove other keys in apply/extend (since newer csftool ignores non-related keys), this is good for including other information (for documentation purpose)
    parser.add_argument("output", help="output file (JSON, csftool compatible)")
    parser.add_argument("-v", "--verbose", action='store_true', help="display debug info")

    args = parser.parse_args()
    main(args)
