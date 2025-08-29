# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

import logging
import sqlite3
import threading
from enum import Enum
from typing import Any, Dict, List, Union

from func_timeout import FunctionTimedOut, func_timeout
from sqlglot import parse_one, exp



class ExecutionStatus(Enum):
    SYNTACTICALLY_CORRECT = "SYNTACTICALLY_CORRECT"
    EMPTY_RESULT = "EMPTY_RESULT"
    NONE_RESULT = "NONE_RESULT"
    ZERO_COUNT_RESULT = "ZERO_COUNT_RESULT"
    ALL_NONE_RESULT = "ALL_NONE_RESULT"
    SYNTACTICALLY_INCORRECT = "SYNTACTICALLY_INCORRECT"

def execute_sql(db_path: str, sql: str, fetch: Union[str, int] = "all", timeout: int = 60) -> Any:
    class QueryThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.result = None
            self.exception = None

        def run(self):
            logging.debug(f"Database path:{db_path}")
            try:
                with sqlite3.connect(db_path, timeout=60) as conn:
                    cursor = conn.cursor()
                    cursor.execute(sql)
                    if fetch == "all":
                        self.result = cursor.fetchall()
                    elif fetch == "one":
                        self.result = cursor.fetchone()
                    elif fetch == "random":
                        samples = cursor.fetchmany(10)
                        import random
                        self.result = random.choice(samples) if samples else []
                    elif isinstance(fetch, int):
                        self.result = cursor.fetchmany(fetch)
                    else:
                        raise ValueError("Invalid fetch argument. Must be 'all', 'one', 'random', or an integer.")
            except Exception as e:
                self.exception = e
    query_thread = QueryThread()
    query_thread.start()
    query_thread.join(timeout)
    if query_thread.is_alive():
        raise TimeoutError(f"SQL query execution exceeded the timeout of {timeout} seconds.")
    if query_thread.exception:
        # logging.error(f"Error in execute_sql: {query_thread.exception}\nSQL: {sql}")
        raise query_thread.exception
    return query_thread.result

def _clean_sql(sql: str) -> str:
    """
    Cleans the SQL query by removing unwanted characters and whitespace.
    
    Args:
        sql (str): The SQL query string.
        
    Returns:
        str: The cleaned SQL query string.
    """
    return sql.replace('\n', ' ').replace('"', "'").strip("`.")


def _compare_sqls_outcomes(db_path: str, predicted_sql: str, ground_truth_sql: str) -> int:
    """
    Compares the outcomes of two SQL queries to check for equivalence.
    
    Args:
        db_path (str): The path to the database file.
        predicted_sql (str): The predicted SQL query.
        ground_truth_sql (str): The ground truth SQL query.
        
    Returns:
        int: 1 if the outcomes are equivalent, 0 otherwise.
    
    Raises:
        Exception: If an error occurs during SQL execution.
    """
    try:
        predicted_res = execute_sql(db_path, predicted_sql)
        ground_truth_res = execute_sql(db_path, ground_truth_sql)
        return int(set(predicted_res) == set(ground_truth_res))
    except Exception as e:
        logging.critical(f"Error comparing SQL outcomes: {e}")
        raise e

def compare_sqls(db_path: str, predicted_sql: str, ground_truth_sql: str, meta_time_out: int = 30) -> Dict[str, Union[int, str]]:
    """
    Compares predicted SQL with ground truth SQL within a timeout.
    
    Args:
        db_path (str): The path to the database file.
        predicted_sql (str): The predicted SQL query.
        ground_truth_sql (str): The ground truth SQL query.
        meta_time_out (int): The timeout for the comparison.
        
    Returns:
        dict: A dictionary with the comparison result and any error message.
    """
    predicted_sql = _clean_sql(predicted_sql)
    try:
        res = func_timeout(meta_time_out, _compare_sqls_outcomes, args=(db_path, predicted_sql, ground_truth_sql))
        error = "incorrect answer" if res == 0 else "--"
    except FunctionTimedOut:
        logging.warning("Comparison timed out.")
        error = "timeout"
        res = 0
    except Exception as e:
        logging.error(f"Error in compare_sqls: {e}")
        error = str(e)
        res = 0
    return {'exec_res': res, 'exec_err': error}

def validate_sql_query(db_path: str, sql: str, max_returned_rows: int = 30) -> Dict[str, Union[str, Any]]:
    """
    Validates an SQL query by executing it and returning the result.
    
    Args:
        db_path (str): The path to the database file.
        sql (str): The SQL query to validate.
        max_returned_rows (int): The maximum number of rows to return.
        
    Returns:
        dict: A dictionary with the SQL query, result, and status.
    """
    try:
        result = execute_sql(db_path, sql, fetch=max_returned_rows)
        return {"SQL": sql, "RESULT": result, "STATUS": "OK"}
    except Exception as e:
        logging.error(f"Error in validate_sql_query: {e}")
        return {"SQL": sql, "RESULT": str(e), "STATUS": "ERROR"}

    
def get_execution_status(db_path: str, sql: str, execution_result: List = None) -> ExecutionStatus:
    """
    Determines the status of an SQL query execution result.
    
    Args:
        execution_result (List): The result of executing an SQL query.
        
    Returns:
        ExecutionStatus: The status of the execution result.
    """
    if not execution_result:
        try:
            execution_result = execute_sql(db_path, sql, fetch="all")
        except FunctionTimedOut:
            logging.warning("Timeout in get_execution_status")
            return ExecutionStatus.SYNTACTICALLY_INCORRECT
        except Exception:
            return ExecutionStatus.SYNTACTICALLY_INCORRECT   
    if (execution_result is None) or (execution_result == []):
        return ExecutionStatus.EMPTY_RESULT
    elif len(execution_result) == 1:
        if execution_result[0] is None or execution_result[0][0] is None:
            return ExecutionStatus.NONE_RESULT
        elif len(execution_result[0]) == 1 and execution_result[0][0] == 0: # suspicious of a failed agg query
            select_expression = list(parse_one(sql, read='sqlite').find_all(exp.Select))[0].expressions[0]
            if isinstance(select_expression, exp.Count):
                return ExecutionStatus.ZERO_COUNT_RESULT
    elif all([all([val is None for val in res]) for res in execution_result]):
        return ExecutionStatus.ALL_NONE_RESULT
    return ExecutionStatus.SYNTACTICALLY_CORRECT
