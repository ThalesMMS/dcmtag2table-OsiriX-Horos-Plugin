"""
Shared pytest fixtures for dcmtag2table tests.
"""
import io

import pydicom
import pytest
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import ExplicitVRLittleEndian, generate_uid


def _make_minimal_dicom(
    tmp_path,
    filename="test.dcm",
    patient_id="P001",
    patient_name="Test^Patient",
    study_uid=None,
    series_uid=None,
    sop_uid=None,
    modality="CT",
    patient_sex="M",
    patient_age="045Y",
):
    """Create a minimal valid DICOM file and return its path."""
    study_uid = study_uid or generate_uid()
    series_uid = series_uid or generate_uid()
    sop_uid = sop_uid or generate_uid()

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = file_meta
    ds.is_implicit_VR = False
    ds.is_little_endian = True
    ds.preamble = b"\x00" * 128

    ds.PatientID = patient_id
    ds.PatientName = patient_name
    ds.PatientSex = patient_sex
    ds.PatientAge = patient_age
    ds.StudyInstanceUID = study_uid
    ds.SeriesInstanceUID = series_uid
    ds.SOPInstanceUID = sop_uid
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
    ds.Modality = modality
    ds.StudyID = "1"
    ds.AccessionNumber = "ACC001"
    ds.StudyDate = "20240101"
    ds.StudyTime = "120000"
    ds.SeriesNumber = "1"
    ds.InstanceNumber = "1"

    filepath = tmp_path / filename
    pydicom.dcmwrite(str(filepath), ds)
    return str(filepath)


@pytest.fixture
def minimal_dicom_file(tmp_path):
    """Return path to a minimal DICOM file."""
    return _make_minimal_dicom(tmp_path)


@pytest.fixture
def dicom_dir_with_files(tmp_path):
    """Create a temporary directory with two DICOM files and return the directory path."""
    study_uid = generate_uid()
    _make_minimal_dicom(
        tmp_path,
        filename="file1.dcm",
        patient_id="P001",
        study_uid=study_uid,
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
    )
    _make_minimal_dicom(
        tmp_path,
        filename="file2.dcm",
        patient_id="P002",
        study_uid=generate_uid(),
        series_uid=generate_uid(),
        sop_uid=generate_uid(),
    )
    return str(tmp_path)