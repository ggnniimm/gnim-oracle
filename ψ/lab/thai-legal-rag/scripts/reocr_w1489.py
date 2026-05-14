"""One-off: re-OCR ว1489 after raw-cache placeholder cleanup (2026-05-14)."""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent.parent / ".env")

from src.ingestion.drive import stream_pdf
from src.ingestion.ocr import pdf_to_markdown

FILE_ID = "15tJfkf_k7KvYi5J1dJBO4jgS0tBwZAq0"
FILENAME = "03_กวจ_ว1489_301165_สถานะของบริษัท_ธนาคารกรุงไทย_จำกัด_(มหาชน)ฯ.pdf"

t0 = time.time()
print(f"[{time.strftime('%H:%M:%S')}] streaming PDF from Drive...", flush=True)
pdf_bytes = stream_pdf(FILE_ID)
print(f"[{time.strftime('%H:%M:%S')}] got {len(pdf_bytes):,} bytes, starting OCR...", flush=True)

result = pdf_to_markdown(
    pdf_bytes,
    file_id=FILE_ID,
    filename=FILENAME,
    force=True,
    per_page=True,
    page_delay=5.0,
)

print(f"[{time.strftime('%H:%M:%S')}] done in {time.time()-t0:.1f}s")
print(f"  doc_type: {result.get('doc_type')}")
print(f"  chars:    {len(result.get('text',''))}")
import re
m = re.search(r'quality:\s*"([^"]+)"', result.get('text',''))
print(f"  quality:  {m.group(1) if m else '?'}")
