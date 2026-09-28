import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/state.dart';
import '../../ui/widgets.dart';
import 'contracts_screen.dart';

class ApplicationsScreen extends StatefulWidget {
  const ApplicationsScreen({super.key});
  @override
  State<ApplicationsScreen> createState() => _ApplicationsScreenState();
}

class _ApplicationsScreenState extends State<ApplicationsScreen> {
  List<J>? items;
  String status = 'new,review';

  @override
  void initState() {
    super.initState();
    _load().catchError((_) {});
  }

  Future<void> _load() async {
    setState(() => items = null);
    try {
      final r = await Api.i.get('/seller/applications/', query: {'status': status, 'page_size': 100}, auth: true);
      setState(() => items = (r['results'] as List).cast<J>());
    } catch (_) {
      setState(() => items = []);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final tabs = {'new,review': app.t('st_new'), 'contract': app.t('st_contract'), 'rejected,cancelled': app.t('st_rejected'), '': app.t('all')};
    return Scaffold(
      appBar: AppBar(title: Text(app.t('applications'))),
      body: Column(children: [
        SizedBox(
          height: 52,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8), children: [
            for (final e in tabs.entries)
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: ChoiceChip(label: Text(e.value), selected: status == e.key, onSelected: (_) {
                  status = e.key;
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
                      ? ListView(children: [Padding(padding: const EdgeInsets.all(40), child: Text(app.t('no_data'), textAlign: TextAlign.center))])
                      : ListView.separated(
                          padding: const EdgeInsets.all(12),
                          itemCount: items!.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 8),
                          itemBuilder: (_, i) {
                            final a = items![i];
                            return Card(
                              child: ListTile(
                                title: Text(a['number'], style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w700)),
                                subtitle: Text(
                                    '${a['buyer_name']} · ${(a['buyer_type'] as String).toUpperCase()}\n${app.money(a['total'])}${a['agent'] != null ? ' · ${app.t('agent')}: ${app.p(a['agent']['name'])}' : ''}'),
                                isThreeLine: true,
                                trailing: StatusChip(a['status'], app.t('st_${a['status']}')),
                                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ApplicationDetailScreen(id: a['id'] as int))).then((_) => _load()),
                              ),
                            );
                          },
                        ),
                ),
        ),
      ]),
    );
  }
}

class ApplicationDetailScreen extends StatefulWidget {
  final int id;
  const ApplicationDetailScreen({super.key, required this.id});
  @override
  State<ApplicationDetailScreen> createState() => _ApplicationDetailScreenState();
}

