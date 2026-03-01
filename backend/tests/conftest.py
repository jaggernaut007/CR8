import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def single_slide_pdf(tmp_path):
    """Generate a minimal test PDF with known content."""
    try:
        from fpdf import FPDF
    except ImportError:
        pytest.skip("fpdf2 not installed")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.cell(text="Word Vectors and Embeddings")
    pdf.ln(12)
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(w=0, text="This lecture covers word vector representations and neural network approaches to NLP.")

    path = tmp_path / "01_Word_Vectors_I.pdf"
    pdf.output(str(path))
    return str(path)


@pytest.fixture
def three_slide_pdfs(tmp_path):
    """Generate three minimal test PDFs."""
    try:
        from fpdf import FPDF
    except ImportError:
        pytest.skip("fpdf2 not installed")

    titles = [
        ("01_Word_Vectors_I.pdf", "Word Vectors and Embeddings"),
        ("08_Transformers.pdf", "Transformer Architecture"),
        ("09_Pretraining.pdf", "Pretraining Language Models"),
    ]
    paths = []
    for filename, title in titles:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=16)
        pdf.cell(text=title)
        pdf.ln(12)
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(w=0, text=f"Content for {title}. This covers key NLP concepts.")
        # Add a few more pages
        for i in range(3):
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)
            pdf.multi_cell(w=0, text=f"Page {i+2} content for {title}.")
        path = tmp_path / filename
        pdf.output(str(path))
        paths.append(str(path))
    return paths


@pytest.fixture
def temp_chroma_dir(tmp_path):
    return str(tmp_path / "test_chroma_db")


# ---------------------------------------------------------------------------
# Shared LLM + state fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm():
    """Reusable deterministic LLM mock. Override .invoke.return_value per test."""
    m = MagicMock()
    m.invoke.return_value = MagicMock(content="default mock response")
    return m


@pytest.fixture
def base_pipeline_state():
    """Minimal valid PipelineState for agent and graph tests."""
    return {
        "job_id": "test0001",
        "file_paths": [],
        "topics": [],
        "raw_text": "",
        "curriculum_scope": "",
        "gap_summary": [],
        "pdf_path": "",
        "ppt_path": "",
        "video_dir": "",
        "output_formats": "pdf",
        "current_stage": "starting",
    }


# ---------------------------------------------------------------------------
# Structural check content fixtures
# ---------------------------------------------------------------------------

_MODULE_SECTIONS = [
    "## Module Overview",
    "## Learning Objectives",
    "## Curriculum Coverage",
    "## Identified Gaps",
    "## Core Content",
    "## Industry Context",
    "## Practice & Review",
    "## Key Takeaways",
    "## Reflection",
]


def _build_valid_module() -> str:
    """Build a minimal valid module with all 9 sections, >2000 chars."""
    parts = []
    parts.append(_MODULE_SECTIONS[0])
    parts.append(
        "\nThis module covers transformer architectures and attention mechanisms "
        "in modern deep learning. Students will develop a comprehensive understanding "
        "of how self-attention enables models to capture long-range dependencies.\n"
    )
    parts.append(_MODULE_SECTIONS[1])
    parts.append(
        "\n- Explain the self-attention mechanism and its role in transformers (Curriculum)\n"
        "- Apply transformer models to practical NLP tasks (Gap)\n"
        "- Evaluate trade-offs between different positional encoding strategies (Curriculum)\n"
        "- Analyze how multi-head attention improves model expressiveness (Gap)\n"
    )
    parts.append(_MODULE_SECTIONS[2])
    parts.append(
        "\nThe course covers attention mechanisms, encoder-decoder architectures, "
        "and foundational transformer papers including the original 'Attention Is All You Need'.\n"
    )
    parts.append(_MODULE_SECTIONS[3])
    parts.append(
        "\n- Deployment and inference optimization techniques are not covered.\n"
        "- Industry-scale fine-tuning practices are absent from curriculum.\n"
    )
    parts.append(_MODULE_SECTIONS[4])
    parts.append(
        "\n### Self-Attention Mechanism\n"
        "Self-attention computes weighted combinations of all positions in a sequence. "
        "For each position, queries, keys, and values are computed via learned projections.\n"
        "The attention score is computed as softmax(QK^T / sqrt(d_k)) * V.\n\n"
        "### Multi-Head Attention\n"
        "Multi-head attention runs h parallel attention functions on projected subspaces, "
        "enabling the model to jointly attend to information from different representation "
        "subspaces at different positions. This dramatically improves model capacity.\n"
    )
    parts.append(_MODULE_SECTIONS[5])
    parts.append(
        "\nTransformers power production systems at major technology companies. "
        "GPT-4 and similar models use transformer architectures with billions of parameters. "
        "Understanding transformers is essential for modern ML engineering roles.\n"
    )
    parts.append(_MODULE_SECTIONS[6])
    parts.append(
        "\n**Quick Check 1**: What is the computational complexity of self-attention?\n"
        "> Answer: O(n^2 * d) where n is sequence length and d is dimension.\n\n"
        "**Quick Check 2**: Why is positional encoding necessary in transformers?\n"
        "> Answer: Transformers have no recurrence, so positional information must be injected.\n"
    )
    parts.append(_MODULE_SECTIONS[7])
    parts.append(
        "\ncurriculum: Transformer fundamentals and attention mechanisms are well understood.\n"
        "gap: Practical deployment optimization and fine-tuning at scale remain critical gaps.\n"
    )
    parts.append(_MODULE_SECTIONS[8])
    parts.append(
        "\nWhich aspect of the transformer architecture do you find most challenging? "
        "Consider how the multi-head attention mechanism differs from single-head attention "
        "and why this design choice improves model performance across diverse tasks.\n"
    )
    return "\n".join(parts)


