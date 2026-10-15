# daemon/Makefile — Lotus mainnet daemon build management
#
# SERIES=v1 (default) — Lotus mainnet, bitcoin-abc-v1-version, workspace-v1/
# SERIES=ecash        — upstream candidates, bitcoin-abc-version, workspace-ecash/
# SERIES=doged        — Dogecoin on pinned Bitcoin ABC, doged-version, workspace-doged-abc/
# SERIES=doged-reference — pinned doged-io/doged reference, doged-reference-version/
# SERIES=bchn         — BCHN candidates, bchn-version, workspace-bchn/

SCRIPTS := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))scripts
SERIES  ?= v1

.PHONY: setup build run mkpatch refresh refresh-chronik prepare-release prepare-component features clean help

help:
	@echo "Lotus daemon build targets:"
	@echo "  make setup [SERIES=v1|ecash|doged|doged-reference|bchn|bitcoin] Clone workspace and apply patches"
	@echo "  Existing workspaces are preserved; move an old workspace aside before setup."
	@echo "  make build [SERIES=v1|ecash|doged|doged-reference|bchn|bitcoin] Build selected daemon and CLI"
	@echo "  make run   [SERIES=v1|ecash|doged|doged-reference|bchn|bitcoin] ARGS=\"...\"  Run selected daemon"
	@echo "  make mkpatch NAME=<n>          Export committed HEAD with authorship and rationale"
	@echo "  make refresh COMMIT=<sha|tag|latest> [SERIES=...]  Rebase patches, then advance the pin"
	@echo "    COMMIT=latest resolves origin's advertised default branch; review every rebase/build result."
	@echo "  make refresh-chronik UPSTREAM=<ABC clone> [REF=latest] CANDIDATE=<new-dir>"
	@echo "    Prepare an isolated shared-Chronik source/export candidate and test adapter patch application."
	@echo "    Does not change active provider pins, host profiles, workspaces, or releases."
	@echo "  Human patch workflow: daemon/docs/adding-patches.md"
	@echo "  make build FEATURES=chronik,nng-off       Select independent build options"
	@echo "  make features FEATURES=chronik,zeromq-off Show resolved flags and dependencies"
	@echo "  make prepare-component COMPONENT=bitcoin-core UPSTREAM=<repo> VERSION=<distributor-x.y.z> CANDIDATE=<new-dir>"
	@echo "  Use PROFILE=custom FEATURES=chronik for explicit independent feature selection."
	@echo "  After reviewing/committing the candidate, validate artifacts for that exact commit:"
	@echo "    gh workflow run release-components.yml --ref REVIEW_BRANCH -f component=bitcoin-abc"
	@echo "  Publish only after exact component CI passes and the reviewed commit reaches main:"
	@echo "    python3 daemon/scripts/component-release.py --component NAME --upstream REPO --publish --reviewed-commit FULL_SHA --validation-run RUN_ID"
	@echo "  Component names/tags/patch profiles: daemon/docs/component-releases.md"
	@echo "  Legacy v11: make prepare-release UPSTREAM=<repo> VERSION=<x.y.z> CANDIDATE=<new-dir>"
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
	@echo "  SERIES=doged:        Dogecoin   — workspace-doged-abc/ (Bitcoin ABC + 174 maintained patches)"
	@echo "  SERIES=doged-reference: doged   — workspace-doged-reference/ (pinned doged-io/doged reference)"
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
ifndef UPSTREAM
	$(error UPSTREAM must identify an existing Bitcoin ABC clone)
endif
ifndef CANDIDATE
	$(error CANDIDATE must identify a new output directory)
endif
	python3 $(SCRIPTS)/prepare-chronik-refresh.py --upstream "$(UPSTREAM)" --ref "$(or $(REF),latest)" --candidate "$(CANDIDATE)"

clean:
	rm -rf workspace-ecash/build workspace-v1/build workspace-doged-abc/build workspace-doged-reference/build workspace-bchn/build workspace-bitcoin/build
