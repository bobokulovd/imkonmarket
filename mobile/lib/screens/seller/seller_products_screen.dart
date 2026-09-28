import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/state.dart';
import '../../ui/widgets.dart';

/// Muassasa mahsulotlari: qoldiq, narx, ko'rinish; yangi mahsulot qo'shish.
class SellerProductsScreen extends StatefulWidget {
  const SellerProductsScreen({super.key});
  @override
  State<SellerProductsScreen> createState() => _SellerProductsScreenState();
}

class _SellerProductsScreenState extends State<SellerProductsScreen> {
  List<J>? items;
  final q = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await Api.i.get('/seller/products/', query: {'q': q.text.trim(), 'page_size': 200}, auth: true);
      setState(() => items = (r['results'] as List).cast<J>());
    } catch (_) {
      setState(() => items = []);
    }
  }

  Future<void> _edit([J? p]) async {
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
        child: _Editor(product: p),
      ),
    );
    if (saved == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(
        title: Text(app.t('my_products')),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(60),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
            child: TextField(controller: q, onSubmitted: (_) => _load(), decoration: InputDecoration(hintText: app.t('search_ph'), prefixIcon: const Icon(Icons.search))),
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(onPressed: () => _edit(), icon: const Icon(Icons.add), label: Text(app.t('add_product'))),
      body: items == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView.separated(
                padding: const EdgeInsets.fromLTRB(12, 12, 12, 90),
                itemCount: items!.length,
                separatorBuilder: (_, __) => const SizedBox(height: 8),
                itemBuilder: (_, i) {
                  final p = items![i];
                  return Opacity(
                    opacity: p['is_active'] == true ? 1 : 0.5,
                    child: Card(
                      child: ListTile(
                        leading: ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: SizedBox(width: 48, height: 48, child: ProductImage(src: p['image_url'], category: p['category'], iconSize: 22)),
                        ),
                        title: Text(app.p(p['name']), maxLines: 1, overflow: TextOverflow.ellipsis),
                        subtitle: Text(
                            '${p['price'] != null ? app.money(p['price']) : app.t('price_on_request')} / ${app.unit(p['unit'])}\n'
                            '${app.t('stock')}: ${p['stock'] ?? '∞'} · ${app.t('reserved')}: ${p['reserved']} · ${app.t('available')}: ${p['available'] ?? '∞'}'),
                        isThreeLine: true,
                        trailing: const Icon(Icons.edit_outlined),
                        onTap: () => _edit(p),
                      ),
                    ),
                  );
                },
              ),
            ),
    );
  }
}

class _Editor extends StatefulWidget {
  final J? product;
  const _Editor({this.product});
  @override
  State<_Editor> createState() => _EditorState();
}

class _EditorState extends State<_Editor> {
  late final J? p = widget.product;
  late final nameUz = TextEditingController(text: p?['name']?['uz'] ?? '');
  late final nameRu = TextEditingController(text: (p?['name']?['ru'] ?? '') == (p?['name']?['uz'] ?? '') ? '' : p?['name']?['ru'] ?? '');
  late final nameEn = TextEditingController(text: (p?['name']?['en'] ?? '') == (p?['name']?['uz'] ?? '') ? '' : p?['name']?['en'] ?? '');
  late final nameKaa = TextEditingController(text: (p?['name']?['kaa'] ?? '') == (p?['name']?['uz'] ?? '') ? '' : p?['name']?['kaa'] ?? '');
  late final spec = TextEditingController(text: p?['spec']?['uz'] ?? '');
  late final price = TextEditingController(text: p?['price'] == null ? '' : '${num.parse(p!['price'].toString()).round()}');
  late final stock = TextEditingController(text: p?['stock']?.toString() ?? '');
  late String category = p?['category'] ?? 'mebel';
  late String unit = p?['unit'] ?? 'dona';
  late bool active = p?['is_active'] ?? true;
  late bool delivery = p?['delivery'] ?? true;
  bool busy = false;
  String? error;

