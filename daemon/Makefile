# daemon/Makefile — Lotus daemon build management
#
# Each series has its own base:
#   SERIES=v2    — bitcoin-abc HEAD (252182e9)       see bitcoin-abc-version
#   SERIES=v1    — eCash v0.24.11  (fa7a44f73)       see ecash-version
#   SERIES=doged — doged-io/doged  (direct clone)    see doged-version
#   SERIES=bchn  — BCHN v28.0.0                      see bchn-version
#
# Four build targets are supported:
#   SERIES=v2 (default) — new chain (workspace-v2/):   bitcoin-abc 252182e9 + Lotus v2 patches
#   SERIES=v1           — mainnet   (workspace-v1/):   lotusd history rebased onto bitcoin-abc
#   SERIES=ecash        — eCash PRs (workspace-v2/):   mining + NNG patches for upstream
#   SERIES=doged        — doged     (workspace-doged/): doged-io/doged direct clone
#   SERIES=bchn         — BCHN      (workspace-bchn/):  BCHN v28.0.0 + mining patches
#
# Targets:
#   make setup              — apply patch series into workspace (V2 default)
#   make setup SERIES=v1    — clone bitcoin-abc + apply v1 patches into workspace-v1/
#   make setup RESET=1      — wipe and recreate workspace from scratch
#   make build              — compile lotusd + lotus-cli
#   make run ARGS="..."     — run lotusd with ulimit -n 65536 pre-set
#   make mkpatch NAME=<n>   — save current workspace changes as patches/<n>.patch
#   make refresh COMMIT=<c> — rebase onto new base (bitcoin-abc commit for v1/v2/doged)

SCRIPTS := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))scripts
SERIES  ?= v2

.PHONY: setup build run mkpatch refresh clean help

help:
	@echo "Lotus daemon build targets:"
	@echo "  make setup [SERIES=v1|v2]      Clone workspace and apply patches"
	@echo "  make setup RESET=1             Wipe and recreate workspace"
	@echo "  make build [SERIES=v1|v2]      Build lotusd and lotus-cli"
	@echo "  make run   [SERIES=v1|v2] ARGS=\"...\"  Run lotusd (sets ulimit -n 65536)"
	@echo "  make mkpatch NAME=<n>          Save workspace changes as patches/<n>.patch"
	@echo "  make refresh COMMIT=<c>        Rebase onto new base commit or tag"
	@echo ""
	@echo "  SERIES=v2 (default): new chain  — workspace-v2/     (bitcoin-abc 252182e9)"
	@echo "  SERIES=v1:           mainnet    — workspace-v1/     (eCash v0.24.11 fa7a44f73)"
	@echo "  SERIES=doged:        doged      — workspace-doged/  (direct clone doged-io/doged)"
	@echo "  SERIES=bchn:         BCHN       — workspace-bchn/   (BCHN v28.0.0)"

setup:
ifdef RESET
	SERIES=$(SERIES) $(SCRIPTS)/setup.sh --reset
else
	SERIES=$(SERIES) $(SCRIPTS)/setup.sh
endif

build:
	SERIES=$(SERIES) $(SCRIPTS)/build.sh

run:
	SERIES=$(SERIES) $(SCRIPTS)/run.sh $(ARGS)

mkpatch:
ifndef NAME
	$(error NAME is required: make mkpatch NAME=02-my-change)
endif
	SERIES=$(SERIES) $(SCRIPTS)/mkpatch.sh $(NAME)

refresh:
ifndef COMMIT
	$(error COMMIT is required: make refresh COMMIT=<hash-or-tag>)
endif
ifdef DESC
	SERIES=$(SERIES) $(SCRIPTS)/refresh.sh $(COMMIT) "$(DESC)"
else
	SERIES=$(SERIES) $(SCRIPTS)/refresh.sh $(COMMIT)
endif

clean:
	rm -rf workspace-v2/build workspace-v1/build workspace-doged/build workspace-bchn/build
