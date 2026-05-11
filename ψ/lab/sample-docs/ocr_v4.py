#!/usr/bin/env python3
"""
OCR V4 Expert — Thai Legal Document OCR
ตาม GCP_GEMINI_OCR_GUIDE_V4: Image-Based, 300 DPI, Expert Prompt, Auto-Naming

Usage:
    python ocr_v4.py <pdf_path>
    python ocr_v4.py  (ใช้ PDF default)
"""

import os
import sys
import time
import json
import re
import fitz  # pymupdf
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from google import genai
from google.genai import types

def log(msg: str, log_path: Path = None):
    print(msg, flush=True)
    if log_path:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

# ─── Config ───────────────────────────────────────────────────────────────────
KEY_FILE  = "/Users/mingsaksaengwilaipon/Downloads/gen-lang-client-0136329629-2930cac103d9.json"
PROJECT_ID = "gen-lang-client-0136329629"
LOCATION   = "us-central1"
MODEL_NAME = "gemini-2.5-pro"
DPI        = 300   # guide กำหนด 300 DPI ขั้นต่ำ
PAGE_SLEEP   = 10    # วินาทีรอระหว่างหน้า
MAX_RETRY    = 5
API_TIMEOUT  = 300   # วินาที — thread-level timeout ต่อ page

DEFAULT_PDF = "/Users/mingsaksaengwilaipon/allinone-oracle/ψ/lab/01012-652191-1f-690224-0000832356.pdf"

_THAI_DIGITS = "๐๑๒๓๔๕๖๗๘๙"

def to_thai(n: int) -> str:
    return "".join(_THAI_DIGITS[int(d)] for d in str(n))


def ocr_prompt(page_num: int, total_pages: int) -> str:
    thai_page  = to_thai(page_num)
    thai_total = to_thai(total_pages)
    return f"""\
คุณคือหุ่นยนต์ OCR ระดับสูง ถอดข้อความจากภาพนี้แบบ 100% Verbatim

══ ข้อมูลหน้านี้ ══
นี่คือหน้าที่ {page_num} ({thai_page}) จากทั้งหมด {total_pages} ({thai_total}) หน้า
เลขหน้าที่ควรปรากฏบนกระดาษ: '{thai_page}' (เลขไทย)
ใช้เป็น anchor ตรวจสอบ — ถ้าอ่านได้ไม่ตรงให้วิเคราะห์รูปทรงซ้ำ

══ กฎเหล็ก ══
1. **เลขหน้า (Header):** ต้องเป็นเลขไทย (๐-๙) เท่านั้น ห้ามใช้เลขอารบิก
2. **ห้าม OCR ตราประทับ:** ตรายางศาล/เครื่องหมายธุรการ → ข้ามไป (Ignore)
3. **รักษาเลขไทยในเนื้อหา:** ถอดตามรูปทรงที่เห็น ห้ามอ่านสลับ
4. **ห้ามสรุป/ห้ามแก้:** ถอดคำต่อคำ แม้ต้นฉบับผิด ห้ามมีคำเกริ่นนำ

══ Visual Guide — คู่ที่สับสนบ่อย ══
- '๒' (สอง)  : ส่วนบนโค้ง ล่างเป็นฐาน  ≠ '๖' (หก)
- '๔' (สี่)  : มีเส้นตั้งขวา มีช่อง      ≠ '๘' (แปด) ≠ '๙' (เก้า)
- '๕' (ห้า)  : หัวม้วนกลมด้านบน          ≠ '๔' (สี่)
- '๖' (หก)   : หัวกลมล่าง หางตวัดสั้น   ≠ '๒' (สอง)
- '๘' (แปด)  : สองวงซ้อนกัน              ≠ '๔' (สี่)
- '๙' (เก้า) : หางสะบัดหยักขึ้นสูง       ≠ '๔' (สี่)\
"""

# ─── Auto-Naming Prompt ────────────────────────────────────────────────────────
NAMING_PROMPT = """\
วิเคราะห์เนื้อหาด้านล่างและตั้งชื่อไฟล์ตาม Pattern: [Court]_[DocType]_[Initial]_[Num]_[Year]

กฎ:
- Court  : ชื่อย่อศาล lowercase
    sac = ศาลปกครองสูงสุด (Supreme Administrative Court)
    ac  = ศาลปกครองชั้นต้น
    sc  = ศาลฎีกา
    cc  = ศาลชั้นต้น (Civil Court)
    cac = ศาลอุทธรณ์คดีชำนัญพิเศษ
- DocType: judgment | order | appeal | ruling
- Initial: อักษรย่อคดีแดง lowercase ไม่มีจุด
    อ → o  (ศาลปกครอง/อาญา — พบบ่อยสุด ถ้าศาลเป็น sac ให้ใช้ o เป็น default)
    บ → b  (ศาลปกครองภาค/ชั้นต้น)
    ก → k  (กร.)
    ฟ → f  (ฟ้อง)
    จ → c  (จ. = civil ศาลแพ่ง — ถ้าศาลเป็น sac ให้ตรวจซ้ำว่าอาจเป็น อ→o)
- Num    : เลขคดีแดง (อารบิก ไม่มีศูนย์นำหน้า)
- Year   : ปี พ.ศ. ของคดีแดง (อารบิก 4 หลัก)

ตอบด้วย JSON บรรทัดเดียว ไม่มีคำอธิบายเพิ่มเติม:
{"filename": "court_doctype_initial_num_year"}

เนื้อหา (3 หน้าแรก):
"""


