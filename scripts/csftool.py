# MIT License
#
# Copyright (c) 2023 lewisxy
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# File Format Reference
# https://modenc.renegadeprojects.com/CSF_File_Format

import logging
import struct
from dataclasses import dataclass, asdict
import json
import argparse
import sys

from typing import Literal, Union, Optional, Any, Dict, ByteString

FILE_MAGIC = b"\x20\x46\x53\x43" # " FSC"
LABEL_MAGIC = b"\x20\x4c\x42\x4c" # " LBL"
VALUE_MAGIC = b"\x20\x52\x54\x53" # " RTS"
EXTRA_VALUE_MAGIC = b"\x57\x52\x54\x53" # "WRTS"

def invert(value: bytes) -> bytes:
    return bytes([((~x)+256) % 256 for x in value])

@dataclass
class Entry:
    label: str
    value: str
    extra_value: Optional[str] = None

    def serialize(self) -> bytes:
        res: list[bytes] = []

        res.append(LABEL_MAGIC)
        res.append(struct.pack("<I", 1)) # count = 1 (we can't handle count > 1 in parsing)
        res.append(struct.pack("<I", len(self.label)))
        res.append(self.label.encode("ascii"))

        if self.extra_value is None:
            res.append(VALUE_MAGIC)
        else:
            res.append(EXTRA_VALUE_MAGIC)
        res.append(struct.pack("<I", len(self.value)))
        res.append(invert(self.value.encode("utf-16-le"))) # must specify "le", otherwise endian mark will be included
        if self.extra_value is not None:
            res.append(struct.pack("<I", len(self.extra_value)))
            res.append(self.extra_value.encode("ascii")) # TODO: not sure if it's always ascii

        return b"".join(res)

class Parser:
    def __init__(self, data) -> None:
        self.content: list[Entry] = []
        self.language_id = 0
        self.data = data
        self.idx = 0
        self.logger = logging.getLogger("Parser")
        self.logger.setLevel(logging.DEBUG)

    def read_u32(self):
        num = struct.unpack("<I", self.data[self.idx:self.idx+4])[0]
        self.idx += 4
        return num
    
    def nextn(self, n):
        res = self.data[self.idx:self.idx+n]
        if len(res) < n:
            raise RuntimeError(f"expecting {n} bytes, only {len(res)} bytes found")
        return res
    
    def consume(self, n):
        res = self.nextn(n)
        self.idx += n
        return res

    def expect_and_consume(self, value):
        data_read = self.nextn(len(value))
        if data_read != value:
            raise RuntimeError(f"invalid magic, expecting \"{value}\", got \"{data_read}\"")
        self.idx += len(value)

    def read_header(self):
        self.expect_and_consume(FILE_MAGIC)
        version = self.read_u32()
        if version > 3:
            self.logger.warning(f"unknown version {version}")
        key_count = self.read_u32()
        value_count = self.read_u32()
        if key_count != value_count:
            self.logger.warning(f"key count ({key_count}) != value count ({value_count})")
        self.consume(4) # consume white space
        self.language_id = self.read_u32()
        if self.language_id > 9:
            self.logger.warning(f"unknown language id {self.language_id}")
        return key_count

    def read_entry(self):
        label = self.read_label()
        value = self.read_value()
        if len(value) == 1:
            return Entry(label=label, value=value[0], extra_value=None)
        else:
            return Entry(label=label, value=value[0], extra_value=value[1])

    def read_label(self):
        self.expect_and_consume(LABEL_MAGIC)
        key_num = self.read_u32()
        if key_num != 1:
            self.logger.warning(f"key num ({key_num}) is not 1, multiple keys are unsupposted")
        key_size = self.read_u32()
        key_data = self.consume(key_size)
        return key_data.decode("ascii")

    def read_value(self):
        magic_read = self.consume(4)
        if magic_read == VALUE_MAGIC or magic_read == EXTRA_VALUE_MAGIC:
            value_size = self.read_u32()
            value_data = self.consume(2*value_size)
            value_decoded = self.decode_value(value_data)
            if magic_read == EXTRA_VALUE_MAGIC:
                ec_value_size = self.read_u32()
                ec_value_data = self.consume(ec_value_size)
                ec_value_decoded = ec_value_data.decode("ascii")
                return (value_decoded, ec_value_decoded)
            else:
                return (value_decoded,)
            
    def decode_value(self, value):
        inverted_value = bytes([((~x)+256) % 256 for x in value])
        try:
            res = inverted_value.decode("utf-16")
            return res
        except UnicodeDecodeError:
            return value

    def parse(self):
        size = self.read_header()
        for x in range(size):
            self.content.append(self.read_entry())
        self.logger.info(f"consumed {size} entries ({self.idx} bytes)")
        if self.idx != len(self.data):
            self.logger.warning(f"provided data ({len(self.data)}) longer than consumed ({self.idx})")

    def to_json(self):
        return {
            "api_version": "1",
            "language_id": self.language_id,
            "content": [asdict(x, dict_factory=lambda x: {k: v for (k, v) in x if v is not None}) for x in self.content]
        }

def serialize(json_data) -> bytes:
    api_version = json_data["api_version"]
    if api_version != "1":
        raise RuntimeError(f"unsupported api_version {api_version}")
    
    res: list[bytes] = []
    # write header
    res.append(FILE_MAGIC)
    res.append(struct.pack("<I", 3)) # version 3
    packed_count = struct.pack("<I", len(json_data["content"]))
    res.append(packed_count)
    res.append(packed_count) # append count twice
    res.append(b"\x00" * 4)
    res.append(struct.pack("<I", json_data["language_id"]))

    # note: the constraint is relaxed such that the presence of other keys will be ignored and not cause errors
    res.extend(Entry(**{k: x[k] for k in ('label', 'value', 'extra_value') if k in x}).serialize() for x in json_data["content"])

    return b"".join(res)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="csftool")
    parser.add_argument("-d", "--decode", help="decode csf file (into JSON)", action="store_true")
    parser.add_argument("-e", "--encode", help="encode csf file (from JSON)", action="store_true")
    parser.add_argument("-i", "--input")
    parser.add_argument("-o", "--output")

    args = parser.parse_args()
    if args.encode and args.decode:
        print("error: cannot encode and decode at the same tiem", file=sys.stderr)
        exit(1)

    if not args.encode and not args.decode:
        parser.print_usage(file=sys.stderr)
        exit(1)
    
    if args.decode:
        with open(args.input, "rb") as f:
            data = f.read()
        p = Parser(data)
        p.parse()
        with open(args.output, "w") as f2:
            f2.write(json.dumps(p.to_json(), indent=4, ensure_ascii=False))

    if args.encode:
        with open(args.input, "r") as f3:
            data2 = f3.read()
        res = json.loads(data2)
        with open(args.output, "wb") as f4:
            f4.write(serialize(res))
