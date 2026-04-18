import hashlib
import hmac

import pandas as pd
import pytest

from dcmtag2table import writers
from dcmtag2table.writers import _PHI_DICOM_TAGS
from dcmtag2table.writers import DEFAULT_ANON_BIRTH_DATE, DEFAULT_ANON_STUDY_DATE
from dcmtag2table.writers import DEFAULT_MAX_WORKERS, DEFAULT_UID_PREFIX, LOG_TOKEN_SECRET_ENV


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

def test_anon_birth_date_constant():
    assert DEFAULT_ANON_BIRTH_DATE == "19190828"


def test_anon_study_date_constant():
    assert DEFAULT_ANON_STUDY_DATE == "20250228"


def test_get_anon_dates_uses_default_values(monkeypatch):
    monkeypatch.delenv("ANON_BIRTH_DATE", raising=False)
    monkeypatch.delenv("ANON_STUDY_DATE", raising=False)
    monkeypatch.setattr(writers, "_ANON_DATES", None)

    assert writers._get_anon_dates() == (DEFAULT_ANON_BIRTH_DATE, DEFAULT_ANON_STUDY_DATE)


def test_invalid_anon_date_raises_when_writer_api_is_used(monkeypatch):
    monkeypatch.setenv("ANON_BIRTH_DATE", "bad-date")
    monkeypatch.setattr(writers, "_ANON_DATES", None)

    with pytest.raises(ValueError, match="ANON_BIRTH_DATE"):
        writers.allow_list("in", "out", [])


def test_default_max_workers_matches_writer_entry_points():
    import inspect

    assert inspect.signature(writers.allow_list).parameters["max_workers"].default == DEFAULT_MAX_WORKERS
    assert (
        inspect.signature(writers.allow_list_parallel).parameters["max_workers"].default
        == DEFAULT_MAX_WORKERS
    )


def test_phi_dicom_tags_is_a_list():
    assert isinstance(_PHI_DICOM_TAGS, list)


def test_phi_dicom_tags_contains_required_phi_fields():
    required = [
        "PatientID",
        "PatientName",
        "PatientBirthDate",
        "StudyInstanceUID",
        "SeriesInstanceUID",
        "SOPInstanceUID",
        "AccessionNumber",
        "StudyID",
    ]
    for tag in required:
        assert tag in _PHI_DICOM_TAGS, f"Expected '{tag}' in _PHI_DICOM_TAGS"


def test_phi_dicom_tags_no_duplicates():
    assert len(_PHI_DICOM_TAGS) == len(set(_PHI_DICOM_TAGS))


def test_phi_dicom_tags_all_strings():
    assert all(isinstance(t, str) for t in _PHI_DICOM_TAGS)


def test_path_token_uses_configured_hmac_secret(monkeypatch):
    monkeypatch.setenv(LOG_TOKEN_SECRET_ENV, "test-secret")
    expected = hmac.new(b"test-secret", b"/phi/path.dcm", hashlib.sha256).hexdigest()[:8]

    assert writers._path_token("/phi/path.dcm") == expected
    assert writers._path_token("/phi/path.dcm") != hashlib.sha256(b"/phi/path.dcm").hexdigest()[:8]


# ---------------------------------------------------------------------------
# allow_list
# ---------------------------------------------------------------------------

def test_allow_list_forwards_max_workers(monkeypatch):
    calls = {}

    def fake_dcmtag2table_parallel(in_path, tags, max_workers):
        calls["reader_max_workers"] = max_workers
        return pd.DataFrame(columns=["Filename"])

    monkeypatch.setattr(writers, "dcmtag2table_parallel", fake_dcmtag2table_parallel)
    monkeypatch.setattr(writers, "replace_ids_parallel_joblib", lambda df, **kwargs: df)

    writers.allow_list("in", "out", [], max_workers=5)

    assert calls["reader_max_workers"] == 5


def test_allow_list_returns_dataframe(monkeypatch):
    """allow_list must return the DataFrame produced by replace_ids_parallel_joblib."""
    # Use an empty DataFrame so allow_list skips per-row iteration (no DICOM reads needed)
    expected_df = pd.DataFrame(columns=["Filename"])

    monkeypatch.setattr(
        writers, "dcmtag2table_parallel", lambda *a, **kw: pd.DataFrame(columns=["Filename"])
    )
    monkeypatch.setattr(writers, "replace_ids_parallel_joblib", lambda df, **kw: expected_df)

    result = writers.allow_list("in", "out", [])
    assert result is expected_df