def call_with_retry(client, contents: list, label: str) -> str:
    for attempt in range(MAX_RETRY):
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(client.models.generate_content, model=MODEL_NAME, contents=contents)
                try:
                    resp = future.result(timeout=API_TIMEOUT)
                except FutureTimeoutError:
                    raise RuntimeError(f"Gemini ไม่ตอบใน {API_TIMEOUT}s")
            return resp.text
        except Exception as e:
            err = str(e)
            if "429" in err:
                wait = (attempt + 1) * 20
                print(f"   ⏳ Rate limited (429). Waiting {wait}s... (Attempt {attempt+1}/{MAX_RETRY})", flush=True)
                time.sleep(wait)
            elif "ไม่ตอบ" in err and attempt < MAX_RETRY - 1:
                print(f"   ⏳ Timeout หน้า {label} retry {attempt+1}/{MAX_RETRY}...", flush=True)
                time.sleep(10)
            else:
                print(f"   ❌ Error [{label}]: {err}", flush=True)
                raise
    raise RuntimeError(f"เกิน {MAX_RETRY} ครั้งสำหรับ {label}")


def auto_name(client, full_text: str) -> str | None:
    # ส่งแค่ 3 หน้าแรกเพื่อประหยัด token
    preview = full_text[:6000]
    prompt  = NAMING_PROMPT + preview
    try:
        raw = call_with_retry(client, [prompt], "auto-naming")
        # แยก JSON จาก response (อาจมี markdown code fence)
        match = re.search(r'\{.*?"filename".*?\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            name = data.get("filename", "").strip().lower()
            # ตรวจ pattern คร่าวๆ
            if re.match(r'^[a-z]+_[a-z]+_[a-z]+_\d+_\d{4}$', name):
                return name
        print(f"   ⚠️  Auto-naming ได้ผลลัพธ์ที่ parse ไม่ได้: {raw[:200]}")
    except Exception as e:
        print(f"   ⚠️  Auto-naming ล้มเหลว: {e}")
    return None


def rename_files(pdf_path: Path, md_path: Path, new_stem: str) -> tuple[Path, Path]:
    new_pdf = pdf_path.parent / f"{new_stem}.pdf"
    new_md  = md_path.parent  / f"{new_stem}_ocr_v4.md"

    if new_pdf != pdf_path:
        pdf_path.rename(new_pdf)
        print(f"   PDF → {new_pdf.name}")
    if new_md != md_path:
        md_path.rename(new_md)
        print(f"   MD  → {new_md.name}")

    return new_pdf, new_md


def main():
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_PDF)
    if not pdf_path.exists():
        sys.exit(f"❌ ไม่พบไฟล์: {pdf_path}")

    # output ชั่วคราวก่อน auto-naming
    out_path = pdf_path.parent / f"{pdf_path.stem}_ocr_v4.md"
    log_path = pdf_path.parent / "ocr_stdout.log"
    log_path.write_text("", encoding="utf-8")  # reset log

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEY_FILE
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

    doc         = fitz.open(str(pdf_path))
    total_pages = len(doc)
    log(f"📄 {pdf_path.name}", log_path)
    log(f"   หน้า: {total_pages} | DPI: {DPI} | Model: {MODEL_NAME}", log_path)
    log(f"   Log: tail -f {log_path}", log_path)
    log("", log_path)

    full_text = ""

    for page_num in range(total_pages):
        log(f"📦 Processing Page {page_num + 1}/{total_pages}...", log_path)

        page = doc[page_num]
        mat  = fitz.Matrix(DPI / 72, DPI / 72)
        pix  = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img  = pix.tobytes("png")

        log(f"   → {pix.width}×{pix.height}px | {len(img) // 1024} KB", log_path)

        text = call_with_retry(
            client,
            [types.Part.from_bytes(data=img, mime_type="image/png"), ocr_prompt(page_num + 1, total_pages)],
            f"page-{page_num + 1}",
        )

        full_text += f"\n\n---\n<!-- Page {page_num + 1} -->\n\n{text}"
        log(f"   ✅ Done — {len(text):,} chars", log_path)

        # บันทึกระหว่างทางเผื่อขัดข้อง
        out_path.write_text(full_text.strip(), encoding="utf-8")

        if page_num < total_pages - 1:
            time.sleep(PAGE_SLEEP)

    doc.close()

    log(f"\n📝 OCR เสร็จ — {len(full_text):,} ตัวอักษร", log_path)
    log(f"   บันทึกไว้ที่: {out_path.name}", log_path)

    # ─── Auto-Naming ──────────────────────────────────────────────────────────
    log("\n🏷️  กำลัง auto-naming...", log_path)
    new_stem = auto_name(client, full_text)

    if new_stem:
        log(f"   ชื่อใหม่: {new_stem}", log_path)
        new_pdf, new_md = rename_files(pdf_path, out_path, new_stem)
        log(f"\n🎉 เสร็จสมบูรณ์!", log_path)
        log(f"   PDF: {new_pdf}", log_path)
        log(f"   MD : {new_md}", log_path)
    else:
        log(f"   ไม่สามารถตั้งชื่ออัตโนมัติได้ — ไฟล์อยู่ที่: {out_path}", log_path)

    log(f"\n✅ Done. รวม {total_pages} หน้า | {len(full_text):,} ตัวอักษร", log_path)


if __name__ == "__main__":
    main()
