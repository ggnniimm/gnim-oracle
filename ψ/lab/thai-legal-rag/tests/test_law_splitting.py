"""
Tests for วรรค (paragraph) splitting in law_extractor.

Covers:
- _post_merge_paragraphs() — list-context merging, continuation word merging
- _split_paragraphs() — blank-line fallback path (Gemini mocked to None)
- _split_list_para() — list detection and tail splitting
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.law_extractor import (
    _post_merge_paragraphs,
    _split_list_para,
    _split_paragraphs,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

# Simple multi-วรรค: two independent paragraphs
SIMPLE_TWO_VARAK = "ข้อ ๕๕\nวรรคแรกของมาตรานี้กำหนดหลักเกณฑ์ทั่วไป\n\nรัฐมนตรีมีอำนาจออกกฎกระทรวง"

# Section with (๑)(๒)(๓) sub-items → should merge into parent วรรค
SECTION_WITH_SUBITEMS = (
    "ข้อ ๑๐\n"
    "ให้หน่วยงานของรัฐจัดทำแผนตามหลักเกณฑ์ดังต่อไปนี้\n"
    "(๑) กำหนดความต้องการ\n"
    "(๒) กำหนดราคากลาง\n"
    "(๓) กำหนดระยะเวลา"
)

# ข้อ 55-style: parent + (๑)-(๔) with internal continuation content → 1 วรรค
KHO_55_STYLE = (
    "ข้อ ๕๕\n"
    "การจัดซื้อจัดจ้างโดยวิธีคัดเลือก ให้กระทำได้ในกรณีดังต่อไปนี้\n"
    "(๑) ใช้วิธีประกาศเชิญชวนทั่วไปแล้วไม่มีผู้ยื่นข้อเสนอ\n"
    "หรือมีผู้ยื่นข้อเสนอน้อยกว่าสามราย\n"
    "(๒) ซื้อจ้างที่มีคุณลักษณะเฉพาะ\n"
    "โดยผู้ประกอบการที่มีคุณสมบัติตรงตามที่กำหนด\n"
    "(๓) เป็นพัสดุที่ต้องการจำนวนจำกัด\n"
    "(๔) กรณีอื่นตามที่กำหนดในกฎกระทรวง"
)

# ข้อ 55-style split across blank lines (issue #1 scenario)
KHO_55_BLANK_LINES = (
    "ข้อ ๕๕\n"
    "การจัดซื้อจัดจ้างโดยวิธีคัดเลือก ให้กระทำได้ในกรณีดังต่อไปนี้\n\n"
    "(๑) ใช้วิธีประกาศเชิญชวนทั่วไปแล้วไม่มีผู้ยื่นข้อเสนอ\n"
    "หรือมีผู้ยื่นข้อเสนอน้อยกว่าสามราย\n\n"
    "(๒) ซื้อจ้างที่มีคุณลักษณะเฉพาะ\n\n"
    "(๓) เป็นพัสดุที่ต้องการจำนวนจำกัด\n\n"
    "(๔) กรณีอื่นตามที่กำหนดในกฎกระทรวง"
)

# Orphan continuation words → should merge back
ORPHAN_CONTINUATION = (
    "ข้อ ๒๐\n"
    "ให้หน่วยงานของรัฐดำเนินการตามแผน\n\n"
    "แต่ในกรณีจำเป็นเร่งด่วนอาจดำเนินการโดยวิธีอื่นได้"
)

# Sub-items with (ก)(ข)(ค) Thai letter markers
SECTION_WITH_LETTER_SUBITEMS = (
    "ข้อ ๓๐\n"
    "ให้คณะกรรมการพิจารณาจากหลักเกณฑ์\n"
    "(ก) ราคา\n"
    "(ข) คุณภาพ\n"
    "(ค) ระยะเวลา"
)

# List items followed by definite new วรรค (tail split)
LIST_THEN_NEW_VARAK = (
    "ข้อ ๔๐\n"
    "ให้ดำเนินการดังต่อไปนี้\n"
    "(๑) จัดทำรายงาน\n"
    "(๒) เสนอต่อหัวหน้าหน่วยงาน\n\n"
    "รัฐมนตรีมีอำนาจกำหนดหลักเกณฑ์เพิ่มเติม"
)

# Mixed: list items with continuation text between them (no blank lines)
LIST_WITH_INLINE_CONTINUATION = (
    "ข้อ ๖๐\n"
    "กรณีดังต่อไปนี้\n"
    "(๑) กรณีแรก\n"
    "โดยต้องดำเนินการตามระเบียบ\n"
    "(๒) กรณีที่สอง\n"
    "ซึ่งมีเงื่อนไขเพิ่มเติม"
)


# ── _post_merge_paragraphs tests ────────────────────────────────────────────

class TestPostMergeParagraphs:
    def test_single_paragraph_passthrough(self):
        """Single paragraph should pass through unchanged."""
        result = _post_merge_paragraphs(["เนื้อหาวรรคเดียว"])
        assert result == ["เนื้อหาวรรคเดียว"]

    def test_empty_list(self):
        assert _post_merge_paragraphs([]) == []

    def test_list_items_merge_into_parent(self):
        """(๑)(๒)(๓) sub-items merge into preceding paragraph."""
        paras = [
            "ให้หน่วยงานดำเนินการดังต่อไปนี้",
            "(๑) กำหนดความต้องการ",
            "(๒) กำหนดราคากลาง",
            "(๓) กำหนดระยะเวลา",
        ]
        result = _post_merge_paragraphs(paras)
        assert len(result) == 1
        assert "(๑)" in result[0]
        assert "(๓)" in result[0]

    def test_letter_markers_merge(self):
        """(ก)(ข)(ค) markers merge into parent."""
        paras = [
            "พิจารณาจากหลักเกณฑ์",
            "(ก) ราคา",
            "(ข) คุณภาพ",
        ]
        result = _post_merge_paragraphs(paras)
        assert len(result) == 1

    def test_continuation_words_merge(self):
        """Continuation words (แต่, และ, etc.) merge back."""
        paras = [
            "ให้หน่วยงานของรัฐดำเนินการตามแผน",
            "แต่ในกรณีจำเป็นเร่งด่วนอาจดำเนินการโดยวิธีอื่นได้",
        ]
        result = _post_merge_paragraphs(paras)
        assert len(result) == 1

    def test_definite_subject_stays_separate(self):
        """Definite new วรรค starters (รัฐมนตรี, etc.) remain separate."""
        paras = [
            "ให้ดำเนินการตามหลักเกณฑ์",
            "รัฐมนตรีมีอำนาจกำหนดหลักเกณฑ์เพิ่มเติม",
        ]
        result = _post_merge_paragraphs(paras)
        assert len(result) == 2

    def test_list_context_merges_continuation_after_list_item(self):
        """After a list marker, continuation text merges (list-context mode).

        This is the ข้อ 55 fix: (๑) + continuation + (๒) + continuation = 1 วรรค.
        """
        paras = [
            "การจัดซื้อจัดจ้างโดยวิธีคัดเลือก",
            "(๑) ใช้วิธีประกาศเชิญชวนทั่วไป",
            "หรือมีผู้ยื่นข้อเสนอน้อยกว่าสามราย",
            "(๒) ซื้อจ้างที่มีคุณลักษณะเฉพาะ",
            "โดยผู้ประกอบการที่มีคุณสมบัติตรงตามที่กำหนด",
            "(๓) เป็นพัสดุที่ต้องการจำนวนจำกัด",
        ]
        result = _post_merge_paragraphs(paras)
        assert len(result) == 1

    def test_list_context_exits_on_definite_subject(self):
        """List-context merging stops at definite new วรรค starters."""
        paras = [
            "ให้ดำเนินการดังต่อไปนี้",
            "(๑) จัดทำรายงาน",
            "(๒) เสนอต่อหัวหน้าหน่วยงาน",
            "รัฐมนตรีมีอำนาจกำหนดหลักเกณฑ์เพิ่มเติม",
        ]
        result = _post_merge_paragraphs(paras)
        assert len(result) == 2
        assert "(๑)" in result[0]
        assert "รัฐมนตรี" in result[1]

    def test_embedded_list_markers_enter_list_context(self):
        """Gemini-merged paragraph with embedded (๑)(๒) enters list context.

        Issue #3: ระเบียบ ข้อ 55 — Gemini merges (๑)(๒) into parent but splits
        continuation text ("ทั้งนี้", "ในกระบวนการ", "ในกรณี") as separate วรรค.
        Post-merge should detect embedded markers and merge them back.
        """
        paras = [
            "เมื่อสิ้นสุดการเสนอราคา ให้คณะกรรมการดําเนินการดังนี้\n(๑) จัดพิมพ์ใบเสนอราคา\n(๒) ตรวจสอบการมีผลประโยชน์ร่วมกัน",
            "ทั้งนี้ การซื้อหรือจ้างที่มีการกําหนดคุณลักษณะเฉพาะ",
            "ในกระบวนการพิจารณา คณะกรรมการอาจสอบถามข้อเท็จจริง",
            "ในกรณีที่ผู้ยื่นข้อเสนอรายใดมีคุณสมบัติไม่ครบถ้วน",
            "ในกรณีที่ผู้ยื่นข้อเสนอรายที่คัดเลือกไว้ไม่ยอมเข้าทําสัญญา",
        ]
        result = _post_merge_paragraphs(paras)
        assert len(result) == 1
        assert "ทั้งนี้" in result[0]
        assert "ในกระบวนการ" in result[0]
        assert "ในกรณี" in result[0]

    def test_embedded_markers_still_exit_on_definite_subject(self):
        """Embedded list context exits on definite subject (รัฐมนตรี etc.)."""
        paras = [
            "ให้ดําเนินการดังนี้\n(๑) จัดทำรายงาน\n(๒) เสนอผู้บังคับบัญชา",
            "ในกรณีที่มีปัญหา ให้แจ้งต่อคณะกรรมการ",
            "รัฐมนตรีมีอำนาจออกกฎกระทรวงเพิ่มเติม",
        ]
        result = _post_merge_paragraphs(paras)
        assert len(result) == 2
        assert "ในกรณี" in result[0]
        assert "รัฐมนตรี" in result[1]

    def test_kho215_look_ahead_two_varak(self):
        """ข้อ 215: list with sub-items → 2 วรรค (list block + closing provision).

        Look-ahead detects that วรรค 2 is between list items (วรรค 3 has markers),
        but วรรค 4 has no markers ahead and doesn't match continuation → new วรรค.
        """
        paras = [
            "ให้เจ้าหน้าที่เสนอรายงาน ดังต่อไปนี้\n(๑) ขาย ให้ดําเนินการ\n(ก) การขายพัสดุ\n(ข) การขายให้แก่หน่วยงาน\n(ค) การขายอุปกรณ์",
            "การขายโดยวิธีทอดตลาดให้ถือปฏิบัติตามประมวลกฎหมายแพ่งและพาณิชย์",
            "หน่วยงานของรัฐจะจ้างผู้ประกอบการ\n(๒) แลกเปลี่ยน\n(๓) โอน\n(๔) แปรสภาพหรือทําลาย",
            "การดําเนินการตามวรรคหนึ่ง โดยปกติให้แล้วเสร็จภายใน ๖๐ วัน",
        ]
        result = _post_merge_paragraphs(paras)
        assert len(result) == 2
        assert "(๑)" in result[0]
        assert "(๔)" in result[0]
        assert "การขายโดยวิธีทอดตลาด" in result[0]
        assert "การดําเนินการตามวรรคหนึ่ง" in result[1]


    def test_definition_list_merges_into_one(self):
        """Issue #4: "คำ" หมายความว่า items merge into parent (บทนิยาม section)."""
        paras = [
            "ในพระราชบัญญัตินี้",
            '"การจัดซื้อจัดจ้าง" หมายความว่า การดําเนินการเพื่อให้ได้มาซึ่งพัสดุ',
            '"พัสดุ" หมายความว่า สินค้า งานบริการ งานก่อสร้าง',
            '"สินค้า" หมายความว่า วัสดุ ครุภัณฑ์ ที่ดิน สิ่งปลูกสร้าง',
            '"รัฐมนตรี" หมายความว่า รัฐมนตรีผู้รักษาการตามพระราชบัญญัตินี้',
        ]
        result = _post_merge_paragraphs(paras)
        assert len(result) == 1
        assert "การจัดซื้อจัดจ้าง" in result[0]
        assert "รัฐมนตรี" in result[0]

    def test_definition_list_starting_directly(self):
        """Definition item as first non-intro paragraph enters list context immediately."""
        paras = [
            '"หัวหน้าหน่วยงานของรัฐ" หมายความว่า ผู้ดํารงตําแหน่งในหน่วยงานของรัฐ\n(๑) ราชการส่วนกลาง\n(๒) ราชการส่วนภูมิภาค',
            '"หัวหน้าเจ้าหน้าที่" หมายความว่า ผู้ดํารงตําแหน่งหัวหน้าสายงาน',
            '"ผู้มีผลประโยชน์ร่วมกัน" หมายความว่า บุคคลธรรมดาหรือนิติบุคคล',
        ]
        result = _post_merge_paragraphs(paras)
        assert len(result) == 1
        assert "หัวหน้าเจ้าหน้าที่" in result[0]
        assert "ผู้มีผลประโยชน์ร่วมกัน" in result[0]

    def test_definition_list_look_ahead_merges_between_items(self):
        """Definition items with continuation text between them all merge."""
        paras = [
            "ในระเบียบนี้",
            '"ผู้มีผลประโยชน์ร่วมกัน" หมายความว่า บุคคลที่เข้าเสนอราคา',
            "การมีส่วนได้เสียดังกล่าวข้างต้น ได้แก่ ความสัมพันธ์ดังต่อไปนี้",
            '"การขัดขวางการแข่งขัน" หมายความว่า การกระทําอย่างใด',
        ]
        result = _post_merge_paragraphs(paras)
        assert len(result) == 1
        assert "ผู้มีผลประโยชน์ร่วมกัน" in result[0]
        assert "การขัดขวางการแข่งขัน" in result[0]

    def test_phuea_starts_new_varak(self):
        """Issue #5: 'เพื่อ' at paragraph start is a new วรรค, not a continuation.

        มาตรา 6 should have 4 วรรค. Previously, Pass 2 merged วรรค 2 into วรรค 1
        because _CONTINUATION_RE matched 'เพื่อ'.
        """
        paras = [
            "เพื่อให้การปฏิบัติงานของรัฐวิสาหกิจเป็นไปตามมาตรฐาน",
            "เพื่อให้การดำเนินงานของรัฐวิสาหกิจเป็นประโยชน์สูงสุด",
            "ระเบียบ ข้อบังคับ หลักเกณฑ์ตามวรรคสอง ให้ตราเป็นพระราชกฤษฎีกา",
            "ระเบียบ ข้อบังคับ หลักเกณฑ์ตามวรรคสองและวรรคสาม ให้นำมาใช้บังคับ",
        ]
        result = _post_merge_paragraphs(paras)
        assert len(result) == 4
        assert result[0].startswith("เพื่อให้การปฏิบัติ")
        assert result[1].startswith("เพื่อให้การดำเนินงาน")

    def test_cross_reference_not_list_context(self):
        """Issue #6: inline cross-references 'ตาม (๑) (๒)' must NOT trigger list context.

        มาตรา 7 should produce 5 วรรค. Previously all 5 merged into 1 because
        วรรค 2 contains 'ตาม (๑) (๒) และ (๓)' — _EMBEDDED_LIST_RE matched these
        inline markers, keeping list context alive and merging วรรค 3-5.
        """
        paras = [
            # วรรค 1: list items inline (Gemini-merged) — no newlines before markers
            "พระราชบัญญัตินี้มิให้ใช้บังคับแก่ (๑) รัฐวิสาหกิจ (๒) กองทุน (๓) องค์การมหาชน (๖) กิจการอื่น",
            # วรรค 2: references (๑)(๒)(๓) inline — NOT list items
            "การจัดซื้อจัดจ้างตาม (๑) (๒) และ (๓) ที่ได้รับยกเว้น ให้หน่วยงานของรัฐปฏิบัติตามหลักเกณฑ์",
            # วรรค 3-5: independent legal sentences
            "การยกเว้นมิให้นำบทบัญญัติแห่งพระราชบัญญัตินี้มาใช้บังคับ ให้ตราเป็นพระราชกฤษฎีกา",
            "กรณีตามวรรคหนึ่งและวรรคสาม ให้หน่วยงานของรัฐจัดทำรายงานสรุปผล",
            "การจัดซื้อจัดจ้างตาม (๖) นอกจากจะต้องปฏิบัติตามกฎหมาย",
        ]
        result = _post_merge_paragraphs(paras)
        assert len(result) == 5
        assert "มิให้ใช้บังคับ" in result[0]
        assert "ตาม (๑) (๒)" in result[1]
        assert "การยกเว้น" in result[2]
        assert "กรณีตามวรรคหนึ่ง" in result[3]
        assert "ตาม (๖)" in result[4]


