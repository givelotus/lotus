#!/usr/bin/env bash

resolve_upstream_ref() {
    local workspace="$1" requested="$2" remote_head branch
    git -C "$workspace" fetch --no-tags origin
    if [[ "$requested" != latest ]]; then
        if git -C "$workspace" rev-parse --verify "$requested^{commit}" 2>/dev/null; then
            return
        fi
        if git -C "$workspace" rev-parse --verify "refs/remotes/origin/$requested^{commit}" 2>/dev/null; then
            return
        fi
        git -C "$workspace" fetch --no-tags origin "$requested"
        git -C "$workspace" rev-parse --verify 'FETCH_HEAD^{commit}'
        return
    fi
    remote_head=$(git -C "$workspace" ls-remote --symref origin HEAD)
    branch=$(awk '$1 == "ref:" && $3 == "HEAD" {sub("refs/heads/", "", $2); print $2; exit}' <<< "$remote_head")
    if [[ -z "$branch" ]]; then
        echo "Cannot resolve the upstream default branch from origin/HEAD" >&2
        return 1
    fi
    git -C "$workspace" fetch --no-tags origin "refs/heads/$branch"
    git -C "$workspace" rev-parse --verify 'FETCH_HEAD^{commit}'
}
