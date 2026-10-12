# Test fixtures

`hon-test-data/` is a subset of [mmalolepszy/hon-test-data](https://github.com/mmalolepszy/hon-test-data)
(MIT, see `hon-test-data/LICENSE`), the collection of real appliance dumps contributed by
hOn users. Snapshot taken from commit `ca379ab6fe4a09b94c163d68e4e9f8fa7de633ec`.

Included appliances: AC 397, AP 137, DW 522, HO 710, OV 577, REF 10009, TD 624, WD 209,
WH 265, WM 1301. The JSON files are the originals re-serialised compactly (no content
changes) to keep the repository small.

## Refresh

```bash
git clone --depth 1 https://github.com/mmalolepszy/hon-test-data /tmp/hon-test-data
python3 - <<'PY'
import json, os
src, dst = "/tmp/hon-test-data/test_data", "tests/fixtures/hon-test-data/test_data"
for d in sorted(os.listdir(dst)):
    for f in os.listdir(f"{src}/{d}"):
        if f.endswith(".json"):
            with open(f"{src}/{d}/{f}") as r, open(f"{dst}/{d}/{f}", "w") as w:
                json.dump(json.load(r), w, separators=(",", ":"), ensure_ascii=False)
PY
```

Entity counts in `tests/test_entities.py` change when fixtures or entity descriptions change;
update the expected values deliberately.