# ── _split_list_para tests ──────────────────────────────────────────────────

class TestSplitListPara:
    def test_pure_list_items(self):
        """List-only paragraph merges entirely into prev."""
        para = "(๑) กำหนดความต้องการ\n(๒) กำหนดราคากลาง"
        merged, tail = _split_list_para(para, "ให้ดำเนินการ")
        assert "ให้ดำเนินการ" in merged
        assert "(๑)" in merged
        assert "(๒)" in merged
        assert tail is None

    def test_list_then_definite_subject_tail(self):
        """List paragraph with trailing definite subject → splits tail."""
        para = "(๑) จัดทำรายงาน\n(๒) เสนอต่อผู้บังคับบัญชา\nรัฐมนตรีมีอำนาจออกกฎ"
        merged, tail = _split_list_para(para, "ให้ดำเนินการ")
        assert "(๑)" in merged
        assert "(๒)" in merged
        assert tail is not None
        assert "รัฐมนตรี" in tail

    def test_continuation_stays_in_list(self):
        """Non-marker, non-subject continuation stays in list part."""
        para = "(๑) กำหนดความต้องการ\nโดยใช้ข้อมูลย้อนหลัง\n(๒) กำหนดราคา"
        merged, tail = _split_list_para(para, "ดังต่อไปนี้")
        assert "โดยใช้ข้อมูลย้อนหลัง" in merged
        assert tail is None


