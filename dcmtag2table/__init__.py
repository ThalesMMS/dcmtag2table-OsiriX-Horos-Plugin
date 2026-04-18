"""
dcmtag2table package
--------------------

Utilities for extracting, anonymizing, and processing DICOM metadata.
"""

from .constants import (
    non_phi_ct_dicom_tags,
    required_mg_dicom_tags,
)
from .readers import (
    dcmtag2table,
    dcmtag2table_parallel,
    dcmtag2table_from_file_list,
)
from .anonymization import (
    replace_uids,
    replace_uids_parallel_joblib,
    replace_ids,
    replace_ids_parallel_joblib,
    age_string_to_int,
    no_phi_age,
)
from .writers import (
    allow_list,
    allow_list_parallel,
)
from .utils import (
    list_files_in_directory,
    copy_files,
    remove_if_tag_contains,
    get_folder_size,
    append_to_csv,
    get_metrics,
    summary,
)
from .inspection import (
    iterate_dicom_tags,
    dump_unique_values,
    dump_unique_values_parallel,
)

__all__ = [
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
]
