#!/bin/bash

# Save Runner native report files to attachments
save_native_report() {
    local native_report_path="$1"
    echo "🔧 Saving native report from: ${native_report_path:-<not specified>}"

    if [ -z "$native_report_path" ]; then
        echo "❌ Error: Native report path not provided."
        return 1
    fi

    if [ -d "$native_report_path" ] && [ "$(ls -A "$native_report_path")" ]; then
      echo "📦 Copying report files from $native_report_path to $TMP_DIR/attachments..."
      cp -r "$native_report_path/." "$TMP_DIR/attachments/"
      echo "✅ Native report successfully copied to attachments."
    else
      echo "⚠️ No files found in $native_report_path or directory does not exist."
    fi
}

