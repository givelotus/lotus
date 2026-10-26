# daemon/Makefile — Lotus mainnet daemon build management
#
# SERIES=v1 (default) — Lotus mainnet, bitcoin-abc-v1-version, workspace-v1/
# SERIES=v2           — Lotus V2 new chain (self-describing @include ../ecash/series + patches/v2/series), workspace-v2/
# SERIES=ecash        — Bitcoin ABC / eCash high-throughput engine & P2P layer, shared bitcoin-abc-version, workspace-ecash/
# SERIES=doged        — Dogecoin on shared Bitcoin ABC pin, workspace-doged-abc/
# SERIES=doged-reference — pinned doged-io/doged reference, doged-reference-version/
# SERIES=bchn         — BCHN candidates, bchn-version, workspace-bchn/

SCRIPTS := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))scripts
SERIES  ?= v1

.PHONY: setup build run mkpatch refresh refresh-abc refresh-chronik prepare-release prepare-component features clean help

help:
	@echo "Pinned daemon source submodules (no automatic stack application):"
	@echo "  make setup SERIES=all|ecash|v2|v1|doged|bchn|bitcoin   Initialize exact gitlinks"
	@echo "  make status                                         Verify repos, pins and trees"
	@echo "  make source-plan SERIES=v2                           Show shared then native order"
	@echo "  make source-plan SERIES=v2 PLAN_ARGS=--commits       Show individual commit order"
	@echo "  make source-verify                                  Check every source submodule"
	@echo "  make build/run SERIES=...                           Require promoted stack first"
	@echo "Stack mutation/replay and releases remain deferred during source-order review."

setup:
ifdef RESET
	SERIES=$(SERIES) $(SCRIPTS)/setup.sh --reset
else
	SERIES=$(SERIES) $(SCRIPTS)/setup.sh
endif
	python3 $(SCRIPTS)/lotus-git.py init $(SERIES)

source-plan:
	python3 $(SCRIPTS)/daemon_sources.py plan $(SERIES) $(PLAN_ARGS)

source-verify:
	python3 $(SCRIPTS)/daemon_sources.py verify all

source-path:
	python3 $(SCRIPTS)/daemon_sources.py path $(SERIES)

status:
	python3 $(SCRIPTS)/lotus-git.py status

init:
	python3 $(SCRIPTS)/lotus-git.py init $(SERIES)

autosquash:
	python3 $(SCRIPTS)/lotus-git.py autosquash $(SERIES) $(if $(filter 1,$(PATCHES)),--export-patches)

sync:
	python3 $(SCRIPTS)/lotus-git.py sync $(SERIES) $(if $(filter 1,$(PATCHES)),--export-patches) $(if $(filter 1,$(VERIFY)),--verify-replay) $(if $(filter 1,$(PUSH)),--push)

sink-to-ecash:
	python3 $(SCRIPTS)/lotus-git.py sink-to-ecash $(or $(COMMIT),HEAD) $(if $(filter 1,$(PATCHES)),--export-patches)

rebase-upstream:
ifndef COMMIT
	$(error COMMIT is required: make rebase-upstream SERIES=v2 COMMIT=<sha|latest>)
endif
	python3 $(SCRIPTS)/lotus-git.py rebase-upstream $(SERIES) --onto "$(COMMIT)" $(if $(filter 1,$(PATCHES)),--export-patches)

extract-pr:
ifndef BRANCH
	$(error BRANCH is required: make extract-pr SERIES=ecash BRANCH=pr/my-feature COMMITS="<sha>")
endif
	python3 $(SCRIPTS)/lotus-git.py extract-pr $(SERIES) --branch "$(BRANCH)" $(or $(COMMITS),base/abc..daemon/$(SERIES))

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
	python3 $(SCRIPTS)/prepare-release.py --upstream "$(UPSTREAM)" --version "$(VERSION)" --patch-revision "$(or $(PATCH_REVISION),1)" --candidate "$(CANDIDATE)"

prepare-component:
ifndef COMPONENT
	$(error COMPONENT is required: lotusd, bitcoin-abc, bchn, doged, or bitcoin-core)
endif
ifndef UPSTREAM
	$(error UPSTREAM must identify an existing read-only Git object source)
endif
ifndef VERSION
	$(error VERSION must identify the distributor version x.y.z)
endif
ifndef CANDIDATE
	$(error CANDIDATE must identify a new isolated review directory)
endif
	python3 $(SCRIPTS)/component-release.py --component "$(COMPONENT)" --upstream "$(UPSTREAM)" --version "$(VERSION)" --patch-revision "$(or $(PATCH_REVISION),1)" --candidate "$(CANDIDATE)" $(if $(PROFILE),--profile "$(PROFILE)") $(if $(FEATURES),--features "$(FEATURES)") $(if $(filter 1,$(ALLOW_EXPERIMENTAL)),--allow-experimental)

run:
	SERIES=$(SERIES) $(SCRIPTS)/run.sh $(ARGS)

mkpatch:
ifndef NAME
	$(error NAME is required: make mkpatch NAME=02-my-change)
endif
	SERIES=$(SERIES) $(SCRIPTS)/mkpatch.sh $(NAME)

refresh:
ifndef COMMIT
	$(error COMMIT is required: make refresh COMMIT=<hash-or-tag|latest>)
endif
ifdef DESC
	SERIES=$(SERIES) $(SCRIPTS)/refresh.sh $(COMMIT) "$(DESC)"
else
	SERIES=$(SERIES) $(SCRIPTS)/refresh.sh $(COMMIT)
endif

refresh-chronik:
ifndef CANDIDATE
	$(error CANDIDATE must identify a new output directory)
endif
	python3 $(SCRIPTS)/prepare-chronik-refresh.py $(if $(UPSTREAM),--upstream "$(UPSTREAM)") --ref "$(or $(REF),latest)" --candidate "$(CANDIDATE)"

refresh-abc:
ifndef CANDIDATE
	$(error CANDIDATE must identify a new review-candidate directory)
endif
	python3 $(SCRIPTS)/prepare-abc-refresh.py --ref "$(or $(REF),latest)" --candidate "$(CANDIDATE)"

clean:
	@series="$$(python3 $(SCRIPTS)/daemon_sources.py canonical "$(SERIES)")" || exit 1; \
	if [ -f "$(SCRIPTS)/../.build/$$series/CMakeCache.txt" ]; then \
	  cmake --build "$(SCRIPTS)/../.build/$$series" --target clean; \
	else echo "No submodule build to clean for $$series; legacy workspaces preserved."; fi

# Historical replay/export entrypoints cannot run against the base-only scaffold.
.PHONY: source-plan source-verify source-path reviewed-source
reviewed-source:
	python3 $(SCRIPTS)/daemon_sources.py release-check all

refresh refresh-abc mkpatch prepare-release prepare-component: reviewed-source
