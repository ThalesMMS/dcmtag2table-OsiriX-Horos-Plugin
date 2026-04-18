import pandas as pd
import pytest

from dcmtag2table import utils
from dcmtag2table.utils import copy_files, remove_if_tag_contains


def test_remove_if_tag_contains_uses_literal_null_safe_matching():
    df = pd.DataFrame({"SeriesDescription": ["A+B", "AxxB", None, "Keep"]})

    filtered = remove_if_tag_contains(df, "SeriesDescription", ["A+B"])

    assert list(filtered["SeriesDescription"].dropna()) == ["AxxB", "Keep"]
    assert filtered["SeriesDescription"].isna().any()


def test_copy_files_replaces_only_matching_path_segment(tmp_path):
    source = tmp_path / "dataset" / "patient_dataset" / "image.dcm"
    source.parent.mkdir(parents=True)
    source.write_text("dicom")
    df = pd.DataFrame({"Filename": [str(source)]})

    copy_files(df, "Filename", "dataset")

    destination = tmp_path / "dataset_filtered" / "patient_dataset" / "image.dcm"
    assert destination.read_text() == "dicom"


def test_copy_files_requires_matching_path_segment(tmp_path):
    source = tmp_path / "other" / "image.dcm"
    source.parent.mkdir(parents=True)
    source.write_text("dicom")
    df = pd.DataFrame({"Filename": [str(source)]})

    with pytest.raises(ValueError, match="dataset"):
        copy_files(df, "Filename", "dataset")


def test_get_metrics_handles_empty_patient_set(monkeypatch):
    columns = [
        "PatientID",
        "StudyInstanceUID",
        "SeriesInstanceUID",
        "SOPInstanceUID",
        "Modality",
        "PatientSex",
        "PatientAge",
    ]
    monkeypatch.setattr(utils, "dcmtag2table", lambda folder, tags: pd.DataFrame(columns=columns))
    monkeypatch.setattr(utils, "get_folder_size", lambda folder: 0)
    written = []
    monkeypatch.setattr(utils, "append_to_csv", lambda path, summary: written.append(summary))

    summary = utils.get_metrics("empty-folder", "metrics.csv")

    assert summary["Percentage of male"] == 0
    assert written == [summary]


# ---------------------------------------------------------------------------
# remove_if_tag_contains – additional edge cases
# ---------------------------------------------------------------------------

def test_remove_if_tag_contains_case_insensitive():
    df = pd.DataFrame({"Modality": ["CT", "ct", "MR", "mr"]})
    filtered = remove_if_tag_contains(df, "Modality", ["CT"])
    remaining = list(filtered["Modality"])
    assert "CT" not in remaining
    assert "ct" not in remaining
    assert "MR" in remaining
    assert "mr" in remaining


def test_remove_if_tag_contains_multiple_substrings():
    df = pd.DataFrame({"Description": ["chest CT", "brain MR", "abdomen CT", "pelvis US"]})
    filtered = remove_if_tag_contains(df, "Description", ["CT", "MR"])
    assert list(filtered["Description"]) == ["pelvis US"]


def test_remove_if_tag_contains_empty_list_leaves_df_unchanged():
    df = pd.DataFrame({"Tag": ["A", "B", "C"]})
    filtered = remove_if_tag_contains(df, "Tag", [])
    assert list(filtered["Tag"]) == ["A", "B", "C"]


def test_remove_if_tag_contains_treats_pattern_as_literal():
    """Regex special characters in list items must be treated as literals."""
    df = pd.DataFrame({"Tag": ["A+B", "A.B", "AXB"]})
    filtered = remove_if_tag_contains(df, "Tag", ["A+B"])
    # Only exact literal "A+B" should be removed, not "AXB" (which + would match as regex)
    remaining = list(filtered["Tag"])
    assert "A+B" not in remaining
    assert "A.B" in remaining
    assert "AXB" in remaining


# ---------------------------------------------------------------------------
# copy_files – additional edge cases
# ---------------------------------------------------------------------------

def test_copy_files_multiple_files(tmp_path):
    for name in ["file1.dcm", "file2.dcm", "file3.dcm"]:
        f = tmp_path / "source" / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"content {name}")

    df = pd.DataFrame(
        {"Filename": [str(tmp_path / "source" / n) for n in ["file1.dcm", "file2.dcm", "file3.dcm"]]}
    )
    copy_files(df, "Filename", "source")

    for name in ["file1.dcm", "file2.dcm", "file3.dcm"]:
        dest = tmp_path / "source_filtered" / name
        assert dest.exists(), f"Expected {dest} to exist"
        assert dest.read_text() == f"content {name}"


def test_copy_files_replaces_first_occurrence_of_segment(tmp_path):
    """When segment appears twice, only the first occurrence should be replaced."""
    source = tmp_path / "data" / "data" / "image.dcm"
    source.parent.mkdir(parents=True)
    source.write_text("dicom")
    df = pd.DataFrame({"Filename": [str(source)]})

    copy_files(df, "Filename", "data")

    # The first "data" segment becomes "data_filtered"
    destination = tmp_path / "data_filtered" / "data" / "image.dcm"
    assert destination.exists()


# ---------------------------------------------------------------------------
# list_files_in_directory
# ---------------------------------------------------------------------------

def test_list_files_in_directory_empty_dir(tmp_path):
    from dcmtag2table.utils import list_files_in_directory
    result = list_files_in_directory(str(tmp_path))
    assert result == set()


def test_list_files_in_directory_finds_files(tmp_path):
    from dcmtag2table.utils import list_files_in_directory
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    result = list_files_in_directory(str(tmp_path))
    assert str(tmp_path / "a.txt") in result
    assert str(tmp_path / "b.txt") in result


