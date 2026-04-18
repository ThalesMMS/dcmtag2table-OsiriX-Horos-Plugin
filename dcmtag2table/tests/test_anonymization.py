import pytest
import pandas as pd

from dcmtag2table import (
    age_string_to_int,
    no_phi_age,
    replace_ids,
    replace_ids_parallel_joblib,
    replace_uids,
    replace_uids_parallel_joblib,
)
from dcmtag2table import anonymization


def test_anonymization_functions_are_importable():
    assert callable(replace_uids)
    assert callable(replace_ids)
    assert callable(replace_uids_parallel_joblib)
    assert callable(replace_ids_parallel_joblib)


@pytest.mark.parametrize(
    ("age_str", "expected"),
    [
        ("045Y", 45),
        ("006M", 0),
        ("", 0),
        ("   ", 0),
        (None, 0),
        ("ABCY", 0),
        ("ABC", 0),
    ],
)
def test_age_string_to_int_known_inputs(age_str, expected):
    assert age_string_to_int(age_str) == expected


@pytest.mark.parametrize("age_str", ["090Y", "091Y", "120Y"])
def test_no_phi_age_caps_ages_over_89(age_str):
    assert no_phi_age(age_str) == "090Y"


def test_no_phi_age_zero_pads_younger_ages():
    assert no_phi_age("005Y") == "005Y"


def test_replace_uid_functions_use_the_same_fake_column_convention(monkeypatch):
    counter = iter(range(1, 20))
    monkeypatch.setattr(
        anonymization.pydicom.uid,
        "generate_uid",
        lambda prefix: f"{prefix}{next(counter)}",
    )
    df = pd.DataFrame(
        {
            "Filename": ["b.dcm", "a.dcm"],
            "StudyInstanceUID": ["study-1", "study-1"],
            "SeriesInstanceUID": ["series-1", "series-2"],
            "SOPInstanceUID": ["sop-1", "sop-2"],
        }
    )

    sequential = replace_uids(df, prefix="1.2.840.1234.")
    parallel = replace_uids_parallel_joblib(df, prefix="1.2.840.1234.", n_jobs=1)

    expected_columns = {
        "fakeStudyInstanceUID",
        "fakeSeriesInstanceUID",
        "fakeSOPInstanceUID",
    }
    assert expected_columns <= set(sequential.columns)
    assert expected_columns <= set(parallel.columns)
    assert "fake_StudyInstanceUID" not in parallel.columns


def test_replace_uid_parallel_requires_filename_column():
    df = pd.DataFrame(
        {
            "StudyInstanceUID": ["study-1"],
            "SeriesInstanceUID": ["series-1"],
            "SOPInstanceUID": ["sop-1"],
        }
    )

    with pytest.raises(ValueError, match="Filename"):
        replace_uids_parallel_joblib(df, n_jobs=1)


def test_replace_ids_parallel_requires_patient_id_column():
    df = pd.DataFrame(
        {
            "Filename": ["image.dcm"],
            "StudyInstanceUID": ["study-1"],
            "SeriesInstanceUID": ["series-1"],
            "SOPInstanceUID": ["sop-1"],
        }
    )

    with pytest.raises(ValueError, match="PatientID"):
        replace_ids_parallel_joblib(df, prefix="1.2.840.1234.", n_jobs=1)


# ---------------------------------------------------------------------------
# age_string_to_int – additional edge cases
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("age_str", "expected"),
    [
        ("45", 45),        # pure integer string – no letter suffix
        ("0", 0),          # zero with no letter suffix
        ("045y", 45),      # lowercase 'y' should be treated as 'Y'
        ("089Y", 89),      # exactly 89
        ("001Y", 1),       # leading zeros
    ],
)
def test_age_string_to_int_additional_inputs(age_str, expected):
    assert age_string_to_int(age_str) == expected


def test_age_string_to_int_with_integer_zero():
    # Integer 0 should not crash
    assert age_string_to_int(0) == 0


def test_age_string_to_int_whitespace_trimmed():
    # Extra surrounding whitespace must be stripped before parsing
    assert age_string_to_int("  050Y  ") == 50


# ---------------------------------------------------------------------------
# no_phi_age – boundary and zero cases
# ---------------------------------------------------------------------------

def test_no_phi_age_boundary_exactly_89():
    # 89 is below the cap, must not be capped
    result = no_phi_age("089Y")
    assert result == "089Y"


def test_no_phi_age_zero_age():
    assert no_phi_age("000Y") == "000Y"


def test_no_phi_age_output_is_always_three_digit_padded():
    assert no_phi_age("001Y") == "001Y"
    assert no_phi_age("010Y") == "010Y"


def test_no_phi_age_capped_value_format():
    # Values >89 must return exactly '090Y'
    result = no_phi_age("100Y")
    assert result == "090Y"


# ---------------------------------------------------------------------------
# replace_uids – does not mutate input DataFrame
# ---------------------------------------------------------------------------

def test_replace_uids_does_not_mutate_input():
    df = pd.DataFrame(
        {
            "StudyInstanceUID": ["study-1"],
            "SeriesInstanceUID": ["series-1"],
            "SOPInstanceUID": ["sop-1"],
        }
    )
    original_columns = list(df.columns)
    replace_uids(df)
    assert list(df.columns) == original_columns


