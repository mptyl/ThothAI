// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

import { useEffect, useState } from 'react';

// Module-level cache: undefined = not yet fetched, null = no Athena, string = origin URL
let cached: string | null | undefined = undefined;

/**
 * Returns the Athena origin URL from runtime config (/api/config → RUNTIME_ATHENA_ORIGIN).
 * Returns null if Athena integration is not configured (standalone ThothAI mode).
 * Returns undefined while the first fetch is in progress.
 */
export function useAthenaOrigin(): string | null | undefined {
  const [origin, setOrigin] = useState<string | null | undefined>(cached);

  useEffect(() => {
    if (cached !== undefined) {
      setOrigin(cached);
      return;
    }

    fetch('/api/config')
      .then(r => r.json())
      .then(cfg => {
        cached = cfg.athenaOrigin || null;
        setOrigin(cached);
      })
      .catch(() => {
        cached = null;
        setOrigin(null);
      });
  }, []);

  return origin;
}
