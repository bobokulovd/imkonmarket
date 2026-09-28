import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/state.dart';
import '../../ui/widgets.dart';
import 'agent_catalog_screen.dart';
import 'applications_screen.dart';
import 'contracts_screen.dart';
import 'marketplace_orders_screen.dart';
import 'seller_products_screen.dart';

/// Sotuvchi (muassasa) kabineti: kirish yoki boshqaruv paneli.
class SellerHome extends StatelessWidget {
  const SellerHome({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return app.me == null ? const _Login() : const _Dashboard();
  }
}

class _Login extends StatefulWidget {
  const _Login();
  @override
  State<_Login> createState() => _LoginState();
}

class _LoginState extends State<_Login> {
  final u = TextEditingController();
  final p = TextEditingController();
  bool busy = false;
  bool wrong = false;

  Future<void> submit() async {
    setState(() {
      busy = true;
      wrong = false;
    });
    try {
      final r = await Api.i.post('/auth/login/', body: {'username': u.text.trim(), 'password': p.text});
      await Api.i.setTokens(r['access'], r['refresh']);
      if (mounted) await context.read<AppState>().loadMe();
    } catch (_) {
      setState(() => wrong = true);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(title: Text(app.t('cabinet')), actions: const [LangButton()]),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        const Center(child: LogoMark(size: 64)),
        const SizedBox(height: 12),
        const Center(child: BrandTitle()),
        const SizedBox(height: 8),
        Text(app.t('sign_in'), textAlign: TextAlign.center, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
        Text(app.t('cabinet_login_sub'), textAlign: TextAlign.center, style: const TextStyle(color: ink500)),
        const SizedBox(height: 24),
        TextField(controller: u, autocorrect: false, decoration: InputDecoration(labelText: app.t('username'), hintText: 'jiek14')),
        const SizedBox(height: 12),
        TextField(controller: p, obscureText: true, onSubmitted: (_) => submit(), decoration: InputDecoration(labelText: app.t('password'))),
        if (wrong) Padding(padding: const EdgeInsets.only(top: 8), child: Text(app.t('wrong_login'), style: const TextStyle(color: Colors.red))),
        const SizedBox(height: 16),
        FilledButton(onPressed: busy ? null : submit, child: Text(app.t('sign_in'))),
      ]),
    );
  }
}

class _Dashboard extends StatefulWidget {
  const _Dashboard();
  @override
  State<_Dashboard> createState() => _DashboardState();
}

class _DashboardState extends State<_Dashboard> {
  J? d;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await Api.i.get('/seller/dashboard/', auth: true);
      setState(() => d = Map<String, dynamic>.from(r));
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final seller = app.me!['seller'] as Map;
    void open(Widget w) => Navigator.push(context, MaterialPageRoute(builder: (_) => w)).then((_) => _load());
    final tiles = [
      [Icons.assignment_outlined, app.t('applications'), '${d?['applications_new'] ?? '…'} ${app.t('new_apps').toLowerCase()}', () => open(const ApplicationsScreen())],
      [Icons.description_outlined, app.t('contracts'), '${d?['contracts_active'] ?? '…'} ${app.t('active_contracts').toLowerCase()}', () => open(const ContractsScreen())],
      [Icons.inventory_2_outlined, app.t('my_products'), '${d?['products'] ?? '…'}', () => open(const SellerProductsScreen())],
      [Icons.warehouse_outlined, app.t('general_catalog'), app.t('create_deal'), () => open(const AgentCatalogScreen())],
      [Icons.storefront_outlined, app.t('marketplaces'), 'Uzum · Ozon · Yandex · WB', () => open(const MarketplaceOrdersScreen())],
    ];
    return Scaffold(
      appBar: AppBar(
        title: Text(app.p(seller['name']), style: const TextStyle(fontWeight: FontWeight.w800)),
        actions: [const LangButton(), IconButton(onPressed: app.logout, icon: const Icon(Icons.logout))],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Row(children: [
            Expanded(child: _kpi(app.t('month_revenue'), d == null ? '…' : app.money(d!['revenue_month']), const Color(0xFF6D28D9))),
            const SizedBox(width: 10),
            Expanded(child: _kpi(app.t('receivable'), d == null ? '…' : app.money(d!['receivable']), const Color(0xFFB45309))),
          ]),
          const SizedBox(height: 12),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 10,
            crossAxisSpacing: 10,
            childAspectRatio: 1.25,
            children: [
              for (final t in tiles)
                Card(
                  child: InkWell(
                    onTap: t[3] as VoidCallback,
                    borderRadius: BorderRadius.circular(16),
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Icon(t[0] as IconData, color: brand, size: 28),
                        const Spacer(),
                        Text(t[1] as String, style: const TextStyle(fontWeight: FontWeight.w800)),
                        Text(t[2] as String, style: const TextStyle(color: ink500, fontSize: 12), maxLines: 2),
                      ]),
                    ),
                  ),
                ),
            ],
          ),
          SectionTitle(app.t('recent_apps')),
          for (final a in ((d?['recent'] as List?) ?? []))
            Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                title: Text(a['number'], style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w700)),
                subtitle: Text('${a['buyer_name']} · ${app.money(a['total'])}'),
                trailing: StatusChip(a['status'], app.t('st_${a['status']}')),
                onTap: () => open(ApplicationDetailScreen(id: a['id'] as int)),
              ),
            ),
        ]),
      ),
    );
  }

  Widget _kpi(String label, String value, Color c) => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(label, style: const TextStyle(color: ink500, fontSize: 12)),
            const SizedBox(height: 4),
            FittedBox(child: Text(value, style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18, color: c))),
          ]),
        ),
      );
}
