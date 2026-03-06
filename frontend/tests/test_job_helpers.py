"""Unit tests for helper functions in frontend/job_routes.py.

Covers:
- _collect_output_files() — various result dicts (no files, pdf only, ppt only,
  video dir with scripts and mp4s, nonexistent paths)
- _zip_directory() — creates valid ZIP, extension filter, nested structure
- _resolve_artifact() — pdf, ppt, scripts, videos, missing paths, unknown type
"""

import os
import zipfile

from frontend.job_routes import _collect_output_files, _resolve_artifact, _zip_directory


# Collect output files tests


class TestCollectOutputFiles:

    def test_empty_result_returns_empty_list(self):
        files = _collect_output_files({})
        assert files == []

    def test_pdf_path_empty_string_skipped(self):
        files = _collect_output_files({"pdf_path": "", "video_dir": ""})
        assert files == []

    def test_nonexistent_pdf_path_skipped(self):
        files = _collect_output_files({"pdf_path": "/no/such/file.pdf", "video_dir": ""})
        assert files == []

    def test_existing_pdf_path_included(self, tmp_path):
        pdf = tmp_path / "guide.pdf"
        pdf.write_bytes(b"%PDF-1.0 content")
        files = _collect_output_files({"pdf_path": str(pdf), "video_dir": ""})
        assert len(files) == 1

    def test_existing_pdf_has_correct_type(self, tmp_path):
        pdf = tmp_path / "guide.pdf"
        pdf.write_bytes(b"%PDF-1.0 content")
        files = _collect_output_files({"pdf_path": str(pdf), "video_dir": ""})
        assert files[0]["type"] == "pdf"

    def test_existing_pdf_has_correct_name(self, tmp_path):
        pdf = tmp_path / "guide.pdf"
        pdf.write_bytes(b"%PDF-1.0 content")
        files = _collect_output_files({"pdf_path": str(pdf), "video_dir": ""})
        assert files[0]["name"] == "guide.pdf"

    def test_existing_pdf_has_correct_size(self, tmp_path):
        pdf = tmp_path / "guide.pdf"
        pdf.write_bytes(b"%PDF-1.0 content")
        files = _collect_output_files({"pdf_path": str(pdf), "video_dir": ""})
        assert files[0]["size"] == pdf.stat().st_size

    def test_nonexistent_ppt_path_skipped(self, tmp_path):
        pdf = tmp_path / "guide.pdf"
        pdf.write_bytes(b"%PDF-1.0 content")
        files = _collect_output_files({
            "pdf_path": str(pdf),
            "ppt_path": "/no/such/file.pptx",
            "video_dir": "",
        })
        types = [f["type"] for f in files]
        assert "ppt" not in types

    def test_existing_ppt_included(self, tmp_path):
        ppt = tmp_path / "slides.pptx"
        ppt.write_bytes(b"PK fake pptx")
        files = _collect_output_files({"pdf_path": "", "ppt_path": str(ppt), "video_dir": ""})
        assert any(f["type"] == "ppt" for f in files)

    def test_existing_ppt_has_correct_name(self, tmp_path):
        ppt = tmp_path / "slides.pptx"
        ppt.write_bytes(b"PK fake pptx")
        files = _collect_output_files({"pdf_path": "", "ppt_path": str(ppt), "video_dir": ""})
        ppt_entry = next(f for f in files if f["type"] == "ppt")
        assert ppt_entry["name"] == "slides.pptx"

    def test_scripts_dir_with_files_produces_scripts_entry(self, tmp_path):
        video_dir = tmp_path / "videos"
        scripts_dir = video_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "01_Topic.txt").write_text("Script content")
        files = _collect_output_files({"pdf_path": "", "video_dir": str(video_dir)})
        assert any(f["type"] == "scripts" for f in files)

    def test_empty_scripts_dir_skipped(self, tmp_path):
        video_dir = tmp_path / "videos"
        scripts_dir = video_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        files = _collect_output_files({"pdf_path": "", "video_dir": str(video_dir)})
        assert not any(f["type"] == "scripts" for f in files)

    def test_mp4_files_produce_videos_entry(self, tmp_path):
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        (video_dir / "01_Topic.mp4").write_bytes(b"\x00\x00\x00 ftyp")
        files = _collect_output_files({"pdf_path": "", "video_dir": str(video_dir)})
        assert any(f["type"] == "videos" for f in files)

    def test_no_mp4_files_skips_videos_entry(self, tmp_path):
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        files = _collect_output_files({"pdf_path": "", "video_dir": str(video_dir)})
        assert not any(f["type"] == "videos" for f in files)

    def test_full_result_includes_all_types(self, tmp_path):
        pdf = tmp_path / "guide.pdf"
        pdf.write_bytes(b"%PDF-1.0 content")
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        (video_dir / "01.mp4").write_bytes(b"\x00\x00\x00 ftyp")
        scripts_dir = video_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "01.txt").write_text("script")
        files = _collect_output_files({
            "pdf_path": str(pdf),
            "video_dir": str(video_dir),
        })
        types = {f["type"] for f in files}
        assert "pdf" in types
        assert "scripts" in types
        assert "videos" in types

    def test_scripts_entry_name_is_zip(self, tmp_path):
        video_dir = tmp_path / "videos"
        scripts_dir = video_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "01.txt").write_text("content")
        files = _collect_output_files({"pdf_path": "", "video_dir": str(video_dir)})
        scripts_entry = next(f for f in files if f["type"] == "scripts")
        assert scripts_entry["name"] == "video_scripts.zip"

    def test_videos_entry_name_is_zip(self, tmp_path):
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        (video_dir / "01.mp4").write_bytes(b"\x00\x00\x00 ftyp")
        files = _collect_output_files({"pdf_path": "", "video_dir": str(video_dir)})
        videos_entry = next(f for f in files if f["type"] == "videos")
        assert videos_entry["name"] == "videos.zip"



