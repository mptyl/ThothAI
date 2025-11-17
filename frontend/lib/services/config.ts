// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

export function getApiConfig() {
  return {
    djangoServer: process.env.DJANGO_SERVER || 'http://localhost:8200',
    djangoApiKey: process.env.DJANGO_API_KEY || '3LHoZzYlGGsvdamksrcZYlah3H5IArxYnLkrSTBB9pg'
  };
}