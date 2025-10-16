from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "Docs" / "status"

FILES = {
    "auth_tokens_json": ROOT / "auth_data/x_tokens.json",
    "auth_tokens_env": ROOT / "auth_data/x_tokens.env",
    "auth_tokens_txt": ROOT / "auth_data/x_tokens.txt",
    "cookies_json": ROOT / "auth_data/x_cookies.json",
    "cookies_netscape": ROOT / "auth_data/x_cookies_netscape.txt",
    "chrome_profile_cookies": ROOT / "chrome_profiles/cookies/default_cookies.json",
    "storage_state_profile": ROOT / "auth/4botbsc/storageState.json",
    "storage_state_config": ROOT / "config/profiles/4botbsc/storageState.json",
}


def exists(p: Path) -> bool:
    try:
        return p.exists()
    except Exception:
        return False


def load_json(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def audit() -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"# Token & Cookie Audit ({now})", ""]
    summary = {}

    for key, path in FILES.items():
        status = {"path": str(path), "exists": exists(path)}
        if status["exists"] and path.suffix == ".json":
            data = load_json(path)
            if isinstance(data, dict):
                txt = json.dumps(list(data.keys())[:8])
                status["json_keys"] = txt
                # quick checks
                if "auth_token" in data:
                    status["has_auth_token"] = True
                if "ct0" in data:
                    status["has_ct0"] = True
            elif isinstance(data, list):
                status["items"] = len(data)
                # check for key cookies
                names = {c.get("name", "") for c in data if isinstance(c, dict)}
                status["has_auth_token"] = ("auth_token" in names)
                status["has_ct0"] = ("ct0" in names)
        summary[key] = status

    # Write human readable
    for k, v in summary.items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines) + "\n"


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    out = DOCS / f"{datetime.now().date()}_token_audit.md"
    out.write_text(audit(), encoding="utf-8")
    print(str(out))


if __name__ == "__main__":
    main()

