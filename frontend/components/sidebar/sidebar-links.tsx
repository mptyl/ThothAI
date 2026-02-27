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

    const token   = typeof window !== 'undefined'
      ? (localStorage.getItem('thoth_token') || sessionStorage.getItem('thoth_token'))
      : null;
    const userStr = typeof window !== 'undefined'
      ? (localStorage.getItem('thoth_user') || sessionStorage.getItem('thoth_user'))
      : null;
    let user: { is_superuser?: boolean } | null = null;
    try {
      user = userStr ? JSON.parse(userStr) : null;
    } catch {
      user = null;
    }
    const base    = baseUrl.replace(/\/$/, '');

    if (user?.is_superuser && token) {
      // Superuser: silent SSO — no second login required
      window.location.href =
        `${base}/auth/admin-callback/?token=${token}&next=/admin/`;
    } else {
      // Non-superuser or no token: redirect to Django admin login form
      window.location.href = `${base}/admin/login/`;
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
      {process.env.NEXT_PUBLIC_ATHENA_ORIGIN && (
        <a
          href={process.env.NEXT_PUBLIC_ATHENA_ORIGIN}
          target="_blank"
          rel="noopener noreferrer"
          className="block text-sm text-gray-300 hover:text-white transition-colors"
        >
          Athena
        </a>
      )}
      <Link
        href="/"
        className="block text-sm text-gray-300 hover:text-white transition-colors"
      >
        Home
      </Link>
    </div>
  );
}