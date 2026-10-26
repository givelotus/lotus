#!/usr/bin/env python3
import pathlib,json,sys
p=pathlib.Path(__file__).resolve().parent
order=json.loads((p/"CHECKER-DESIRED-ORDER.json").read_text());owners=json.loads((p/"CHECKER-OWNERS.json").read_text())
pathlib.Path(sys.argv[1]).write_text("".join(("edit " if c in owners.values() else "pick ")+c+"\n" for c in order))
