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
          cart.add(CartLine(Map<String, dynamic>.from(e['product']), e['qty'] as int));
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

  // -------- savat
  int get cartCount => cart.length;
  bool inCart(int id) => cart.any((l) => l.product['id'] == id);

  int _clamp(J p, int q) {
    final min = (p['min_order'] as int?) ?? 1;
    var v = q < min ? min : q;
    final av = p['available'] as int?;
    if (av != null && v > av) v = av;
    return v;
  }

  void addToCart(J p, [int qty = 1]) {
    final ex = cart.where((l) => l.product['id'] == p['id']).firstOrNull;
    if (ex != null) {
      ex.qty = _clamp(p, ex.qty + qty);
    } else {
      cart.add(CartLine(p, _clamp(p, qty)));
    }
    _saveCart();
  }

  void setQty(int id, int qty) {
    for (final l in cart) {
      if (l.product['id'] == id) l.qty = _clamp(l.product, qty);
    }
    _saveCart();
  }

  void removeFromCart(int id) {
    cart.removeWhere((l) => l.product['id'] == id);
    _saveCart();
  }

  void clearCart() {
    cart.clear();
    _saveCart();
  }

  double get cartTotal => cart.fold<double>(0.0, (s, l) => s + (double.tryParse('${l.product['price']}') ?? 0) * l.qty);

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
    await p.setString('cart', jsonEncode(cart.map((l) => {'product': l.product, 'qty': l.qty}).toList()));
  }
}

class CartLine {
  J product;
  int qty;
  CartLine(this.product, this.qty);
}

String fmtDate(String? s, {bool time = false}) {
  if (s == null || s.isEmpty) return '';
  final d = DateTime.tryParse(s)?.toLocal();
  if (d == null) return s;
  return DateFormat(time ? 'dd.MM.yyyy HH:mm' : 'dd.MM.yyyy').format(d);
}
