#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

# Script to clean Antigravity cache across all relevant directories,
# keeping only the most recent N conversations based on the 'brain' directory.
# Usage: ./cleanup-antigravity-cache.sh [keep_count]

KEEP=${1:-10}
ANTIGRAVITY_DIR="$HOME/.gemini/antigravity"
BRAIN_DIR="$ANTIGRAVITY_DIR/brain"
CONVERSATIONS_DIR="$ANTIGRAVITY_DIR/conversations"
ANNOTATIONS_DIR="$ANTIGRAVITY_DIR/annotations"
IMPLICIT_DIR="$ANTIGRAVITY_DIR/implicit"

# Verify that BRAIN_DIR exists
if [ ! -d "$BRAIN_DIR" ]; then
    echo "❌ Brain directory $BRAIN_DIR not found"
    exit 1
fi

# Total number of conversations
TOTAL=$(find "$BRAIN_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | xargs)

echo "📊 Total conversations: $TOTAL"
echo "✅ Conversations to keep: $KEEP"

if [ "$TOTAL" -le "$KEEP" ]; then
    echo "✨ No conversations to delete (total: $TOTAL <= keep: $KEEP)"
    exit 0
fi

TO_DELETE=$((TOTAL - KEEP))
echo "🗑️  Conversations to delete: $TO_DELETE"
echo ""

# Get the list of directory paths in brain, sorted by modification time (oldest first)
# and get only those that should be deleted.
OLD_CONVS=$(find "$BRAIN_DIR" -mindepth 1 -maxdepth 1 -type d -print0 | \
    xargs -0 stat -f "%m %N" | \
    sort -n | \
    head -n "$TO_DELETE" | \
    cut -d' ' -f2-)

# Calculate space before
SPACE_BEFORE=$(du -sh "$ANTIGRAVITY_DIR" | cut -f1)
echo "📦 Space before: $SPACE_BEFORE"

IFS=$'\n'
for path in $OLD_CONVS; do
    conv_id=$(basename "$path")
    timestamp=$(stat -f "%m" "$path")
    last_modified=$(date -r "$timestamp" "+%Y-%m-%d %H:%M:%S")
    
    echo "🗑️  Deleting conversation: $conv_id (last modified: $last_modified)"
    
    # Delete from brain (directory)
    rm -rf "$BRAIN_DIR/$conv_id"
    
    # Delete from conversations (.pb file)
    rm -f "$CONVERSATIONS_DIR/$conv_id.pb"
    
    # Delete from annotations (.pbtxt file)
    rm -f "$ANNOTATIONS_DIR/$conv_id.pbtxt"
    
    # Delete from implicit (.pb file)
    rm -f "$IMPLICIT_DIR/$conv_id.pb"
done

echo ""
echo "✅ Cleanup complete!"

# Space after
SPACE_AFTER=$(du -sh "$ANTIGRAVITY_DIR" | cut -f1)
echo "📦 Space after: $SPACE_AFTER"

# Remaining count
REMAINING=$(find "$BRAIN_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | xargs)
echo "📊 Conversations remaining: $REMAINING"