def test_replace_uids_generates_distinct_uids_per_unique_source():
    """Each unique source UID must receive a unique replacement."""
    df = pd.DataFrame(
        {
            "StudyInstanceUID": ["study-1", "study-1", "study-2"],
            "SeriesInstanceUID": ["series-1", "series-2", "series-3"],
            "SOPInstanceUID": ["sop-1", "sop-2", "sop-3"],
        }
    )
    result = replace_uids(df)

    # Unique source study UIDs → unique fake study UIDs
    assert result["fakeStudyInstanceUID"].nunique() == 2
    # Rows that share the same source UID share the same fake UID
    assert (
        result.loc[result["StudyInstanceUID"] == "study-1", "fakeStudyInstanceUID"].nunique()
        == 1
    )


def test_replace_uids_raises_when_uid_columns_missing():
    df = pd.DataFrame({"StudyInstanceUID": ["study-1"]})
    with pytest.raises(ValueError):
        replace_uids(df)


# ---------------------------------------------------------------------------
# replace_ids – validation and mapping correctness
# ---------------------------------------------------------------------------

def _make_ids_df():
    return pd.DataFrame(
        {
            "Filename": ["c.dcm", "b.dcm", "a.dcm"],
            "StudyInstanceUID": ["study-1", "study-1", "study-2"],
            "SeriesInstanceUID": ["series-1", "series-2", "series-3"],
            "SOPInstanceUID": ["sop-1", "sop-2", "sop-3"],
            "PatientID": ["P001", "P001", "P002"],
            "StudyID": ["S01", "S01", "S02"],
            "AccessionNumber": ["ACC1", "ACC1", "ACC2"],
        }
    )


def test_replace_ids_raises_when_uid_columns_missing():
    df = pd.DataFrame(
        {
            "PatientID": ["P001"],
            "StudyID": ["S01"],
            "AccessionNumber": ["ACC1"],
        }
    )
    with pytest.raises(ValueError, match="StudyInstanceUID"):
        replace_ids(df, prefix="1.2.")


def test_replace_ids_raises_when_patient_columns_missing():
    df = pd.DataFrame(
        {
            "StudyInstanceUID": ["study-1"],
            "SeriesInstanceUID": ["series-1"],
            "SOPInstanceUID": ["sop-1"],
        }
    )
    with pytest.raises(ValueError, match="PatientID"):
        replace_ids(df, prefix="1.2.")


def test_replace_ids_start_pct_applied():
    df = _make_ids_df()
    result = replace_ids(df, prefix="1.2.", start_pct=100)
    assert result["fake_PatientID"].min() >= 100


def test_replace_ids_start_study_applied():
    df = _make_ids_df()
    result = replace_ids(df, prefix="1.2.", start_study=50)
    assert result["fake_StudyID"].min() >= 50


def test_replace_ids_studyid_and_accession_share_mapping():
    """fake_StudyID and fake_AccessionNumber should both be derived from StudyInstanceUID."""
    df = _make_ids_df()
    result = replace_ids(df, prefix="1.2.", start_study=1)
    # Rows with the same StudyInstanceUID should have the same fake_StudyID and fake_AccessionNumber
    for study_uid in df["StudyInstanceUID"].unique():
        mask = result["StudyInstanceUID"] == study_uid
        assert result.loc[mask, "fake_StudyID"].nunique() == 1
        assert result.loc[mask, "fake_AccessionNumber"].nunique() == 1


# ---------------------------------------------------------------------------
# replace_ids_parallel_joblib – mapping correctness
# ---------------------------------------------------------------------------

def test_replace_ids_parallel_joblib_output_sorted_by_filename():
    df = _make_ids_df()
    result = replace_ids_parallel_joblib(df, prefix="1.2.", n_jobs=1)
    filenames = list(result["Filename"])
    assert filenames == sorted(filenames)


def test_replace_ids_parallel_joblib_fake_study_and_accession_same_mapping():
    df = _make_ids_df()
    result = replace_ids_parallel_joblib(df, prefix="1.2.", n_jobs=1)
    # fake_StudyID and fake_AccessionNumber both come from StudyInstanceUID
    assert list(result["fake_StudyID"]) == list(result["fake_AccessionNumber"])


def test_replace_ids_parallel_joblib_start_pct_applied():
    df = _make_ids_df()
    result = replace_ids_parallel_joblib(df, prefix="1.2.", start_pct=200, n_jobs=1)
    assert result["fake_PatientID"].min() >= 200


def test_replace_ids_parallel_joblib_does_not_mutate_input():
    df = _make_ids_df()
    original_columns = list(df.columns)
    replace_ids_parallel_joblib(df, prefix="1.2.", n_jobs=1)
    assert list(df.columns) == original_columns


# ---------------------------------------------------------------------------
# replace_uids_parallel_joblib – output sorted by Filename
# ---------------------------------------------------------------------------

def test_replace_uids_parallel_joblib_output_sorted_by_filename():
    df = pd.DataFrame(
        {
            "Filename": ["c.dcm", "a.dcm", "b.dcm"],
            "StudyInstanceUID": ["study-1", "study-2", "study-3"],
            "SeriesInstanceUID": ["series-1", "series-2", "series-3"],
            "SOPInstanceUID": ["sop-1", "sop-2", "sop-3"],
        }
    )
    result = replace_uids_parallel_joblib(df, n_jobs=1)
    filenames = list(result["Filename"])
    assert filenames == sorted(filenames)


def test_replace_uids_parallel_requires_uid_columns():
    df = pd.DataFrame(
        {
            "Filename": ["a.dcm"],
            "StudyInstanceUID": ["study-1"],
            # Missing SeriesInstanceUID and SOPInstanceUID
        }
    )
    with pytest.raises(ValueError):
        replace_uids_parallel_joblib(df, n_jobs=1)