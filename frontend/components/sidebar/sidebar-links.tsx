// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React from 'react';
import Link from 'next/link';

export function SidebarLinks() {
  const adminUrl = process.env.NEXT_PUBLIC_DJANGO_SERVER 
    ? `${process.env.NEXT_PUBLIC_DJANGO_SERVER}/admin/`
    : 'http://localhost:8200/admin/';

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
        href={adminUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="block text-sm text-gray-300 hover:text-white transition-colors"
      >
        Admin
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