# ── _split_paragraphs tests (blank-line fallback) ──────────────────────────

class TestSplitParagraphs:
    """Tests for _split_paragraphs with Gemini mocked to return None."""

    @patch("src.ingestion.law_extractor._split_paragraphs_gemini", return_value=None)
    def test_simple_two_varak(self, _mock):
        result = _split_paragraphs(SIMPLE_TWO_VARAK)
        assert len(result) == 2
        assert "วรรคแรก" in result[0]
        assert "รัฐมนตรี" in result[1]

    @patch("src.ingestion.law_extractor._split_paragraphs_gemini", return_value=None)
    def test_subitems_merge_into_one(self, _mock):
        """(๑)(๒)(๓) sub-items → single วรรค."""
        result = _split_paragraphs(SECTION_WITH_SUBITEMS)
        assert len(result) == 1
        assert "(๑)" in result[0]
        assert "(๓)" in result[0]

    @patch("src.ingestion.law_extractor._split_paragraphs_gemini", return_value=None)
    def test_kho55_style_one_varak(self, _mock):
        """ข้อ 55-style with continuation text between items → 1 วรรค."""
        result = _split_paragraphs(KHO_55_STYLE)
        assert len(result) == 1
        assert "(๑)" in result[0]
        assert "(๔)" in result[0]
        assert "หรือมีผู้ยื่นข้อเสนอ" in result[0]

    @patch("src.ingestion.law_extractor._split_paragraphs_gemini", return_value=None)
    def test_kho55_blank_lines_merge(self, _mock):
        """Issue #1: blank-line separated list items → still merge to 1 วรรค."""
        result = _split_paragraphs(KHO_55_BLANK_LINES)
        assert len(result) == 1
        assert "(๑)" in result[0]
        assert "(๔)" in result[0]

    @patch("src.ingestion.law_extractor._split_paragraphs_gemini", return_value=None)
    def test_orphan_continuation_merges(self, _mock):
        """Orphan continuation word (แต่) merges back."""
        result = _split_paragraphs(ORPHAN_CONTINUATION)
        assert len(result) == 1

    @patch("src.ingestion.law_extractor._split_paragraphs_gemini", return_value=None)
    def test_letter_subitems_merge(self, _mock):
        """(ก)(ข)(ค) sub-items → single วรรค."""
        result = _split_paragraphs(SECTION_WITH_LETTER_SUBITEMS)
        assert len(result) == 1

    @patch("src.ingestion.law_extractor._split_paragraphs_gemini", return_value=None)
    def test_list_then_new_varak(self, _mock):
        """List items followed by definite new วรรค → 2 วรรค."""
        result = _split_paragraphs(LIST_THEN_NEW_VARAK)
        assert len(result) == 2
        assert "(๑)" in result[0]
        assert "รัฐมนตรี" in result[1]

    @patch("src.ingestion.law_extractor._split_paragraphs_gemini", return_value=None)
    def test_inline_continuation_in_list(self, _mock):
        """Continuation text between list items stays merged."""
        result = _split_paragraphs(LIST_WITH_INLINE_CONTINUATION)
        assert len(result) == 1
        assert "โดยต้องดำเนินการ" in result[0]
        assert "ซึ่งมีเงื่อนไข" in result[0]
