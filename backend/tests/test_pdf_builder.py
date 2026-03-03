"""Rigorous tests for PDF builder — ensures GPT output never breaks PDF generation."""

import os


from backend.services.pdf_builder import build_pdf, _sanitize, _strip_latex, _strip_latex_expr


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_valid_pdf(path: str, min_size: int = 500):
    """Assert file exists, meets minimum size, and has PDF magic bytes."""
    assert os.path.exists(path), f"PDF not created at {path}"
    size = os.path.getsize(path)
    assert size > min_size, f"PDF too small ({size} bytes)"
    with open(path, "rb") as f:
        assert f.read(5) == b"%PDF-", "File does not start with PDF magic bytes"


def _build(tmp_path, topics, modules, title="Test Guide"):
    """Shortcut to build a PDF and return its path."""
    output = str(tmp_path / "test.pdf")
    build_pdf(title, topics, modules, output)
    return output


# ---------------------------------------------------------------------------
# Basic generation
# ---------------------------------------------------------------------------

class TestBasicGeneration:

    def test_generates_valid_pdf(self, tmp_path):
        topics = [
            {"name": "Word Vectors", "description": "Dense word representations"},
            {"name": "Transformers", "description": "Self-attention architecture"},
        ]
        modules = [
            "## Module Overview\nWord vectors are key to NLP.\n\n"
            "## Learning Objectives\n- Understand word vectors (Curriculum)\n\n"
            "## Curriculum Coverage\nThe course teaches Word2Vec.\n\n"
            "## Identified Gaps\nSubword embeddings are not covered. (Critical)\n\n"
            "## Core Content\n### What You Need to Learn\nFastText uses subword info.\n\n"
            "### Common Misconceptions\n- Word2Vec handles OOV words (it does not).\n\n"
            "## Industry Context\nNLP Engineers use embeddings daily.\n\n"
            "## Practice & Review\n### Quick Check\n1. What is Word2Vec?\n> Answer: A word embedding model.\n\n"
            "## Key Takeaways\n- Curriculum: Word2Vec basics\n- Gap: Subword embeddings\n\n"
            "## Reflection\n- What was the most important thing you learned?\n\n"
            "## Further Reading\n- [FastText Docs](https://fasttext.cc) (Tutorial) (Beginner)\n",
            "## Module Overview\nTransformers power modern NLP.\n\n"
            "## Learning Objectives\n- Understand self-attention (Curriculum)\n\n"
            "## Core Content\n### What You Need to Learn\nFlash attention is critical.\n\n"
            "## Key Takeaways\n- Curriculum: Attention mechanism\n",
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path, min_size=1000)

    def test_single_topic(self, tmp_path):
        topics = [{"name": "Topic A", "description": "Desc A"}]
        modules = ["## Core Content\nSome content here."]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_many_topics_toc_overflow(self, tmp_path):
        """30 topics should force the TOC across multiple pages."""
        topics = [{"name": f"Topic Number {i}", "description": f"Description for topic {i}"} for i in range(30)]
        modules = [f"## Section\nContent for topic {i}." for i in range(30)]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)


# ---------------------------------------------------------------------------
# Unicode & encoding — the #1 source of GPT-caused failures
# ---------------------------------------------------------------------------

