## ptyterm Integration (Developer Guide)

This repo depends on the standalone `ptyterm` toolkit for all PTY/VTerm functionality.

### Bootstrap

```bash
make submodules-init
make deps-pty
```

Alternatively via CLI:

```bash
python -m xbot.cli deps pty-install
python -m xbot.cli deps pty-verify
```

### Remote Sync (optional)

Attach your ptyterm local repo to a remote and repoint the submodule URL:

```bash
make pty-remote-sync URL=git@github.com:YOURORG/ptyterm.git
```

### CI Notes

CI installs `ptyterm` from the submodule if present. If the submodule is not available, it falls back to installing a released version that satisfies `ptyterm>=0.1.0`.

