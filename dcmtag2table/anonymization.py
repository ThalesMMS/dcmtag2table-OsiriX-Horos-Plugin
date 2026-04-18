import time

import pandas as pd
import pydicom
from joblib import Parallel, delayed
from tqdm import tqdm


_UID_TAGS = ["StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID"]
_UID_TAGS_ERROR = (
    "Tags StudyInstanceUID, SeriesInstanceUID, and SOPInstanceUID must be columns of the DataFrame"
)


def _require_columns(df: pd.DataFrame, columns, message: str) -> None:
    if any(column not in df.columns for column in columns):
        raise ValueError(message)


def replace_uids(df_in: pd.DataFrame, prefix="1.2.840.1234.") -> pd.DataFrame:
    """
    # Maps the StudyInstanceUID, SeriesInstanceUID, and SOPInstanceUID
    # in a Pandas DataFrame with newly generated UIDs taking into account the
    # Study/Series/SOP hierarchy.
    # New columns with "Fake" prefix are created.

    # Parameters:
    #    df_in (Pandas DataFrame): DataFrame containing the three columns of UIDs
    #    prefix (str): string containing your particular prefix.

    # Returns:
    #    df (DataFrame): with three new columns containing the new UIDs
    """
    start = time.time()
    df = df_in.copy()

    _require_columns(df, _UID_TAGS, _UID_TAGS_ERROR)

    for _tag in _UID_TAGS:
        print("Reassigning " + _tag)
        mapping = {
            _UID: pydicom.uid.generate_uid(prefix=prefix)
            for _UID in tqdm(df[_tag].unique())
        }
        df["fake" + _tag] = df[_tag].map(mapping)
    print("Time: " + str(time.time() - start))
    return df


def replace_uids_parallel_joblib(
    df_in: pd.DataFrame, prefix="1.2.840.1234.", n_jobs=-1
) -> pd.DataFrame:
    """
    Parallel method using joblib to map the UID columns in a DataFrame.
    New columns with "fake" prefix are created.

    Parameters:
        df_in (pd.DataFrame): DataFrame with the UIDs
        Must include Filename, StudyInstanceUID, SeriesInstanceUID, and SOPInstanceUID columns.
        prefix (str): prefix for generating new UIDs
        n_jobs (int): number of parallel jobs (-1 = all cores)

    Returns:
        df (pd.DataFrame)
    """
    start = time.time()
    df = df_in.copy()

    _require_columns(df, ["Filename"], "DataFrame must have a Filename column")
    _require_columns(df, _UID_TAGS, _UID_TAGS_ERROR)

    def make_mapping(tag):
        """Generate the mapping dict for a single column."""
        unique_vals = df[tag].unique()
        # tqdm here if you'd like to monitor progress
        mapping = {val: pydicom.uid.generate_uid(prefix=prefix) for val in unique_vals}
        return tag, mapping

    # Generate mapping dicts in parallel
    results = Parallel(n_jobs=n_jobs)(
        delayed(make_mapping)(tag) for tag in tqdm(_UID_TAGS, desc="Generating UID maps")
    )

    # Apply mapping to the DataFrame
    for tag, mapping in results:
        df["fake" + tag] = df[tag].map(mapping)

    df = df.sort_values(by=["Filename"], ascending=True)

    print("Time: {:.2f} seconds".format(time.time() - start))
    return df


def replace_ids(
    df_in: pd.DataFrame, prefix: str, start_pct=1, start_study=1
) -> pd.DataFrame:
    """
    # Maps the PatientID, StudyID
    # in a Pandas DataFrame with newly generated IDs taking into account the
    # Patient/Study/Series/SOP hierarchy.
    # New columns with "Fake" prefix are created.

    # Parameters:
    #    df_in (Pandas DataFrame): DataFrame containing the three columns of UIDs
    #    prefix (str): string containing your particular prefix.

    # Returns:
    #    df (DataFrame): with three new columns containing the new UIDs
    """
    start = time.time()
    df = df_in.copy()

    list_of_tags = ["PatientID", "StudyID", "AccessionNumber"]
    _require_columns(df, _UID_TAGS, _UID_TAGS_ERROR)
    _require_columns(
        df,
        list_of_tags,
        "Tags PatientID, StudyID, AccessionNumber must be columns of the DataFrame",
    )

    for _tag in _UID_TAGS:
        print("Reassigning " + _tag)
        mapping = {
            _UID: pydicom.uid.generate_uid(prefix=prefix)
            for _UID in tqdm(df[_tag].unique())
        }
        df["fake_" + _tag] = df[_tag].map(mapping)

    for _tag in list_of_tags:
        print("Reassigning " + _tag)

        if _tag == "PatientID":
            patient_mapping = {
                _UID: i + start_pct for i, _UID in enumerate(df[_tag].unique())
            }
            df["fake_" + _tag] = df[_tag].map(patient_mapping)
            counter = start_pct + len(patient_mapping)
        else:
            study_mapping = {
                _UID: i + start_study
                for i, _UID in enumerate(df["StudyInstanceUID"].unique())
            }
            df["fake_" + _tag] = df["StudyInstanceUID"].map(study_mapping)
            counter = start_study + len(study_mapping)

        if _tag == "PatientID":
            last_patient = counter
        elif _tag == "StudyID":
            last_study = counter

    print("Time: " + str(time.time() - start))
    print("Last Patient: " + str(last_patient))
    print("Last Study: " + str(last_study))
    return df


