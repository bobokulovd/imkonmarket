import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api.dart';

typedef J = Map<String, dynamic>;

const langs = <String, String>{
  'uz': "O'zbekcha",
  'uz_cyrl': 'Ўзбекча',
  'uz_new': 'Ózbekçe (yangi)',
  'ru': 'Русский',
  'kaa': 'Qaraqalpaqsha',
  'en': 'English',
};

/// Til, meta-ma'lumot (kategoriyalar, hududlar, sotuvchilar) va savat.
class AppState extends ChangeNotifier {
  String lang = 'uz';
  Map<String, Map<String, String>> _dicts = {};
  J? meta;
  final List<CartLine> cart = [];
  J? me; // sotuvchi profili (kabinetga kirilgan bo'lsa)

  Future<void> init() async {
    for (final l in langs.keys) {
      final raw = await rootBundle.loadString('assets/i18n/$l.json');
      _dicts[l] = (jsonDecode(raw) as Map).map((k, v) => MapEntry(k as String, v.toString()));
    }
    final p = await SharedPreferences.getInstance();
    lang = p.getString('lang') ?? 'uz';
    final saved = p.getString('cart');
    if (saved != null) {
      try {
        for (final e in jsonDecode(saved) as List) {
          // eski format: {product, qty} — variant yo'q; yangi: {product, variant?, qty}
          final v = e['variant'];
          cart.add(CartLine(Map<String, dynamic>.from(e['product']), (e['qty'] as num).toInt(),
              v is Map ? Map<String, dynamic>.from(v) : null));
        }
      } catch (_) {}
    }
    await Api.i.loadTokens();
    notifyListeners();
    loadMeta();
    if (Api.i.authed) loadMe();
  }

  Future<void> loadMeta() async {
    try {
      meta = Map<String, dynamic>.from(await Api.i.get('/meta/'));
      notifyListeners();
    } catch (_) {}
  }

  Future<void> loadMe() async {
    try {
      me = Map<String, dynamic>.from(await Api.i.get('/auth/me/', auth: true));
    } catch (_) {
      me = null;
      await Api.i.clearTokens();
    }
    notifyListeners();
  }

  Future<void> logout() async {
    await Api.i.clearTokens();
    me = null;
    notifyListeners();
  }

  Future<void> setLang(String l) async {
    lang = l;
    notifyListeners();
    final p = await SharedPreferences.getInstance();
    await p.setString('lang', l);
  }

  /// Interfeys matni: t('add_to_cart'), t('in_stock', {'n': 5, 'unit': 'dona'})
  String t(String key, [Map<String, Object?>? vars]) {
    var s = _dicts[lang]?[key] ?? _dicts['uz']?[key] ?? key;
    vars?.forEach((k, v) => s = s.replaceAll('{$k}', '$v'));
    return s;
  }

  /// Ko'p tilli maydon: {"uz": "...", "ru": "..."}
  String p(dynamic d) {
    if (d is! Map) return d?.toString() ?? '';
    final v = d[lang] ?? d['uz'];
    if (v != null && v.toString().isNotEmpty) return v.toString();
    return d.values.firstWhere((x) => x != null && x.toString().isNotEmpty, orElse: () => '').toString();
  }

  String money(dynamic v) {
    if (v == null || v.toString().isEmpty) return '';
    final n = num.tryParse(v.toString()) ?? 0;
    final s = NumberFormat.decimalPattern('ru').format(n).replaceAll(' ', ' ');
    return '$s ${t('sum')}';
  }

  String unit(String u) {
    final s = p((meta?['units'] as Map?)?[u]);
    return s.isEmpty ? u : s;
  }

  List<J> get categories => ((meta?['categories'] as List?) ?? []).cast<J>();
  List<J> get sellers => ((meta?['sellers'] as List?) ?? []).cast<J>();
  List<J> get regions => ((meta?['regions'] as List?) ?? []).cast<J>();
  J? category(String slug) => categories.where((c) => c['slug'] == slug).firstOrNull;
  bool demo(String method) => (((meta?['payments'] as Map?)?[method] as Map?)?['demo'] as bool?) ?? true;

  // -------- savat (qator kaliti: mahsulot id + variant id)
  int get cartCount => cart.length;

