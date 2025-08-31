# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

FROM alpine:latest

WORKDIR /init

# Copy data directory from build context
COPY ./data /init/data

# Script to copy data to shared volume
RUN echo '#!/bin/sh' > /init/copy-data.sh && \
    echo 'echo "Initializing shared data volume..."' >> /init/copy-data.sh && \
    echo 'cp -r /init/data/* /shared_data/ 2>/dev/null || true' >> /init/copy-data.sh && \
    echo 'echo "Data initialization complete."' >> /init/copy-data.sh && \
    chmod +x /init/copy-data.sh

CMD ["/init/copy-data.sh"]