@pytest.fixture
def valid_module_md() -> str:
    """Minimal valid 9-section module with all structural checks passing (>2000 chars)."""
    return _build_valid_module()


@pytest.fixture
def valid_script() -> str:
    """400-word spoken script: contractions, question mark, no markdown or stage directions."""
    return (
        "Today we're going to explore one of the most important ideas in modern machine learning. "
        "You'll be surprised to discover how something called self-attention completely changed "
        "the way computers understand language. It's a concept that's both elegant and powerful, "
        "and by the time we're done here, you'll have a solid intuition for why it works so well.\n\n"
        "So here's the question we need to answer: how does a model know which words in a sentence "
        "are most relevant to each other? Think about the sentence 'The animal didn't cross the "
        "street because it was too tired.' What does 'it' refer to? A human reader knows instantly "
        "that it refers to the animal, not the street. But how can a computer figure that out?\n\n"
        "Here's where self-attention comes in. Instead of processing words one by one in order, "
        "self-attention looks at all words simultaneously and computes a score for every pair. "
        "These scores tell the model how much each word should 'attend' to every other word. "
        "Words that are semantically related get high scores, so 'it' and 'animal' will be "
        "strongly connected, even though they're separated by several words.\n\n"
        "Now you might be wondering: that sounds expensive. And you're right. If you have n words, "
        "you need n squared comparisons. That's why transformers require so much compute. But "
        "here's what's remarkable: this simple mechanism, repeated across many layers and multiple "
        "attention heads, turns out to be incredibly expressive. Each head can learn to focus on "
        "different types of relationships, like syntactic structure, coreference, or semantic roles.\n\n"
        "What makes this especially interesting is the role of position. Traditional recurrent "
        "networks processed text sequentially, so position was built in naturally. Transformers "
        "don't have that, so they add positional encodings explicitly. It's a clever workaround "
        "that preserves the ability to process all positions in parallel, which is what makes "
        "training so fast on modern hardware.\n\n"
        "So what's the key takeaway here? Self-attention gives neural networks a way to model "
        "relationships between arbitrary positions in a sequence, and that's why transformers "
        "have become the dominant architecture for language, vision, and beyond. Once you "
        "understand attention, you'll see it everywhere in modern AI research."
    )


def _make_ppt_single() -> str:
    return json.dumps({
        "topic_name": "Transformer Architecture",
        "slide_title": "Transformers fundamentally changed how models process sequential data",
        "severity": "critical",
        "gap_concepts": [
            {
                "concept": "Deployment Optimization",
                "description": "Techniques for efficient transformer inference in production",
                "diagram_type": "none",
            }
        ],
    })


def _make_ppt_full() -> str:
    return json.dumps({
        "presentation_title": "NLP Curriculum Gap Analysis",
        "executive_summary": {
            "total_gaps": 2,
            "topic_scores": [
                {"topic": "Transformers", "curriculum_score": 75, "industry_requirement": 95},
                {"topic": "BERT Pretraining", "curriculum_score": 60, "industry_requirement": 90},
            ],
        },
        "topic_slides": [
            {
                "topic_name": "Transformer Architecture",
                "slide_title": "Transformers fundamentally changed how models process sequential data",
                "severity": "critical",
                "gap_concepts": [
                    {
                        "concept": "Deployment Optimization",
                        "description": "Efficient inference in production",
                        "diagram_type": "none",
                    }
                ],
            },
            {
                "topic_name": "BERT Pretraining",
                "slide_title": "BERT changed how models learn from unlabeled text data at scale",
                "severity": "moderate",
                "gap_concepts": [
                    {
                        "concept": "Masked Language Modeling",
                        "description": "Pre-training technique using masked token prediction",
                        "diagram_type": "none",
                    }
                ],
            },
        ],
    })


@pytest.fixture
def valid_ppt_single() -> str:
    """Valid single-topic PPT JSON string with all structural checks passing."""
    return _make_ppt_single()


@pytest.fixture
def valid_ppt_full() -> str:
    """Valid full-presentation PPT JSON with executive_summary and 2 topic_slides."""
    return _make_ppt_full()