  /// Mahsulotning (istalgan varianti) savatda bormi.
  bool inCart(int id) => cart.any((l) => l.productId == id);

  /// Aniq mahsulot + variant savatda bormi.
  bool inCartLine(int id, int? variantId) => cart.any((l) => l.productId == id && l.variantId == variantId);

  int _clamp(CartLine l, int q) {
    final min = l.minOrder;
    var v = q < min ? min : q;
    final av = l.available;
    if (av != null && v > av) v = av;
    return v;
  }

  /// [variant] — mahsulot tafsilotidagi `variants` elementi (has_variants bo'lsa majburiy).
  void addToCart(J p, [int qty = 1, J? variant]) {
    final vid = variant?['id'] as int?;
    final ex = cart.where((l) => l.productId == p['id'] && l.variantId == vid).firstOrNull;
    if (ex != null) {
      ex.qty = _clamp(ex, ex.qty + qty);
    } else {
      final l = CartLine(CartLine.slimProduct(p), qty, variant == null ? null : CartLine.slimVariant(variant));
      l.qty = _clamp(l, qty);
      cart.add(l);
    }
    _saveCart();
  }

  void setQty(CartLine line, int qty) {
    if (cart.contains(line)) line.qty = _clamp(line, qty);
    _saveCart();
  }

  void removeFromCart(CartLine line) {
    cart.remove(line);
    _saveCart();
  }

  void clearCart() {
    cart.clear();
    _saveCart();
  }

  double get cartTotal => cart.fold<double>(0.0, (s, l) => s + (double.tryParse('${l.price}') ?? 0) * l.qty);

  /// Variant tanlanmagan variantli mahsulot qatorlari (eski savatdan qolgan bo'lishi mumkin).
  bool get cartNeedsVariant => cart.any((l) => l.needsVariant);

  Map<String, List<CartLine>> get cartBySeller {
    final m = <String, List<CartLine>>{};
    for (final l in cart) {
      m.putIfAbsent(l.product['seller']['code'] as String, () => []).add(l);
    }
    return m;
  }

  Future<void> _saveCart() async {
    notifyListeners();
    final p = await SharedPreferences.getInstance();
    await p.setString('cart', jsonEncode(cart.map((l) => l.toJson()).toList()));
  }
}

class CartLine {
  J product;
  int qty;

  /// Tanlangan variant: {id, sku, label, price, available, image_url, attributes}
  J? variant;
  CartLine(this.product, this.qty, [this.variant]);

  int get productId => product['id'] as int;
  int? get variantId => variant?['id'] as int?;
  String get key => '$productId:${variantId ?? ''}';

  /// Variantning narxi (variant narxi backendda mahsulot narxiga tushib qoladi).
  dynamic get price => variant != null ? variant!['price'] : product['price'];
  int? get available => variant != null ? variant!['available'] as int? : product['available'] as int?;
  String get sku => (variant?['sku'] ?? product['sku'] ?? '').toString();
  String? get image {
    final u = variant?['image_url'];
    if (u is String && u.isNotEmpty) return u;
    return product['image'] as String?;
  }

  int get minOrder => (product['min_order'] as int?) ?? 1;
  bool get needsVariant => variant == null && product['has_variants'] == true;

  /// Savatda saqlanadigan qisqa mahsulot ma'lumoti (tafsilotdagi og'ir ro'yxatlarsiz).
  static J slimProduct(J p) {
    const drop = {'similar', 'same_seller', 'seller_full', 'description', 'images', 'variants', 'variant_axes', 'characteristics'};
    return {for (final e in p.entries) if (!drop.contains(e.key)) e.key: e.value};
  }

  static J slimVariant(J v) => {
        for (final k in const ['id', 'sku', 'label', 'price', 'available', 'image_url', 'attributes'])
          if (v.containsKey(k)) k: v[k],
      };

  J toJson() => {'product': product, if (variant != null) 'variant': variant, 'qty': qty};
}

String fmtDate(String? s, {bool time = false}) {
  if (s == null || s.isEmpty) return '';
  final d = DateTime.tryParse(s)?.toLocal();
  if (d == null) return s;
  return DateFormat(time ? 'dd.MM.yyyy HH:mm' : 'dd.MM.yyyy').format(d);
}
