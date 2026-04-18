import hashlib
import hmac
import logging
import os
from datetime import datetime

import pydicom
from joblib import Parallel, delayed
from pydicom import Dataset
from pydicom.dataset import FileMetaDataset
from pydicom.errors import InvalidDicomError
from tqdm import tqdm

from .anonymization import replace_ids_parallel_joblib
from .readers import dcmtag2table_parallel


logger = logging.getLogger(__name__)
DEFAULT_MAX_WORKERS = 8
DEFAULT_UID_PREFIX = os.environ.get("ANON_UID_PREFIX", "1.2.840.12345.")
DEFAULT_ANON_BIRTH_DATE = "19190828"
DEFAULT_ANON_STUDY_DATE = "20250228"
LOG_TOKEN_SECRET_ENV = "DCMTAG2TABLE_LOG_TOKEN_SECRET"
_DEFAULT_LOG_TOKEN_SECRET = os.urandom(32)
_ANON_DATES = None
_DICOM_READ_ERRORS = (OSError, TypeError, InvalidDicomError)
_DICOM_WRITE_ERRORS = (
    OSError,
    ValueError,
    AttributeError,
    FileExistsError,
    NotImplementedError,
    TypeError,
)


def _load_anon_date(env_var, default):
    value = os.environ.get(env_var, default)
    if len(value) != 8 or not value.isdigit():
        raise ValueError(f"{env_var} must be a valid YYYYMMDD date")
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as e:
        raise ValueError(f"{env_var} must be a valid YYYYMMDD date") from e
    return value


def _get_anon_dates():
    global _ANON_DATES
    if _ANON_DATES is None:
        _ANON_DATES = (
            _load_anon_date("ANON_BIRTH_DATE", DEFAULT_ANON_BIRTH_DATE),
            _load_anon_date("ANON_STUDY_DATE", DEFAULT_ANON_STUDY_DATE),
        )
    return _ANON_DATES


_PHI_DICOM_TAGS = [
    "PatientID",
    "PatientName",
    "PatientBirthDate",
    "PatientSex",
    "PatientAge",
    "ReferringPhysicianName",
    "StudyID",
    "AccessionNumber",
    "DeviceSerialNumber",
    "StudyInstanceUID",
    "StudyDate",
    "StudyTime",
    "SeriesInstanceUID",
    "SOPInstanceUID",
    "ProtocolName",
]


def _log_token(value) -> str:
    # Set LOG_TOKEN_SECRET_ENV in tests or deployments for deterministic HMACs.
    secret = os.environ.get(LOG_TOKEN_SECRET_ENV)
    key = secret.encode("utf-8") if secret else _DEFAULT_LOG_TOKEN_SECRET
    return hmac.new(key, str(value).encode("utf-8"), hashlib.sha256).hexdigest()[:8]


def _path_token(path: str) -> str:
    return _log_token(path)


def _zero_padded_row_id(row, key: str, width: int = 6):
    try:
        value = row[key]
        number = int(value)
    except (KeyError, TypeError, ValueError):
        return None
    if number < 0:
        return None
    return str(number).zfill(width)


def _build_anonymized_dataset(
    row, original_ds, list_of_tags, patient_id=None, study_id=None
):
    """
    Build an anonymized DICOM dataset from original_ds, retaining only list_of_tags
    and replacing identifiers with values from the anonymized row.

    Returns the new Dataset, or None if file_meta cannot be copied.
    """
    new_ds = Dataset()
    new_ds.file_meta = FileMetaDataset()

    if not hasattr(original_ds, "file_meta"):
        return None
    new_ds.file_meta = original_ds.file_meta

    for tag in list_of_tags:
        if hasattr(original_ds, tag):
            element = original_ds[tag]
            if element.VR == "SQ":
                logger.warning("Skipping DICOM sequence tag %s during allow-list copy.", tag)
                continue
            new_ds.add(element)

    if patient_id is None:
        patient_id = _zero_padded_row_id(row, "fake_PatientID")
    if study_id is None:
        study_id = _zero_padded_row_id(row, "fake_AccessionNumber")
    if patient_id is None or study_id is None:
        return None

    anon_birth_date, anon_study_date = _get_anon_dates()
    new_ds.PatientID = patient_id
    new_ds.PatientName = patient_id
    new_ds.PatientBirthDate = anon_birth_date
    new_ds.PatientSex = row.get("PatientSex", "O")
    new_ds.PatientAge = row.get("PatientAge", "000Y")
    new_ds.StudyID = study_id
    new_ds.AccessionNumber = study_id
    new_ds.StudyInstanceUID = row["fake_StudyInstanceUID"]
    new_ds.SeriesInstanceUID = row["fake_SeriesInstanceUID"]
    new_ds.SOPInstanceUID = row["fake_SOPInstanceUID"]
    new_ds.file_meta.MediaStorageSOPInstanceUID = row["fake_SOPInstanceUID"]
    new_ds.ProtocolName = ""
    new_ds.StudyDate = anon_study_date
    new_ds.SeriesDate = anon_study_date
    new_ds.ContentDate = anon_study_date
    new_ds.AcquisitionDate = anon_study_date
    new_ds.StudyTime = "000000"
    new_ds.SeriesTime = "000000"
    new_ds.ContentTime = "000000"
    new_ds.AcquisitionTime = "000000"

    return new_ds


