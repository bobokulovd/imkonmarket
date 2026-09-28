import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api.dart';
import '../../core/state.dart';
import '../../ui/widgets.dart';

class HomeScreen extends StatefulWidget {
  final void Function({String? category, String? q}) onOpenCatalog;
  const HomeScreen({super.key, required this.onOpenCatalog});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<J>? featured;
  List<J>? schools;
  final search = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final a = await Api.i.get('/products/', query: {'ordering': 'featured', 'priced': 1, 'page_size': 10});
      final b = await Api.i.get('/products/', query: {'category': 'talim-mebeli', 'priced': 1, 'page_size': 6});
      setState(() {
        featured = (a['results'] as List).cast<J>();
        schools = (b['results'] as List).cast<J>();
      });
    } catch (_) {
      setState(() => featured = schools = []);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final stats = app.meta?['stats'] as Map?;
    return Scaffold(
      body: RefreshIndicator(
        onRefresh: () async {
          await app.loadMeta();
          await _load();
        },
        child: CustomScrollView(slivers: [
          SliverAppBar(
            pinned: true,
            backgroundColor: brandDark,
            foregroundColor: Colors.white,
            title: const BrandTitle(light: true),
            actions: const [LangButton()],
            bottom: PreferredSize(
              preferredSize: const Size.fromHeight(64),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                child: TextField(
                  controller: search,
                  textInputAction: TextInputAction.search,
                  onSubmitted: (q) => widget.onOpenCatalog(q: q),
                  decoration: InputDecoration(
                    hintText: app.t('search_ph'),
                    prefixIcon: const Icon(Icons.search),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                    enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  ),
                ),
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Container(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
              decoration: const BoxDecoration(gradient: LinearGradient(colors: [brandDark, brand], begin: Alignment.topCenter, end: Alignment.bottomCenter)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(app.t('hero_title'), style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w800, height: 1.2)),
                const SizedBox(height: 8),
                Text(app.t('hero_sub'), style: const TextStyle(color: Color(0xFFBCD6FF), fontSize: 13.5)),
                const SizedBox(height: 16),
                Row(children: [
                  for (final s in [
                    ['${stats?['products'] ?? '—'}', app.t('stat_products')],
                    ['${stats?['sellers'] ?? '—'}', app.t('stat_sellers')],
                    ['${stats?['regions'] ?? '—'}', app.t('stat_regions')],
                  ])
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(s[0], style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w800)),
                        Text(s[1], style: const TextStyle(color: Color(0xFFBCD6FF), fontSize: 11), maxLines: 2),
                      ]),
                    ),
                ]),
              ]),
            ),
          ),
          SliverToBoxAdapter(
            child: SizedBox(
              height: 118,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.fromLTRB(12, 14, 12, 0),
                children: [
                  for (final c in app.categories)
                    InkWell(
                      borderRadius: BorderRadius.circular(12),
                      onTap: () => widget.onOpenCatalog(category: c['slug']),
                      child: SizedBox(
                        width: 92,
                        child: Column(children: [
                          Container(
                            width: 52,
                            height: 52,
                            decoration: BoxDecoration(color: Color((catTone[c['slug']] ?? [0xFFF1F5F9])[0]), borderRadius: BorderRadius.circular(16)),
                            child: Icon(catIcons[c['icon']] ?? Icons.category, color: Color((catTone[c['slug']] ?? [0, 0, 0xFF64748B])[2])),
                          ),
                          const SizedBox(height: 6),
                          Text(app.p(c['name']), maxLines: 2, textAlign: TextAlign.center, overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: 11.5, height: 1.15)),
                        ]),
                      ),
                    ),
                ],
              ),
            ),
          ),
          SliverToBoxAdapter(child: SectionTitle(app.t('popular'), onMore: () => widget.onOpenCatalog())),
          _grid(featured),
          SliverToBoxAdapter(child: SectionTitle(app.t('schools_title'), onMore: () => widget.onOpenCatalog(category: 'talim-mebeli'))),
          _grid(schools),
          SliverToBoxAdapter(
            child: Container(
              margin: const EdgeInsets.all(16),
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(color: ink, borderRadius: BorderRadius.circular(20)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(app.t('b2b_title'), style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800)),
                const SizedBox(height: 6),
                Text(app.t('b2b_sub'), style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 13)),
                const SizedBox(height: 12),
                FilledButton(
                  style: FilledButton.styleFrom(backgroundColor: accent),
                  onPressed: () => widget.onOpenCatalog(),
                  child: Text(app.t('b2b_cta')),
                ),
              ]),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _grid(List<J>? items) {
    if (items == null) {
      return const SliverToBoxAdapter(child: Padding(padding: EdgeInsets.all(32), child: Center(child: CircularProgressIndicator())));
    }
    return SliverPadding(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      sliver: SliverGrid(
        gridDelegate: productGridDelegate(context),
        delegate: SliverChildBuilderDelegate((_, i) => ProductCard(items[i]), childCount: items.length),
      ),
    );
  }
}
