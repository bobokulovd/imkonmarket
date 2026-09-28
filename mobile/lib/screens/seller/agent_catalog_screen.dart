import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/state.dart';
import '../../ui/buyer_form.dart';
import '../../ui/widgets.dart';
import 'contracts_screen.dart';

class _Line {
  final J product;
  int qty;
  final TextEditingController price;
  _Line(this.product, this.qty, String p) : price = TextEditingController(text: p);
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

  void _add(J p) {
    if (deal.any((l) => l.product['id'] == p['id'])) return;
    setState(() => deal.add(_Line(p, (p['min_order'] as int?) ?? 1, p['price'] == null ? '' : '${num.parse(p['price'].toString()).round()}')));
  }

  Future<void> _checkout() async {
    final res = await Navigator.push<List<J>>(context, MaterialPageRoute(builder: (_) => _DealForm(lines: deal)));
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
                final inDeal = deal.any((l) => l.product['id'] == p['id']);
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
                          Text('${app.t('stock')}: ${p['stock'] ?? '∞'} · ${app.t('reserved')}: ${p['reserved'] ?? 0} · ${app.t('available')}: ${p['available'] ?? '∞'}',
                              style: const TextStyle(fontSize: 12, color: Color(0xFF047857), fontWeight: FontWeight.w600)),
                        ]),
                      ),
                      IconButton.filled(onPressed: inDeal ? null : () => _add(p), icon: Icon(inDeal ? Icons.check : Icons.add)),
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
        'items': [for (final l in widget.lines) {'product': l.product['id'], 'qty': l.qty, 'price': l.price.text.trim()}],
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
                Text(app.p(l.product['name']), style: const TextStyle(fontWeight: FontWeight.w700)),
                Text('${app.t('owner')}: ${app.p(l.product['seller']['name'])}', style: const TextStyle(color: ink500, fontSize: 12)),
                const SizedBox(height: 8),
                Row(children: [
                  QtyStepper(
                    value: l.qty,
                    min: (l.product['min_order'] as int?) ?? 1,
                    max: l.product['available'] as int?,
                    onChanged: (v) => setState(() => l.qty = v),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: l.price,
                      enabled: l.product['price'] == null,
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
          child: FilledButton(onPressed: busy ? null : submit, child: Text(app.t('create_deal'))),
        ),
      ),
    );
  }
}
