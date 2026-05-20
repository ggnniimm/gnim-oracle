---
name: prod-ssh-nohup-log-pattern
description: Run prod commands via SSH with nohup + server-side log file — never pipe docker exec output directly through SSH
metadata:
  type: feedback
---

เมื่อรัน command นาน ๆ บน prod ผ่าน SSH ให้แยก execution ออกจาก observation เสมอ

**Pattern ที่ถูก:**
```bash
ssh prod 'nohup docker exec app python3 -u script.py > /tmp/out.log 2>&1 &'
ssh prod 'tail -f /tmp/out.log'
```

**Pattern ที่ผิด (อย่าทำ):**
```bash
ssh prod 'docker exec app python3 script.py 2>&1 | tail -5'
```

**Why:** SSH buffers output ทั้งหมดจนกว่า session จะ close (clean) พอ connection drop แบบกะทันหัน output ที่ buffer ไว้หายหมด แต่ `docker exec` ยังทำงานต่อใน container (ไม่ตามตาม SSH) → ไม่รู้ว่างานเสร็จหรือยัง

**How to apply:** ทุก prod command ที่ใช้เวลา >30 วินาที ผ่าน SSH ให้ใช้ nohup + /tmp/out.log ก่อน แล้วค่อย tail แยก session ยืนยันผลด้วย dedup.db หรือ chunk count แทนการรัน index ซ้ำ
