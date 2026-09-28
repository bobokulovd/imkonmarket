#!/usr/bin/env bash
# Android/iOS platforma papkalarini yaratadi va kerakli ruxsatlarni qo'shadi.
# Ishlatish:  cd mobile && bash setup.sh
set -e
flutter create . --platforms=android,ios --org uz.imkonmarket --project-name imkonmarket
M=android/app/src/main/AndroidManifest.xml
if ! grep -q "android.permission.INTERNET" "$M"; then
  sed -i.bak 's#<application#<uses-permission android:name="android.permission.INTERNET"/>\n    <application#' "$M"
fi
# Test serverlar uchun http (production'da https ishlating)
grep -q usesCleartextTraffic "$M" || sed -i.bak 's#<application#<application android:usesCleartextTraffic="true"#' "$M"
# url_launcher (Android 11+): brauzer / PDF ochish
grep -q 'android.intent.action.VIEW' "$M" || sed -i.bak 's#</manifest>#    <queries>\n        <intent><action android:name="android.intent.action.VIEW"/><data android:scheme="https"/></intent>\n        <intent><action android:name="android.intent.action.VIEW"/><data android:scheme="http"/></intent>\n    </queries>\n</manifest>#' "$M"
sed -i.bak "s/android:label=\"[^\"]*\"/android:label=\"ImkonMarket\"/" "$M"
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName ImkonMarket" ios/Runner/Info.plist 2>/dev/null || true
rm -f "$M.bak"
flutter pub get
echo "Tayyor. Ishga tushirish: flutter run --dart-define=API_URL=http://10.0.2.2:8000"
