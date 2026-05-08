"""Compare two Vertex AI embedding models on Thai legal text.

Usage:
    python3 scripts/compare_embed_models.py \
        --model-a gemini-embedding-2-preview \
        --model-b gemini-embedding-2

Reports:
    1. Cross-model cosine for same text (compat check — close to 1.0 = same space)
    2. Within-model retrieval rank for query→doc pairs (quality check)
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

try:
    from google import genai
except ImportError:
    sys.exit("pip install google-genai>=1.74.0")


# Thai legal text samples — queries paired with their expected top doc
PAIRS = [
    (
        "ผู้รับจ้างส่งมอบงานล่าช้า หน่วยงานต้องทำอย่างไร",
        "กรณีผู้รับจ้างส่งมอบงานเกินกำหนดเวลาตามสัญญา ให้หน่วยงานคิดค่าปรับรายวันตามอัตราที่กำหนดในสัญญา และพิจารณาบอกเลิกสัญญาเมื่อค่าปรับเกินร้อยละสิบของวงเงินสัญญา",
    ),
    (
        "การจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจงทำได้เมื่อใด",
        "วิธีเฉพาะเจาะจงใช้ได้เมื่อวงเงินไม่เกินห้าแสนบาท หรือมีผู้ประกอบการรายเดียวที่สามารถดำเนินการได้ตามที่กฎหมายกำหนด",
    ),
    (
        "ผู้ทิ้งงานคืออะไร มีผลอย่างไร",
        "ผู้ทิ้งงานคือผู้ที่ถูกแจ้งเวียนชื่อให้หน่วยงานของรัฐทราบว่าเป็นผู้ละทิ้งงาน ห้ามหน่วยงานของรัฐทำสัญญาด้วยจนกว่าจะพ้นกำหนดเวลา",
    ),
    (
        "การคำนวณค่าปรับเริ่มนับวันใด",
        "ให้คำนวณค่าปรับโดยเริ่มนับตั้งแต่วันถัดจากวันครบกำหนดส่งมอบตามสัญญา จนถึงวันที่หน่วยงานได้รับมอบงาน",
    ),
]

DISTRACTORS = [
    "การรักษาความปลอดภัยข้อมูลส่วนบุคคลตามพระราชบัญญัติคุ้มครองข้อมูลส่วนบุคคล",
    "การจดทะเบียนเครื่องหมายการค้ากับกรมทรัพย์สินทางปัญญา",
    "ภาษีเงินได้นิติบุคคลคำนวณจากกำไรสุทธิตามประมวลรัษฎากร",
]


def embed(client, model: str, text: str, retries: int = 5) -> np.ndarray:
    for attempt in range(1, retries + 1):
        try:
            r = client.models.embed_content(model=model, contents=text)
            return np.array(r.embeddings[0].values, dtype=np.float32)
        except Exception as e:
            err = str(e)
            if attempt == retries:
                raise
            wait = 30 if "429" in err or "RESOURCE_EXHAUSTED" in err else 3
            print(f"  retry {attempt}/{retries} after {wait}s: {err[:100]}", file=sys.stderr)
            time.sleep(wait)


def cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model-a", default="gemini-embedding-2-preview")
    p.add_argument("--model-b", default="gemini-embedding-2")
    args = p.parse_args()

    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    if not project:
        sys.exit("set GOOGLE_CLOUD_PROJECT")

    client = genai.Client(vertexai=True, project=project, location=location)

    queries = [q for q, _ in PAIRS]
    pos_docs = [d for _, d in PAIRS]
    all_docs = pos_docs + DISTRACTORS

    print(f"Model A: {args.model_a}")
    print(f"Model B: {args.model_b}")
    print(f"Project: {project}  Location: {location}\n")

    # Embed all texts under both models
    def embed_all(model: str) -> tuple[list[np.ndarray], list[np.ndarray]]:
        print(f"embedding under {model}...")
        qs = [embed(client, model, q) for q in queries]
        ds = [embed(client, model, d) for d in all_docs]
        return qs, ds

    qa, da = embed_all(args.model_a)
    qb, db = embed_all(args.model_b)

    print(f"\ndim A={len(qa[0])}  dim B={len(qb[0])}")

    # 1. Cross-model cosine for same text — vector-space compatibility
    print("\n=== Cross-model cosine (same text, A vs B) ===")
    print("  ~0.99+ = same vector space (no re-index needed)")
    print("  <0.5   = different space (must re-index everything)\n")
    cross = []
    for i, q in enumerate(queries):
        # Pad/truncate to min dim if shapes differ
        n = min(len(qa[i]), len(qb[i]))
        c = cos(qa[i][:n], qb[i][:n])
        cross.append(c)
        print(f"  Q{i+1}: {c:.4f}  | {q[:50]}")
    print(f"\n  mean cross-model cosine = {np.mean(cross):.4f}")

    # 2. Retrieval quality — for each query, rank pos_doc among all_docs
    def rank_quality(qs, ds, label):
        print(f"\n=== Retrieval quality under {label} ===")
        print("  query → cos to correct doc | cos to top distractor | gap")
        gaps = []
        for i, q in enumerate(qs):
            sims = [cos(q, d) for d in ds]
            pos_sim = sims[i]
            distractor_sims = sims[len(pos_docs):]
            top_distractor = max(distractor_sims)
            gap = pos_sim - top_distractor
            gaps.append(gap)
            ok = "✓" if gap > 0 else "✗"
            print(f"  {ok} Q{i+1}: pos={pos_sim:.3f}  top-distractor={top_distractor:.3f}  gap={gap:+.3f}")
        print(f"  mean gap = {np.mean(gaps):+.4f}  (higher = better separation)")
        return gaps

    gaps_a = rank_quality(qa, da, args.model_a)
    gaps_b = rank_quality(qb, db, args.model_b)

    print("\n=== Summary ===")
    print(f"  cross-model mean cosine: {np.mean(cross):.4f}")
    print(f"  retrieval gap A: {np.mean(gaps_a):+.4f}")
    print(f"  retrieval gap B: {np.mean(gaps_b):+.4f}")
    print(f"  gap delta (B − A): {np.mean(gaps_b) - np.mean(gaps_a):+.4f}")


if __name__ == "__main__":
    main()
