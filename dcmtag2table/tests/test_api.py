import dcmtag2table
from dcmtag2table import __all__, non_phi_ct_dicom_tags, required_mg_dicom_tags


def test_public_api_symbols_are_accessible_from_package_root():
    expected_exports = {
        "dcmtag2table",
        "dcmtag2table_parallel",
        "dcmtag2table_from_file_list",
        "replace_uids",
        "replace_uids_parallel_joblib",
        "replace_ids",
        "replace_ids_parallel_joblib",
        "allow_list",
        "allow_list_parallel",
        "age_string_to_int",
        "no_phi_age",
        "list_files_in_directory",
        "iterate_dicom_tags",
        "dump_unique_values",
        "dump_unique_values_parallel",
        "copy_files",
        "remove_if_tag_contains",
        "get_folder_size",
        "append_to_csv",
        "get_metrics",
        "summary",
        "non_phi_ct_dicom_tags",
        "required_mg_dicom_tags",
    }

    assert set(__all__) == expected_exports
    assert len(__all__) == 23

    for name in __all__:
        assert hasattr(dcmtag2table, name)


def test_tag_set_lengths_match_expected_values():
    assert len(non_phi_ct_dicom_tags) == 39
    assert len(required_mg_dicom_tags) == 87
