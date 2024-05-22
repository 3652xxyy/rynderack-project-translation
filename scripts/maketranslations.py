import json
import re

import argparse

def main(args):
    with open(args.input, "r") as f:
        input_data = json.loads(f.read())

    output = []
    for x in input_data:
        output.append({
            "label": x["label"],
            "value": x["translated"] if x["translated"] != "TODO" else x["value"],
            "original": x["value"]
        })

    # write data out
    with open(args.output, "w") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="maketranslations")
    parser.add_argument("input", help="input file (JSON)")
    parser.add_argument("output", help="output file (JSON)")

    args = parser.parse_args()
    main(args)
