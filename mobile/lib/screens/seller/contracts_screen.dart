import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api.dart';
import '../../core/state.dart';
import '../../ui/widgets.dart';

class ContractsScreen extends StatefulWidget {
  const ContractsScreen({super.key});
  @override
  State<ContractsScreen> createState() => _ContractsScreenState();
}

class _ContractsScreenState extends State<ContractsScreen> {
  List<J>? items;
  String status = '';

  @override
  void initState() {
    super.initState();
    _load().catchError((_) {});
  }

  Future<void> _load() async {
    setState(() => items = null);
    try {
      final r = await Api.i.get('/seller/contracts/', query: {'status': status, 'page_size': 100}, auth: true);
      setState(() => items = (r['results'] as List).cast<J>());
    } catch (_) {
      setState(() => items = []);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final tabs = ['', 'active', 'paid', 'shipped', 'done', 'cancelled'];
    return Scaffold(
      appBar: AppBar(title: Text(app.t('contracts'))),
      body: Column(children: [
        SizedBox(
          height: 52,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8), children: [
            for (final s in tabs)
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: ChoiceChip(label: Text(s.isEmpty ? app.t('all') : app.t('c_$s')), selected: status == s, onSelected: (_) {
                  status = s;
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
                            final c = items![i];
                            return Card(
                              child: ListTile(
                                title: Text(c['number'], style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w700)),
                                subtitle: Text('${c['application']['buyer_name']}\n${app.money(c['grand_total'])} · ${app.t('paid')}: ${app.money(c['paid_amount'])}'),
                                isThreeLine: true,
                                trailing: StatusChip(c['status'], app.t('c_${c['status']}')),
                                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ContractDetailScreen(id: c['id'] as int))).then((_) => _load()),
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

class ContractDetailScreen extends StatefulWidget {
  final int id;
  const ContractDetailScreen({super.key, required this.id});
  @override
  State<ContractDetailScreen> createState() => _ContractDetailScreenState();
}

class _ContractDetailScreenState extends State<ContractDetailScreen> {
  J? c;
  final amount = TextEditingController();
  final doc = TextEditingController();
  bool busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final r = Map<String, dynamic>.from(await Api.i.get('/seller/contracts/${widget.id}/', auth: true));
    amount.text = '${num.parse(r['due_amount'].toString()).round()}';
    setState(() => c = r);
  }

  Future<void> _act(String kind, [Map<String, dynamic>? body]) async {
    final app = context.read<AppState>();
    if (kind == 'ship' || kind == 'cancel') {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          content: Text(app.t('confirm_q')),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(app.t('cancel'))),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('OK')),
          ],
        ),
      );
      if (ok != true) return;
    }
    setState(() => busy = true);
    try {
      final r = await Api.i.post('/seller/contracts/${widget.id}/$kind/', body: body ?? {}, auth: true);
      if (kind == 'pay-link') {
        final url = r['url'] as String?;
        if (url != null) {
          await Clipboard.setData(ClipboardData(text: url));
          if (mounted) toast(context, '${app.t('copied')}: $url');
        }
      } else {
        setState(() => c = Map<String, dynamic>.from(r));
      }
    } on ApiException catch (e) {
      if (mounted) toast(context, e.message);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    if (c == null) return Scaffold(appBar: AppBar(), body: const Center(child: CircularProgressIndicator()));
    final x = c!;
    final me = app.me!['seller'] as Map;
    final own = me['role'] == 'operator' || x['seller']['code'] == me['code'];
    final st = x['status'] as String;
    final due = double.tryParse('${x['due_amount']}') ?? 0;
    return Scaffold(
      appBar: AppBar(title: Text(x['number'], style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w800))),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Wrap(spacing: 8, runSpacing: 6, children: [
          StatusChip(st, app.t('c_$st')),
          StatusChip('cancelled', (x['buyer_type'] as String).toUpperCase()),
          if (x['agent'] != null) StatusChip('shipped', '${app.t('agent')}: ${app.p(x['agent']['name'])}'),
        ]),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(children: [
              _kv(app.t('buyer'), '${x['application']['buyer_name']}'),
              _kv(app.t('phone'), '${x['application']['buyer_phone']}'),
              _kv(app.t('grand_total'), app.money(x['grand_total'])),
              _kv(app.t('paid'), app.money(x['paid_amount'])),
              _kv(app.t('due'), app.money(x['due_amount'])),
              _kv(app.t('prepayment'), '${x['prepayment_percent']}%'),
              const Divider(),
              for (final i in (x['application']['items'] as List))
                _kv('${app.p(i['name'])} × ${i['qty']}', app.money(i['amount'])),
            ]),
          ),
        ),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: () => launchUrl(Uri.parse(x['pdf_url']), mode: LaunchMode.externalApplication),
          icon: const Icon(Icons.picture_as_pdf_outlined),
          label: Text(app.t('open_pdf')),
        ),
        if (own && st != 'cancelled') ...[
          if ((st == 'active' || st == 'paid') && due > 0) ...[
            const SizedBox(height: 16),
            Text(app.t('register_payment'), style: const TextStyle(fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            Row(children: [
              Expanded(child: TextField(controller: amount, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: app.t('amount')))),
              const SizedBox(width: 8),
              Expanded(child: TextField(controller: doc, decoration: InputDecoration(labelText: app.t('document_no')))),
            ]),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: busy ? null : () => _act('payment', {'amount': amount.text, 'document_no': doc.text, 'method': 'bank'}),
              child: Text(app.t('register_payment')),
            ),
            if (x['payment_method'] != 'bank') ...[
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: busy ? null : () => _act('pay-link', {'method': x['payment_method']}),
                icon: const Icon(Icons.link),
                label: Text(app.t('pay_link')),
              ),
            ],
          ],
          const SizedBox(height: 16),
          if (st == 'paid' || (st == 'active' && x['buyer_type'] == 'b2b'))
            FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: accent),
              onPressed: busy ? null : () => _act('ship'),
              icon: const Icon(Icons.local_shipping),
              label: Text(app.t('ship')),
            ),
          if (st == 'shipped')
            FilledButton.icon(onPressed: busy ? null : () => _act('complete'), icon: const Icon(Icons.done_all), label: Text(app.t('complete'))),
          if (st == 'active' || st == 'paid')
            TextButton(onPressed: busy ? null : () => _act('cancel'), child: Text(app.t('cancel_contract'), style: const TextStyle(color: Colors.red))),
        ],
        if ((x['payments'] as List).isNotEmpty) ...[
          const SizedBox(height: 16),
          Text(app.t('payments'), style: const TextStyle(fontWeight: FontWeight.w800)),
          for (final p in (x['payments'] as List))
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text('${p['method']}${(p['document_no'] ?? '').toString().isNotEmpty ? ' · №${p['document_no']}' : ''}${p['is_demo'] == true ? ' · DEMO' : ''}'),
              subtitle: Text(fmtDate(p['paid_at'] ?? p['created_at'], time: true)),
              trailing: Text('${app.money(p['amount'])} · ${p['status']}'),
            ),
        ],
      ]),
    );
  }

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(child: Text(k, style: const TextStyle(color: ink500))),
          const SizedBox(width: 8),
          Text(v, style: const TextStyle(fontWeight: FontWeight.w600)),
        ]),
      );
}
