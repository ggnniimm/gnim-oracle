"""List all PDF files from all Drive folders and save correct filename→ID mapping."""
import json, os, sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))

from src.ingestion.drive import list_files

FOLDERS = {
    "CGD":     os.getenv("DRIVE_FOLDER_CGD",     "1ALzpEcLpelOFEpTzmLCt_gTpV8vcpqXV"),
    "CGD_W":   os.getenv("DRIVE_FOLDER_CGD_W",   "1rIcnibnDOp7-Br4V0OZQ6LJCyLJGzjnu"),
    "CGD3":    os.getenv("DRIVE_FOLDER_CGD3",     "11ZLGuCMRO3OhOHbIJSbDcZW8UIU_sobE"),
    "CGD_OLD": os.getenv("DRIVE_FOLDER_CGD_OLD",  "1pWKcKJ_YhJ9MfXwkmY6MFUCJ4Sar-3d4"),
    "OAG":     os.getenv("DRIVE_FOLDER_OAG",      "1Z6qg4Hi1uvUtpwGH2n1wVgIng4FuJauK"),
    "AC":      os.getenv("DRIVE_FOLDER_AC",       "1_NGGLSfMmlaICUNLXZym6MrCfJiWyRfI"),
    "LAW":     os.getenv("DRIVE_FOLDER_LAW",      "1VLrTuQieZ3tdI8o_MO8RvA69tq-m5MGI"),
    "ETC":     os.getenv("DRIVE_FOLDER_ETC",      "1HO_XcrMKaEWIcPa-es6eHuF3pjAAJalf"),
}

mapping = {}  # filename_stem → {file_id, file_url, folder}
for folder_name, folder_id in FOLDERS.items():
    print(f"Listing {folder_name}...", flush=True)
    try:
        files = list_files(folder_id)
        for f in files:
            stem = __import__('pathlib').Path(f["name"]).stem
            mapping[stem] = {
                "file_id": f["id"],
                "file_url": f"https://drive.google.com/file/d/{f['id']}/view",
                "folder": folder_name,
                "name": f["name"],
            }
        print(f"  {len(files)} files")
    except Exception as e:
        print(f"  ERROR: {e}")

out = "/tmp/drive_mapping.json"
with open(out, "w") as f:
    json.dump(mapping, f, ensure_ascii=False, indent=2)
print(f"\nSaved {len(mapping)} entries to {out}")