def test_allow_list_reads_phi_tags(monkeypatch):
    """allow_list must read exactly _PHI_DICOM_TAGS from the input directory."""
    captured_tags = []

    def fake_parallel(in_path, tags, max_workers):
        captured_tags.extend(tags)
        return pd.DataFrame(columns=["Filename"])

    monkeypatch.setattr(writers, "dcmtag2table_parallel", fake_parallel)
    monkeypatch.setattr(writers, "replace_ids_parallel_joblib", lambda df, **kw: df)

    writers.allow_list("in", "out", [])

    assert captured_tags == _PHI_DICOM_TAGS


def test_allow_list_uses_default_uid_prefix(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        writers, "dcmtag2table_parallel", lambda *a, **kw: pd.DataFrame(columns=["Filename"])
    )

    def fake_replace(df, prefix, **kw):
        captured["prefix"] = prefix
        return df

    monkeypatch.setattr(writers, "replace_ids_parallel_joblib", fake_replace)

    writers.allow_list("in", "out", [])
    assert captured["prefix"] == DEFAULT_UID_PREFIX


def test_allow_list_accepts_uid_prefix(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        writers, "dcmtag2table_parallel", lambda *a, **kw: pd.DataFrame(columns=["Filename"])
    )

    def fake_replace(df, prefix, **kw):
        captured["prefix"] = prefix
        return df

    monkeypatch.setattr(writers, "replace_ids_parallel_joblib", fake_replace)

    writers.allow_list("in", "out", [], uid_prefix="1.2.826.0.1.")
    assert captured["prefix"] == "1.2.826.0.1."


def test_allow_list_logs_and_continues_on_save_failure(tmp_path, monkeypatch, caplog):
    df = pd.DataFrame(
        {"Filename": ["input.dcm"], "fake_PatientID": [1], "fake_AccessionNumber": [1]}
    )

    class FakeDataset:
        StudyID = "000001"
        SOPInstanceUID = "1.2.840.999.3"

        def save_as(self, path):
            raise OSError("disk full")

    monkeypatch.setattr(writers, "dcmtag2table_parallel", lambda *a, **kw: df)
    monkeypatch.setattr(writers, "replace_ids_parallel_joblib", lambda data, **kw: data)
    monkeypatch.setattr(writers.pydicom, "dcmread", lambda *a, **kw: object())
    monkeypatch.setattr(writers, "_build_anonymized_dataset", lambda *a, **kw: FakeDataset())

    with caplog.at_level("WARNING", logger="dcmtag2table.writers"):
        result = writers.allow_list("in", str(tmp_path / "out"), [])

    assert result is df
    assert "Failed to save DICOM" in caplog.text
    assert "study_id=000001" in caplog.text
    assert "sop_instance_uid_hash=" in caplog.text
    assert "1.2.840.999.3" not in caplog.text


# ---------------------------------------------------------------------------
# allow_list_parallel
# ---------------------------------------------------------------------------

def test_allow_list_parallel_forwards_max_workers(monkeypatch):
    calls = {}

    def fake_dcmtag2table_parallel(in_path, tags, max_workers):
        calls["reader_max_workers"] = max_workers
        return pd.DataFrame(columns=["Filename"])

    class FakeParallel:
        def __init__(self, n_jobs):
            calls["writer_max_workers"] = n_jobs

        def __call__(self, tasks):
            list(tasks)

    monkeypatch.setattr(writers, "dcmtag2table_parallel", fake_dcmtag2table_parallel)
    monkeypatch.setattr(writers, "replace_ids_parallel_joblib", lambda df, **kwargs: df)
    monkeypatch.setattr(writers, "Parallel", FakeParallel)

    writers.allow_list_parallel("in", "out", [], max_workers=3)

    assert calls["reader_max_workers"] == 3
    assert calls["writer_max_workers"] == 3


