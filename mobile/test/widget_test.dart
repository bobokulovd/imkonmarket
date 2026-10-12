// `flutter create .` (setup.sh) mavjud faylni qayta yozmaydi — aks holda u `MyApp`ga
// murojaat qiluvchi shablon test yaratib, `flutter analyze` xato beradi.
import 'package:flutter_test/flutter_test.dart';
import 'package:imkonmarket/core/state.dart';

void main() {
  test('fmtDate', () {
    expect(fmtDate(null), '');
    expect(fmtDate('2026-01-05'), '05.01.2026');
  });

  test('CartLine: eski format va variant', () {
    final old = CartLine({'id': 1, 'price': '100.00', 'available': 5, 'min_order': 1}, 2);
    expect(old.variantId, null);
    expect(old.price, '100.00');
    expect(old.toJson().containsKey('variant'), false);
    final v = CartLine({'id': 2, 'price': '50.00', 'has_variants': true}, 1,
        CartLine.slimVariant({'id': 7, 'sku': 'X-1', 'price': '70.00', 'available': null, 'extra': 1}));
    expect(v.price, '70.00');
    expect(v.available, null);
    expect(v.needsVariant, false);
    expect(v.toJson()['variant'], {'id': 7, 'sku': 'X-1', 'price': '70.00', 'available': null});
    expect(CartLine({'id': 3, 'has_variants': true}, 1).needsVariant, true);
  });
}
