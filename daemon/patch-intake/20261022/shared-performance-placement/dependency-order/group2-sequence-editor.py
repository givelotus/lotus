#!/usr/bin/env python3
import pathlib,json,sys
p=pathlib.Path(__file__).resolve().parent
pathlib.Path(sys.argv[1]).write_text("".join("pick "+c+"\n" for c in json.loads((p/"GROUP2-DESIRED-ORDER.json").read_text())))