def test_allow_list_parallel_returns_dataframe(monkeypatch):
    expected_df = pd.DataFrame({"Filename": ["a.dcm"]})

    monkeypatch.setattr(
        writers, "dcmtag2table_parallel", lambda *a, **kw: pd.DataFrame(columns=["Filename"])
    )
    monkeypatch.setattr(writers, "replace_ids_parallel_joblib", lambda df, **kw: expected_df)

    class FakeParallel:
        def __init__(self, n_jobs):
            pass

        def __call__(self, tasks):
            list(tasks)

    monkeypatch.setattr(writers, "Parallel", FakeParallel)

    result = writers.allow_list_parallel("in", "out", [])
    assert result is expected_df


def test_allow_list_parallel_reads_phi_tags(monkeypatch):
    captured_tags = []
    captured = {}

    def fake_parallel(in_path, tags, max_workers):
        captured_tags.extend(tags)
        return pd.DataFrame(columns=["Filename"])

    def fake_replace(df, prefix, **kw):
        captured["prefix"] = prefix
        return df

    monkeypatch.setattr(writers, "dcmtag2table_parallel", fake_parallel)
    monkeypatch.setattr(writers, "replace_ids_parallel_joblib", fake_replace)

    class FakeParallel:
        def __init__(self, n_jobs):
            pass

        def __call__(self, tasks):
            list(tasks)

    monkeypatch.setattr(writers, "Parallel", FakeParallel)

    writers.allow_list_parallel("in", "out", [])

    assert captured_tags == _PHI_DICOM_TAGS
    assert captured["prefix"] == DEFAULT_UID_PREFIX


def test_allow_list_parallel_accepts_uid_prefix(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        writers, "dcmtag2table_parallel", lambda *a, **kw: pd.DataFrame(columns=["Filename"])
    )

    def fake_replace(df, prefix, **kw):
        captured["prefix"] = prefix
        return df

    monkeypatch.setattr(writers, "replace_ids_parallel_joblib", fake_replace)

    class FakeParallel:
        def __init__(self, n_jobs):
            pass

        def __call__(self, tasks):
            list(tasks)

    monkeypatch.setattr(writers, "Parallel", FakeParallel)

    writers.allow_list_parallel("in", "out", [], uid_prefix="1.2.826.0.1.")
    assert captured["prefix"] == "1.2.826.0.1."


# ---------------------------------------------------------------------------
# _process_single_row - unit tests
# ---------------------------------------------------------------------------

def test_process_single_row_skips_unreadable_file(tmp_path, caplog):
    from dcmtag2table.writers import _process_single_row

    bad_file = tmp_path / "missing.dcm"
    out_dir = tmp_path / "out"
    row = {
        "Filename": str(bad_file),
        "fake_PatientID": 1,
        "fake_AccessionNumber": 1,
        "fake_StudyInstanceUID": "1.2.3",
        "fake_SeriesInstanceUID": "1.2.4",
        "fake_SOPInstanceUID": "1.2.5",
    }
    with caplog.at_level("WARNING", logger="dcmtag2table.writers"):
        _process_single_row(0, row, str(out_dir), [])

    assert not out_dir.exists() or not any(out_dir.rglob("*"))
    assert "Failed to read DICOM" in caplog.text


def test_process_single_row_skips_invalid_dicom_error(tmp_path, monkeypatch, caplog):
    from pydicom.errors import InvalidDicomError
    from dcmtag2table.writers import _process_single_row

    def raise_invalid_dicom(*args, **kwargs):
        raise InvalidDicomError("malformed")

    monkeypatch.setattr(writers.pydicom, "dcmread", raise_invalid_dicom)
    row = {
        "Filename": str(tmp_path / "bad.dcm"),
        "fake_PatientID": 1,
        "fake_AccessionNumber": 1,
        "fake_StudyInstanceUID": "1.2.3",
        "fake_SeriesInstanceUID": "1.2.4",
        "fake_SOPInstanceUID": "1.2.5",
    }

    with caplog.at_level("WARNING", logger="dcmtag2table.writers"):
        _process_single_row(0, row, str(tmp_path / "out"), [])

    assert "Failed to read DICOM" in caplog.text


def test_process_single_row_skips_invalid_fake_ids(tmp_path, minimal_dicom_file, caplog):
    from dcmtag2table.writers import _process_single_row

    out_dir = tmp_path / "output"
    row = {
        "Filename": minimal_dicom_file,
        "fake_PatientID": "not-a-number",
        "fake_AccessionNumber": 1,
        "fake_StudyInstanceUID": "1.2.840.999.1",
        "fake_SeriesInstanceUID": "1.2.840.999.2",
        "fake_SOPInstanceUID": "1.2.840.999.3",
    }

    with caplog.at_level("WARNING", logger="dcmtag2table.writers"):
        _process_single_row(0, row, str(out_dir), [])

    assert not out_dir.exists() or not any(out_dir.rglob("*"))
    assert "Invalid fake ID values" in caplog.text


