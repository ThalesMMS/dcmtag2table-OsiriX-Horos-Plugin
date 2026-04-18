import os
import time
from concurrent.futures import BrokenExecutor, CancelledError, ProcessPoolExecutor, as_completed
from contextlib import contextmanager

import pandas as pd
import pydicom
from tqdm import tqdm


@contextmanager
def _permissive_pydicom_validation():
    """Temporarily allow malformed values during force=True DICOM reads."""
    original = pydicom.config.enforce_valid_values
    pydicom.config.enforce_valid_values = False
    try:
        yield
    finally:
        pydicom.config.enforce_valid_values = original


def dcmtag2table(folder, list_of_tags):
    """
    # Create a Pandas DataFrame with the <list_of_tags> DICOM tags
    # from the DICOM files in <folder>

    # Parameters:
    #    folder (str): folder to be recursively walked looking for DICOM files.
    #    list_of_tags (list of strings): list of DICOM tags with no whitespaces.

    # Returns:
    #    df (DataFrame): table of DICOM tags from the files in folder.
    """
    list_of_tags = list_of_tags.copy()
    filelist = []
    print("Listing all files...")
    start = time.time()
    for root, _dirs, files in os.walk(folder):
        for name in files:
            filelist.append(os.path.join(root, name))
    print("Time: " + str(time.time() - start))
    print("Reading files...")

    column_names = ["Filename", *list_of_tags]
    rows = []
    for _f in tqdm(filelist):
        try:
            with _permissive_pydicom_validation():
                ds = pydicom.dcmread(_f, stop_before_pixels=True, force=True)
            row = [_f] + [
                ds.data_element(_tag).value if _tag in ds else "Not found"
                for _tag in list_of_tags
            ]
            rows.append(row)
        except Exception:
            print("Skipping non-DICOM: " + _f)

    df = pd.DataFrame(rows, columns=column_names)
    print("Finished.")
    return df


def _read_dicom_tags(filepath, list_of_tags):
    """
    Helper function to read a single DICOM file
    and extract the requested tags.
    Returns a list [filepath, tag1, tag2, ...] or None on failure.
    """
    try:
        with _permissive_pydicom_validation():
            ds = pydicom.dcmread(filepath, stop_before_pixels=True, force=True)
        row = [filepath]
        for tag in list_of_tags:
            value = ds.data_element(tag).value if tag in ds else "Not found"
            row.append(value)
        return row
    except Exception:
        # If it's not a valid DICOM or can't be read, return None
        return None


def _collect_parallel_results(filelist, list_of_tags, max_workers, desc="Reading DICOM files"):
    """
    Submit DICOM reading tasks to a process pool and collect results.
    Returns a list of rows, each being [filepath, tag1, tag2, ...].
    """
    rows = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_read_dicom_tags, f, list_of_tags): f for f in filelist
        }
        for future in tqdm(as_completed(futures), total=len(futures), desc=desc):
            fpath = futures[future]
            try:
                result = future.result()
            except CancelledError as e:
                print(f"Skipping cancelled DICOM read {fpath}: {e}")
                continue
            except BrokenExecutor as e:
                print(f"Skipping failed DICOM read {fpath}: {e}")
                continue
            except Exception as e:
                print(f"Skipping failed DICOM read {fpath}: {e}")
                continue
            if result is None:
                print(f"Skipping non-DICOM or unreadable: {fpath}")
            else:
                rows.append(result)
    return rows


def dcmtag2table_parallel(folder, list_of_tags, max_workers=4):
    """
    Create a Pandas DataFrame with the <list_of_tags> DICOM tags
    from the DICOM files in <folder>, in parallel.

    Parameters:
        folder (str): folder to be recursively walked looking for DICOM files.
        list_of_tags (list of str): list of DICOM tags with no whitespaces.
        max_workers (int): number of parallel processes to use.

    Returns:
        df (pd.DataFrame): table of DICOM tags from the files in folder.
    """
    list_of_tags = list_of_tags.copy()
    filelist = []

    print("Listing all files...")
    start = time.time()
    for root, _dirs, files in os.walk(folder):
        for name in files:
            filelist.append(os.path.join(root, name))
    print("Time for listing: {:.2f} seconds".format(time.time() - start))

    print("Reading DICOM tags in parallel...")
    start_read = time.time()
    rows = _collect_parallel_results(filelist, list_of_tags, max_workers)
    print("Time for reading: {:.2f} seconds".format(time.time() - start_read))

    column_names = ["Filename", *list_of_tags]
    df = pd.DataFrame(rows, columns=column_names)
    df = df.sort_values(by=["Filename"], ascending=True)
    print("Finished.")
    return df


def dcmtag2table_from_file_list(filelist, list_of_tags, max_workers=4):
    """
    Create a Pandas DataFrame with the <list_of_tags> DICOM tags
    from an explicit list of DICOM file paths, in parallel.

    This is a helper for processing a manifest-provided file list
    without performing directory walk.

    Parameters:
        filelist (list of str): explicit list of DICOM file paths.
        list_of_tags (list of str): list of DICOM tags with no whitespaces.
        max_workers (int): number of parallel processes to use.

    Returns:
        df (pd.DataFrame): table of DICOM tags from the files in filelist.
    """
    list_of_tags = list_of_tags.copy()

    print(f"Processing {len(filelist)} files...")
    start_read = time.time()
    rows = _collect_parallel_results(filelist, list_of_tags, max_workers, desc="Reading DICOM files")
    print("Time for reading: {:.2f} seconds".format(time.time() - start_read))

    column_names = ["Filename", *list_of_tags]
    df = pd.DataFrame(rows, columns=column_names)
    df = df.sort_values(by=["Filename"], ascending=True)
    print("Finished.")
    return df
