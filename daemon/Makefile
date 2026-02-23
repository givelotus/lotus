# daemon/Makefile — Lotus daemon build management
#
# Targets:
#   make setup              — clone eCash workspace and apply patch series
#   make setup RESET=1      — wipe and recreate workspace from scratch
#   make build              — compile lotusd + lotus-cli
#   make run ARGS="..."     — run lotusd with ulimit -n 65536 pre-set
#   make mkpatch NAME=<n>   — save current workspace changes as patches/<n>.patch
#   make refresh COMMIT=<c> — rebase patch series onto new eCash commit
#   make refresh COMMIT=<c> DESC="v0.27.0" — with description
#   make clean              — remove build artifacts (not workspace)

SCRIPTS := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))scripts

.PHONY: setup build run mkpatch refresh clean help

help:
	@echo "Lotus daemon build targets:"
	@echo "  make setup               Clone workspace and apply patches"
	@echo "  make setup RESET=1       Wipe and recreate workspace"
	@echo "  make build               Build lotusd and lotus-cli"
	@echo "  make run ARGS=\"...\"      Run lotusd (sets ulimit -n 65536)"
	@echo "  make mkpatch NAME=<n>    Save workspace changes as patches/<n>.patch"
	@echo "  make refresh COMMIT=<c>  Rebase patches onto new eCash commit"
	@echo "  make clean               Remove build directory"

setup:
ifdef RESET
	$(SCRIPTS)/setup.sh --reset
else
	$(SCRIPTS)/setup.sh
endif

build:
	$(SCRIPTS)/build.sh

run:
	$(SCRIPTS)/run.sh $(ARGS)

mkpatch:
ifndef NAME
	$(error NAME is required: make mkpatch NAME=02-my-change)
endif
	$(SCRIPTS)/mkpatch.sh $(NAME)

refresh:
ifndef COMMIT
	$(error COMMIT is required: make refresh COMMIT=<ecash-git-hash>)
endif
ifdef DESC
	$(SCRIPTS)/refresh.sh $(COMMIT) "$(DESC)"
else
	$(SCRIPTS)/refresh.sh $(COMMIT)
endif

clean:
	rm -rf workspace/build
