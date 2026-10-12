import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/state.dart';
import '../../ui/widgets.dart';
import 'checkout_screen.dart';

class ProductScreen extends StatefulWidget {
  final int id;
  const ProductScreen({super.key, required this.id});

  @override
  State<ProductScreen> createState() => _ProductScreenState();
}

class _ProductScreenState extends State<ProductScreen> {
  J? d;
  String? error;
  int qty = 1;
  int? vid; // tanlangan variant id
  int page = 0; // galereyadagi joriy rasm
  final pager = PageController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    pager.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final r = await Api.i.get('/products/${widget.id}/');
      if (!mounted) return;
      setState(() {
        d = Map<String, dynamic>.from(r);
        // birinchi mavjud variantni oldindan tanlaymiz
        final vs = _variants;
        final first = vs.where(_avail).firstOrNull ?? vs.firstOrNull;
        vid = first?['id'] as int?;
        qty = _clampQty((d!['min_order'] as int?) ?? 1);
      });
      WidgetsBinding.instance.addPostFrameCallback((_) => _syncImage(animate: false));
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    }
  }

  // ---------------------------------------------------------------- variantlar
  List<J> get _variants => ((d?['variants'] as List?) ?? []).cast<J>();
  List<J> get _axes => ((d?['variant_axes'] as List?) ?? []).cast<J>();
  J? get _variant => vid == null ? null : _variants.where((v) => v['id'] == vid).firstOrNull;

  static bool _avail(J v) {
    final a = v['available'] as int?;
    return a == null || a > 0;
  }

  static String _attr(J v, String code) => '${(v['attributes'] as Map?)?[code] ?? ''}';

  /// Narx/qoldiq/artikul tanlangan variantdan olinadigan mahsulot ko'rinishi.
  J get _eff {
    final p = d!;
    final v = _variant;
    if (v == null) return p;
    return {...p, 'price': v['price'], 'available': v['available'], 'sku': v['sku'], 'has_variants': false};
  }

  int _clampQty(int q) {
    final min = (d?['min_order'] as int?) ?? 1;
    final av = _eff['available'] as int?;
    var r = q < min ? min : q;
    if (av != null && av > 0 && r > av) r = av;
    return r;
  }

  void _selectVariant(J v) {
    setState(() {
      vid = v['id'] as int;
      qty = _clampQty(qty);
    });
    _syncImage();
  }

  /// O'q qiymati tanlanganda — shu qiymatli, mavjud va boshqa o'qlarda joriy tanlovga eng yaqin variant.
  void _pick(String code, String value) {
    final cur = _variant;
    final cands = _variants.where((v) => _attr(v, code) == value).toList();
    if (cands.isEmpty) return;
    int score(J v) {
      var n = _avail(v) ? 1000 : 0;
      if (cur != null) {
        for (final a in _axes) {
          final c = a['code'] as String;
          if (c != code && _attr(v, c) == _attr(cur, c)) n++;
        }
      }
      return n;
    }

    var best = cands.first;
    for (final v in cands) {
      if (score(v) > score(best)) best = v;
    }
    _selectVariant(best);
  }

  // ---------------------------------------------------------------- galereya
  List<J> _images(J p) {
    final imgs = ((p['images'] as List?) ?? []).cast<J>().where((i) => '${i['url'] ?? ''}'.isNotEmpty).toList();
    if (imgs.isEmpty && p['image'] != null && '${p['image']}'.isNotEmpty) {
      return [
        {'id': null, 'url': p['image'], 'is_sample': p['image_is_sample'] == true},
      ];
    }
    return imgs;
  }

  /// Variantning o'z rasmi bo'lsa — galereyani shu rasmga o'tkazamiz.
  void _syncImage({bool animate = true}) {
    final v = _variant;
    final imgId = v?['image'];
    if (d == null || imgId == null || !pager.hasClients) return;
    final i = _images(d!).indexWhere((x) => x['id'] == imgId);
    if (i < 0 || i == page) return;
    if (animate) {
      pager.animateToPage(i, duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
    } else {
      pager.jumpToPage(i);
    }
  }

  void _openViewer(List<J> imgs, int i) {
    Navigator.push(
      context,
      MaterialPageRoute(
        fullscreenDialog: true,
        builder: (_) => _ImageViewer(urls: imgs.map((e) => '${e['url']}').toList(), initial: i),
      ),
    );
  }

  Widget _gallery(J p) {
    final imgs = _images(p);
    if (imgs.isEmpty) {
      return AspectRatio(aspectRatio: 4 / 3, child: ProductImage(src: null, category: p['category'], iconSize: 72));
    }
    final cur = page < imgs.length ? page : 0;
    return Column(children: [
      AspectRatio(
        aspectRatio: 4 / 3,
        child: Stack(fit: StackFit.expand, children: [
          PageView.builder(
            controller: pager,
            itemCount: imgs.length,
            onPageChanged: (i) => setState(() => page = i),
            itemBuilder: (_, i) => GestureDetector(
              onTap: () => _openViewer(imgs, i),
              child: ProductImage(src: '${imgs[i]['url']}', category: p['category'], iconSize: 72),
            ),
          ),
          if (imgs[cur]['is_sample'] == true) const Positioned(right: 10, top: 10, child: SampleBadge()),
          if (imgs.length > 1)
            Positioned(
              left: 0,
              right: 0,
              bottom: 10,
              child: IgnorePointer(
                child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                  for (var i = 0; i < imgs.length; i++)
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 200),
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      width: i == cur ? 18 : 7,
                      height: 7,
                      decoration: BoxDecoration(
                        color: i == cur ? brand : Colors.white.withValues(alpha: 0.85),
                        borderRadius: BorderRadius.circular(99),
                        boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 3)],
                      ),
                    ),
                ]),
              ),
            ),
        ]),
      ),
      if (imgs.length > 1)
        SizedBox(
          height: 70,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 0),
            itemCount: imgs.length,
            separatorBuilder: (_, __) => const SizedBox(width: 8),
            itemBuilder: (_, i) => GestureDetector(
              onTap: () => pager.animateToPage(i, duration: const Duration(milliseconds: 250), curve: Curves.easeOut),
              child: Container(
                width: 60,
                decoration: BoxDecoration(
                  border: Border.all(color: i == cur ? brand : const Color(0xFFE2E8F0), width: 2),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: ProductImage(src: '${imgs[i]['url']}', category: p['category'], iconSize: 20),
                ),
              ),
            ),
          ),
        ),
    ]);
  }

  // ---------------------------------------------------------------- variant tanlagich
  Widget _variantPicker(AppState app) {
    final cur = _variant;
    final axes = _axes;
    final vs = _variants;
    if (axes.isEmpty) {
      // o'qlar ta'rifi yo'q — variantlarni nomi bilan ko'rsatamiz
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(app.t('variant'), style: const TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 6),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final v in vs)
            ChoiceChip(
              label: Text(app.p(v['label']).isEmpty ? '${v['sku']}' : app.p(v['label'])),
              selected: v['id'] == vid,
              onSelected: _avail(v) ? (_) => _selectVariant(v) : null,
            ),
        ]),
      ]);
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      for (final a in axes) ...[
        Builder(builder: (_) {
          final code = a['code'] as String;
          final opts = ((a['options'] as List?) ?? []).cast<J>();
          String optName(J o) {
            final n = app.p(o['name']);
            return n.isEmpty ? '${o['v']}' : n;
          }

          final selOpt = cur == null ? null : opts.where((o) => '${o['v']}' == _attr(cur, code)).firstOrNull;
          return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text.rich(TextSpan(children: [
              TextSpan(text: app.p(a['name']), style: const TextStyle(fontWeight: FontWeight.w700)),
              if (selOpt != null) TextSpan(text: ': ${optName(selOpt)}', style: const TextStyle(color: ink500)),
            ])),
            const SizedBox(height: 6),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final o in opts)
                Builder(builder: (_) {
                  final value = '${o['v']}';
                  // shu qiymatli mavjud variant umuman bormi
                  final enabled = vs.any((v) => _attr(v, code) == value && _avail(v));
                  // joriy tanlovning boshqa o'qlari bilan mos keladimi
                  final exact = cur == null ||
                      vs.any((v) =>
                          _avail(v) &&
                          _attr(v, code) == value &&
                          axes.every((b) => b['code'] == code || _attr(v, b['code'] as String) == _attr(cur, b['code'] as String)));
                  final selected = cur != null && _attr(cur, code) == value;
                  return ChoiceChip(
                    label: Text(optName(o),
                        style: TextStyle(
                          color: enabled && !exact && !selected ? ink500 : null,
                          decoration: enabled ? null : TextDecoration.lineThrough,
                        )),
                    selected: selected,
                    onSelected: enabled ? (_) => _pick(code, value) : null,
                  );
                }),
            ]),
            const SizedBox(height: 10),
          ]);
        }),
      ],
    ]);
  }

  // ---------------------------------------------------------------- xususiyatlar
  static String? _num(dynamic v) {
    if (v == null) return null;
    final s = '$v'.trim();
    if (s.isEmpty) return null;
    final n = num.tryParse(s);
    if (n == null) return s;
    var r = n.toString();
    if (r.contains('.')) r = r.replaceFirst(RegExp(r'\.?0+$'), '');
    return r;
  }

  List<List<String>> _characteristics(AppState app, J p) {
    final out = <List<String>>[];
    final brandName = '${p['brand'] ?? ''}'.trim();
    if (brandName.isNotEmpty) out.add([app.t('mp_brand'), brandName]);
    final country = '${p['country'] ?? ''}'.trim();
    if (country.isNotEmpty) out.add([app.t('mp_country'), country]);
    for (final c in ((p['characteristics'] as List?) ?? []).cast<J>()) {
      final v = app.p(c['value']);
      if (v.isNotEmpty) out.add([app.p(c['name']), v]);
    }
    final w = _num(p['weight_kg']);
    if (w != null) out.add([app.t('mp_weight'), w]);
    final dims = [p['length_cm'], p['width_cm'], p['height_cm']].map(_num).toList();
    if (dims.any((x) => x != null)) out.add([app.t('mp_dims'), dims.map((x) => x ?? '—').join(' × ')]);
    return out;
  }

  Widget _table(List<List<String>> rows) => Card(
        child: Column(children: [
          for (final r in rows)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(width: 130, child: Text(r[0], style: const TextStyle(color: ink500))),
                Expanded(child: Text(r[1])),
              ]),
            ),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    if (d == null) {
      return Scaffold(appBar: AppBar(), body: Center(child: error != null ? Text(app.t('not_found')) : const CircularProgressIndicator()));
    }
    final p = d!;
    final v = _variant;
    final hasVariants = p['has_variants'] == true;
    final needVariant = hasVariants && v == null;
    final eff = _eff;
    final av = eff['available'] as int?;
    final soldOut = av != null && av <= 0;
    final inCart = app.inCartLine(p['id'] as int, v?['id'] as int?);
    final price = needVariant ? null : double.tryParse('${eff['price']}');
    final rows = <List<String>>[
      [app.t('sku'), '${eff['sku'] ?? ''}'],
      [app.t('unit'), app.unit(p['unit'])],
      [app.t('specs'), app.p(p['spec']).isEmpty ? '—' : app.p(p['spec'])],
      [app.t('produced_at'), app.p(p['address'])],
      [app.t('daily_capacity'), p['daily_capacity'] != null ? '${p['daily_capacity']} ${app.unit(p['unit'])}' : '—'],
      [app.t('delivery'), p['delivery'] == true ? app.t('delivery_yes') : app.t('delivery_no')],
    ];
    final chars = _characteristics(app, p);
    final similar = ((p['similar'] as List?) ?? []).cast<J>();

    void add() => app.addToCart(p, qty, v);

    return Scaffold(
      appBar: AppBar(title: Text(app.p(p['name']), maxLines: 1, overflow: TextOverflow.ellipsis)),
      body: ListView(padding: EdgeInsets.zero, children: [
        _gallery(p),
        Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if ('${p['brand'] ?? ''}'.trim().isNotEmpty)
              Text('${p['brand']}', style: const TextStyle(color: ink500, fontWeight: FontWeight.w600, fontSize: 13)),
            Text(app.p(p['name']), style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, height: 1.2)),
            if (app.p(p['spec']).isNotEmpty) Text(app.p(p['spec']), style: const TextStyle(color: ink500, fontSize: 16)),
            const SizedBox(height: 6),
            Row(children: [
              const Icon(Icons.factory_outlined, size: 16, color: brand),
              const SizedBox(width: 4),
              Expanded(child: Text('${app.p(p['seller']['name'])} · ${app.p(p['seller']['region_i18n'])}', style: const TextStyle(color: brand, fontWeight: FontWeight.w600))),
            ]),
            const SizedBox(height: 14),
            PriceText(eff, big: true),
            StockText(eff),
            if (hasVariants) ...[
              const SizedBox(height: 14),
              _variantPicker(app),
              if (needVariant) Text(app.t('choose_variant'), style: const TextStyle(color: Color(0xFFB45309), fontWeight: FontWeight.w600)),
            ],
            const SizedBox(height: 12),
            if (!soldOut && !needVariant)
              Row(children: [
                QtyStepper(value: qty, min: (p['min_order'] as int?) ?? 1, max: av, onChanged: (x) => setState(() => qty = x)),
                const SizedBox(width: 8),
                Text(app.unit(p['unit']), style: const TextStyle(color: ink500)),
                const Spacer(),
                if (price != null) Text(app.money(price * qty), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17)),
              ]),
            const SizedBox(height: 12),
            _info(Icons.local_shipping_outlined, p['delivery'] == true ? app.t('delivery_yes') : app.t('delivery_no')),
            _info(Icons.schedule, app.t('lead_days', {'n': p['lead_days']})),
            _info(Icons.description_outlined, app.t('price_note')),
            const SizedBox(height: 12),
            _table(rows),
            if (chars.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text(app.t('characteristics'), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              _table(chars),
            ],
            if (app.p(p['description']).isNotEmpty) Padding(padding: const EdgeInsets.only(top: 12), child: Text(app.p(p['description']))),
          ]),
        ),
        if (similar.isNotEmpty) ...[
          SectionTitle(app.t('similar')),
          SizedBox(
            height: 340,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              itemCount: similar.length,
              separatorBuilder: (_, __) => const SizedBox(width: 10),
              itemBuilder: (_, i) => SizedBox(width: 180, child: ProductCard(similar[i])),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ]),
      bottomNavigationBar: soldOut
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
                child: Row(children: [
                  Expanded(
                    child: FilledButton.tonalIcon(
                      onPressed: inCart || needVariant ? null : add,
                      icon: Icon(inCart ? Icons.check : Icons.add_shopping_cart),
                      label: Text(inCart ? app.t('in_cart') : app.t('add_to_cart')),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton.icon(
                      style: FilledButton.styleFrom(backgroundColor: accent),
                      onPressed: needVariant
                          ? null
                          : () {
                              if (!inCart) add();
                              Navigator.push(context, MaterialPageRoute(builder: (_) => const CheckoutScreen()));
                            },
                      icon: const Icon(Icons.bolt),
                      label: Text(app.t('buy_now')),
                    ),
                  ),
                ]),
              ),
            ),
    );
  }

  Widget _info(IconData i, String text) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(children: [Icon(i, size: 20, color: ink500), const SizedBox(width: 10), Expanded(child: Text(text))]),
      );
}

/// To'liq ekranli rasm ko'rish: varaqlash va kattalashtirish (pinch-zoom).
class _ImageViewer extends StatefulWidget {
  final List<String> urls;
  final int initial;
  const _ImageViewer({required this.urls, required this.initial});

  @override
  State<_ImageViewer> createState() => _ImageViewerState();
}

class _ImageViewerState extends State<_ImageViewer> {
  late final PageController ctrl = PageController(initialPage: widget.initial);
  late int page = widget.initial;

  @override
  void dispose() {
    ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: widget.urls.length > 1 ? Text('${page + 1} / ${widget.urls.length}') : null,
      ),
      body: PageView.builder(
        controller: ctrl,
        itemCount: widget.urls.length,
        onPageChanged: (i) => setState(() => page = i),
        itemBuilder: (_, i) => InteractiveViewer(
          minScale: 1,
          maxScale: 5,
          child: Center(
            child: Image.network(
              widget.urls[i],
              fit: BoxFit.contain,
              errorBuilder: (_, __, ___) => const Icon(Icons.broken_image_outlined, color: Colors.white54, size: 64),
            ),
          ),
        ),
      ),
    );
  }
}