def allow_list(
    in_path: str,
    out_path: str,
    list_of_tags: list,
    start_pct=1,
    start_study=1,
    max_workers=DEFAULT_MAX_WORKERS,
    uid_prefix=DEFAULT_UID_PREFIX,
):
    """
    Processes DICOM files to anonymize and retain only a specified list of tags, saving the modified files to a new location.

    This function reads DICOM files from a specified input path, anonymizes patient and study identifiers, and creates new DICOM files that include only a predefined list of DICOM tags, along with newly anonymized tags. The new files are saved to a specified output path, organized by StudyID.

    Parameters:
    - in_path (str): The file path to the directory containing the original DICOM files.
    - out_path (str): The file path to the directory where the modified DICOM files will be saved.
    - list_of_tags (list): A list of DICOM tags that should be retained in the new DICOM files.
    - start_pct (int, optional): Starting value for the pseudonymization counter for PatientID and PatientName. Defaults to 1.
    - start_study (int, optional): Starting value for the pseudonymization counter for StudyID and AccessionNumber. Defaults to 1.
    - max_workers (int, optional): Number of parallel workers used while reading input metadata. Defaults to 8.
    - uid_prefix (str, optional): UID prefix used for generated anonymized UIDs. Defaults to ANON_UID_PREFIX, or "1.2.840.12345." when unset.

    Returns:
    - DataFrame: A pandas DataFrame containing the mappings between original and fake identifiers for all processed DICOM files.

    Note:
    The function uses `dcmtag2table` to extract specified DICOM tags into a DataFrame and `replace_ids` to anonymize identifiers. It requires `pydicom` for DICOM file handling and `os` for file path operations. Progress is tracked using `tqdm`.

    The anonymization process assigns new values to PatientID, PatientName, StudyID, AccessionNumber, StudyInstanceUID, SeriesInstanceUID, and SOPInstanceUID, while retaining specified clinical tags. Certain fixed values are assigned to PatientBirthDate, PatientSex, PatientAge, and StudyDate, StudyTime, and the ProtocolName is cleared.
    """
    _get_anon_dates()
    df = dcmtag2table_parallel(in_path, _PHI_DICOM_TAGS, max_workers=max_workers)

    df = replace_ids_parallel_joblib(
        df, prefix=uid_prefix, start_pct=start_pct, start_study=start_study
    )
    for _index, row in tqdm(df.iterrows(), total=len(df)):
        _process_single_row(_index, row, out_path, list_of_tags)

    return df


def _process_single_row(_index, row, out_path: str, list_of_tags: list):
    """
    Process a single row from the DataFrame: read the original DICOM,
    copy only certain tags, anonymize / replace IDs, and write out the new DICOM.
    """
    original_file_path = row["Filename"]

    try:
        original_ds = pydicom.dcmread(original_file_path, force=True)
    except _DICOM_READ_ERRORS as e:
        logger.warning(
            "Failed to read DICOM file path_hash=%s - %s",
            _path_token(original_file_path),
            e,
        )
        return

    patient_id = _zero_padded_row_id(row, "fake_PatientID")
    study_id = _zero_padded_row_id(row, "fake_AccessionNumber")
    if patient_id is None or study_id is None:
        logger.warning(
            "Invalid fake ID values for DICOM file path_hash=%s. Skipping file.",
            _path_token(original_file_path),
        )
        return

    new_ds = _build_anonymized_dataset(
        row, original_ds, list_of_tags, patient_id=patient_id, study_id=study_id
    )
    if new_ds is None:
        logger.warning(
            "No file_meta found for DICOM file path_hash=%s. Skipping file.",
            _path_token(original_file_path),
        )
        return

    new_file_path = os.path.join(
        out_path, str(new_ds.StudyID), str(new_ds.SOPInstanceUID) + ".dcm"
    )
    os.makedirs(os.path.dirname(new_file_path), exist_ok=True)

    try:
        new_ds.save_as(new_file_path)
    except _DICOM_WRITE_ERRORS as e:
        logger.warning(
            "Failed to save DICOM file path_hash=%s study_id=%s sop_instance_uid_hash=%s - %s",
            _path_token(new_file_path),
            new_ds.StudyID,
            _log_token(new_ds.SOPInstanceUID),
            e,
        )


def allow_list_parallel(
    in_path: str,
    out_path: str,
    list_of_tags: list,
    start_pct=1,
    start_study=1,
    max_workers=DEFAULT_MAX_WORKERS,
    uid_prefix=DEFAULT_UID_PREFIX,
):
    """
    Processes DICOM files to anonymize and retain only a specified list of tags,
    saving the modified files to a new location, **in parallel**.
    """
    _get_anon_dates()
    df = dcmtag2table_parallel(in_path, _PHI_DICOM_TAGS, max_workers=max_workers)

    df = replace_ids_parallel_joblib(
        df, prefix=uid_prefix, start_pct=start_pct, start_study=start_study
    )

    tasks = (
        delayed(_process_single_row)(_index, row, out_path, list_of_tags)
        for _index, row in df.iterrows()
    )

    Parallel(n_jobs=max_workers)(tqdm(tasks, total=len(df), desc="Processing DICOMs"))

    return df