def replace_ids_parallel_joblib(
    df_in: pd.DataFrame, prefix: str, start_pct=1, start_study=1, n_jobs=-1
) -> pd.DataFrame:
    """
    # Maps the PatientID, StudyID
    # in a Pandas DataFrame with newly generated IDs taking into account the
    # Patient/Study/Series/SOP hierarchy.
    # New columns with "Fake" prefix are created.

    # Parameters:
    #    df_in (Pandas DataFrame): DataFrame containing Filename, PatientID,
    #        and the three columns of UIDs
    #    prefix (str): string containing your particular prefix.

    # Returns:
    #    df (DataFrame): with three new columns containing the new UIDs
    """
    start = time.time()
    df = df_in.copy()

    _require_columns(df, ["Filename"], "DataFrame must have a Filename column")
    _require_columns(df, _UID_TAGS, _UID_TAGS_ERROR)
    _require_columns(df, ["PatientID"], "DataFrame must have a PatientID column")

    def make_mapping(tag):
        """Generate the mapping dict for a single column."""
        unique_vals = df[tag].unique()
        # tqdm here if you'd like to monitor progress
        mapping = {val: pydicom.uid.generate_uid(prefix=prefix) for val in unique_vals}
        return tag, mapping

    # Generate mapping dicts in parallel
    results = Parallel(n_jobs=n_jobs)(
        delayed(make_mapping)(tag)
        for tag in tqdm(
            _UID_TAGS,
            desc="Generating StudyInstanceUID, SeriesInstanceUID, and SOPInstanceUID maps",
        )
    )

    # Apply mapping to the DataFrame
    for tag, mapping in results:
        df[f"fake_{tag}"] = df[tag].map(mapping)

    # list_of_tags = ["PatientID", "StudyID", "AccessionNumber" ]
    print("Assigning new PatientIDs.")
    unique_patients = df["PatientID"].unique()
    patient_mapping = {pat_id: i + start_pct for i, pat_id in enumerate(unique_patients)}
    df["fake_PatientID"] = df["PatientID"].map(patient_mapping)

    print("Assigning new StudyIDs.")
    unique_studies = df["StudyInstanceUID"].unique()
    study_mapping = {
        study_uid: i + start_study for i, study_uid in enumerate(unique_studies)
    }
    df["fake_StudyID"] = df["StudyInstanceUID"].map(study_mapping)
    print("Assigning new AccessionNumbers.")
    df["fake_AccessionNumber"] = df["StudyInstanceUID"].map(study_mapping)

    df = df.sort_values(by=["Filename"], ascending=True)

    last_patient = start_pct + len(unique_patients)
    last_study = start_study + len(unique_studies)
    print("Time: " + str(time.time() - start))
    print("Last Patient: " + str(last_patient))
    print("Last Study: " + str(last_study))
    return df


def age_string_to_int(age_str: str) -> int:
    """
    Convert an age string of format "NNL" to an integer.
    If 'L' is 'Y', remove it. If 'L' is any other letter, return 0.
    If 'L' is not present, return the number as is.

    :param age_str: Age in string format
    :return: Age as an integer
    """
    if age_str is None:
        return 0

    age_str = str(age_str).strip()
    if not age_str:
        return 0

    if age_str[-1].isalpha():
        if age_str[-1].upper() != "Y":
            return 0
        age_str = age_str[:-1]

    try:
        return int(age_str)
    except ValueError:
        return 0


def no_phi_age(age_str: str) -> str:
    """
    Convert an age string of format "NNL" to a HIPAA compliant
    age.
    Patients older than 89Y will be assigned to 90Y

    :param age_str: Age in string format
    :return: Age in string format never older than 90Y
    """
    age_int = age_string_to_int(age_str)
    if age_int > 89:
        age_int = 90
    return f"{age_int:03d}Y"