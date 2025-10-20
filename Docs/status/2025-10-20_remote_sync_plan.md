## Input Analysis

- Goal: Point submodule to remote repo and push ptyterm `main` upstream.
- Constraint: Credentials may be required for `git push`; step proceeds best-effort.

## Synthesis (Step Plan)

1) Set `origin` remote on `/Users/doctordre/projects/pty` to provided URL.
2) Push `main` to remote (best-effort; may require auth).
3) Update `.gitmodules` entry `submodule.submodules/ptyterm.url` to the URL.
4) Sync submodule and commit `.gitmodules` change in 4bot.
5) CI remains compatible (checks out submodules and installs ptyterm).

## Output

- CLI command: `python -m xbot.cli deps pty-remote-sync --url <REMOTE>`
- Make target: `make pty-remote-sync URL=<REMOTE>`
- After running and authenticating, submodule points to the remote.

