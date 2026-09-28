import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/state.dart';
import '../../ui/widgets.dart';

class CatalogScreen extends StatefulWidget {
  final String? initialCategory;
  final String? initialQuery;
  const CatalogScreen({super.key, this.initialCategory, this.initialQuery});

  @override
  State<CatalogScreen> createState() => _CatalogScreenState();
}

class _CatalogScreenState extends State<CatalogScreen> {
  final items = <J>[];
  int count = 0;
  int page = 1;
  bool loading = false;
  bool hasMore = true;
  late final TextEditingController q = TextEditingController(text: widget.initialQuery ?? '');
  late Set<String> cats = {if (widget.initialCategory != null) widget.initialCategory!};
  Set<String> regions = {};
  bool inStock = false, delivery = false, priced = false;
  String ordering = 'featured';
  final scroll = ScrollController();

  @override
  void initState() {
    super.initState();
    scroll.addListener(() {
      if (scroll.position.pixels > scroll.position.maxScrollExtent - 600) _load();
    });
    _reload();
  }

  void _reload() {
    items.clear();
    page = 1;
    hasMore = true;
    _load();
  }

  Future<void> _load() async {
    if (loading || !hasMore) return;
    setState(() => loading = true);
    try {
      final r = await Api.i.get('/products/', query: {
        'q': q.text.trim(),
        'category': cats.join(','),
        'region': regions.join(','),
        'in_stock': inStock ? 1 : null,
        'delivery': delivery ? 1 : null,
        'priced': priced ? 1 : null,
        'ordering': ordering,
        'page': page,
        'page_size': 24,
      });
      setState(() {
        items.addAll((r['results'] as List).cast<J>());
        count = r['count'] as int;
        hasMore = r['next'] != null;
        page++;
      });
    } catch (_) {
      hasMore = false;
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  void _filters() {
    final app = context.read<AppState>();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) => StatefulBuilder(builder: (ctx, set) {
        Widget chip(String label, bool on, VoidCallback tap) =>
            FilterChip(label: Text(label), selected: on, onSelected: (_) => set(tap));
        return DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.85,
          builder: (_, sc) => Column(children: [
            Expanded(
              child: ListView(controller: sc, padding: const EdgeInsets.all(16), children: [
                Text(app.t('categories'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                const SizedBox(height: 8),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  for (final c in app.categories)
                    chip(app.p(c['name']), cats.contains(c['slug']), () => cats.contains(c['slug']) ? cats.remove(c['slug']) : cats.add(c['slug'])),
                ]),
                const SizedBox(height: 16),
                Text(app.t('region'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                const SizedBox(height: 8),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  for (final r in app.regions)
                    chip(app.p(r['name']), regions.contains(r['key']), () => regions.contains(r['key']) ? regions.remove(r['key']) : regions.add(r['key'])),
                ]),
                const SizedBox(height: 12),
                SwitchListTile(contentPadding: EdgeInsets.zero, title: Text(app.t('only_in_stock')), value: inStock, onChanged: (v) => set(() => inStock = v)),
                SwitchListTile(contentPadding: EdgeInsets.zero, title: Text(app.t('with_delivery')), value: delivery, onChanged: (v) => set(() => delivery = v)),
                SwitchListTile(contentPadding: EdgeInsets.zero, title: Text(app.t('only_priced')), value: priced, onChanged: (v) => set(() => priced = v)),
              ]),
            ),
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => set(() {
                        cats.clear();
                        regions.clear();
                        inStock = delivery = priced = false;
                      }),
                      child: Text(app.t('reset')),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton(
                      onPressed: () {
                        Navigator.pop(ctx);
                        _reload();
                      },
                      child: Text(app.t('show_results')),
                    ),
                  ),
                ]),
              ),
            ),
          ]),
        );
      }),
    );
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final title = cats.length == 1 ? app.p(app.category(cats.first)?['name']) : app.t('catalog');
    return Scaffold(
      appBar: AppBar(
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
        actions: const [LangButton()],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(108),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
            child: Column(children: [
              TextField(
                controller: q,
                textInputAction: TextInputAction.search,
                onSubmitted: (_) => _reload(),
                decoration: InputDecoration(hintText: app.t('search_ph'), prefixIcon: const Icon(Icons.search)),
              ),
              const SizedBox(height: 8),
              Row(children: [
                Expanded(child: Text(app.t('found', {'n': count}), style: const TextStyle(color: ink500, fontSize: 13))),
                TextButton.icon(onPressed: _filters, icon: const Icon(Icons.tune, size: 18), label: Text(app.t('filters'))),
                PopupMenuButton<String>(
                  initialValue: ordering,
                  onSelected: (v) {
                    ordering = v;
                    _reload();
                  },
                  itemBuilder: (_) => [
                    PopupMenuItem(value: 'featured', child: Text(app.t('sort_popular'))),
                    PopupMenuItem(value: 'price', child: Text(app.t('sort_price_asc'))),
                    PopupMenuItem(value: '-price', child: Text(app.t('sort_price_desc'))),
                    PopupMenuItem(value: 'new', child: Text(app.t('sort_new'))),
                  ],
                  child: const Padding(padding: EdgeInsets.all(8), child: Icon(Icons.sort)),
                ),
              ]),
            ]),
          ),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: items.isEmpty && !loading
            ? ListView(children: [Padding(padding: const EdgeInsets.all(40), child: Text(app.t('nothing_found'), textAlign: TextAlign.center))])
            : GridView.builder(
                controller: scroll,
                padding: const EdgeInsets.all(12),
                gridDelegate: productGridDelegate(context),
                itemCount: items.length + (hasMore ? 1 : 0),
                itemBuilder: (_, i) => i < items.length ? ProductCard(items[i]) : const Center(child: CircularProgressIndicator()),
              ),
      ),
    );
  }
}
