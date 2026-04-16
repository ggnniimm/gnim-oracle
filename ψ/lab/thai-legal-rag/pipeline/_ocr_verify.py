"""One-off script: OCR-verify fuzzy-matched PDFs against MDs."""
import json, re, yaml, os, time, sys
from pathlib import Path
from difflib import SequenceMatcher

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.drive import stream_pdf
from google import genai
from google.genai import types
from dotenv import find_dotenv, dotenv_values

env = dotenv_values(find_dotenv())
client = genai.Client(api_key=env.get('GEMINI_API_KEY'))

_FM_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
_CTRL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

with open('/tmp/all_cgd_pdfs.json') as f:
    all_pdfs = json.load(f)
with open('/tmp/ac_pdfs.json') as f:
    ac_pdfs = json.load(f)
all_combined = all_pdfs + ac_pdfs
new_ids = {p['id'] for p in all_combined}
pdf_stems = {Path(p['name']).stem: p for p in all_combined}

md_dir = Path(__file__).parent.parent / 'data' / 'md_backup'

candidates = []
for md in sorted(md_dir.glob('*.md')):
    text = md.read_text('utf-8')
    m = _FM_RE.match(text)
    if not m:
        continue
    try:
        meta = yaml.safe_load(_CTRL_RE.sub('', m.group(1))) or {}
    except:
        continue
    fid = str(meta.get('file_id', '')).strip()
    if fid in new_ids:
        continue

    best_score = 0
    best_pdf = None
    for ps, p in pdf_stems.items():
        score = SequenceMatcher(None, md.stem, ps).ratio()
        if score > best_score:
            best_score = score
            best_pdf = p
    if best_score >= 0.75 and best_pdf:
        candidates.append({
            'md': md,
            'meta': meta,
            'pdf': best_pdf,
            'score': best_score,
        })

print(f'Total: {len(candidates)}')


def thai_to_arabic(s):
    return s.translate(str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789'))


SKIP = 13  # already done

match_yes = []
match_no = []
errors = []

for i, c in enumerate(candidates):
    if i < SKIP:
        continue
    md = c['md']
    meta = c['meta']
    pdf = c['pdf']
    score = c['score']

    md_ref = meta.get('doc_number') or meta.get('ref_number') or ''
    md_title = meta.get('title', '')

    try:
        pdf_bytes = stream_pdf(pdf['id'])
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[types.Content(parts=[
                types.Part.from_text(text='อ่านหน้าแรก ให้เฉพาะ: เลขที่หนังสือ, เรื่อง — 2 บรรทัด'),
                types.Part.from_bytes(data=pdf_bytes, mime_type='application/pdf'),
            ])]
        )
        pdf_ocr = response.text.strip()
    except Exception as e:
        errors.append((md.name, str(e)[:80]))
        print(f'[{i+1}/{len(candidates)}] ERROR {md.name}: {str(e)[:80]}')
        continue

    md_ref_n = thai_to_arabic(md_ref)
    pdf_ocr_n = thai_to_arabic(pdf_ocr)

    md_nums = re.findall(r'[0-9]+', md_ref_n)
    pdf_nums = re.findall(r'[0-9]+', pdf_ocr_n.split('\n')[0])

    is_match = False
    md_big = [n for n in md_nums if len(n) >= 3]
    pdf_big = [n for n in pdf_nums if len(n) >= 3]
    if md_big and pdf_big:
        if md_big[-1] == pdf_big[-1]:
            is_match = True

    if not is_match and md_title and len(pdf_ocr.split('\n')) > 1:
        pdf_title = pdf_ocr.split('\n')[-1]
        title_sim = SequenceMatcher(
            None,
            thai_to_arabic(md_title[:60]),
            thai_to_arabic(pdf_title[:60]),
        ).ratio()
        if title_sim > 0.7:
            is_match = True

    status = 'MATCH' if is_match else 'MISMATCH'
    if is_match:
        match_yes.append(c)
    else:
        match_no.append(c)

    print(f'[{i+1}/{len(candidates)}] {status} [{int(score*100)}%] {md.name}')
    print(f'  MD:  {md_ref} | {md_title[:60]}')
    print(f'  PDF: {pdf_ocr[:150]}')
    print()
    time.sleep(2)

print(f'\n=== SUMMARY ===')
print(f'MATCH:    {len(match_yes)}')
print(f'MISMATCH: {len(match_no)}')
print(f'ERROR:    {len(errors)}')

if match_no:
    print(f'\n=== MISMATCH list ===')
    for c in match_no:
        print(f'  {c["md"].name} -> {c["pdf"]["name"]}')
