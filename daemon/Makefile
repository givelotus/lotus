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
	@echo "  Release preparation updates daemon/Arch/Docker versions and records patch hashes/source tree."
	@echo "  UPSTREAM is a read-only local ABC repository; CANDIDATE must be a new directory."
	@echo "  Seeds/checkpoints are preserved unless verified network inputs are supplied to the script."
	@echo "  Example from the monorepo root:"
	@echo "    make -C daemon prepare-release UPSTREAM=/tmp/rebase-latest-abc VERSION=11.6.1 CANDIDATE=/tmp/lotus-release-11.6.1"
	@echo "  Review and commit the candidate, then run artifact-only CI for that exact commit:"
	@echo "    gh workflow run release-daemon.yml --repo givelotus/lotus --ref REVIEW_BRANCH"
	@echo "  After the reviewed commit reaches origin/main and CI passes, publish from the candidate:"
	@echo "    python3 daemon/scripts/prepare-release.py --upstream /path/to/abc --publish --reviewed-commit FULL_SHA --validation-run RUN_ID"
	@echo "  Publication creates a new immutable tag; existing releases are refused. Deployment is separate."
	@echo "  Full instructions and validation limits: daemon/docs/release-preparation.md"
	@echo "  Network input schema: daemon/NETWORK-RELEASE.md"
	@echo ""
	@echo "  SERIES=v1 (default): mainnet    — workspace-v1/     (bitcoin-abc 8c67fe1e85 + Chronik)"
	@echo "  SERIES=ecash:        upstream   — workspace-ecash/  (bitcoin-abc 1fb7db17)"
	@echo "  SERIES=doged:        doged      — workspace-doged/  (direct clone doged-io/doged)"
	@echo "  SERIES=bchn:         BCHN       — workspace-bchn/   (exact current-tip pin in bchn-version)"
	@echo "  eCash/BCHN defaults apply no candidates; experimental/placeholder patches are not validated features."
	@echo "  Exact application/build/test evidence: daemon/docs/support-matrix.md"

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
