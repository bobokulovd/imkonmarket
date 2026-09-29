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

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await Api.i.get('/products/${widget.id}/');
      if (!mounted) return;
      setState(() {
        d = Map<String, dynamic>.from(r);
        qty = (d!['min_order'] as int?) ?? 1;
      });
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    if (d == null) {
      return Scaffold(appBar: AppBar(), body: Center(child: error != null ? Text(app.t('not_found')) : const CircularProgressIndicator()));
    }
    final p = d!;
    final av = p['available'] as int?;
    final soldOut = av != null && av <= 0;
    final inCart = app.inCart(p['id'] as int);
    final price = double.tryParse('${p['price']}');
    final rows = <List<String>>[
      [app.t('sku'), p['sku']],
      [app.t('unit'), app.unit(p['unit'])],
      [app.t('specs'), app.p(p['spec']).isEmpty ? '—' : app.p(p['spec'])],
      [app.t('produced_at'), app.p(p['address'])],
      [app.t('daily_capacity'), p['daily_capacity'] != null ? '${p['daily_capacity']} ${app.unit(p['unit'])}' : '—'],
      [app.t('delivery'), p['delivery'] == true ? app.t('delivery_yes') : app.t('delivery_no')],
    ];
    final similar = ((p['similar'] as List?) ?? []).cast<J>();

    return Scaffold(
      appBar: AppBar(title: Text(app.p(p['name']), maxLines: 1, overflow: TextOverflow.ellipsis)),
      body: ListView(padding: EdgeInsets.zero, children: [
        AspectRatio(aspectRatio: 4 / 3, child: Stack(fit: StackFit.expand, children: [
          ProductImage(src: p['image'], category: p['category'], iconSize: 72),
          if (p['image'] != null && p['image_is_sample'] == true) const Positioned(right: 10, bottom: 10, child: SampleBadge()),
        ])),
        Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(app.p(p['name']), style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, height: 1.2)),
            if (app.p(p['spec']).isNotEmpty) Text(app.p(p['spec']), style: const TextStyle(color: ink500, fontSize: 16)),
            const SizedBox(height: 6),
            Row(children: [
              const Icon(Icons.factory_outlined, size: 16, color: brand),
              const SizedBox(width: 4),
              Expanded(child: Text('${app.p(p['seller']['name'])} · ${app.p(p['seller']['region_i18n'])}', style: const TextStyle(color: brand, fontWeight: FontWeight.w600))),
            ]),
            const SizedBox(height: 14),
            PriceText(p, big: true),
            StockText(p),
            const SizedBox(height: 12),
            if (!soldOut)
              Row(children: [
                QtyStepper(value: qty, min: (p['min_order'] as int?) ?? 1, max: av, onChanged: (v) => setState(() => qty = v)),
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
            Card(
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
            ),
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
                      onPressed: inCart ? null : () => app.addToCart(p, qty),
                      icon: Icon(inCart ? Icons.check : Icons.add_shopping_cart),
                      label: Text(inCart ? app.t('in_cart') : app.t('add_to_cart')),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton.icon(
                      style: FilledButton.styleFrom(backgroundColor: accent),
                      onPressed: () {
                        if (!inCart) app.addToCart(p, qty);
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
