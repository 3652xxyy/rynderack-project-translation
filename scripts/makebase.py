"""
Create the base CSF (JSON) for Rynderack Project translation
"""

import json
import argparse

def main(args):
    with open(args.input, "r") as f:
        original_data = json.loads(f.read())

    exclude_from_original = ["Name:Hero1", "Name:Hero2", "Name:Hero3"]

    add_to_original = [
        {
            "label": "Name:TRAIN",
            "value": "Train"
        },
        {
            "label": "Name:TSHIP",
            "value": "Cargo Ship"
        },
        {
            "label": "Name:BSHIP",
            "value": "Battleship"
        },
        {
            "label": "Name:HWTZ",
            "value": "Howitzer"
        },
    ]

    # replace value
    overwrite_original = {
        "Name:CASANF15": "Water Tower",
        "Name:CATRAN03": "Dracula's Castle",
        "Name:CALA06": "Control Tower",
    }

    # overwrite to empty
    remove_original = ["TXT_LIGHTNING_STORM_APPROACHING", "TXT_LIGHTNING_STORM"]

    new_content = []
    for x in original_data["content"]:
        if x["label"] not in exclude_from_original:
            # overwrite if needed
            x["value"] = overwrite_original.get(x["label"], x["value"])
            # remove if needed
            x["value"] = "" if x["label"] in remove_original else x["value"]
            new_content.append(x)

    for x in add_to_original:
        new_content.append(x)

    original_data["content"] = new_content

    # write data out
    with open(args.output, "w") as f:
        json.dump(original_data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="makebase")
    parser.add_argument("input", help="input file (JSON)")
    parser.add_argument("output", help="output file (JSON)")

    args = parser.parse_args()
    main(args)
