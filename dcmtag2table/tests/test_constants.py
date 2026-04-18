"""Tests for dcmtag2table.constants"""
import pytest

from dcmtag2table.constants import non_phi_ct_dicom_tags, required_mg_dicom_tags


class TestNonPhiCtDicomTags:
    def test_is_a_list(self):
        assert isinstance(non_phi_ct_dicom_tags, list)

    def test_all_items_are_strings(self):
        assert all(isinstance(tag, str) for tag in non_phi_ct_dicom_tags)

    def test_no_duplicates(self):
        assert len(non_phi_ct_dicom_tags) == len(set(non_phi_ct_dicom_tags))

    def test_no_empty_strings(self):
        assert all(tag.strip() for tag in non_phi_ct_dicom_tags)

    def test_pixel_data_included(self):
        assert "PixelData" in non_phi_ct_dicom_tags

    def test_required_imaging_tags_present(self):
        required = ["Modality", "Rows", "Columns", "BitsAllocated", "BitsStored"]
        for tag in required:
            assert tag in non_phi_ct_dicom_tags, f"Expected '{tag}' in non_phi_ct_dicom_tags"

    def test_no_phi_tags_included(self):
        phi_tags = ["PatientID", "PatientName", "PatientBirthDate", "PatientSex"]
        for tag in phi_tags:
            assert tag not in non_phi_ct_dicom_tags, (
                f"PHI tag '{tag}' should NOT be in non_phi_ct_dicom_tags"
            )

    def test_window_center_and_width_included(self):
        assert "WindowCenter" in non_phi_ct_dicom_tags
        assert "WindowWidth" in non_phi_ct_dicom_tags

    def test_rescale_tags_included(self):
        assert "RescaleIntercept" in non_phi_ct_dicom_tags
        assert "RescaleSlope" in non_phi_ct_dicom_tags


class TestRequiredMgDicomTags:
    def test_is_a_list(self):
        assert isinstance(required_mg_dicom_tags, list)

    def test_all_items_are_strings(self):
        assert all(isinstance(tag, str) for tag in required_mg_dicom_tags)

    def test_no_duplicates(self):
        assert len(required_mg_dicom_tags) == len(set(required_mg_dicom_tags))

    def test_no_empty_strings(self):
        assert all(tag.strip() for tag in required_mg_dicom_tags)

    def test_pixel_data_included(self):
        assert "PixelData" in required_mg_dicom_tags

    def test_modality_included(self):
        assert "Modality" in required_mg_dicom_tags

    def test_mammography_specific_tags_present(self):
        required = ["BodyPartExamined", "ViewPosition", "CompressionForce"]
        for tag in required:
            assert tag in required_mg_dicom_tags, (
                f"Expected '{tag}' in required_mg_dicom_tags"
            )

    def test_no_phi_tags_included(self):
        phi_tags = ["PatientID", "PatientName", "PatientBirthDate"]
        for tag in phi_tags:
            assert tag not in required_mg_dicom_tags, (
                f"PHI tag '{tag}' should NOT be in required_mg_dicom_tags"
            )

    def test_image_pixel_module_tags_present(self):
        pixel_module = [
            "SamplesPerPixel",
            "PhotometricInterpretation",
            "Rows",
            "Columns",
            "BitsAllocated",
        ]
        for tag in pixel_module:
            assert tag in required_mg_dicom_tags

    def test_malformed_keyword_variants_removed(self):
        malformed = [
            "DistanceSourcetoDetector",
            "DistanceSourcetoPatient",
            "X-rayTubeCurrent",
            "ExposureinuAs",
            "RelativeX-rayExposure",
            "ImagesinAcquisition",
            "SamplesperPixel",
            "ImplantPresent",
        ]
        for tag in malformed:
            assert tag not in required_mg_dicom_tags

    def test_canonical_keyword_variants_remain(self):
        canonical = [
            "DistanceSourceToDetector",
            "DistanceSourceToPatient",
            "XRayTubeCurrent",
            "ExposureInuAs",
            "RelativeXRayExposure",
            "ImagesInAcquisition",
            "SamplesPerPixel",
        ]
        for tag in canonical:
            assert tag in required_mg_dicom_tags


class TestTagListsDistinctContent:
    def test_lists_are_different_objects(self):
        assert non_phi_ct_dicom_tags is not required_mg_dicom_tags

    def test_lists_share_common_imaging_tags(self):
        common = set(non_phi_ct_dicom_tags) & set(required_mg_dicom_tags)
        # Both lists should share at least basic tags like Modality, Rows, Columns
        assert "Modality" in common
        assert "Rows" in common
        assert "Columns" in common
