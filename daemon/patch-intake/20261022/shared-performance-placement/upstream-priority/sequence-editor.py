#!/usr/bin/env python3
import sys,json,pathlib
p=pathlib.Path(__file__).resolve().parent
order=json.loads((p/"DESIRED-ORDER.json").read_text())
pathlib.Path(sys.argv[1]).write_text("".join("pick "+x+"\n" for x in order))
