# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Gunicorn configuration file
import multiprocessing

# Bind to this socket
bind = "0.0.0.0:8000"

# Number of worker processes - optimized for Django applications
# Using fewer workers to reduce plugin registration spam and improve performance
workers = min(4, multiprocessing.cpu_count() + 1)

# Timeout for worker processes (in seconds)
timeout = 120

# Maximum number of requests a worker will process before restarting
max_requests = 1000
max_requests_jitter = 50

# Process name
proc_name = "thoth_gunicorn"

# Access log format
accesslog = "-"
errorlog = "-"

# Log level
loglevel = "info"