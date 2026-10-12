import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/state.dart';
import '../../ui/buyer_form.dart';
import '../../ui/widgets.dart';
import 'contracts_screen.dart';

class _Line {
  final J product;
  final J? variant; // variantli mahsulotda tanlangan variant
  int qty;
  final TextEditingController price;
  _Line(this.product, this.variant, this.qty, String p) : price = TextEditingController(text: p);

  /// Belgilangan narx (variantniki yoki mahsulotniki); null — narx kelishiladi.
  dynamic get basePrice => variant != null ? variant!['price'] : product['price'];
  int? get available => variant != null ? variant!['available'] as int? : product['available'] as int?;
  bool same(J p, J? v) => product['id'] == p['id'] && variant?['id'] == v?['id'];
}

/// Umumiy katalog: barcha muassasalar mahsulotlari va qoldig'i.
/// Muassasa boshqa muassasa mahsulotini xaridorga rasmiylashtirsa — shartnoma mahsulot egasi nomidan tuziladi.
class AgentCatalogScreen extends StatefulWidget {
  const AgentCatalogScreen({super.key});
  @override
  State<AgentCatalogScreen> createState() => _AgentCatalogScreenState();
}

class _AgentCatalogScreenState extends State<AgentCatalogScreen> {
  List<J>? items;
  final q = TextEditingController();
  String seller = '';
  bool inStock = true;
  final deal = <_Line>[];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => items = null);
    try {
      final r = await Api.i.get('/seller/catalog/',
          query: {'q': q.text.trim(), 'seller': seller, 'in_stock': inStock ? 1 : null, 'page_size': 100, 'ordering': 'name'}, auth: true);
      setState(() => items = (r['results'] as List).cast<J>());
    } catch (_) {
      setState(() => items = []);
    }
  }

  void _add(J p, [J? v]) {
    if (deal.any((l) => l.same(p, v))) return;
    final base = v != null ? v['price'] : p['price'];
    final min = (p['min_order'] as int?) ?? 1;
    setState(() => deal.add(_Line(p, v, min, base == null ? '' : '${num.parse(base.toString()).round()}')));
  }

  List<J> _variants(J p) => ((p['variants'] as List?) ?? []).cast<J>();

  /// Variantli mahsulot: variantni tanlash oynasi.
  Future<void> _pickVariant(J p) async {
    final app = context.read<AppState>();
    final vs = _variants(p);
    final picked = await showModalBottomSheet<J>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(ctx).size.height * 0.7),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: Text('${app.t('choose_variant')} · ${app.p(p['name'])}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
            ),
            Flexible(
              child: ListView(shrinkWrap: true, children: [
                for (final v in vs)
                  Builder(builder: (_) {
                    final av = v['available'] as int?;
                    final inDeal = deal.any((l) => l.same(p, v));
                    final disabled = (av != null && av <= 0) || inDeal;
                    return ListTile(
                      enabled: !disabled,
                      title: Text(app.p(v['label']).isEmpty ? '${v['sku']}' : app.p(v['label'])),
                      subtitle: Text('${v['sku']} · ${app.t('available')}: ${av ?? '∞'}'),
                      trailing: inDeal
                          ? const Icon(Icons.check)
                          : Text(v['price'] != null ? app.money(v['price']) : app.t('price_on_request'),
                              style: const TextStyle(fontWeight: FontWeight.w700)),
                      onTap: disabled ? null : () => Navigator.pop(ctx, v),
                    );
                  }),
              ]),
            ),
          ]),
        ),
      ),
    );
    if (picked != null && mounted) _add(p, picked);
  }

  Future<void> _checkout() async {
    final res = await Navigator.push<List<J>>(context, MaterialPageRoute(builder: (_) => _DealForm(lines: deal)));
    if (mounted) setState(() {}); // formada qatorlar olib tashlangan bo'lishi mumkin
    if (res != null && mounted) {
      setState(deal.clear);
      _load();
      final app = context.read<AppState>();
      await showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(app.t('deal_done')),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            for (final a in res)
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text('${a['contract']?['number'] ?? a['number']}', style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w700)),
                subtitle: Text('${app.t('owner')}: ${app.p(a['seller']['name'])}'),
                trailing: const Icon(Icons.chevron_right),
                onTap: a['contract'] == null
                    ? null
                    : () {
                        Navigator.pop(ctx);
                        Navigator.push(context, MaterialPageRoute(builder: (_) => ContractDetailScreen(id: a['contract']['id'] as int)));
                      },
              ),
          ]),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final total = deal.fold<double>(0.0, (s, l) => s + (double.tryParse(l.price.text) ?? 0) * l.qty);
    return Scaffold(
      appBar: AppBar(
        title: Text(app.t('general_catalog')),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(112),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
            child: Column(children: [
              TextField(controller: q, onSubmitted: (_) => _load(), decoration: InputDecoration(hintText: app.t('search_ph'), prefixIcon: const Icon(Icons.search))),
              Row(children: [
                Expanded(
                  child: DropdownButton<String>(
                    value: seller,
                    isExpanded: true,
                    underline: const SizedBox(),
                    items: [
                      DropdownMenuItem(value: '', child: Text(app.t('sellers'))),
                      ...app.sellers.where((s) => (s['product_count'] as int? ?? 0) > 0).map((s) => DropdownMenuItem(value: s['code'] as String, child: Text(app.p(s['name'])))),
                    ],
                    onChanged: (v) {
                      seller = v ?? '';
                      _load();
                    },
                  ),
                ),
                FilterChip(label: Text(app.t('only_in_stock')), selected: inStock, onSelected: (v) {
                  inStock = v;
                  _load();
                }),
              ]),
            ]),
          ),
        ),
      ),
      body: items == null
          ? const Center(child: CircularProgressIndicator())
          : ListView.separated(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 100),
              itemCount: items!.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) {
                final p = items![i];
                final hasVariants = p['has_variants'] == true;
                final nVariants = _variants(p).length;
                final inDeal = !hasVariants && deal.any((l) => l.same(p, null));
                final variantsInDeal = hasVariants ? deal.where((l) => l.product['id'] == p['id']).length : 0;
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Row(children: [
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(app.p(p['name']), style: const TextStyle(fontWeight: FontWeight.w700)),
                          Text('${app.p(p['spec'])} · ${p['sku']}', style: const TextStyle(color: ink500, fontSize: 12)),
                          Text('${app.t('owner')}: ${app.p(p['seller']['name'])}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                          const SizedBox(height: 4),
                          PriceText(p),
                          if (hasVariants)
                            Text('${app.t('variants_n', {'n': nVariants})}${variantsInDeal > 0 ? ' · ${app.t('deal')}: $variantsInDeal' : ''}',
                                style: const TextStyle(fontSize: 12, color: brandDark, fontWeight: FontWeight.w600)),
                          Text('${app.t('stock')}: ${p['stock'] ?? '∞'} · ${app.t('reserved')}: ${p['reserved'] ?? 0} · ${app.t('available')}: ${p['available'] ?? '∞'}',
                              style: const TextStyle(fontSize: 12, color: Color(0xFF047857), fontWeight: FontWeight.w600)),
                        ]),
                      ),
                      IconButton.filled(
                        onPressed: inDeal || (hasVariants && nVariants == 0) ? null : (hasVariants ? () => _pickVariant(p) : () => _add(p)),
                        icon: Icon(inDeal ? Icons.check : hasVariants ? Icons.tune : Icons.add),
                      ),
                    ]),
                  ),
                );
              },
            ),
      bottomNavigationBar: deal.isEmpty
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: accent),
                  onPressed: _checkout,
                  icon: const Icon(Icons.draw_outlined),
                  label: Text('${app.t('create_deal')} · ${deal.length} · ${app.money(total)}'),
                ),
              ),
            ),
    );
  }
}