# Zip directory tests


class TestZipDirectory:

    def test_creates_zip_file(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "file.txt").write_text("hello")
        zip_path = str(tmp_path / "out.zip")
        _zip_directory(str(src), zip_path)
        assert os.path.exists(zip_path)

    def test_zip_contains_all_files(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.txt").write_text("aaa")
        (src / "b.txt").write_text("bbb")
        zip_path = str(tmp_path / "out.zip")
        _zip_directory(str(src), zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        assert "a.txt" in names
        assert "b.txt" in names

    def test_extension_filter_includes_only_matching_files(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "video.mp4").write_bytes(b"\x00\x00\x00 ftyp")
        (src / "notes.txt").write_text("notes")
        zip_path = str(tmp_path / "out.zip")
        _zip_directory(str(src), zip_path, extension=".mp4")
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        assert "video.mp4" in names
        assert "notes.txt" not in names

    def test_no_extension_filter_includes_all_files(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "video.mp4").write_bytes(b"\x00\x00\x00 ftyp")
        (src / "notes.txt").write_text("notes")
        zip_path = str(tmp_path / "out.zip")
        _zip_directory(str(src), zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        assert "video.mp4" in names
        assert "notes.txt" in names

    def test_nested_directories_are_included(self, tmp_path):
        src = tmp_path / "src"
        sub = src / "sub"
        sub.mkdir(parents=True)
        (sub / "deep.txt").write_text("deep")
        zip_path = str(tmp_path / "out.zip")
        _zip_directory(str(src), zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        assert any("deep.txt" in n for n in names)

    def test_zip_is_valid_zip_format(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "f.txt").write_text("content")
        zip_path = str(tmp_path / "out.zip")
        _zip_directory(str(src), zip_path)
        assert zipfile.is_zipfile(zip_path)

    def test_empty_directory_creates_empty_zip(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        zip_path = str(tmp_path / "out.zip")
        _zip_directory(str(src), zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            assert zf.namelist() == []

    def test_relative_paths_used_in_archive(self, tmp_path):
        """Archived file paths must be relative to the source directory."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "file.txt").write_text("data")
        zip_path = str(tmp_path / "out.zip")
        _zip_directory(str(src), zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        # Must not contain the absolute path prefix
        assert all(not n.startswith("/") for n in names)



# Resolve artifact tests


class TestResolveArtifact:

    def test_pdf_existing_returns_file_response(self, tmp_path):
        pdf = tmp_path / "guide.pdf"
        pdf.write_bytes(b"%PDF-1.0 content")
        result = {"pdf_path": str(pdf), "video_dir": ""}
        resp = _resolve_artifact(result, "pdf")
        assert resp is not None

    def test_pdf_nonexistent_returns_none(self):
        result = {"pdf_path": "/no/such/file.pdf", "video_dir": ""}
        assert _resolve_artifact(result, "pdf") is None

    def test_pdf_empty_path_returns_none(self):
        result = {"pdf_path": "", "video_dir": ""}
        assert _resolve_artifact(result, "pdf") is None

    def test_pdf_missing_key_returns_none(self):
        assert _resolve_artifact({}, "pdf") is None

    def test_ppt_existing_returns_file_response(self, tmp_path):
        ppt = tmp_path / "slides.pptx"
        ppt.write_bytes(b"PK fake")
        result = {"ppt_path": str(ppt), "pdf_path": "", "video_dir": ""}
        resp = _resolve_artifact(result, "ppt")
        assert resp is not None

    def test_ppt_nonexistent_returns_none(self):
        result = {"ppt_path": "/no/such/slides.pptx", "pdf_path": "", "video_dir": ""}
        assert _resolve_artifact(result, "ppt") is None

    def test_ppt_empty_path_returns_none(self):
        result = {"ppt_path": "", "pdf_path": "", "video_dir": ""}
        assert _resolve_artifact(result, "ppt") is None

    def test_scripts_existing_dir_returns_file_response(self, tmp_path):
        video_dir = tmp_path / "videos"
        scripts_dir = video_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "01.txt").write_text("script content")
        result = {"pdf_path": "", "video_dir": str(video_dir)}
        resp = _resolve_artifact(result, "scripts")
        assert resp is not None

    def test_scripts_creates_zip_file(self, tmp_path):
        video_dir = tmp_path / "videos"
        scripts_dir = video_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "01.txt").write_text("script content")
        result = {"pdf_path": "", "video_dir": str(video_dir)}
        _resolve_artifact(result, "scripts")
        zip_path = str(scripts_dir).rstrip("/") + ".zip"
        assert os.path.exists(zip_path)

    def test_scripts_missing_dir_returns_none(self, tmp_path):
        result = {"pdf_path": "", "video_dir": str(tmp_path / "no_such_dir")}
        assert _resolve_artifact(result, "scripts") is None

    def test_scripts_empty_video_dir_string_returns_none(self):
        result = {"pdf_path": "", "video_dir": ""}
        assert _resolve_artifact(result, "scripts") is None

    def test_videos_existing_dir_returns_file_response(self, tmp_path):
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        (video_dir / "01.mp4").write_bytes(b"\x00\x00\x00 ftyp")
        result = {"pdf_path": "", "video_dir": str(video_dir)}
        resp = _resolve_artifact(result, "videos")
        assert resp is not None

    def test_videos_creates_zip_file(self, tmp_path):
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        (video_dir / "01.mp4").write_bytes(b"\x00\x00\x00 ftyp")
        result = {"pdf_path": "", "video_dir": str(video_dir)}
        _resolve_artifact(result, "videos")
        zip_path = str(video_dir).rstrip("/") + "_videos.zip"
        assert os.path.exists(zip_path)

    def test_videos_missing_dir_returns_none(self):
        result = {"pdf_path": "", "video_dir": "/no/such/dir"}
        assert _resolve_artifact(result, "videos") is None

    def test_unknown_file_type_returns_none(self, tmp_path):
        pdf = tmp_path / "guide.pdf"
        pdf.write_bytes(b"%PDF-1.0 content")
        result = {"pdf_path": str(pdf), "video_dir": ""}
        assert _resolve_artifact(result, "unknown") is None

    def test_pdf_response_filename_matches_basename(self, tmp_path):
        pdf = tmp_path / "my_guide.pdf"
        pdf.write_bytes(b"%PDF-1.0 content")
        result = {"pdf_path": str(pdf), "video_dir": ""}
        resp = _resolve_artifact(result, "pdf")
        assert resp.filename == "my_guide.pdf"

    def test_scripts_response_filename_is_zip(self, tmp_path):
        video_dir = tmp_path / "videos"
        scripts_dir = video_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "01.txt").write_text("content")
        result = {"pdf_path": "", "video_dir": str(video_dir)}
        resp = _resolve_artifact(result, "scripts")
        assert resp.filename == "video_scripts.zip"

    def test_videos_response_filename_is_zip(self, tmp_path):
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        (video_dir / "01.mp4").write_bytes(b"\x00\x00\x00 ftyp")
        result = {"pdf_path": "", "video_dir": str(video_dir)}
        resp = _resolve_artifact(result, "videos")
        assert resp.filename == "videos.zip"
