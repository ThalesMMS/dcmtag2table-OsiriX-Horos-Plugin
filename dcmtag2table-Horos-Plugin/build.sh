#!/bin/bash

# Build script for dcmtag2tableHorosPlugin
# Usage: ./build.sh [horos|osirix]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/dcmtag2tableHorosPlugin.xcodeproj"
RELEASES_DIR="$(dirname "$SCRIPT_DIR")/Releases"

usage() {
    echo "Usage: $0 [horos|osirix|both]"
    echo "  horos  - Build for Horos"
    echo "  osirix - Build for OsiriX"
    echo "  both   - Build for both platforms"
    exit 1
}

build_for_platform() {
    local PLATFORM="$1"
    local PLATFORM_UPPER=$(echo "$PLATFORM" | tr '[:lower:]' '[:upper:]' | sed 's/OSIRIX/OsiriX/' | sed 's/HOROS/Horos/')

    echo "========================================"
    echo "Building for $PLATFORM_UPPER..."
    echo "========================================"

    # Copy platform-specific files
    echo "Copying $PLATFORM_UPPER project files..."
    cp "$PROJECT_DIR/project_${PLATFORM_UPPER}.pbxproj" "$PROJECT_DIR/project.pbxproj"
    cp "$SCRIPT_DIR/dcmtag2tableHorosPlugin-Bridging-Header_${PLATFORM_UPPER}.h" "$SCRIPT_DIR/dcmtag2tableHorosPlugin-Bridging-Header.h"

    # Clean and build
    echo "Building..."
    xcodebuild -project "$PROJECT_DIR" -configuration Release clean build 2>&1 | grep -E "(BUILD|error:|warning:)" || true

    # Check if build succeeded
    if [ -d "$SCRIPT_DIR/build/Release/dcmtag2tableHorosPlugin.osirixplugin" ]; then
        echo "Build successful!"

        # Create releases directory if needed
        mkdir -p "$RELEASES_DIR/$PLATFORM_UPPER"

        # Copy to releases
        rm -rf "$RELEASES_DIR/$PLATFORM_UPPER/dcmtag2tableHorosPlugin.osirixplugin"
        cp -R "$SCRIPT_DIR/build/Release/dcmtag2tableHorosPlugin.osirixplugin" "$RELEASES_DIR/$PLATFORM_UPPER/"

        # Create zip
        echo "Creating zip..."
        cd "$RELEASES_DIR/$PLATFORM_UPPER"
        rm -f dcmtag2tableHorosPlugin.osirixplugin.zip
        zip -r -q dcmtag2tableHorosPlugin.osirixplugin.zip dcmtag2tableHorosPlugin.osirixplugin
        cd - > /dev/null

        echo "Plugin copied to: $RELEASES_DIR/$PLATFORM_UPPER/"
        echo "Zip created: $RELEASES_DIR/$PLATFORM_UPPER/dcmtag2tableHorosPlugin.osirixplugin.zip"
    else
        echo "Build failed!"
        exit 1
    fi
}

# Main
case "${1:-}" in
    horos)
        build_for_platform "horos"
        ;;
    osirix)
        build_for_platform "osirix"
        ;;
    both)
        build_for_platform "horos"
        echo ""
        build_for_platform "osirix"
        echo ""
        echo "========================================"
        echo "Both builds completed successfully!"
        echo "========================================"
        ;;
    *)
        usage
        ;;
esac