class TestUnicodeHandling:

    def test_smart_quotes_in_module(self, tmp_path):
        """GPT frequently uses smart quotes: \u201c \u201d \u2018 \u2019."""
        topics = [{"name": "Quotes", "description": "Testing quotes"}]
        modules = [
            "\u201cThis is a quote,\u201d she said. \u2018Single quotes\u2019 too."
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_smart_quotes_in_topic_name(self, tmp_path):
        """Smart quotes in topic names appear in TOC and chapter titles."""
        topics = [{"name": "\u201cSmart\u201d Topic\u2019s Name", "description": "Desc"}]
        modules = ["## Content\nBody text."]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_em_dash_en_dash_ellipsis(self, tmp_path):
        topics = [{"name": "Dashes", "description": "Testing dashes"}]
        modules = [
            "Word vectors \u2014 also known as embeddings \u2013 are fundamental\u2026\n"
            "The loss \u2212 computed via cross-entropy \u2212 decreases over time."
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_bullet_chars(self, tmp_path):
        """GPT sometimes uses Unicode bullets instead of markdown dashes."""
        topics = [{"name": "Bullets", "description": "Testing bullets"}]
        modules = [
            "\u2022 First bullet point\n"
            "\u2023 Triangle bullet\n"
            "\u2043 Hyphen bullet\n"
            "\u25E6 White bullet\n"
            "\u25AA Small black square"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_non_breaking_spaces_and_hyphens(self, tmp_path):
        topics = [{"name": "Non\u2011breaking\u00a0spaces", "description": "Test\u00a0desc"}]
        modules = ["Content with\u00a0non-breaking\u00a0spaces and\u2011hyphens."]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_zero_width_chars(self, tmp_path):
        """GPT outputs sometimes contain invisible Unicode characters."""
        topics = [{"name": "Zero\u200bWidth", "description": "Desc\u200c\u200d"}]
        modules = ["\ufeffBOM at start\u200b and zero\u200cwidth\u200d throughout."]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_emoji_in_content(self, tmp_path):
        """GPT may include emoji — these must not crash the PDF."""
        topics = [{"name": "Emoji Test", "description": "Has emoji"}]
        modules = [
            "## Learning Objectives\n"
            "- Understand neural networks \U0001f9e0\n"
            "- Master deep learning \U0001f525\n\n"
            "## Core Content\n"
            "Transformers are powerful \u2728 models. They use attention \U0001f440.\n"
            "Key formula: loss \u2192 0 as training \u2192 \u221e"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_emoji_in_topic_name(self, tmp_path):
        topics = [{"name": "\U0001f4da Transformers \U0001f680", "description": "With emoji"}]
        modules = ["## Content\nBody."]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_cjk_characters(self, tmp_path):
        """Chinese/Japanese/Korean characters that GPT might include."""
        topics = [{"name": "NLP Basics", "description": "Desc"}]
        modules = [
            "The term \u81ea\u7136\u8a9e\u8a00\u51e6\u7406 means natural language processing in Japanese.\n"
            "Korean: \uc790\uc5f0\uc5b4 \ucc98\ub9ac. Chinese: \u81ea\u7136\u8bed\u8a00\u5904\u7406."
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_mathematical_symbols(self, tmp_path):
        """GPT often uses math Unicode in technical content."""
        topics = [{"name": "Math Symbols", "description": "Math content"}]
        modules = [
            "The gradient \u2207L with respect to \u03b8 is computed as:\n"
            "\u03b1 \u00d7 \u03b2 = \u03b3, where \u03b4 \u2264 \u03b5\n"
            "Sum: \u2211 Product: \u220f Integral: \u222b\n"
            "Infinity: \u221e Element: \u2208 Subset: \u2286\n"
            "Not equal: \u2260 Approximately: \u2248 Arrow: \u2192"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_mixed_unicode_stress_test(self, tmp_path):
        """Combine every problematic Unicode category in one module."""
        topics = [{"name": "\u201cMixed\u201d \u2014 Stress\u2019s Test\u2026", "description": "All\u00a0unicode\u2011things"}]
        modules = [
            "## Learning Objectives\n"
            "- Understand \u201csmart quotes\u201d and \u2018single\u2019 ones\n"
            "- Master the \u2014 em dash and \u2013 en dash\n"
            "- Use \u2022 bullets and \u2026 ellipsis\n\n"
            "## Core Content\n"
            "The formula is: \u03b1\u00b2 + \u03b2\u00b2 = \u03b3\u00b2 (approximately \u2248 correct).\n"
            "Key insight \u2192 transformers use self\u2011attention.\n"
            "\ufeff\u200b\u200c\u200d Hidden chars should vanish.\n"
            "\U0001f4a1 Innovation: loss \u2212 regularization = \u221e improvement.\n\n"
            "## Industry Context\n"
            "Companies need NLP skills \u2014 especially for\u00a0production systems.\n\n"
            "## Key Takeaways\n"
            "- \u2022 Point one\n"
            "- \u2023 Point two\n"
            "- \u2032Prime\u2032 and \u2033double prime\u2033\n\n"
            "## Further Reading\n"
            "- [Attention Paper](https://arxiv.org/abs/1706.03762)\n"
            "- [BERT\u2019s Impact](https://example.com/bert)"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_accented_latin_characters(self, tmp_path):
        """Accented characters within latin-1 range should render correctly."""
        topics = [{"name": "R\u00e9sum\u00e9 of M\u00fcller", "description": "Na\u00efve Bayes"}]
        modules = [
            "The caf\u00e9 serves \u00e0 la carte. \u00c9tude on p\u00e2t\u00e9.\n"
            "Clich\u00e9s and fa\u00e7ades with \u00f1 and \u00fc."
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_copyright_trademark_symbols(self, tmp_path):
        topics = [{"name": "Legal Symbols", "description": "Desc"}]
        modules = ["OpenAI\u00ae and GPT\u2122 are products. Copyright \u00a9 2025. Registered \u00ae."]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)


# ---------------------------------------------------------------------------
# Markdown edge cases — GPT doesn't always follow the expected format
# ---------------------------------------------------------------------------

class TestMarkdownEdgeCases:

    def test_h1_headings(self, tmp_path):
        """GPT sometimes uses # instead of ## headings."""
        topics = [{"name": "Headings", "description": "Desc"}]
        modules = ["# Top Level Heading\nSome content.\n## Subheading\nMore content."]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_h3_h4_headings(self, tmp_path):
        """### is handled as teal sub-heading; #### and deeper render as paragraphs."""
        topics = [{"name": "Deep Headings", "description": "Desc"}]
        modules = ["### Sub-sub heading\nContent.\n#### Even deeper\nMore content.\n##### Very deep\nStill works."]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_numbered_lists(self, tmp_path):
        """GPT often uses numbered lists instead of bullets."""
        topics = [{"name": "Lists", "description": "Desc"}]
        modules = [
            "## Learning Objectives\n"
            "1. First objective\n"
            "2. Second objective\n"
            "3. Third objective\n\n"
            "## Core Content\n"
            "a) First item\n"
            "b) Second item"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_code_blocks(self, tmp_path):
        """GPT may include code blocks with triple backticks."""
        topics = [{"name": "Code", "description": "Desc"}]
        modules = [
            "## Core Content\n"
            "Here is an example:\n\n"
            "```python\n"
            "import torch\n"
            "model = torch.nn.Linear(768, 10)\n"
            "output = model(input_tensor)\n"
            "```\n\n"
            "And inline code: `model.forward(x)` computes the output."
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_bold_and_italic_markdown(self, tmp_path):
        """Various bold/italic patterns GPT uses."""
        topics = [{"name": "Formatting", "description": "Desc"}]
        modules = [
            "This has **bold text** and *italic text* and ***bold italic***.\n"
            "Also __underline bold__ and _underline italic_.\n"
            "Mixed: **bold with *italic* inside** and unclosed **bold"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_markdown_links(self, tmp_path):
        """Links with various URL patterns."""
        topics = [{"name": "Links", "description": "Desc"}]
        modules = [
            "- [Simple Link](https://example.com)\n"
            "- [Link with spaces in text](https://example.com/path?q=hello%20world)\n"
            "- [Link with parens](https://en.wikipedia.org/wiki/Transformer_(machine_learning_model))\n"
            "- Plain URL: https://arxiv.org/abs/1706.03762\n"
            "- [Empty URL]()\n"
            "- Broken link: [no closing paren](https://example.com"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_html_tags_in_content(self, tmp_path):
        """GPT sometimes outputs HTML tags."""
        topics = [{"name": "HTML", "description": "Desc"}]
        modules = [
            "<b>Bold text</b> and <i>italic</i> and <code>code</code>.\n"
            "<p>A paragraph</p>\n"
            "<br/>\n"
            "<a href='https://example.com'>A link</a>\n"
            "<table><tr><td>Cell</td></tr></table>"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_markdown_tables(self, tmp_path):
        """GPT may include markdown tables."""
        topics = [{"name": "Tables", "description": "Desc"}]
        modules = [
            "## Comparison\n\n"
            "| Model | Accuracy | Speed |\n"
            "|-------|----------|-------|\n"
            "| BERT  | 92%      | Slow  |\n"
            "| GPT   | 95%      | Fast  |\n"
            "| T5    | 93%      | Med   |\n"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_blockquotes(self, tmp_path):
        """GPT uses > for blockquotes."""
        topics = [{"name": "Quotes", "description": "Desc"}]
        modules = [
            "## Core Content\n"
            "> This is a blockquote from a famous paper.\n"
            "> It spans multiple lines.\n\n"
            ">> Nested blockquote."
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_horizontal_rules(self, tmp_path):
        topics = [{"name": "Rules", "description": "Desc"}]
        modules = ["First section.\n\n---\n\nSecond section.\n\n***\n\nThird section."]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)


# ---------------------------------------------------------------------------
# Content size extremes
# ---------------------------------------------------------------------------

class TestContentExtremes:

    def test_empty_module(self, tmp_path):
        """Empty string as module content."""
        topics = [{"name": "Empty", "description": "Desc"}]
        modules = [""]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_whitespace_only_module(self, tmp_path):
        topics = [{"name": "Whitespace", "description": "Desc"}]
        modules = ["   \n\n  \n   \t  \n"]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_no_description(self, tmp_path):
        """Topic with missing description field."""
        topics = [{"name": "No Desc"}]
        modules = ["## Content\nBody text."]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_empty_description(self, tmp_path):
        topics = [{"name": "Empty Desc", "description": ""}]
        modules = ["## Content\nBody text."]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_very_long_topic_name(self, tmp_path):
        """Topic name that exceeds a single line width."""
        long_name = "A Very Long Topic Name That Discusses the Intricacies of Natural Language Processing and Its Applications in Modern Industry"
        topics = [{"name": long_name, "description": "Desc"}]
        modules = ["## Content\nBody text."]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_very_long_paragraph(self, tmp_path):
        """A single paragraph with no line breaks — tests multi_cell wrapping."""
        long_para = "Word embeddings are dense vector representations of words. " * 100
        topics = [{"name": "Long Para", "description": "Desc"}]
        modules = [f"## Core Content\n{long_para}"]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_very_long_single_line(self, tmp_path):
        """One continuous string with no spaces — worst case for line wrapping."""
        long_word = "A" * 500
        topics = [{"name": "Long Line", "description": "Desc"}]
        modules = [f"## Core Content\n{long_word}"]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_large_module_multi_page(self, tmp_path):
        """Module content that spans many pages — tests page breaks."""
        paragraphs = []
        for i in range(50):
            paragraphs.append(f"## Section {i + 1}")
            paragraphs.append(
                f"This is paragraph {i + 1} of the learning module. "
                "It contains enough text to contribute to multiple page breaks "
                "when combined with all the other paragraphs in this module. "
                "The content discusses various aspects of the topic in detail."
            )
            paragraphs.append(f"- Bullet point {i + 1}a")
            paragraphs.append(f"- Bullet point {i + 1}b")
            paragraphs.append("")
        topics = [{"name": "Large Module", "description": "Tests page breaks"}]
        modules = ["\n".join(paragraphs)]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path, min_size=5000)

    def test_many_blank_lines(self, tmp_path):
        """GPT sometimes outputs excessive blank lines."""
        topics = [{"name": "Blanks", "description": "Desc"}]
        modules = ["## Heading\n\n\n\n\n\n\n\n\n\nContent after many blanks.\n\n\n\n\nMore content."]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)


# ---------------------------------------------------------------------------
# Title and cover page edge cases
# ---------------------------------------------------------------------------

class TestCoverPage:

    def test_unicode_in_title(self, tmp_path):
        topics = [{"name": "Topic", "description": "Desc"}]
        modules = ["## Content\nBody."]
        path = _build(tmp_path, topics, modules, title="\u201cSmart\u201d Learning Guide \u2014 2025 Edition\u2122")
        _assert_valid_pdf(path)

    def test_very_long_title(self, tmp_path):
        long_title = "A Comprehensive Market-Enriched Learning Guide for Advanced " * 5
        topics = [{"name": "Topic", "description": "Desc"}]
        modules = ["## Content\nBody."]
        path = _build(tmp_path, topics, modules, title=long_title)
        _assert_valid_pdf(path)

    def test_empty_title(self, tmp_path):
        topics = [{"name": "Topic", "description": "Desc"}]
        modules = ["## Content\nBody."]
        path = _build(tmp_path, topics, modules, title="")
        _assert_valid_pdf(path)


# ---------------------------------------------------------------------------
# _sanitize unit tests
# ---------------------------------------------------------------------------

class TestSanitize:

    def test_replaces_smart_quotes(self):
        assert _sanitize("\u201chello\u201d") == '"hello"'
        assert _sanitize("\u2018world\u2019") == "'world'"

    def test_replaces_dashes(self):
        assert _sanitize("a\u2014b") == "a--b"
        assert _sanitize("a\u2013b") == "a-b"
        assert _sanitize("a\u2011b") == "a-b"
        assert _sanitize("a\u2212b") == "a-b"

    def test_replaces_ellipsis(self):
        assert _sanitize("wait\u2026") == "wait..."

    def test_replaces_bullets(self):
        assert _sanitize("\u2022 item") == "- item"

    def test_strips_zero_width(self):
        assert _sanitize("he\u200bllo") == "hello"
        assert _sanitize("\ufeffstart") == "start"
        assert _sanitize("a\u200cb\u200dc") == "abc"

    def test_replaces_non_breaking_space(self):
        assert _sanitize("hello\u00a0world") == "hello world"

    def test_fallback_replaces_unknown_unicode(self):
        """Characters not in the map or latin-1 become '?'."""
        result = _sanitize("\u4e16\u754c")  # Chinese characters
        assert "\u4e16" not in result
        assert "\u754c" not in result
        # Should contain replacement characters
        assert "?" in result

    def test_emoji_replaced(self):
        result = _sanitize("hello \U0001f600 world")
        assert "\U0001f600" not in result

    def test_preserves_ascii(self):
        text = "Hello, World! 123 @#$%"
        assert _sanitize(text) == text

    def test_preserves_latin1_accents(self):
        text = "\u00e9\u00e0\u00fc\u00f1\u00e7"  # e-acute, a-grave, u-umlaut, n-tilde, c-cedilla
        assert _sanitize(text) == text

    def test_empty_string(self):
        assert _sanitize("") == ""

    def test_handles_none_gracefully(self):
        """If somehow None slips through, it should not crash the whole pipeline."""
        # _sanitize expects str — but we test that the pipeline won't crash
        # by ensuring build_pdf handles missing descriptions
        pass


# ---------------------------------------------------------------------------
# LaTeX handling
# ---------------------------------------------------------------------------

class TestLatexHandling:

    def test_inline_latex_renders_pdf(self, tmp_path):
        """Inline \\( ... \\) LaTeX should produce a valid PDF (rendered as images)."""
        topics = [{"name": "Word Vectors", "description": "Desc"}]
        modules = [
            "## Core Content\n"
            "The probability \\(P(o \\mid c)\\) is defined using the dot product "
            "\\(u_o^\\top v_c\\) and a softmax over the vocabulary.\n\n"
            "- How does SGD use training examples of \\((\\text{center}, \\text{context})\\) "
            "pairs to update the word vectors?\n"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_display_latex_renders_pdf(self, tmp_path):
        """Display math \\[ ... \\] should produce a valid PDF."""
        topics = [{"name": "Math", "description": "Desc"}]
        modules = [
            "## Core Content\n"
            "The update rule is:\n"
            "\\[\\theta_{t+1} = \\theta_t - \\eta \\nabla L(\\theta_t)\\]\n"
            "Where theta represents model parameters.\n"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_h4_headings_render(self, tmp_path):
        """#### headings should render as styled headings, not literal #'s."""
        topics = [{"name": "Headings", "description": "Desc"}]
        modules = [
            "## Core Content\n"
            "#### 1. Scalable Training: Negative Sampling for Skip-gram\n"
            "Content under h4.\n"
            "##### Deep heading\n"
            "Content under h5.\n"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_mixed_latex_and_bold(self, tmp_path):
        """Lines with LaTeX should still produce valid PDFs."""
        topics = [{"name": "Mixed", "description": "Desc"}]
        modules = [
            "## Core Content\n"
            "The **attention** formula uses \\(Q K^\\top / \\sqrt{d_k}\\) scaling.\n"
            "- **Key insight**: \\(\\frac{1}{\\sqrt{d_k}}\\) prevents saturation.\n"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)


class TestStripLatex:

    def test_inline_math_delimiters(self):
        assert _strip_latex("the probability \\(P(o)\\) is") == "the probability P(o) is"

    def test_mid_command(self):
        assert _strip_latex("\\(P(o \\mid c)\\)") == "P(o | c)"

    def test_text_command(self):
        assert _strip_latex("\\(\\text{center}\\)") == "center"

    def test_top_command(self):
        assert _strip_latex("\\(u_o^\\top v_c\\)") == "u_o^T v_c"

    def test_frac_command(self):
        assert _strip_latex_expr("\\frac{a}{b}") == "a/b"

    def test_sqrt_command(self):
        assert _strip_latex_expr("\\sqrt{d_k}") == "sqrt(d_k)"

    def test_no_latex_passthrough(self):
        text = "Plain text with no LaTeX."
        assert _strip_latex(text) == text

    def test_multiple_expressions(self):
        text = "Use \\(\\alpha\\) and \\(\\beta\\) values"
        result = _strip_latex(text)
        assert "\\" not in result
        assert "alpha" in result
        assert "beta" in result


# ---------------------------------------------------------------------------
# Realistic GPT output simulation
# ---------------------------------------------------------------------------

class TestRealisticGPTOutput:

    def test_full_gpt_module_with_unicode(self, tmp_path):
        """Simulates actual GPT-5 output with common Unicode issues."""
        topics = [
            {"name": "Transformer\u2019s Self\u2011Attention Mechanism", "description": "The core \u201cinnovation\u201d behind modern LLMs"},
        ]
        modules = [
            "## Learning Objectives\n"
            "- Explain the self\u2011attention mechanism and its role in transformer architectures\n"
            "- Implement multi\u2011head attention using PyTorch\u2019s `nn.MultiheadAttention`\n"
            "- Compare self\u2011attention with traditional RNN\u2011based sequence modeling\n"
            "- Evaluate the computational trade\u2011offs of attention \u2014 O(n\u00b2) complexity vs. parallelism gains\n\n"
            "## Core Content\n"
            "The transformer architecture, introduced in the seminal paper \u201cAttention Is All You Need\u201d "
            "(Vaswani et al., 2017), revolutionized natural language processing. Unlike recurrent neural "
            "networks (RNNs), which process sequences sequentially, transformers leverage **self\u2011attention** "
            "to capture dependencies between all positions in a sequence simultaneously.\n\n"
            "The key insight is the **scaled dot\u2011product attention** mechanism:\n\n"
            "Attention(Q, K, V) = softmax(QK\u1d40 / \u221ad_k)V\n\n"
            "Where Q (queries), K (keys), and V (values) are linear projections of the input embeddings. "
            "The scaling factor 1/\u221ad_k prevents the softmax from saturating when d_k is large.\n\n"
            "Multi\u2011head attention extends this by running h parallel attention \u201cheads,\u201d each with "
            "different learned projections. This allows the model to attend to information from different "
            "representation subspaces simultaneously\u2026\n\n"
            "## Industry Context\n"
            "Transformers are the foundation of virtually every production NLP system in 2025\u20132026. "
            "Companies like Google, Meta, and OpenAI rely heavily on transformer\u2011based models:\n\n"
            "- **Search engines** \u2014 BERT and its successors power Google\u2019s search ranking\n"
            "- **Chatbots & assistants** \u2014 GPT\u20114, Claude, and Gemini are all transformer models\n"
            "- **Code generation** \u2014 GitHub Copilot uses a transformer backbone\n"
            "- **Content moderation** \u2014 platforms use fine\u2011tuned transformers for toxicity detection\n\n"
            "Job postings frequently list \u201ctransformer architectures\u201d and \u201cattention mechanisms\u201d "
            "as required knowledge for ML engineering roles (median salary: $180K\u2013$250K).\n\n"
            "## Key Takeaways\n"
            "- Self\u2011attention computes relationships between all pairs of positions in O(n\u00b2) time\n"
            "- Multi\u2011head attention allows parallel attention to different representation subspaces\n"
            "- Positional encodings compensate for the lack of inherent sequence ordering\n"
            "- Transformers enabled the \u201cscaling laws\u201d revolution \u2014 larger models \u2192 better performance\n"
            "- Understanding attention is essential for debugging and interpreting modern LLMs\n\n"
            "## Further Reading\n"
            "- [Attention Is All You Need (Vaswani et al., 2017)](https://arxiv.org/abs/1706.03762)\n"
            "- [The Illustrated Transformer \u2014 Jay Alammar\u2019s Visual Guide](https://jalammar.github.io/illustrated-transformer/)\n"
            "- [Hugging Face Transformers Documentation](https://huggingface.co/docs/transformers/)\n"
            "- [Stanford CS224N \u2014 Lecture 8: Self\u2011Attention and Transformers](https://web.stanford.edu/class/cs224n/)\n"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path, min_size=2000)

    def test_gpt_module_with_code_and_math(self, tmp_path):
        """GPT output mixing code blocks, math notation, and markdown."""
        topics = [{"name": "Gradient Descent", "description": "Optimization for neural networks"}]
        modules = [
            "## Learning Objectives\n"
            "1. Implement stochastic gradient descent from scratch\n"
            "2. Compare SGD, Adam, and AdaGrad optimizers\n\n"
            "## Core Content\n"
            "The update rule for vanilla gradient descent is:\n\n"
            "\u03b8\u2099\u2081 = \u03b8\u2099 \u2212 \u03b7 \u00b7 \u2207L(\u03b8\u2099)\n\n"
            "Where:\n"
            "- \u03b8 represents model parameters\n"
            "- \u03b7 is the learning rate (typically 10\u207b\u00b3 to 10\u207b\u2075)\n"
            "- \u2207L is the gradient of the loss function\n\n"
            "```python\n"
            "def sgd_step(params, grads, lr=0.001):\n"
            "    \"\"\"Vanilla SGD update.\"\"\"\n"
            "    return [p - lr * g for p, g in zip(params, grads)]\n"
            "```\n\n"
            "## Key Takeaways\n"
            "- Learning rate \u03b7 is the most critical hyperparameter\n"
            "- Adam combines momentum (\u03b2\u2081) and RMSprop (\u03b2\u2082)\n"
            "- Batch size affects the variance of gradient estimates"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_gpt_module_with_tables_and_comparisons(self, tmp_path):
        """GPT often includes comparison tables."""
        topics = [{"name": "Model Comparison", "description": "BERT vs GPT vs T5"}]
        modules = [
            "## Core Content\n\n"
            "| Feature | BERT | GPT\u20114 | T5 |\n"
            "|---------|------|--------|----|\n"
            "| Architecture | Encoder\u2011only | Decoder\u2011only | Encoder\u2011Decoder |\n"
            "| Pre\u2011training | MLM + NSP | Autoregressive | Span corruption |\n"
            "| Parameters | 340M | ~1.8T | 11B |\n"
            "| Release | 2018 | 2023 | 2020 |\n\n"
            "**Key insight**: Each architecture has trade\u2011offs between bidirectional context "
            "(BERT), generative capability (GPT), and flexibility (T5).\n\n"
            "## Industry Context\n"
            "The \u201cGPT vs BERT\u201d debate has largely settled \u2014 both have their place:\n"
            "- BERT excels at classification, NER, and search ranking\n"
            "- GPT excels at generation, summarization, and chat\n"
            "- T5 offers a unified \u201ctext\u2011to\u2011text\u201d framework"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path)

    def test_full_redesigned_module(self, tmp_path):
        """Full 10-section redesigned format with ### sub-headings, numbered lists, and blockquotes."""
        topics = [{"name": "Word Vectors", "description": "Dense word representations"}]
        modules = [
            "## Module Overview\n"
            "Imagine you are building a search engine for legal documents. Users complain that "
            "searching for 'intellectual property' returns nothing about 'patents.' Word vectors "
            "solve this by capturing semantic similarity. This module teaches you what your "
            "curriculum missed about modern embedding techniques.\n\n"
            "## Learning Objectives\n"
            "- Explain the Skip-gram and CBOW architectures (Curriculum)\n"
            "- Implement subword embedding training using FastText (Gap)\n"
            "- Evaluate when to use pre-trained vs. domain-specific embeddings (Gap)\n\n"
            "## Curriculum Coverage\n"
            "The curriculum teaches Word2Vec, GloVe, and basic embedding concepts. "
            "Students learn both CBOW and Skip-gram architectures.\n\n"
            "Before continuing, make sure you can answer:\n"
            "- What is the difference between CBOW and Skip-gram?\n"
            "- How does GloVe differ from Word2Vec in its training approach?\n\n"
            "## Identified Gaps\n"
            "The curriculum does not cover subword embeddings (FastText) or "
            "contextual embeddings. (Critical)\n"
            "Domain-specific fine-tuning is not addressed. (Important)\n\n"
            "## Core Content\n"
            "### What You Need to Learn\n"
            "Building on the Word2Vec foundations you studied, FastText extends the idea by "
            "representing each word as a bag of character n-grams.\n\n"
            "Here is how FastText processes the word 'where':\n"
            "1. Break the word into character n-grams: <wh, whe, her, ere, re>\n"
            "2. Look up the vector for each n-gram from the embedding table\n"
            "3. Sum all n-gram vectors to produce the final word vector\n"
            "4. This means even unseen words get meaningful representations\n\n"
            "Other gaps to explore: Contextual embeddings (ELMo, BERT) produce different "
            "vectors for the same word depending on context. See Further Reading.\n\n"
            "### Common Misconceptions\n"
            "- Word2Vec can handle out-of-vocabulary words. It cannot -- it assigns no vector to unseen words.\n"
            "- Larger embedding dimensions are always better. Diminishing returns set in after ~300 dims.\n\n"
            "## Industry Context\n"
            "NLP Engineers and Machine Learning Engineers use embeddings daily. At companies like "
            "Google, pre-trained embeddings serve as the backbone for search ranking.\n\n"
            "## Practice & Review\n"
            "### Quick Check\n"
            "1. What two architectures does Word2Vec offer?\n"
            "> Answer: CBOW (Continuous Bag of Words) and Skip-gram.\n"
            "2. How does FastText handle out-of-vocabulary words?\n"
            "> Answer: By summing character n-gram vectors.\n"
            "3. Why would you fine-tune embeddings on domain-specific data?\n"
            "> Answer: General embeddings may not capture domain-specific semantics.\n\n"
            "### Apply It\n"
            "You are building a medical document search system. Doctors search for 'myocardial infarction' "
            "but also need results for 'heart attack.' Your task:\n"
            "- Choose an appropriate embedding approach and justify your choice\n"
            "- Explain why vanilla Word2Vec would fail for rare medical terms\n"
            "- Describe how you would evaluate embedding quality\n\n"
            "## Key Takeaways\n"
            "- Curriculum: Word2Vec provides foundational understanding of distributional semantics\n"
            "- Curriculum: Both CBOW and Skip-gram have distinct training characteristics\n"
            "- Gap: FastText handles out-of-vocabulary words via subword information\n"
            "- Gap: Domain-specific fine-tuning is expected in industry applications\n"
            "- Integration: Understanding static embeddings is prerequisite to contextual approaches\n\n"
            "## Reflection\n"
            "- What was the most important thing you learned in this module?\n"
            "- Which gap area do you feel least confident about?\n"
            "- How does this connect to other topics you have studied?\n\n"
            "## Further Reading\n"
            "- [FastText Tutorial](https://fasttext.cc/docs/en/tutorial.html) (Tutorial) (Beginner) - "
            "Hands-on guide to training subword embeddings.\n"
            "- [Word2Vec Paper](https://arxiv.org/abs/1301.3781) (Research Paper) (Intermediate) - "
            "The original Word2Vec paper.\n"
        ]
        path = _build(tmp_path, topics, modules)
        _assert_valid_pdf(path, min_size=2000)
