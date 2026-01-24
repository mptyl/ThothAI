// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React from 'react';
import Link from 'next/link';

interface SidebarLinksProps {
  backendUrl?: string;
}

export function SidebarLinks({ backendUrl: runtimeBackendUrl }: SidebarLinksProps) {
  // Use runtime value if provided, otherwise fallback to build-time embedded value
  const baseUrl = runtimeBackendUrl || process.env.NEXT_PUBLIC_DJANGO_SERVER || 'http://localhost:8200';

  // Function to handle backend link click with token passing
  const handleBackendClick = (e: React.MouseEvent) => {
    e.preventDefault();

    // Try to get the token from localStorage
    const token = typeof window !== 'undefined' ? localStorage.getItem('thoth_token') : null;

    if (token) {
      // If we have a token, pass it to backend for seamless auth
      window.location.href = `${baseUrl.replace(/\/$/, '')}/auth/admin-callback/?token=${token}`;
    } else {
      // No token, just go to backend home (will require login)
      window.location.href = `${baseUrl.replace(/\/$/, '')}/`;
    }
  };

  return (
    <div className="space-y-2">
      <Link
        href="/settings"
        className="block text-sm text-gray-300 hover:text-white transition-colors"
      >
        ⚙️ Settings
      </Link>
      <Link
        href="/about"
        className="block text-sm text-gray-300 hover:text-white transition-colors"
      >
        About
      </Link>
      <Link
        href="/documentation"
        className="block text-sm text-gray-300 hover:text-white transition-colors"
      >
        Documentation
      </Link>

      {/* Separator */}
      <div className="border-t border-gray-600 my-3"></div>

      <a
        href="#"
        onClick={handleBackendClick}
        className="block text-sm text-gray-300 hover:text-white transition-colors"
      >
        Backend
      </a>
      <Link
        href="/"
        className="block text-sm text-gray-300 hover:text-white transition-colors"
      >
        Home
      </Link>
    </div>
  );
}