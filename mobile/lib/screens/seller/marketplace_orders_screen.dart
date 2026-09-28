import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/state.dart';
import '../../ui/widgets.dart';

/// Uzum / Ozon / Yandex Market / Wildberries buyurtmalari (muassasa kabinetlaridan tortilgan).
/// Amallar (tasdiqlash, bekor qilish...) serverda fon vazifasi sifatida bajariladi.
class MarketplaceOrdersScreen extends StatefulWidget {
  const MarketplaceOrdersScreen({super.key});
  @override
  State<MarketplaceOrdersScreen> createState() => _MarketplaceOrdersScreenState();
}

const _mpColor = {'uzum': Color(0xFF7000FF), 'ozon': Color(0xFF005BFF), 'yandex': Color(0xFFFFCC00), 'wb': Color(0xFFCB11AB)};
const _mpShort = {'uzum': 'U', 'ozon': 'O', 'yandex': 'Я', 'wb': 'WB'};
const _stateKey = {
  'new': 'mp_o_new', 'processing': 'mp_o_processing', 'shipped': 'mp_o_shipped',
  'delivered': 'mp_o_delivered', 'cancelled': 'mp_o_cancelled', 'returned': 'mp_o_returned',
};
const _actionKey = {'confirm': 'mp_a_confirm', 'ship': 'mp_a_ship', 'deliver': 'mp_a_deliver', 'cancel': 'mp_a_cancel'};

class _MarketplaceOrdersScreenState extends State<MarketplaceOrdersScreen> {
  List<J>? items;
  String state = 'new,processing';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => items = null);
    try {
      final r = await Api.i.get('/mp/orders/', query: {'state': state, 'page_size': 100}, auth: true);
      setState(() => items = (r['results'] as List).cast<J>());
    } catch (_) {
      setState(() => items = []);
    }
  }

  Future<void> _act(J o, String action) async {
    final app = context.read<AppState>();
    if (action == 'cancel') {
      final ok = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
          content: Text(app.t('confirm_q')),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: Text(app.t('close'))),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: Text(app.t('mp_a_cancel'))),
          ],
        ),
      );
      if (ok != true) return;
    }
    try {
      await Api.i.post('/mp/orders/${o['id']}/action/', body: {'action': action}, auth: true);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(app.t('mp_queued'))));
      Future.delayed(const Duration(seconds: 5), _load);
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final filters = {'new,processing': '${app.t('mp_o_new')} + ${app.t('mp_o_processing')}', '': app.t('all')};
    return Scaffold(
      appBar: AppBar(title: Text(app.t('mp_orders'))),
      body: Column(children: [
        SizedBox(
          height: 52,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8), children: [
            for (final e in filters.entries)
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: ChoiceChip(label: Text(e.value), selected: state == e.key, onSelected: (_) {
                  state = e.key;
                  _load();
                }),
              ),
          ]),
        ),
        Expanded(
          child: items == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(
                  onRefresh: _load,
                  child: items!.isEmpty
                      ? ListView(children: [Padding(padding: const EdgeInsets.all(40), child: Text(app.t('nothing_found'), textAlign: TextAlign.center))])
                      : ListView.separated(
                          padding: const EdgeInsets.all(12),
                          itemCount: items!.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 10),
                          itemBuilder: (_, i) => _card(app, items![i]),
                        ),
                ),
        ),
      ]),
    );
  }

  Widget _card(AppState app, J o) {
    final mp = o['marketplace'] as String? ?? '';
    final lines = (o['items'] as List? ?? []).cast<J>();
    final actions = (o['actions'] as List? ?? []).cast<String>();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(
              width: 26, height: 26, alignment: Alignment.center,
              decoration: BoxDecoration(color: _mpColor[mp] ?? ink500, borderRadius: BorderRadius.circular(7)),
              child: Text(_mpShort[mp] ?? '?', style: TextStyle(color: mp == 'yandex' ? Colors.black : Colors.white, fontWeight: FontWeight.w900, fontSize: 11)),
            ),
            const SizedBox(width: 8),
            Expanded(child: Text('№ ${o['external_id']}', style: const TextStyle(fontWeight: FontWeight.w800))),
            Chip(label: Text(app.t(_stateKey[o['state']] ?? 'mp_o_new')), visualDensity: VisualDensity.compact),
          ]),
          Text('${o['scheme']} · ${o['status']} · ${fmtDate(o['ordered_at'], time: true)}', style: const TextStyle(color: ink500, fontSize: 12)),
          const SizedBox(height: 6),
          for (final it in lines)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(children: [
                Expanded(child: Text('${it['name'] ?? it['offer_id']}', maxLines: 1, overflow: TextOverflow.ellipsis)),
                Text('${it['qty']} × ${it['price']}'),
              ]),
            ),
          const SizedBox(height: 6),
          Row(children: [
            Text('${o['total']} ${o['currency'] == 'UZS' ? app.t('sum') : o['currency']}', style: const TextStyle(fontWeight: FontWeight.w800)),
            const SizedBox(width: 8),
            if (o['stock_state'] == 'reserved') Text(app.t('mp_stock_reserved'), style: const TextStyle(color: Color(0xFFB45309), fontSize: 12)),
          ]),
          if (actions.isNotEmpty)
            Wrap(spacing: 8, children: [
              for (final a in actions)
                a == 'cancel'
                    ? OutlinedButton(onPressed: () => _act(o, a), child: Text(app.t(_actionKey[a]!)))
                    : FilledButton(onPressed: () => _act(o, a), child: Text(app.t(_actionKey[a]!))),
            ]),
        ]),
      ),
    );
  }
}
