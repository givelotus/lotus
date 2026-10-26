#!/usr/bin/env python3
import pathlib,json,sys
p=pathlib.Path(__file__).resolve().parent
t=json.loads((p/"HUNK-TRANSFER.json").read_text());ed={t["db"],t["logger"]}
pathlib.Path(sys.argv[1]).write_text("".join(("edit " if c in ed else "pick ")+c+"\n"for c in json.loads((p/"GROUP3-DESIRED-ORDER.json").read_text())))
