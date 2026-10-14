# daemon/Makefile — Lotus mainnet daemon build management
#
# SERIES=v1 (default) — Lotus mainnet, bitcoin-abc-v1-version, workspace-v1/
# SERIES=ecash        — upstream candidates, bitcoin-abc-version, workspace-ecash/
# SERIES=doged        — doged reference, doged-version, workspace-doged/
# SERIES=bchn         — BCHN candidates, bchn-version, workspace-bchn/

SCRIPTS := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))scripts
SERIES  ?= v1

.PHONY: setup build run mkpatch refresh prepare-release features clean help

help:
	@echo "Lotus daemon build targets:"
	@echo "  make setup [SERIES=v1|ecash|doged|bchn]      Clone workspace and apply patches"
	@echo "  Existing workspaces are preserved; move an old workspace aside before setup."
	@echo "  make build [SERIES=v1|ecash|doged|bchn]      Build lotusd and lotus-cli (with Chronik on v1)"
	@echo "  make run   [SERIES=v1|ecash|doged|bchn] ARGS=\"...\"  Run lotusd (sets ulimit -n 65536)"
	@echo "  make mkpatch NAME=<n>          Export committed HEAD with authorship and rationale"
	@echo "  make refresh COMMIT=<c>        Rebase onto new base commit or tag"
	@echo "  make build FEATURES=chronik,nng-off       Select independent build options"
	@echo "  make features FEATURES=chronik,zeromq-off Show resolved flags and dependencies"
	@echo "  make prepare-release UPSTREAM=<repo> VERSION=<x.y.z> CANDIDATE=<new-dir>"
	@echo "                                Prepare an atomic review candidate; never publish"
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
	SERIES=$(SERIES) FEATURES="$(FEATURES)" $(SCRIPTS)/build.sh

features:
ifndef FEATURES
	$(error FEATURES is required: make features FEATURES=chronik,nng-off)
endif
	python3 $(SCRIPTS)/feature-plan.py --target $(SERIES) --features "$(FEATURES)"

prepare-release:
ifndef UPSTREAM
	$(error UPSTREAM must identify an existing Git repository containing the pinned ABC base)
endif
ifndef VERSION
	$(error VERSION is required: VERSION=11.6.1)
endif
ifndef CANDIDATE
	$(error CANDIDATE must identify a new directory for the review candidate)
endif
	python3 $(SCRIPTS)/prepare-release.py --upstream "$(UPSTREAM)" --version "$(VERSION)" --candidate "$(CANDIDATE)"

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
