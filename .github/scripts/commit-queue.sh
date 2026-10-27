#!/usr/bin/env bash
# Commit and push queue.json if the publisher changed it; retried because a weekly batch may be pushed meanwhile.
if git diff --quiet queue.json; then exit 0; fi
git config user.name "stoic-autopilot"
git config user.email "stoic-autopilot@users.noreply.github.com"
git commit -m "chore: update queue status" queue.json
for attempt in 1 2 3; do
  if git pull --rebase && git push; then exit 0; fi
  git rebase --abort 2>/dev/null || true
  sleep 15
done
echo "could not push queue.json; published posts may be republished" >&2
exit 1
