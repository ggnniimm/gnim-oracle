import sys; sys.path.insert(0, '.')
from src.ingestion.law_extractor import _trim_trailing_structure

cases = [
    ('ข้อ 28', 'ข้อ ๒๘ การซื้อหรือจ้าง  กระทำได้  ๓  วิธี  ดังนี้ \n(๑) วิธีประกาศเชิญชวนทั่วไป \n(๒) วิธีคัดเลือก \n(๓) วิธีเฉพาะเจาะจง \nวิธีประกาศเชิญชวนทั่วไป', True),
    ('ข้อ 73', 'ข้อ ๗๓ ให้นำความในข้อ  ๖๐  มาใช้บังคับ  โดยอนุโลม   \nวิธีคัดเลือก', True),
    ('ข้อ 77', 'ข้อ ๗๗ ให้นำความในข้อ  ๔๒  มาใช้บังคับ  โดยอนุโลม \nวิธีเฉพาะเจาะจง', True),
    ('มาตรา 13 regression (no trim)', 'มาตรา ๑๓\nในการจัดซื้อ ผู้ที่มีหน้าที่ไม่เป็นผู้มีส่วนได้เสีย\n\nในกรณีที่ปรากฏว่า\nให้คณะกรรมการวินิจฉัย\nมีอำนาจสั่งยกเลิก', False),
    ('ข้อ 24 (trim ด้วย ได้)', 'ข้อ ๒๔ เมื่อหัวหน้าหน่วยงานของรัฐให้ความเห็นชอบ\nหรือข้อ ๒๓ แล้ว ให้เจ้าหน้าที่ดำเนินการต่อไปได้ \nคณะกรรมการซื้อหรือจ้าง', True),
]

all_pass = True
for label, text, expect_trim in cases:
    trimmed = _trim_trailing_structure(text)
    changed = (trimmed != text)
    ok = (changed == expect_trim)
    status = 'PASS' if ok else 'FAIL'
    if not ok:
        all_pass = False
    print(f'{status}  {label}: trim={changed} (expected {expect_trim}) | last 50: {repr(trimmed[-50:])}')

print()
print('All pass:', all_pass)
