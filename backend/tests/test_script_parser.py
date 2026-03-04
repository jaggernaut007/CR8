"""Tests for backend.services.script_parser — pure logic, no mocks needed."""

import pytest

from backend.services.script_parser import distribute_script, parse_script


class TestParseScript:
    """Tests for parse_script()."""

    def test_single_slide_no_markers(self):
        text = "Welcome to this lesson on neural networks."
        result = parse_script(text)
        assert result == [{"slide_num": 1, "text": text}]

    def test_multiple_slides(self):
        text = "[SLIDE 1]\nWelcome to the lesson.\n\n[SLIDE 2]\nNow let's discuss GloVe."
        result = parse_script(text)
        assert len(result) == 2
        assert result[0]["slide_num"] == 1
        assert result[0]["text"] == "Welcome to the lesson."
        assert result[1]["slide_num"] == 2
        assert result[1]["text"] == "Now let's discuss GloVe."

    def test_empty_segment_skipped(self):
        text = "[SLIDE 1]\n\n[SLIDE 2]\nActual content here."
        result = parse_script(text)
        assert len(result) == 1
        assert result[0]["slide_num"] == 2

    def test_whitespace_trimmed(self):
        text = "[SLIDE 1]\n   Hello world   \n"
        result = parse_script(text)
        assert result[0]["text"] == "Hello world"

    def test_preserves_internal_newlines(self):
        text = "[SLIDE 1]\nFirst paragraph.\n\nSecond paragraph."
        result = parse_script(text)
        assert "\n\n" in result[0]["text"]

    def test_returns_correct_slide_numbers(self):
        text = "[SLIDE 3]\nContent A\n\n[SLIDE 7]\nContent B"
        result = parse_script(text)
        assert result[0]["slide_num"] == 3
        assert result[1]["slide_num"] == 7

    def test_text_before_first_marker(self):
        text = "Intro text here.\n\n[SLIDE 1]\nSlide content."
        result = parse_script(text)
        assert len(result) == 2
        assert result[0]["slide_num"] == 1
        assert result[0]["text"] == "Intro text here."
        assert result[1]["slide_num"] == 1
        assert result[1]["text"] == "Slide content."

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="empty"):
            parse_script("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="empty"):
            parse_script("   \n\n  ")

    def test_many_slides(self):
        parts = [f"[SLIDE {i}]\nContent for slide {i}." for i in range(1, 11)]
        text = "\n\n".join(parts)
        result = parse_script(text)
        assert len(result) == 10
        assert result[9]["slide_num"] == 10

    def test_num_slides_distributes_when_no_markers(self):
        text = "Para one.\n\nPara two.\n\nPara three."
        result = parse_script(text, num_slides=3)
        assert len(result) == 3
        assert result[0]["slide_num"] == 1
        assert result[2]["slide_num"] == 3

    def test_num_slides_ignored_when_markers_present(self):
        text = "[SLIDE 1]\nContent A\n\n[SLIDE 2]\nContent B"
        result = parse_script(text, num_slides=5)
        assert len(result) == 2
        assert result[0]["slide_num"] == 1

    def test_num_slides_zero_falls_back_to_single(self):
        text = "One long paragraph of text."
        result = parse_script(text, num_slides=0)
        assert len(result) == 1
        assert result[0]["slide_num"] == 1


class TestDistributeScript:
    """Tests for distribute_script()."""

    def test_even_split(self):
        text = "A first.\n\nB second.\n\nC third.\n\nD fourth.\n\nE fifth.\n\nF sixth."
        result = distribute_script(text, 3)
        assert len(result) == 3
        assert result[0]["slide_num"] == 1
        assert result[1]["slide_num"] == 2
        assert result[2]["slide_num"] == 3
        # All text is present
        all_text = " ".join(s["text"] for s in result)
        assert "A first." in all_text
        assert "F sixth." in all_text

    def test_fewer_paras_than_slides(self):
        text = "Para one.\n\nPara two."
        result = distribute_script(text, 4)
        assert len(result) == 4
        assert result[0]["text"] == "Para one."
        assert result[1]["text"] == "Para two."
        # Remaining slides get the last paragraph
        assert result[2]["text"] == "Para two."
        assert result[3]["text"] == "Para two."

    def test_single_slide(self):
        text = "All text here.\n\nMore text."
        result = distribute_script(text, 1)
        assert len(result) == 1
        assert result[0]["slide_num"] == 1

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            distribute_script("", 3)

    def test_uneven_paragraphs(self):
        # One very long para + several short ones
        long = "A" * 500
        text = f"{long}\n\nShort.\n\nTiny."
        result = distribute_script(text, 2)
        assert len(result) == 2
        # Long paragraph should be in first segment
        assert "A" * 100 in result[0]["text"]

    def test_preserves_paragraph_breaks(self):
        text = "First.\n\nSecond.\n\nThird.\n\nFourth."
        result = distribute_script(text, 2)
        assert len(result) == 2
        # Each segment should have internal paragraph breaks
        assert "\n\n" in result[0]["text"] or "\n\n" in result[1]["text"]
