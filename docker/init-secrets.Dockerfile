# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

FROM python:3.11-alpine
WORKDIR /app
COPY docker/scripts/generate-django-secret.py /app/
CMD ["python", "generate-django-secret.py"]