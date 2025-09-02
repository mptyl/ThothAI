// Copyright (c) 2025 Marco Pancotti
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//     http://www.apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/**
 * Centralized AbortController management for cancellation support
 */
export class AbortManager {
  private controllers: Map<string, AbortController> = new Map();
  private static instance: AbortManager;

  private constructor() {
    // Singleton pattern
  }

  static getInstance(): AbortManager {
    if (!AbortManager.instance) {
      AbortManager.instance = new AbortManager();
      // Expose for testing in development
      if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
        (window as any).__abortManager = AbortManager.instance;
      }
    }
    return AbortManager.instance;
  }

  /**
   * Create a new AbortController for a specific operation
   */
  createController(id: string): AbortController {
    // Cancel existing controller if it exists
    this.abort(id);
    
    const controller = new AbortController();
    this.controllers.set(id, controller);
    
    console.log(`[AbortManager] Created controller for: ${id}`);
    return controller;
  }

  /**
   * Get an existing controller
   */
  getController(id: string): AbortController | undefined {
    return this.controllers.get(id);
  }

  /**
   * Abort a specific operation
   */
  abort(id: string, reason?: string): boolean {
    const controller = this.controllers.get(id);
    if (controller) {
      controller.abort(reason);
      this.controllers.delete(id);
      console.log(`[AbortManager] Aborted controller: ${id}`, reason || '');
      return true;
    }
    return false;
  }

  /**
   * Abort all active operations
   */
  abortAll(reason?: string): void {
    console.log(`[AbortManager] Aborting all ${this.controllers.size} controllers`);
    this.controllers.forEach((controller, id) => {
      controller.abort(reason);
      console.log(`[AbortManager] Aborted: ${id}`);
    });
    this.controllers.clear();
  }

  /**
   * Clean up a controller after operation completes
   */
  cleanup(id: string): void {
    if (this.controllers.delete(id)) {
      console.log(`[AbortManager] Cleaned up controller: ${id}`);
    }
  }

  /**
   * Check if a controller exists and is active
   */
  isActive(id: string): boolean {
    const controller = this.controllers.get(id);
    return controller !== undefined && !controller.signal.aborted;
  }

  /**
   * Get the number of active controllers
   */
  getActiveCount(): number {
    return this.controllers.size;
  }

  /**
   * Get all active controller IDs
   */
  getActiveIds(): string[] {
    return Array.from(this.controllers.keys());
  }
}

// Export singleton instance
export const abortManager = AbortManager.getInstance();