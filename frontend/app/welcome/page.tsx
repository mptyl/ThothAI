// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

import { ProtectedRoute } from '@/components/protected-route';
import { WelcomeScreen } from '@/components/welcome-screen';

export default function WelcomePage() {
  return (
    <ProtectedRoute>
      <WelcomeScreen />
    </ProtectedRoute>
  );
}