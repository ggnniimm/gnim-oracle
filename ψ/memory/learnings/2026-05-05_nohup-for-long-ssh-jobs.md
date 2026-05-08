---
name: nohup บน server เสมอสำหรับ long-running jobs บน SSH
description: docker exec ถูก kill ทันทีที่ SSH session ขาด — ต้อง nohup + redirect output ไฟล์บน server
type: project
date: 2026-05-05
---

## Pattern

เมื่อรัน job บน remote server ผ่าน SSH ที่ใช้เวลานาน (>5 นาที) ต้องใช้ `nohup` เสมอ

## ตัวอย่างจริง (2026-05-05)

- รัน `ssh root@X 'docker exec ... python3 run_eval.py'` แบบ foreground
- eval ดำเนินไปถึง TC-032 (~1 ชั่วโมง) แล้ว SSH session ขาด
- `docker exec` ถูก kill ทันที — ต้องเริ่ม eval ใหม่ทั้งหมด

## วิธีที่ถูกต้อง

```bash
# รันแบบ detached — SSH ขาดก็ไม่หยุด
ssh root@SERVER 'nohup docker exec CONTAINER python3 -u /app/script.py > /tmp/out.txt 2>&1 & echo "PID: $!"'

# Monitor จาก Mac
ssh root@SERVER 'tail -f /tmp/out.txt' | grep --line-buffered -E "pattern"
```

## กฎ

- Job ใช้เวลา **>5 นาที** → `nohup` บน server เสมอ
- Output → redirect ไปไฟล์บน server ไม่ใช่ pipe กลับมา Mac
- Monitor แยก: `tail -f` ผ่าน SSH อีก session