def test_process_single_row_writes_output_dicom(tmp_path, minimal_dicom_file):
    from dcmtag2table.writers import _process_single_row

    out_dir = tmp_path / "output"
    out_dir.mkdir()
    row = {
        "Filename": minimal_dicom_file,
        "fake_PatientID": 42,
        "fake_AccessionNumber": 7,
        "fake_StudyInstanceUID": "1.2.840.999.1",
        "fake_SeriesInstanceUID": "1.2.840.999.2",
        "fake_SOPInstanceUID": "1.2.840.999.3",
        "PatientSex": "M",
        "PatientAge": "045Y",
    }
    _process_single_row(0, row, str(out_dir), [])

    expected_path = out_dir / "000007" / "1.2.840.999.3.dcm"
    assert expected_path.exists(), f"Expected output DICOM at {expected_path}"


def test_build_anonymized_dataset_skips_sequence_tags(caplog):
    from pydicom import Dataset
    from pydicom.dataset import FileMetaDataset
    from pydicom.sequence import Sequence

    nested = Dataset()
    nested.PatientName = "Original^Patient"
    nested.PatientID = "P001"
    original_ds = Dataset()
    original_ds.file_meta = FileMetaDataset()
    original_ds.RequestAttributesSequence = Sequence([nested])
    row = {
        "fake_PatientID": 1,
        "fake_AccessionNumber": 1,
        "fake_StudyInstanceUID": "1.2.840.999.1",
        "fake_SeriesInstanceUID": "1.2.840.999.2",
        "fake_SOPInstanceUID": "1.2.840.999.3",
    }

    with caplog.at_level("WARNING", logger="dcmtag2table.writers"):
        new_ds = writers._build_anonymized_dataset(
            row, original_ds, ["RequestAttributesSequence"]
        )

    assert new_ds is not None
    assert not hasattr(new_ds, "RequestAttributesSequence")
    assert str(new_ds.PatientName) == "000001"
    assert "Original^Patient" not in str(new_ds)
    assert "Skipping DICOM sequence tag RequestAttributesSequence" in caplog.text


def test_process_single_row_uses_anon_birth_date(tmp_path, minimal_dicom_file):
    import pydicom as dcm
    from dcmtag2table.writers import _process_single_row

    out_dir = tmp_path / "output"
    out_dir.mkdir()
    row = {
        "Filename": minimal_dicom_file,
        "fake_PatientID": 1,
        "fake_AccessionNumber": 1,
        "fake_StudyInstanceUID": "1.2.840.999.1",
        "fake_SeriesInstanceUID": "1.2.840.999.2",
        "fake_SOPInstanceUID": "1.2.840.999.3",
        "PatientSex": "F",
        "PatientAge": "030Y",
    }
    _process_single_row(0, row, str(out_dir), [])

    output_dcm = out_dir / "000001" / "1.2.840.999.3.dcm"
    ds = dcm.dcmread(str(output_dcm), force=True)
    assert ds.PatientBirthDate == DEFAULT_ANON_BIRTH_DATE


def test_process_single_row_patient_id_zero_padded(tmp_path, minimal_dicom_file):
    import pydicom as dcm
    from dcmtag2table.writers import _process_single_row

    out_dir = tmp_path / "output"
    out_dir.mkdir()
    row = {
        "Filename": minimal_dicom_file,
        "fake_PatientID": 5,
        "fake_AccessionNumber": 3,
        "fake_StudyInstanceUID": "1.2.840.999.1",
        "fake_SeriesInstanceUID": "1.2.840.999.2",
        "fake_SOPInstanceUID": "1.2.840.999.3",
        "PatientSex": "M",
        "PatientAge": "045Y",
    }
    _process_single_row(0, row, str(out_dir), [])

    output_dcm = out_dir / "000003" / "1.2.840.999.3.dcm"
    ds = dcm.dcmread(str(output_dcm), force=True)
    assert ds.PatientID == "000005"
    assert str(ds.PatientName) == "000005"
