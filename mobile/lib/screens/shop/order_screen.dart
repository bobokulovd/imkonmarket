import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api.dart';
import '../../core/state.dart';
import '../../ui/widgets.dart';

const _logKeys = {
  'new': 'st_new', 'review': 'st_review', 'contract': 'st_contract', 'payment': 'paid', 'shipped': 'c_shipped',
  'done': 'c_done', 'rejected': 'st_rejected', 'cancelled': 'st_cancelled',
};

class OrderScreen extends StatefulWidget {
  final String token;
  const OrderScreen({super.key, required this.token});
  @override
  State<OrderScreen> createState() => _OrderScreenState();
}

class _OrderScreenState extends State<OrderScreen> {
  J? o;
  String? error;
  String? paying;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await Api.i.get('/orders/${widget.token}/');
      setState(() => o = Map<String, dynamic>.from(r));
    } catch (e) {
      setState(() => error = e.toString());
    }
  }

  Future<void> _pay(String method) async {
    setState(() => paying = method);
    try {
      final r = await Api.i.post('/orders/${widget.token}/pay/', body: {'method': method, 'lang': context.read<AppState>().lang});
      final url = r['url'] as String?;
      if (url != null) await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } catch (e) {
      if (mounted) toast(context, e.toString());
    } finally {
      if (mounted) setState(() => paying = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    if (o == null) {
      return Scaffold(appBar: AppBar(), body: Center(child: error != null ? Text(app.t('not_found')) : const CircularProgressIndicator()));
    }
    final a = o!;
    final c = a['contract'] as Map?;
    final st = c != null ? c['status'] as String : a['status'] as String;
    final label = c != null ? app.t('c_$st') : app.t('st_$st');
    final items = (a['items'] as List).cast<J>();
    final seller = a['seller'] as Map;

    return Scaffold(
      appBar: AppBar(title: Text(a['number'], style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w800))),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Row(children: [StatusChip(st, label), const SizedBox(width: 8), Expanded(child: Text(fmtDate(a['created_at'], time: true), style: const TextStyle(color: ink500)))]),
          const SizedBox(height: 12),
          Card(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              ListTile(
                leading: const Icon(Icons.factory_outlined),
                title: Text(app.p(seller['name']), style: const TextStyle(fontWeight: FontWeight.w800)),
                subtitle: Text(app.p(seller['region_i18n'])),
              ),
              if (a['agent'] != null)
                Padding(padding: const EdgeInsets.fromLTRB(16, 0, 16, 8), child: Text(app.t('via_agent', {'a': app.p(a['agent']['name'])}), style: const TextStyle(color: ink500))),
              for (final i in items)
                ListTile(
                  dense: true,
                  title: Text(app.p(i['name'])),
                  subtitle: Text('${app.p(i['spec'])} · ${i['qty']} ${app.unit(i['unit'])} × ${i['price'] != null ? app.money(i['price']) : app.t('price_on_request')}'),
                  trailing: Text(i['price'] != null ? app.money(i['amount']) : '—', style: const TextStyle(fontWeight: FontWeight.w700)),
                ),
              if (c != null && (double.tryParse('${c['delivery_cost']}') ?? 0) > 0)
                ListTile(dense: true, title: Text(app.t('delivery_cost')), trailing: Text(app.money(c['delivery_cost']))),
              ListTile(
                title: Text(app.t('total'), style: const TextStyle(fontWeight: FontWeight.w800)),
                trailing: Text(app.money(c != null ? c['grand_total'] : a['total']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
              ),
            ]),
          ),
          const SizedBox(height: 12),
          if (c == null && a['status'] != 'rejected' && a['status'] != 'cancelled')
            Card(child: Padding(padding: const EdgeInsets.all(16), child: Text(app.t('waiting_seller')))),
          if (c != null)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Row(children: [
                    const Icon(Icons.description_outlined, color: brand),
                    const SizedBox(width: 8),
                    Expanded(child: Text('${app.t('contract')} ${c['number']}', style: const TextStyle(fontWeight: FontWeight.w800))),
                  ]),
                  const SizedBox(height: 8),
                  _kv(app.t('grand_total'), app.money(c['grand_total'])),
                  _kv(app.t('paid'), app.money(c['paid_amount'])),
                  _kv(app.t('due'), app.money(c['due_amount']), bold: true),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: () => launchUrl(Uri.parse(c['pdf_url']), mode: LaunchMode.externalApplication),
                    icon: const Icon(Icons.picture_as_pdf_outlined),
                    label: Text(app.t('open_pdf')),
                  ),
                  if (c['status'] == 'active' && (double.tryParse('${c['due_amount']}') ?? 0) > 0) ...[
                    const SizedBox(height: 12),
                    if (c['payment_method'] != 'bank') ...[
                      for (final m in ['payme', 'click'])
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: FilledButton(
                            style: FilledButton.styleFrom(backgroundColor: m == c['payment_method'] ? accent : brand),
                            onPressed: paying != null ? null : () => _pay(m),
                            child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                              Text(app.t('pay_with', {'m': m == 'payme' ? 'Payme' : 'Click'})),
                              if (app.demo(m)) ...[const SizedBox(width: 8), const DemoBadge()],
                            ]),
                          ),
                        ),
                    ] else
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(color: const Color(0xFFF1F5F9), borderRadius: BorderRadius.circular(12)),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(app.t('bank_title'), style: const TextStyle(fontWeight: FontWeight.w700)),
                          Text(app.t('bank_hint'), style: const TextStyle(color: ink500, fontSize: 12)),
                          const SizedBox(height: 6),
                          SelectableText('${app.p(seller['name'])}\n${app.t('inn')}: ${seller['inn']}\n${app.t('contract_no')}: ${c['number']}\n${app.t('amount')}: ${app.money(c['due_amount'])}',
                              style: const TextStyle(fontFamily: 'monospace', fontSize: 13)),
                        ]),
                      ),
                  ],
                ]),
              ),
            ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(app.t('history'), style: const TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 8),
                for (final l in (a['logs'] as List))
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 3),
                    child: Row(children: [
                      SizedBox(width: 120, child: Text(fmtDate(l['created_at'], time: true), style: const TextStyle(color: ink500, fontSize: 12))),
                      Expanded(child: Text(_logKeys[l['status']] != null ? app.t(_logKeys[l['status']]!) : '${l['status']}')),
                    ]),
                  ),
              ]),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _kv(String k, String v, {bool bold = false}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(children: [Text(k, style: const TextStyle(color: ink500)), const Spacer(), Text(v, style: TextStyle(fontWeight: bold ? FontWeight.w800 : FontWeight.w500))]),
      );
}
