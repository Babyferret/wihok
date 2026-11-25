"""Which real songs the optional real-audio tests use.

That choice is personal (the songs come from your own music folder), so it is not kept in the
repository. Put it in samples/wihok-samples.json, which git ignores, or point WIHOK_SAMPLES_CONFIG
at another file. The format:

    {
      "labeled": [{"file": "<file name or glob>", "bpm": 120, "key": "A minor"}],
      "pairs":   [{"full": "<song with vocals>", "reference": "<the same song, vocals removed>"}]
    }

"key" may be null. File names are looked up in the folder that WIHOK_SAMPLES points to. Without
this file the real-audio tests are skipped.
"""
import json
import os
from pathlib import Path

CONFIG = Path(
    os.environ.get("WIHOK_SAMPLES_CONFIG")
    or Path(__file__).resolve().parent.parent / "samples" / "wihok-samples.json"
)


def configured(section: str) -> list[dict]:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8")).get(section, [])
    except FileNotFoundError:
        return []
