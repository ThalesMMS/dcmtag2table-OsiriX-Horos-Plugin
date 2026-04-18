"""Tests for dcmtag2table.inspection"""
import os
from unittest.mock import MagicMock, patch

import pydicom
import pytest
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence

from dcmtag2table.inspection import (
    dump_unique_values,
    dump_unique_values_parallel,
    extract_tags_from_file,
    iterate_dicom_tags,
    process_element,
    save_set_to_file,
)


# ---------------------------------------------------------------------------
# process_element
# ---------------------------------------------------------------------------

def test_process_element_non_sq_adds_value_to_set():
    ds = Dataset()
    ds.PatientID = "TEST123"
    element = ds["PatientID"]
    tag_values = set()
    process_element(element, tag_values)
    assert "TEST123" in tag_values


def test_process_element_sq_processes_sub_elements():
    """SQ element must be recursed into, and sub-element values added."""
    sub_ds = Dataset()
    sub_ds.PatientID = "SUB001"

    sq_ds = Dataset()
    # Create a Sequence with one item
    sq_ds.ReferencedStudySequence = Sequence([sub_ds])

    element = sq_ds["ReferencedStudySequence"]
    tag_values = set()
    process_element(element, tag_values)
    assert "SUB001" in tag_values


def test_process_element_sq_removes_pixel_data_from_items():
    """PixelData inside a sequence item should be deleted before processing."""
    sub_ds = Dataset()
    sub_ds.PatientID = "P001"
    sub_ds.PixelData = b"\x00\x01"  # raw bytes to avoid full DICOM structure

    sq_ds = Dataset()
    sq_ds.ReferencedStudySequence = Sequence([sub_ds])

    element = sq_ds["ReferencedStudySequence"]
    tag_values = set()
    # Should not raise, and PixelData bytes should not appear
    process_element(element, tag_values)
    # PixelData value ("\x00\x01") should NOT be in the result
    assert b"\x00\x01" not in {v.encode() if isinstance(v, str) else v for v in tag_values}


# ---------------------------------------------------------------------------
# save_set_to_file
# ---------------------------------------------------------------------------

def test_save_set_to_file_writes_each_item_on_new_line(tmp_path):
    output_file = str(tmp_path / "output.txt")
    data = ["alpha", "beta", "gamma"]
    save_set_to_file(data, output_file)

    with open(output_file) as f:
        lines = f.read().splitlines()

    assert lines == ["alpha", "beta", "gamma"]


def test_save_set_to_file_empty_iterable_creates_empty_file(tmp_path):
    output_file = str(tmp_path / "empty.txt")
    save_set_to_file([], output_file)
    assert os.path.exists(output_file)
    with open(output_file) as f:
        assert f.read() == ""


def test_save_set_to_file_overwrites_existing_file(tmp_path):
    output_file = str(tmp_path / "output.txt")
    # Write initial content
    with open(output_file, "w") as f:
        f.write("old content\n")

    save_set_to_file(["new"], output_file)
    with open(output_file) as f:
        content = f.read()

    assert "old content" not in content
    assert "new" in content


# ---------------------------------------------------------------------------
# iterate_dicom_tags
# ---------------------------------------------------------------------------

def test_iterate_dicom_tags_with_empty_list_returns_empty_set():
    result = iterate_dicom_tags([])
    assert isinstance(result, set)
    assert len(result) == 0


def test_iterate_dicom_tags_with_real_dicom_file(minimal_dicom_file):
    result = iterate_dicom_tags([minimal_dicom_file])
    assert isinstance(result, set)
    # Should at least contain the PatientID value from the fixture
    assert "P001" in result


def test_iterate_dicom_tags_returns_set_not_list(minimal_dicom_file):
    result = iterate_dicom_tags([minimal_dicom_file])
    assert isinstance(result, set)


def test_iterate_dicom_tags_pixel_data_excluded(minimal_dicom_file):
    """PixelData bytes should NOT appear in the tag values set."""
    result = iterate_dicom_tags([minimal_dicom_file])
    # PixelData appears as bytes; confirm no raw bytes in the set of string values
    for value in result:
        assert not value.startswith("b'\\x")


def test_iterate_dicom_tags_multiple_files_union(dicom_dir_with_files):
    f1 = os.path.join(dicom_dir_with_files, "file1.dcm")
    f2 = os.path.join(dicom_dir_with_files, "file2.dcm")

    result = iterate_dicom_tags([f1, f2])
    assert "P001" in result
    assert "P002" in result


# ---------------------------------------------------------------------------
# extract_tags_from_file
# ---------------------------------------------------------------------------

def test_extract_tags_from_file_returns_empty_set_for_nonexistent_file():
    result = extract_tags_from_file("/nonexistent/path/that/does/not/exist.dcm")
    assert isinstance(result, set)
    assert len(result) == 0


def test_extract_tags_from_file_returns_set_for_valid_dicom(minimal_dicom_file):
    result = extract_tags_from_file(minimal_dicom_file)
    assert isinstance(result, set)
    assert len(result) > 0


def test_extract_tags_from_file_contains_known_values(minimal_dicom_file):
    result = extract_tags_from_file(minimal_dicom_file)
    # PatientID "P001" must appear in the tag values
    assert "P001" in result


def test_extract_tags_from_file_does_not_raise_on_non_dicom(tmp_path):
    bad_file = tmp_path / "not_a_dicom.txt"
    bad_file.write_text("this is not a DICOM file")
    # Must not raise, just return empty set
    result = extract_tags_from_file(str(bad_file))
    assert isinstance(result, set)


# ---------------------------------------------------------------------------
# dump_unique_values (orchestration - mocked internals)
# ---------------------------------------------------------------------------

def test_dump_unique_values_writes_sorted_output(tmp_path, monkeypatch):
    from dcmtag2table import inspection

    output_file = str(tmp_path / "unique.txt")
    monkeypatch.setattr(
        inspection, "list_files_in_directory", lambda d: {"/fake/file.dcm"}
    )
    monkeypatch.setattr(
        inspection, "iterate_dicom_tags", lambda paths: {"zebra", "apple", "mango"}
    )

    dump_unique_values(str(tmp_path), output_file)

    with open(output_file) as f:
        lines = f.read().splitlines()

    assert lines == sorted(["zebra", "apple", "mango"])


# ---------------------------------------------------------------------------
# dump_unique_values_parallel (orchestration - mocked internals)
# ---------------------------------------------------------------------------

def test_dump_unique_values_parallel_writes_sorted_output(tmp_path, monkeypatch):
    from dcmtag2table import inspection

    output_file = str(tmp_path / "parallel_unique.txt")
    monkeypatch.setattr(
        inspection,
        "list_files_in_directory",
        lambda d: {"/fake/file1.dcm", "/fake/file2.dcm"},
    )

    # Patch ProcessPoolExecutor.map to return known tag sets
    class FakeExecutor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def map(self, fn, iterable):
            return [{"zebra", "apple"}, {"mango"}]

    import concurrent.futures

    monkeypatch.setattr(inspection, "ProcessPoolExecutor", lambda **_kwargs: FakeExecutor())

    dump_unique_values_parallel(str(tmp_path), output_file, max_workers=1)

    with open(output_file) as f:
        lines = f.read().splitlines()

    assert lines == sorted(["zebra", "apple", "mango"])
