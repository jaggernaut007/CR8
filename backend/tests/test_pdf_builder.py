import os
from backend.services.pdf_builder import build_pdf


def test_generates_valid_pdf(tmp_path):
    output = str(tmp_path / "test.pdf")
    topics = [
        {"name": "Word Vectors", "description": "Dense word representations"},
        {"name": "Transformers", "description": "Self-attention architecture"},
    ]
    modules = [
        "## Learning Objectives\n- Understand word vectors\n\n## Core Content\nWord vectors map words to dense vectors.\n\n## Industry Context\nUsed in search and NLP.\n\n## Key Takeaways\n- Dense representations\n\n## Further Reading\n- [Example](https://example.com)",
        "## Learning Objectives\n- Understand self-attention\n\n## Core Content\nTransformers use attention.\n\n## Industry Context\nFoundation of modern LLMs.\n\n## Key Takeaways\n- Attention is all you need\n\n## Further Reading\n- [Example](https://example.com)",
    ]
    build_pdf("Test Guide", topics, modules, output)

    assert os.path.exists(output)
    assert os.path.getsize(output) > 1000

    # Verify it starts with PDF magic bytes
    with open(output, "rb") as f:
        assert f.read(5) == b"%PDF-"