class _DealForm extends StatefulWidget {
  final List<_Line> lines;
  const _DealForm({required this.lines});
  @override
  State<_DealForm> createState() => _DealFormState();
}

class _DealFormState extends State<_DealForm> {
  final data = BuyerData()
    ..type = 'b2b'
    ..payment = 'bank';
  Set<String> errors = {};
  bool busy = false;
  String? error;

  Future<void> submit() async {
    setState(() => errors = data.validate());
    if (errors.isNotEmpty) return;
    if (widget.lines.any((l) => l.price.text.trim().isEmpty)) {
      setState(() => error = context.read<AppState>().t('set_price'));
      return;
    }
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final r = await Api.i.post('/seller/agent-order/', auth: true, body: {
        ...data.toJson(),
        'items': [
          for (final l in widget.lines)
            {'product': l.product['id'], if (l.variant != null) 'variant': l.variant!['id'], 'qty': l.qty, 'price': l.price.text.trim()},
        ],
      });
      if (mounted) Navigator.pop(context, (r as List).cast<J>());
    } on ApiException catch (e) {
      setState(() => error = e.message);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(title: Text(app.t('create_deal'))),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text(app.t('deal_note'), style: const TextStyle(color: ink500, fontSize: 12)),
        const SizedBox(height: 8),
        for (final l in widget.lines)
          Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text(app.p(l.product['name']), style: const TextStyle(fontWeight: FontWeight.w700))),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    onPressed: () => setState(() => widget.lines.remove(l)),
                    icon: const Icon(Icons.close, size: 18),
                  ),
                ]),
                if (l.variant != null)
                  Text('${app.p(l.variant!['label'])} · ${l.variant!['sku']}',
                      style: const TextStyle(color: brandDark, fontSize: 13, fontWeight: FontWeight.w600)),
                Text('${app.t('owner')}: ${app.p(l.product['seller']['name'])}', style: const TextStyle(color: ink500, fontSize: 12)),
                const SizedBox(height: 8),
                Row(children: [
                  QtyStepper(
                    value: l.qty,
                    min: (l.product['min_order'] as int?) ?? 1,
                    max: l.available,
                    onChanged: (v) => setState(() => l.qty = v),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: l.price,
                      enabled: l.basePrice == null,
                      keyboardType: TextInputType.number,
                      decoration: InputDecoration(labelText: app.t('price_per')),
                    ),
                  ),
                ]),
              ]),
            ),
          ),
        const SizedBox(height: 12),
        BuyerForm(data: data, errors: errors),
        if (error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(error!, style: const TextStyle(color: Colors.red))),
        const SizedBox(height: 80),
      ]),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: FilledButton(onPressed: busy || widget.lines.isEmpty ? null : submit, child: Text(app.t('create_deal'))),
        ),
      ),
    );
  }
}
