import pandas as pd

from dcmtag2table import (
    dcmtag2table,
    dcmtag2table_from_file_list,
    dcmtag2table_parallel,
)
from dcmtag2table import readers as _readers_mod


class _SerialExecutor:
    """Drop-in replacement for ProcessPoolExecutor that runs tasks serially."""

    def __init__(self, max_workers=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def submit(self, fn, *args, **kwargs):
        import concurrent.futures
        fut = concurrent.futures.Future()
        try:
            result = fn(*args, **kwargs)
            fut.set_result(result)
        except Exception as exc:
            fut.set_exception(exc)
        return fut


def test_reader_functions_are_importable():
    assert callable(dcmtag2table)
    assert callable(dcmtag2table_parallel)
    assert callable(dcmtag2table_from_file_list)


def test_dcmtag2table_from_file_list_empty_returns_empty_dataframe(monkeypatch):
    monkeypatch.setattr(_readers_mod, "ProcessPoolExecutor", _SerialExecutor)
    list_of_tags = ["PatientID", "Modality"]

    df = dcmtag2table_from_file_list([], list_of_tags, max_workers=1)

    assert df.empty
    assert list(df.columns) == ["Filename", *list_of_tags]


def test_dcmtag2table_nonexistent_directory_returns_empty_dataframe(tmp_path):
    missing_dir = tmp_path / "does-not-exist"
    list_of_tags = ["PatientID", "Modality"]

    df = dcmtag2table(str(missing_dir), list_of_tags)

    assert df.empty
    assert list(df.columns) == ["Filename", *list_of_tags]


# ---------------------------------------------------------------------------
# dcmtag2table – with real DICOM files
# ---------------------------------------------------------------------------

def test_dcmtag2table_reads_real_dicom_file(minimal_dicom_file):
    import os
    folder = os.path.dirname(minimal_dicom_file)
    list_of_tags = ["PatientID", "Modality"]

    df = dcmtag2table(folder, list_of_tags)

    assert not df.empty
    assert list(df.columns) == ["Filename", "PatientID", "Modality"]
    assert "P001" in df["PatientID"].values


def test_dcmtag2table_missing_tag_fills_not_found(minimal_dicom_file):
    import os
    folder = os.path.dirname(minimal_dicom_file)
    list_of_tags = ["PatientID", "NonExistentTag9999"]

    df = dcmtag2table(folder, list_of_tags)

    assert "Not found" in df["NonExistentTag9999"].values


def test_dcmtag2table_does_not_mutate_input_list():
    original_tags = ["PatientID", "Modality"]
    tags_copy = list(original_tags)
    dcmtag2table("/nonexistent_dir", original_tags)
    assert original_tags == tags_copy


def test_dcmtag2table_skips_non_dicom_files(tmp_path):
    # Create a non-DICOM file in the directory
    bad_file = tmp_path / "not_dicom.txt"
    bad_file.write_text("not a dicom")
    list_of_tags = ["PatientID"]

    df = dcmtag2table(str(tmp_path), list_of_tags)

    # The non-DICOM file should be skipped and result in empty df
    assert df.empty or "not_dicom.txt" not in df.get("Filename", {}).values


def test_dcmtag2table_filename_in_output(minimal_dicom_file):
    import os
    folder = os.path.dirname(minimal_dicom_file)

    df = dcmtag2table(folder, ["Modality"])

    assert minimal_dicom_file in df["Filename"].values


# ---------------------------------------------------------------------------
# dcmtag2table_parallel – mocked to avoid ProcessPoolExecutor
# ---------------------------------------------------------------------------

def test_dcmtag2table_parallel_reads_dicom_via_mock(tmp_path, minimal_dicom_file, monkeypatch):
    import os
    folder = os.path.dirname(minimal_dicom_file)
    monkeypatch.setattr(_readers_mod, "ProcessPoolExecutor", _SerialExecutor)

    df = dcmtag2table_parallel(folder, ["PatientID", "Modality"], max_workers=1)

    assert not df.empty
    assert "P001" in df["PatientID"].values


def test_dcmtag2table_parallel_nonexistent_dir_returns_empty(tmp_path, monkeypatch):
    missing_dir = tmp_path / "does-not-exist"
    monkeypatch.setattr(_readers_mod, "ProcessPoolExecutor", _SerialExecutor)

    df = dcmtag2table_parallel(str(missing_dir), ["PatientID"], max_workers=1)

    assert df.empty


def test_dcmtag2table_parallel_output_sorted_by_filename(dicom_dir_with_files, monkeypatch):
    monkeypatch.setattr(_readers_mod, "ProcessPoolExecutor", _SerialExecutor)

    df = dcmtag2table_parallel(dicom_dir_with_files, ["Modality"], max_workers=1)

    filenames = list(df["Filename"])
    assert filenames == sorted(filenames)


def test_dcmtag2table_parallel_does_not_mutate_input_list(monkeypatch):
    monkeypatch.setattr(_readers_mod, "ProcessPoolExecutor", _SerialExecutor)
    original_tags = ["PatientID", "Modality"]
    tags_copy = list(original_tags)
    dcmtag2table_parallel("/nonexistent_dir", original_tags, max_workers=1)
    assert original_tags == tags_copy


# ---------------------------------------------------------------------------
# dcmtag2table_from_file_list – mocked to avoid ProcessPoolExecutor
# ---------------------------------------------------------------------------

def test_dcmtag2table_from_file_list_reads_dicom_via_mock(minimal_dicom_file, monkeypatch):
    monkeypatch.setattr(_readers_mod, "ProcessPoolExecutor", _SerialExecutor)
    list_of_tags = ["PatientID", "Modality"]

    df = dcmtag2table_from_file_list([minimal_dicom_file], list_of_tags, max_workers=1)

    assert not df.empty
    assert "P001" in df["PatientID"].values


def test_dcmtag2table_from_file_list_non_dicom_returns_not_found(tmp_path, monkeypatch):
    """pydicom with force=True reads any file; non-DICOM files get 'Not found' for all tags."""
    monkeypatch.setattr(_readers_mod, "ProcessPoolExecutor", _SerialExecutor)
    bad_file = tmp_path / "bad.txt"
    bad_file.write_text("not dicom")

    df = dcmtag2table_from_file_list([str(bad_file)], ["PatientID"], max_workers=1)

    # With force=True, pydicom reads the file but DICOM tags won't be present
    if not df.empty:
        assert df["PatientID"].iloc[0] == "Not found"


def test_dcmtag2table_from_file_list_output_sorted(tmp_path, monkeypatch):
    from dcmtag2table.tests.conftest import _make_minimal_dicom
    from pydicom.uid import generate_uid

    monkeypatch.setattr(_readers_mod, "ProcessPoolExecutor", _SerialExecutor)

    f1 = _make_minimal_dicom(tmp_path, filename="z_file.dcm", patient_id="P001",
                              study_uid=generate_uid(), series_uid=generate_uid(),
                              sop_uid=generate_uid())
    f2 = _make_minimal_dicom(tmp_path, filename="a_file.dcm", patient_id="P002",
                              study_uid=generate_uid(), series_uid=generate_uid(),
                              sop_uid=generate_uid())

    df = dcmtag2table_from_file_list([f1, f2], ["PatientID"], max_workers=1)

    filenames = list(df["Filename"])
    assert filenames == sorted(filenames)


def test_dcmtag2table_from_file_list_does_not_mutate_input_list(monkeypatch):
    monkeypatch.setattr(_readers_mod, "ProcessPoolExecutor", _SerialExecutor)
    original_tags = ["PatientID", "Modality"]
    tags_copy = list(original_tags)
    dcmtag2table_from_file_list([], original_tags, max_workers=1)
    assert original_tags == tags_copy


def test_dcmtag2table_from_file_list_empty_with_mock(monkeypatch):
    """dcmtag2table_from_file_list with an empty list must return empty df with correct columns."""
    monkeypatch.setattr(_readers_mod, "ProcessPoolExecutor", _SerialExecutor)
    list_of_tags = ["PatientID", "Modality"]

    df = dcmtag2table_from_file_list([], list_of_tags, max_workers=1)

    assert df.empty
    assert list(df.columns) == ["Filename", *list_of_tags]


def test_dcmtag2table_from_file_list_skips_worker_exception(monkeypatch):
    monkeypatch.setattr(_readers_mod, "ProcessPoolExecutor", _SerialExecutor)

    def fake_read(filepath, list_of_tags):
        if filepath == "bad.dcm":
            raise RuntimeError("worker failed")
        return [filepath, "P001"]

    monkeypatch.setattr(_readers_mod, "_read_dicom_tags", fake_read)

    df = dcmtag2table_from_file_list(["bad.dcm", "good.dcm"], ["PatientID"], max_workers=1)

    assert list(df["Filename"]) == ["good.dcm"]
    assert list(df["PatientID"]) == ["P001"]


def test_read_dicom_tags_restores_pydicom_validation(monkeypatch):
    original = _readers_mod.pydicom.config.enforce_valid_values
    seen_values = []

    def fake_dcmread(*args, **kwargs):
        seen_values.append(_readers_mod.pydicom.config.enforce_valid_values)
        raise RuntimeError("read failed")

    monkeypatch.setattr(_readers_mod.pydicom, "dcmread", fake_dcmread)
    _readers_mod.pydicom.config.enforce_valid_values = True
    try:
        assert _readers_mod._read_dicom_tags("broken.dcm", []) is None
        assert seen_values == [False]
        assert _readers_mod.pydicom.config.enforce_valid_values is True
    finally:
        _readers_mod.pydicom.config.enforce_valid_values = original
