# daemon/Makefile — Lotus mainnet daemon build management
#
# SERIES=v1 (default) — Lotus mainnet, bitcoin-abc-v1-version, workspace-v1/
# SERIES=ecash        — upstream candidates, bitcoin-abc-version, workspace-ecash/
# SERIES=doged        — doged reference, doged-version, workspace-doged/
# SERIES=bchn         — BCHN candidates, bchn-version, workspace-bchn/

SCRIPTS := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))scripts
SERIES  ?= v1

.PHONY: setup build run mkpatch refresh clean help

help:
	@echo "Lotus daemon build targets:"
	@echo "  make setup [SERIES=v1|ecash|doged|bchn]      Clone workspace and apply patches"
	@echo "  make setup RESET=1             Wipe and recreate workspace"
	@echo "  make build [SERIES=v1|ecash|doged|bchn]      Build lotusd and lotus-cli (with Chronik on v1)"
	@echo "  make run   [SERIES=v1|ecash|doged|bchn] ARGS=\"...\"  Run lotusd (sets ulimit -n 65536)"
	@echo "  make mkpatch NAME=<n>          Save workspace changes as patches/<n>.patch"
	@echo "  make refresh COMMIT=<c>        Rebase onto new base commit or tag"
	@echo ""
	@echo "  SERIES=v1 (default): mainnet    — workspace-v1/     (bitcoin-abc 8c67fe1e85 + Chronik)"
	@echo "  SERIES=ecash:        upstream   — workspace-ecash/  (bitcoin-abc 252182e9)"
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
	rm -rf workspace-ecash/build workspace-v1/build workspace-doged/build workspace-bchn/build
