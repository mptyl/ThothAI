# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

import logging
import pickle
from pathlib import Path
from typing import Dict, List, Tuple

from datasketch import MinHash, MinHashLSH
from tqdm import tqdm
from thoth_ai_backend.utils.progress_tracker import ProgressTracker


def _create_minhash(signature_size: int, string: str, n_gram: int) -> MinHash:
    """
    Creates a MinHash object for a given string.

    Args:
        signature_size (int): The size of the MinHash signature.
        string (str): The input string to create the MinHash for.
        n_gram (int): The n-gram size for the MinHash.

    Returns:
        MinHash: The MinHash object for the input string.
    """
    m = MinHash(num_perm=signature_size)
    for d in [string[i : i + n_gram] for i in range(len(string) - n_gram + 1)]:
        m.update(d.encode("utf8"))
    return m


def skip_column(column_name: str, column_values: List[str]) -> bool:
    """
    Determines whether to skip processing a column based on its values.

    Args:
        column_name (str): The name of the column.
        column_values (List[str]): The list of values in the column.

    Returns:
        bool: True if the column should be skipped, False otherwise.
    """
    if "name" in column_name.lower():
        return False
    sum_of_lengths = sum(len(value) for value in column_values)
    average_length = sum_of_lengths / len(column_values)
    return (sum_of_lengths > 50000) and (average_length > 20)


def make_lsh(
    unique_values: Dict[str, Dict[str, List[str]]],
    signature_size: int,
    n_gram: int,
    threshold: float,
    verbose: bool = True,
    workspace_id: int = None,
    processed_items_offset: int = 0,
) -> Tuple[MinHashLSH, Dict[str, Tuple[MinHash, str, str, str]]]:
    """
    Creates a MinHash Locality-Sensitive Hashing (LSH) index from unique values in a database.

    This function processes unique values from database tables and columns, creates MinHash
    signatures for each value, and builds an LSH index for efficient similarity search.

    Args:
        unique_values (Dict[str, Dict[str, List[str]]]): A nested dictionary containing unique values
            from the database. The structure is {table_name: {column_name: [values]}}.
        signature_size (int): The number of permutations to use in the MinHash signatures.
        n_gram (int): The size of n-grams to use when creating MinHash signatures.
        threshold (float): The similarity threshold for the LSH index. Values closer to 1 require
            higher similarity for matches.
        verbose (bool, optional): If True, displays a progress bar during processing. Defaults to True.

    Returns:
        Tuple[MinHashLSH, Dict[str, Tuple[MinHash, str, str, str]]]: A tuple containing:
            - MinHashLSH: The constructed LSH index.
            - Dict[str, Tuple[MinHash, str, str, str]]: A dictionary mapping unique keys to tuples
              containing (MinHash object, table name, column name, original value).

    Raises:
        Exception: If an error occurs during LSH creation, it's logged but not raised.

    Note:
        This function uses the datasketch library for MinHash and LSH operations.
    """
    lsh = MinHashLSH(threshold=threshold, num_perm=signature_size)
    minhashes: Dict[str, Tuple[MinHash, str, str, str]] = {}
    try:
        total_unique_values = sum(
            len(column_values)
            for table_values in unique_values.values()
            for column_values in table_values.values()
        )
        logging.info(f"Total unique values: {total_unique_values}")

        progress_bar = (
            tqdm(total=total_unique_values, desc="Creating LSH") if verbose else None
        )
        
        processed_items = 0
        successful_items = 0
        failed_items = 0

        for table_name, table_values in unique_values.items():
            for column_name, column_values in table_values.items():
                if column_name.lower() == "doctype":
                    logging.info("=" * 20)
                    logging.info("Doctype found")
                    logging.info("=" * 20)
                logging.info(
                    f"Processing {table_name} - {column_name} - {len(column_values)}"
                )

                for id, value in enumerate(column_values):
                    minhash = _create_minhash(signature_size, value, n_gram)
                    minhash_key = f"{table_name}_{column_name}_{id}"
                    minhashes[minhash_key] = (minhash, table_name, column_name, value)
                    lsh.insert(minhash_key, minhash)

                    if verbose:
                        progress_bar.update(1)
                    
                    processed_items += 1
                    successful_items += 1
                    
                    # Update progress tracker if workspace_id is provided
                    if workspace_id and processed_items % 100 == 0:  # Update every 100 items to reduce overhead
                        ProgressTracker.update_progress(
                            workspace_id, 'preprocessing',
                            processed_items_offset + processed_items,
                            processed_items_offset + successful_items,
                            failed_items
                        )

        if verbose:
            progress_bar.close()
    except Exception as e:
        logging.error(f"Error creating LSH: {e}")

    return lsh, minhashes


def make_db_lsh(db, db_directory_path, db_name, **kwargs) -> int:
    """
    Creates a MinHash LSH for the database and saves the results.

    Args:
        db_directory_path (str): The path to the database directory.
        **kwargs (Any): Additional arguments for the LSH creation.
    """
    # db_id = Path(db_directory_path).name
    preprocessed_path = Path(db_directory_path) / "preprocessed"
    logging.info(f"Preprocessed directory: {preprocessed_path}")
    preprocessed_path.mkdir(parents=True, exist_ok=True)

    unique_values = db.get_unique_values()

    # unique_values = _get_unique_values(str(Path(db_directory_path) / f"{db_id}.sqlite"))
    logging.info("Unique values obtained")

    with open(preprocessed_path / f"{db_name}_unique_values.pkl", "wb") as file:
        pickle.dump(unique_values, file)
    logging.info("Saved unique values")

    # Extract workspace_id if present in kwargs
    workspace_id = kwargs.pop('workspace_id', None)
    
    lsh, minhashes = make_lsh(unique_values, **kwargs, workspace_id=workspace_id, processed_items_offset=0)

    with open(preprocessed_path / f"{db_name}_lsh.pkl", "wb") as file:
        pickle.dump(lsh, file)
    with open(preprocessed_path / f"{db_name}_minhashes.pkl", "wb") as file:
        pickle.dump(minhashes, file)
    
    # Return the number of processed items
    total_unique_values = sum(
        len(column_values)
        for table_values in unique_values.values()
        for column_values in table_values.values()
    )
    return total_unique_values
