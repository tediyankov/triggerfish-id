#!/bin/bash

# config

SCRIPT_DIR="/gws/nopw/j04/iecdt/tyankov/triggerfish-id/code"
PYTHON_SCRIPT="$SCRIPT_DIR/inaturalist_scraper.py"
OUTPUT_DIR="gws/nopw/j04/iecdt/triggerfish-id/data/inaturalist"

SPECIES=(
    "Rhinecanthus aculeatus" # Picasso triggerfish
)

# settings
OBSERVATIONS=4000 # max observations per species
QUALITY="research" # research | needs_id | casual | any
IMAGE_SIZE="large" # small | medium | large | original
LICENSE="any" # any | cc-by | cc-by-nc | cc-by-nc-nd | cc-by-nc-sa | cc-by-nd | cc-by-sa | cc0

if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    echo "ERROR : Python script not found at $PYTHON_SCRIPT"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "ERROR : python3 not found"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

# running the scraper for each species

echo ""
echo "======================================================================"
echo "iNaturalist scraper — $(date '+%Y-%m-%d %H:%M:%S')"
echo "Species count: ${#SPECIES[@]}"
echo "Output dir: $OUTPUT_DIR"
echo "======================================================================"
echo ""

for species in "${SPECIES[@]}"; do
    echo ">>> Starting: $species"
    python3 "$PYTHON_SCRIPT" \
        --species "$species" \
        --observations "$OBSERVATIONS" \
        --quality "$QUALITY" \
        --image-size "$IMAGE_SIZE" \
        --license "$LICENSE" \
        --output-dir "$OUTPUT_DIR"

    exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        echo "ERROR : Scraper exited with code $exit_code for '$species'"
        echo "Continuing with next species..."
    fi

    echo ">>> Finished: $species"
    echo ""
done

echo "======================================================================"
echo "  All species processed — $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================================"
echo ""