class _ApplicationDetailScreenState extends State<ApplicationDetailScreen> {
  J? a;
  final qty = <int, TextEditingController>{};
  final price = <int, TextEditingController>{};
  final deliveryCost = TextEditingController(text: '0');
  final prepay = TextEditingController(text: '100');
  final payDays = TextEditingController(text: '10');
  final delDays = TextEditingController(text: '15');
  final reason = TextEditingController();
  String lang = 'uz';
  bool busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final r = Map<String, dynamic>.from(await Api.i.get('/seller/applications/${widget.id}/', auth: true));
    for (final i in (r['items'] as List)) {
      qty[i['id'] as int] = TextEditingController(text: '${i['qty']}');
      final pr = i['price'] == null ? '' : '${num.parse(i['price'].toString())}';
      price[i['id'] as int] = TextEditingController(text: pr.endsWith('.0') ? pr.substring(0, pr.length - 2) : pr);
    }
    setState(() {
      a = r;
      lang = r['lang'] ?? 'uz';
    });
  }

  Future<void> _act(String kind, [Map<String, dynamic>? body]) async {
    setState(() => busy = true);
    try {
      await Api.i.post('/seller/applications/${widget.id}/$kind/', body: body ?? {}, auth: true);
      await _load();
      if (mounted) toast(context, context.read<AppState>().t('saved'));
    } on ApiException catch (e) {
      if (mounted) toast(context, e.message);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    if (a == null) return Scaffold(appBar: AppBar(), body: const Center(child: CircularProgressIndicator()));
    final x = a!;
    final me = app.me!['seller'] as Map;
    final own = me['role'] == 'operator' || x['seller']['code'] == me['code'];
    final editable = own && (x['status'] == 'new' || x['status'] == 'review');
    final b2b = x['buyer_type'] == 'b2b';
    final info = <List<String>>[
      [b2b ? app.t('company_name') : app.t('full_name'), '${x['buyer_name']}'],
      if (b2b) [app.t('inn'), '${x['buyer_inn']}'] else [app.t('pinfl'), '${x['buyer_pinfl']}'],
      [app.t('phone'), '${x['buyer_phone']}'],
      if ('${x['buyer_address']}'.isNotEmpty) [app.t('address'), '${x['buyer_address']}'],
      if (b2b && '${x['buyer_bank_account']}'.isNotEmpty) [app.t('bank_account'), '${x['buyer_bank_name']} ${x['buyer_bank_account']} (${x['buyer_bank_mfo']})'],
      [app.t('payment_method'), x['payment_method'] == 'bank' ? app.t('pay_bank') : '${x['payment_method']}'.toUpperCase()],
      [app.t('delivery'), x['delivery_required'] == true ? '${app.t('delivery_to')}: ${x['delivery_address']}' : app.t('pickup')],
      if (x['agent'] != null) [app.t('agent'), app.p(x['agent']['name'])],
      if ('${x['comment']}'.isNotEmpty) [app.t('comment'), '${x['comment']}'],
    ];
    Widget numField(TextEditingController c, String label) =>
        TextField(controller: c, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: label));

    return Scaffold(
      appBar: AppBar(title: Text(x['number'], style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w800))),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Row(children: [StatusChip(x['status'], app.t('st_${x['status']}')), const SizedBox(width: 8), Text(fmtDate(x['created_at'], time: true), style: const TextStyle(color: ink500))]),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(children: [
              for (final r in info)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    SizedBox(width: 120, child: Text(r[0], style: const TextStyle(color: ink500))),
                    Expanded(child: SelectableText(r[1])),
                  ]),
                ),
            ]),
          ),
        ),
        const SizedBox(height: 12),
        Text(app.t('items'), style: const TextStyle(fontWeight: FontWeight.w800)),
        const SizedBox(height: 6),
        for (final i in (x['items'] as List))
          Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(app.p(i['name']), style: const TextStyle(fontWeight: FontWeight.w700)),
                Text('${app.p(i['spec'])} · ${i['sku']} · ${app.t('available')}: ${i['available'] ?? '∞'}', style: const TextStyle(color: ink500, fontSize: 12)),
                const SizedBox(height: 8),
                if (editable)
                  Row(children: [
                    Expanded(child: numField(qty[i['id']]!, '${app.t('qty')}, ${app.unit(i['unit'])}')),
                    const SizedBox(width: 8),
                    Expanded(child: numField(price[i['id']]!, app.t('price_per'))),
                  ])
                else
                  Text('${i['qty']} ${app.unit(i['unit'])} × ${i['price'] != null ? app.money(i['price']) : '—'} = ${app.money(i['amount'])}'),
              ]),
            ),
          ),
        if (x['contract'] != null)
          Card(
            color: const Color(0xFFECFDF5),
            child: ListTile(
              leading: const Icon(Icons.description, color: Color(0xFF047857)),
              title: Text(x['contract']['number']),
              subtitle: Text(app.t('c_${x['contract']['status']}')),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ContractDetailScreen(id: x['contract']['id'] as int))),
            ),
          ),
        if (editable) ...[
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: numField(deliveryCost, '${app.t('delivery_cost')}, ${app.t('sum')}')),
            const SizedBox(width: 8),
            if (b2b) Expanded(child: numField(prepay, app.t('prepayment'))),
          ]),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: numField(payDays, app.t('payment_days'))),
            const SizedBox(width: 8),
            Expanded(child: numField(delDays, app.t('delivery_days'))),
          ]),
          const SizedBox(height: 10),
          DropdownButtonFormField<String>(
            value: lang,
            decoration: InputDecoration(labelText: app.t('contract_lang')),
            items: langs.entries.map((e) => DropdownMenuItem(value: e.key, child: Text(e.value))).toList(),
            onChanged: (v) => setState(() => lang = v ?? 'uz'),
          ),
          const SizedBox(height: 14),
          FilledButton.icon(
            onPressed: busy
                ? null
                : () => _act('confirm', {
                      'items': [
                        for (final i in (x['items'] as List))
                          {'id': i['id'], 'qty': int.tryParse(qty[i['id']]!.text) ?? i['qty'], 'price': price[i['id']]!.text.trim()}
                      ],
                      'delivery_cost': deliveryCost.text,
                      'prepayment_percent': prepay.text,
                      'payment_days': payDays.text,
                      'delivery_days': delDays.text,
                      'lang': lang,
                    }),
            icon: const Icon(Icons.draw_outlined),
            label: Text(app.t('confirm')),
          ),
          if (x['status'] == 'new') ...[
            const SizedBox(height: 8),
            OutlinedButton(onPressed: busy ? null : () => _act('review'), child: Text(app.t('review'))),
          ],
          const SizedBox(height: 20),
          TextField(controller: reason, decoration: InputDecoration(labelText: app.t('reject_reason'))),
          const SizedBox(height: 8),
          OutlinedButton(
            style: OutlinedButton.styleFrom(foregroundColor: Colors.red),
            onPressed: busy ? null : () => reason.text.trim().isEmpty ? null : _act('reject', {'reason': reason.text.trim()}),
            child: Text(app.t('reject')),
          ),
        ],
        const SizedBox(height: 24),
      ]),
    );
  }
}
