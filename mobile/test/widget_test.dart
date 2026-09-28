// `flutter create .` (setup.sh) mavjud faylni qayta yozmaydi — aks holda u `MyApp`ga
// murojaat qiluvchi shablon test yaratib, `flutter analyze` xato beradi.
import 'package:flutter_test/flutter_test.dart';
import 'package:ustabozor/core/state.dart';

void main() {
  test('fmtDate', () {
    expect(fmtDate(null), '');
    expect(fmtDate('2026-01-05'), '05.01.2026');
  });
}
