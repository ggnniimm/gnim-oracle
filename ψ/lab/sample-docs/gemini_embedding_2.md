# Gemini Embedding 2: Natively Multimodal Embedding Model

**อ้างอิงจาก:**
- [Google Blog: Gemini Embedding 2](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-embedding-2/)
- [Testing Catalog: Google launches new multimodal Gemini Embedding 2 model](https://www.testingcatalog.com/google-launches-new-multimodal-gemini-embedding-2-model/)

## 1. ข้อมูลทั่วไป
**Gemini Embedding 2** เป็นโมเดล Embedding ตัวแรกของ Google ที่เป็นแบบ **Natively Multimodal อย่างแท้จริง** ซึ่งสามารถแปลงข้อมูลหลายประเภทให้อยู่ในพื้นที่เวกเตอร์ (Vector Space) เดียวกันได้ ทำให้ง่ายต่อการนำไปประยุกต์ใช้ในระบบ AI ขั้นสูง

## 2. ความสามารถอันโดดเด่น
* **Text:** รองรับบริบทกว้างถึง 8,192 tokens สามารถจับความหมายข้ามภาษาได้กว่า 100 ภาษา
* **Images:** รองรับการซิงก์ภาพพร้อมกันได้สูงสุด 6 รูปต่อหนึ่งคำขอ (ฟอร์แมต PNG, JPEG)
* **Videos:** รองรับวิดีโอความยาวสูงสุด 120 วินาที (ฟอร์แมต MP4, MOV)
* **Audio:** ประมวลผลและทำ Embedding ไฟล์เสียงได้โดยตรง โดยไม่ต้องผ่านการถอดความ (transcription) เป็นข้อความก่อน
* **Documents:** อ่านและทำ Embedding หน้าเอกสาร PDF ได้โดยตรงสูงสุด 6 หน้า
* **Interleaved Input:** รองรับการใส่ข้อมูลหลายประเภทผสมกันใน 1 คำขอ (เช่น ภาพ + ข้อความ) เพื่อให้โมเดลเข้าใจความสัมพันธ์แบบลึกซึ้ง
* **Flexible Output Dimensions (MRL - Matryoshka Representation Learning):** สามารถเลือกขนาดมิติของเวกเตอร์ที่ส่งออกได้ (3072, 1536, หรือ 768 มิติ) เพื่อประหยัดพื้นที่ Database แต่ยังคงประสิทธิภาพที่ยอดเยี่ยม (ค่าเริ่มต้นคือ 3072)

## 3. การใช้งานแทนโมเดลเดิม
**สามารถใช้แทนโมเดลเดิมได้อย่างสมบูรณ์และได้ผลลัพธ์ที่ดีขึ้น** เนื่องจากโมเดลนี้สร้างมาตรฐานใหม่ด้านประสิทธิภาพ (State-of-the-Art) เอาชนะโมเดลชั้นนำรุ่นเก่าในตัวชี้วัดด้าน Text, Image และ Video

**วิธีการเริ่มต้นใช้งาน:**
1. **ผ่านบริการของ Google:** ใช้งานแบบ Public Preview ผ่านทาง **Gemini API** หรือ **Vertex AI**
2. **Frameworks Integration:** รองรับการทำงานในไลบรารียอดนิยมทันที เช่น LangChain, LlamaIndex, Haystack
3. **Vector Databases:** สามารถรันใช้งานร่วมกับ Vector Search Systems ได้เลย เช่น Qdrant, ChromaDB, Weaviate และ Google Cloud Vector Search

**ตัวอย่างการเขียนโค้ดเพื่อใช้งานผ่าน Gemini API (Python):**
```python
import google.generativeai as genai

# 1. ระบุคีย์
genai.configure(api_key="YOUR_API_KEY")

# 2. ปรับการตั้งค่ามาเรียกใช้ โมเดลตัวใหม่ 
# หมายเหตุ: ชื่อเรียกของ API ในปัจจุบันรอการระบุแน่ชัดใน Document (เช่น models/text-embedding-004 แต่เป็นเวอร์ชันใหม่)
result = genai.embed_content(
    model="models/text-embedding-004", # <- แก้ชื่อโมเดลตรงจุดนี้ให้เรียกใช้ Gemini Embedding 2
    content="ทดสอบการทำงานของ Embedding รุ่นใหม่",
    task_type="retrieval_document"
)

# 3. นำค่าเวกเตอร์ไปใช้ช้งาน หรือเอาไปเก็บเข้า Database
print(result['embedding'])
```