def test_list_files_in_directory_recursive(tmp_path):
    from dcmtag2table.utils import list_files_in_directory
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.txt").write_text("nested")
    result = list_files_in_directory(str(tmp_path))
    assert str(sub / "nested.txt") in result


# ---------------------------------------------------------------------------
# get_folder_size
# ---------------------------------------------------------------------------

def test_get_folder_size_empty_directory(tmp_path):
    from dcmtag2table.utils import get_folder_size
    size = get_folder_size(str(tmp_path))
    assert size == 0


def test_get_folder_size_with_files(tmp_path):
    from dcmtag2table.utils import get_folder_size
    content = b"hello world"
    (tmp_path / "test.bin").write_bytes(content)
    size = get_folder_size(str(tmp_path))
    assert size == len(content)


def test_get_folder_size_accumulates_multiple_files(tmp_path):
    from dcmtag2table.utils import get_folder_size
    (tmp_path / "f1.txt").write_bytes(b"abc")    # 3 bytes
    (tmp_path / "f2.txt").write_bytes(b"defgh")  # 5 bytes
    size = get_folder_size(str(tmp_path))
    assert size == 8


# ---------------------------------------------------------------------------
# append_to_csv
# ---------------------------------------------------------------------------

def test_append_to_csv_creates_new_file(tmp_path):
    from dcmtag2table.utils import append_to_csv
    csv_file = str(tmp_path / "metrics.csv")
    data = {"col1": 1, "col2": "hello"}
    append_to_csv(csv_file, data)

    result = pd.read_csv(csv_file)
    assert len(result) == 1
    assert result.iloc[0]["col1"] == 1
    assert result.iloc[0]["col2"] == "hello"


def test_append_to_csv_appends_to_existing_file(tmp_path):
    from dcmtag2table.utils import append_to_csv
    csv_file = str(tmp_path / "metrics.csv")
    append_to_csv(csv_file, {"val": 1})
    append_to_csv(csv_file, {"val": 2})

    result = pd.read_csv(csv_file)
    assert len(result) == 2
    assert list(result["val"]) == [1, 2]


# ---------------------------------------------------------------------------
# get_metrics – with patient data (mocked)
# ---------------------------------------------------------------------------

def _make_metrics_df():
    return pd.DataFrame(
        {
            "PatientID": ["P001", "P001", "P002", "P002"],
            "StudyInstanceUID": ["S1", "S1", "S2", "S3"],
            "SeriesInstanceUID": ["SR1", "SR2", "SR3", "SR4"],
            "SOPInstanceUID": ["SOP1", "SOP2", "SOP3", "SOP4"],
            "Modality": ["CT", "CT", "MR", "MR"],
            "PatientSex": ["M", "M", "F", "F"],
            "PatientAge": ["045Y", "045Y", "060Y", "060Y"],
        }
    )


def test_get_metrics_counts_patients_correctly(monkeypatch):
    df = _make_metrics_df()
    monkeypatch.setattr(utils, "dcmtag2table", lambda f, t: df)
    monkeypatch.setattr(utils, "get_folder_size", lambda f: 0)
    monkeypatch.setattr(utils, "append_to_csv", lambda p, s: None)

    result = utils.get_metrics("folder", "out.csv")
    assert result["Number of patients"] == 2


def test_get_metrics_counts_studies_correctly(monkeypatch):
    df = _make_metrics_df()
    monkeypatch.setattr(utils, "dcmtag2table", lambda f, t: df)
    monkeypatch.setattr(utils, "get_folder_size", lambda f: 0)
    monkeypatch.setattr(utils, "append_to_csv", lambda p, s: None)

    result = utils.get_metrics("folder", "out.csv")
    assert result["Number of studies"] == 3


def test_get_metrics_percentage_male_calculation(monkeypatch):
    df = _make_metrics_df()  # 1 male out of 2 unique patients = 0.5
    monkeypatch.setattr(utils, "dcmtag2table", lambda f, t: df)
    monkeypatch.setattr(utils, "get_folder_size", lambda f: 0)
    monkeypatch.setattr(utils, "append_to_csv", lambda p, s: None)

    result = utils.get_metrics("folder", "out.csv")
    assert result["Percentage of male"] == pytest.approx(0.5)


def test_get_metrics_modality_counts(monkeypatch):
    df = _make_metrics_df()  # study S1=CT, S2=MR, S3=MR
    monkeypatch.setattr(utils, "dcmtag2table", lambda f, t: df)
    monkeypatch.setattr(utils, "get_folder_size", lambda f: 0)
    monkeypatch.setattr(utils, "append_to_csv", lambda p, s: None)

    result = utils.get_metrics("folder", "out.csv")
    assert result["Number of CTs"] == 1
    assert result["Number of MRs"] == 2
    assert result["Number of USs"] == 0


def test_get_metrics_number_of_files(monkeypatch):
    df = _make_metrics_df()
    monkeypatch.setattr(utils, "dcmtag2table", lambda f, t: df)
    monkeypatch.setattr(utils, "get_folder_size", lambda f: 1024)
    monkeypatch.setattr(utils, "append_to_csv", lambda p, s: None)

    result = utils.get_metrics("folder", "out.csv")
    assert result["Number of files"] == 4
    assert result["Batch Size Bytes"] == 1024


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------

def test_summary_prints_column_info(capsys):
    from dcmtag2table.utils import summary
    df = pd.DataFrame({"A": [1, 2, 2], "B": ["x", "y", "z"]})
    summary(df)
    captured = capsys.readouterr()
    assert "A:" in captured.out
    assert "B:" in captured.out
    assert "2" in captured.out  # A has 2 unique values
    assert "3" in captured.out  # B has 3 unique values