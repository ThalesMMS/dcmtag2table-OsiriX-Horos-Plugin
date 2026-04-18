from concurrent.futures import ProcessPoolExecutor
from typing import Iterable, Set

import pydicom
from tqdm import tqdm

from .utils import list_files_in_directory


def process_element(element, tag_values):
    """
    Process an individual DICOM element.
    If the element is a sequence, process each item recursively.
    Otherwise, add the tag and its value to the set.
    """
    if element.VR == "SQ":  # Sequence of items
        for item in element:
            if "PixelData" in item:
                del item.PixelData
            for sub_element in item.iterall():
                process_element(sub_element, tag_values)
    else:
        tag_values.add(f"{element.value}")


def iterate_dicom_tags(file_paths: list) -> Set[str]:
    """
    Iterate over all DICOM tags in a given file, including sequences and nested sequences.
    """
    tag_values = set()
    for file_path in tqdm(file_paths):
        dicom_file = pydicom.dcmread(file_path, force=True)
        if "PixelData" in dicom_file:
            del dicom_file.PixelData
        for element in dicom_file.iterall():
            process_element(element, tag_values)

    return tag_values


def extract_tags_from_file(file_path: str) -> Set[str]:
    """
    Extract a set of DICOM tag values from a single file.
    """
    tag_values = set()
    try:
        dicom_file = pydicom.dcmread(file_path, force=True)

        # Remove PixelData if present to avoid large memory usage
        if "PixelData" in dicom_file:
            del dicom_file.PixelData

        # Iterate over all elements in the DICOM
        for element in dicom_file.iterall():
            process_element(element, tag_values)
    except Exception as e:
        # You may log errors or handle them as needed
        print(f"Error reading {file_path}: {e}")

    return tag_values


def save_set_to_file(data: Iterable[str], file_name: str):
    """
    Save the elements of a set to a file, each on a new line.

    :param data: Set of data to be saved.
    :param file_name: Name of the file to save the data.
    """
    with open(file_name, "w") as file:
        for item in data:
            file.write(f"{item}\n")


def dump_unique_values(directory: str, output="unique_values.txt"):
    print("Listing files")
    file_paths = list_files_in_directory(directory)
    print("Reading DICOM tags")
    dicom_tags = iterate_dicom_tags(file_paths)
    save_set_to_file(sorted(dicom_tags), output)


def dump_unique_values_parallel(directory: str, output="unique_values.txt", max_workers=8):
    """
    List DICOM files in `directory`, read them in parallel,
    accumulate all unique tag values, and save them to `output`.
    """
    print("Listing files...")
    file_paths = list_files_in_directory(directory)
    file_paths = list(file_paths)  # Convert to list for easier iteration

    print(f"Found {len(file_paths)} files. Reading DICOM tags in parallel...")

    # Use a process pool to parallelize across CPU cores
    all_tags = set()
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Use tqdm to show progress over the number of files
        for tag_set in tqdm(
            executor.map(extract_tags_from_file, file_paths),
            total=len(file_paths),
            desc="Reading files",
        ):
            all_tags.update(tag_set)

    # Sort before saving
    sorted_tags = sorted(all_tags)

    print(f"Saving {len(sorted_tags)} unique tag values to '{output}'...")
    save_set_to_file(sorted_tags, output)
    print("Done.")
