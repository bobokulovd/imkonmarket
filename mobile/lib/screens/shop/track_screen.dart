import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/api.dart';
import '../../core/state.dart';
import '../../ui/widgets.dart';
import 'order_screen.dart';

class TrackScreen extends StatefulWidget {
  const TrackScreen({super.key});
  @override
  State<TrackScreen> createState() => _TrackScreenState();
}

class _TrackScreenState extends State<TrackScreen> {
  final number = TextEditingController();
  final phone = TextEditingController(text: '+998 ');
  bool busy = false;
  bool notFound = false;
  List<String> recent = [];

  @override
  void initState() {
    super.initState();
    _loadRecent();
  }

  Future<void> _loadRecent() async {
    final p = await SharedPreferences.getInstance();
    setState(() => recent = p.getStringList('orders') ?? []);
  }

  Future<void> find() async {
    setState(() {
      busy = true;
      notFound = false;
    });
    try {
      final r = await Api.i.get('/orders/track/', query: {'number': number.text.trim().toUpperCase(), 'phone': phone.text});
      if (!mounted) return;
      Navigator.push(context, MaterialPageRoute(builder: (_) => OrderScreen(token: r['token'])));
    } catch (_) {
      setState(() => notFound = true);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(title: Text(app.t('track_title')), actions: const [LangButton()]),
      body: RefreshIndicator(
        onRefresh: _loadRecent,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Text(app.t('track_sub'), style: const TextStyle(color: ink500)),
          const SizedBox(height: 16),
          TextField(controller: number, textCapitalization: TextCapitalization.characters, decoration: InputDecoration(labelText: app.t('order_number'), hintText: 'A-2026-000001')),
          const SizedBox(height: 12),
          TextField(controller: phone, keyboardType: TextInputType.phone, decoration: InputDecoration(labelText: app.t('phone'))),
          if (notFound) Padding(padding: const EdgeInsets.only(top: 8), child: Text(app.t('not_found'), style: const TextStyle(color: Colors.red))),
          const SizedBox(height: 16),
          FilledButton(onPressed: busy ? null : find, child: Text(app.t('find'))),
          if (recent.isNotEmpty) ...[
            const SizedBox(height: 24),
            Text(app.t('history'), style: const TextStyle(fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            for (final r in recent)
              Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  title: Text(r.split('|').first, style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w700)),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => OrderScreen(token: r.split('|').last))),
                ),
              ),
          ],
        ]),
      ),
    );
  }
}