  Future<void> save() async {
    setState(() {
      busy = true;
      error = null;
    });
    final old = (p?['name'] as Map?) ?? {};
    final body = {
      // uz o'zgarsa kirill/yangi alifbo backendda qayta hosil qilinadi
      'name': {
        'uz': nameUz.text.trim(),
        'uz_cyrl': old['uz'] == nameUz.text.trim() ? old['uz_cyrl'] : '',
        'uz_new': old['uz'] == nameUz.text.trim() ? old['uz_new'] : '',
        'ru': nameRu.text.trim(),
        'en': nameEn.text.trim(),
        'kaa': nameKaa.text.trim(),
      },
      'spec': {'uz': spec.text.trim()},
      'category': category,
      'unit': unit,
      'price': price.text.trim().isEmpty ? null : price.text.trim(),
      'stock': stock.text.trim().isEmpty ? null : stock.text.trim(),
      'is_active': active,
      'delivery': delivery,
    };
    try {
      if (p == null) {
        await Api.i.post('/seller/products/', body: body, auth: true);
      } else {
        await Api.i.patch('/seller/products/${p!['id']}/', body: body, auth: true);
      }
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (e) {
      setState(() => error = e.message);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    const units = ['dona', 'juft', 'kg', 'm²', 'm³', 'p/m', "to'plam", 'tonna', 'xizmat'];
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(p == null ? app.t('add_product') : app.t('edit'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text(app.t('tr_hint'), style: const TextStyle(color: ink500, fontSize: 12)),
          const SizedBox(height: 12),
          TextField(controller: nameUz, onChanged: (_) => setState(() {}), decoration: InputDecoration(labelText: "${app.t('name')} (O'zbekcha) *")),
          const SizedBox(height: 8),
          TextField(controller: nameRu, decoration: InputDecoration(labelText: '${app.t('name')} (Русский)')),
          const SizedBox(height: 8),
          TextField(controller: nameKaa, decoration: InputDecoration(labelText: '${app.t('name')} (Qaraqalpaqsha)')),
          const SizedBox(height: 8),
          TextField(controller: nameEn, decoration: InputDecoration(labelText: '${app.t('name')} (English)')),
          const SizedBox(height: 8),
          TextField(controller: spec, decoration: InputDecoration(labelText: app.t('spec'))),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            value: app.categories.any((c) => c['slug'] == category) ? category : null,
            isExpanded: true,
            decoration: InputDecoration(labelText: app.t('category')),
            items: app.categories.map((c) => DropdownMenuItem(value: c['slug'] as String, child: Text(app.p(c['name'])))).toList(),
            onChanged: (v) => setState(() => category = v ?? category),
          ),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(
              child: DropdownButtonFormField<String>(
                value: unit,
                decoration: InputDecoration(labelText: app.t('unit')),
                items: units.map((u) => DropdownMenuItem(value: u, child: Text(app.unit(u)))).toList(),
                onChanged: (v) => setState(() => unit = v ?? unit),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(child: TextField(controller: price, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: '${app.t('price')}, ${app.t('sum')}'))),
          ]),
          const SizedBox(height: 8),
          TextField(controller: stock, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: app.t('stock'), helperText: app.t('stock_hint'))),
          SwitchListTile(contentPadding: EdgeInsets.zero, title: Text(app.t('delivery_yes')), value: delivery, onChanged: (v) => setState(() => delivery = v)),
          SwitchListTile(contentPadding: EdgeInsets.zero, title: Text(app.t('published')), value: active, onChanged: (v) => setState(() => active = v)),
          if (error != null) Text(error!, style: const TextStyle(color: Colors.red)),
          const SizedBox(height: 8),
          FilledButton(onPressed: busy || nameUz.text.trim().isEmpty ? null : save, child: Text(app.t('save'))),
        ]),
      ),
    );
  }
}
