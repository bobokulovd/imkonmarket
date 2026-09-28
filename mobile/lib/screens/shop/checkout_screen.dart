import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/api.dart';
import '../../core/state.dart';
import '../../ui/buyer_form.dart';
import '../../ui/widgets.dart';
import 'order_screen.dart';

class CheckoutScreen extends StatefulWidget {
  const CheckoutScreen({super.key});
  @override
  State<CheckoutScreen> createState() => _CheckoutScreenState();
}

class _CheckoutScreenState extends State<CheckoutScreen> {
  final data = BuyerData();
  Set<String> errors = {};
  bool busy = false;
  String? error;
  List<J>? created;

  @override
  void initState() {
    super.initState();
    data.lang = context.read<AppState>().lang;
  }

  Future<void> submit() async {
    final app = context.read<AppState>();
    setState(() => errors = data.validate());
    if (errors.isNotEmpty) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final res = await Api.i.post('/applications/', body: {
        ...data.toJson(),
        'items': app.cart.map((l) => {'product': l.product['id'], 'qty': l.qty}).toList(),
      });
      final list = (res as List).cast<J>();
      final p = await SharedPreferences.getInstance();
      final hist = p.getStringList('orders') ?? [];
      await p.setStringList('orders', [...list.map((a) => '${a['number']}|${a['token']}'), ...hist].take(30).toList());
      app.clearCart();
      setState(() => created = list);
    } on ApiException catch (e) {
      setState(() => error = e.message);
    } catch (e) {
      setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    if (created != null) {
      return Scaffold(
        appBar: AppBar(),
        body: ListView(padding: const EdgeInsets.all(20), children: [
          const Icon(Icons.check_circle, color: Color(0xFF10B981), size: 72),
          const SizedBox(height: 12),
          Text(app.t('success_title'), textAlign: TextAlign.center, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          Text(app.t('success_sub'), textAlign: TextAlign.center, style: const TextStyle(color: ink500)),
          const SizedBox(height: 20),
          for (final a in created!)
            Card(
              child: ListTile(
                title: Text(a['number'], style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w800)),
                subtitle: Text('${app.p(a['seller'])} · ${app.money(a['total'])}'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => OrderScreen(token: a['token']))),
              ),
            ),
        ]),
      );
    }
    return Scaffold(
      appBar: AppBar(title: Text(app.t('checkout_title'))),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(app.t('order_summary'), style: const TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 6),
              for (final l in app.cart)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Row(children: [
                    Expanded(child: Text('${app.p(l.product['name'])} × ${l.qty}', style: const TextStyle(fontSize: 13))),
                    Text(l.product['price'] != null ? app.money((double.tryParse('${l.product['price']}') ?? 0) * l.qty) : '—',
                        style: const TextStyle(fontSize: 13)),
                  ]),
                ),
              const Divider(),
              Row(children: [
                Text(app.t('total'), style: const TextStyle(fontWeight: FontWeight.w700)),
                const Spacer(),
                Text(app.money(app.cartTotal), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18)),
              ]),
            ]),
          ),
        ),
        const SizedBox(height: 16),
        BuyerForm(data: data, errors: errors),
        if (error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(error!, style: const TextStyle(color: Colors.red))),
        const SizedBox(height: 12),
        Text(app.t('agree'), style: const TextStyle(color: ink500, fontSize: 12)),
        const SizedBox(height: 80),
      ]),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: FilledButton(
            style: FilledButton.styleFrom(backgroundColor: accent),
            onPressed: busy || app.cart.isEmpty ? null : submit,
            child: busy ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : Text(app.t('submit')),
          ),
        ),
      ),
    );
  }
}
