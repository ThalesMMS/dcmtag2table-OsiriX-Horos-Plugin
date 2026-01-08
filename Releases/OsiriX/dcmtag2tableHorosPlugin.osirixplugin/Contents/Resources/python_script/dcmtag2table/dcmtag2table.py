from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd
import pydicom
from tqdm import tqdm


def _read_dicom_tags(filepath, list_of_tags):
    """
    Read a single DICOM file and extract requested tags.
    Returns a list [filepath, tag1, tag2, ...] or None on failure.
    """
    try:
        ds = pydicom.dcmread(filepath, stop_before_pixels=True, force=True)
        row = [filepath]
        for tag in list_of_tags:
            value = ds.data_element(tag).value if tag in ds else "Not found"
            row.append(value)
        return row
    except Exception:
        return None


def dcmtag2table_from_file_list(filelist, list_of_tags, max_workers=4):
    """
    Create a DataFrame from an explicit list of DICOM file paths.

    Parameters:
        filelist (list of str): list of DICOM file paths.
        list_of_tags (list of str): list of DICOM tags.
        max_workers (int): number of parallel processes.

    Returns:
        pd.DataFrame with a Filename column plus requested tags.
    """
    list_of_tags = list(list_of_tags)
    filelist = [path for path in (filelist or []) if path]

    if not filelist:
        return pd.DataFrame(columns=["Filename"] + list_of_tags)

    rows = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_read_dicom_tags, f, list_of_tags): f for f in filelist}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Reading DICOM files"):
            fpath = futures[future]
            try:
                result = future.result()
            except Exception:
                result = None
            if result is None:
                print(f"Skipping non-DICOM or unreadable: {fpath}")
            else:
                rows.append(result)

    df = pd.DataFrame(rows, columns=["Filename"] + list_of_tags)
    if not df.empty:
        df = df.sort_values(by=["Filename"], ascending=True)
    return df
