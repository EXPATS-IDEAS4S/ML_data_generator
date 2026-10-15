#!/usr/bin/env bash

set -euo pipefail

# Source directory containing the generated .nc files.
SRC_DIR="/sat_data/crops/crops_IR_108_CMA_100x100_2006-2024_3-randomcrops/nc/2021-2025"

# Destination directory for the yearly tar.gz archives.
ARCHIVE_DIR="/sat_data/crops/crops_IR_108_CMA_100x100_2006-2024_3-randomcrops/tar"

# Archive name prefix.
ARCHIVE_PREFIX="nc"

mkdir -p "$ARCHIVE_DIR"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

# Build one NUL-separated file list per year.
while IFS= read -r -d '' file_name; do
    if [[ "$file_name" =~ ([0-9]{4})-[0-9]{2}-[0-9]{2} ]]; then
        year="${BASH_REMATCH[1]}"
        printf '%s\0' "$file_name" >> "$tmp_dir/${year}.list"
    fi
done < <(find "$SRC_DIR" -maxdepth 1 -type f -name '*.nc' -printf '%P\0')

# Create one tar.gz per year.
shopt -s nullglob
for list_file in "$tmp_dir"/*.list; do
    year="$(basename "$list_file" .list)"
    archive_path="$ARCHIVE_DIR/${ARCHIVE_PREFIX}_${year}.tar.gz"

    tar -czf "$archive_path" \
        -C "$SRC_DIR" \
        --null \
        --files-from="$list_file" \
        --transform="s|^|${year}/|"

    echo "Created $archive_path"
done
