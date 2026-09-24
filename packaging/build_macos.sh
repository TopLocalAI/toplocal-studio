#!/usr/bin/env bash
# Build "TopLocal Studio.app" and a drag-to-install DMG.
#   packaging/build_macos.sh            → app/src-tauri/target/release/bundle/{macos,dmg}/
# Signing: ad-hoc by default. For distribution:
#   APPLE_SIGNING_IDENTITY="Developer ID Application: …"   sign with a Developer ID (secure timestamp)
#   NOTARY_PROFILE=<keychain profile>                       also notarize + staple the DMG
# Create the profile once with:
#   xcrun notarytool store-credentials <profile> --apple-id <id> --team-id <team> --password <app-specific password>
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE="$ROOT/app/src-tauri/target/release/bundle"
APP="$BUNDLE/macos/TopLocal Studio.app"
VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$ROOT/app/src-tauri/tauri.conf.json")"
DMG="$BUNDLE/dmg/TopLocal-Studio-$VERSION-arm64.dmg"

if [ "${SKIP_BUILD:-0}" != 1 ]; then
  "$ROOT/packaging/build_runtime.sh"
  (cd "$ROOT/app" && npx tauri build --bundles app)
fi

IDENTITY="${APPLE_SIGNING_IDENTITY:--}"
# A Developer ID signature needs Apple's secure timestamp for notarization; ad-hoc cannot have one.
if [ "$IDENTITY" = "-" ]; then TS="--timestamp=none"; else TS="--timestamp"; fi
ENT="$ROOT/packaging/entitlements.plist"
# Sign nested code first, then the app. Executables (python3.12, engines) need the same
# entitlements as the app: with the hardened runtime, library validation would otherwise
# stop python3.12 from loading its own libpython (ad-hoc signatures carry no Team ID).
find "$APP/Contents/Resources" -type f \( -name "*.dylib" -o -name "*.so" \) -print0 \
  | xargs -0 -n 50 codesign --force "$TS" -s "$IDENTITY"
find "$APP/Contents/Resources" -type f -perm -u+x ! -name "*.dylib" ! -name "*.so" -print0 \
  | while IFS= read -r -d '' f; do
      if file -b "$f" | grep -q "Mach-O"; then
        codesign --force "$TS" --options runtime --entitlements "$ENT" -s "$IDENTITY" "$f"
      fi
    done
codesign --force "$TS" --options runtime \
  --entitlements "$ENT" -s "$IDENTITY" "$APP"
codesign --verify --deep --strict "$APP"

STAGE="$(mktemp -d)"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
mkdir -p "$(dirname "$DMG")"
rm -f "$DMG"
hdiutil create -volname "TopLocal Studio" -srcfolder "$STAGE" -fs HFS+ -format UDZO -imagekey zlib-level=9 "$DMG" >/dev/null
rm -rf "$STAGE"
if [ "$IDENTITY" != "-" ]; then
  codesign --force --timestamp -s "$IDENTITY" "$DMG"
fi
if [ -n "${NOTARY_PROFILE:-}" ]; then
  xcrun notarytool submit "$DMG" --keychain-profile "$NOTARY_PROFILE" --wait
  xcrun stapler staple "$DMG"
  spctl -a -t open --context context:primary-signature -vv "$DMG"
fi
du -sh "$APP" "$DMG"
