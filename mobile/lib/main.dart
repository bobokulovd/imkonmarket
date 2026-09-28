import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/state.dart';
import 'screens/seller/seller_home.dart';
import 'screens/shop/cart_screen.dart';
import 'screens/shop/catalog_screen.dart';
import 'screens/shop/home_screen.dart';
import 'screens/shop/track_screen.dart';
import 'ui/widgets.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final app = AppState();
  await app.init();
  runApp(ChangeNotifierProvider.value(value: app, child: const ImkonMarketApp()));
}

class ImkonMarketApp extends StatelessWidget {
  const ImkonMarketApp({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return MaterialApp(
      title: (app.meta?['brand'] as String?) ?? 'ImkonMarket',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      home: const RootScreen(),
    );
  }
}

/// Pastki navigatsiya: Bosh sahifa · Katalog · Savat · Kuzatish · Kabinet
class RootScreen extends StatefulWidget {
  const RootScreen({super.key});

  @override
  State<RootScreen> createState() => RootScreenState();
}

class RootScreenState extends State<RootScreen> {
  int index = 0;
  String? catalogCategory;
  String? catalogQuery;

  void openCatalog({String? category, String? q}) => setState(() {
        catalogCategory = category;
        catalogQuery = q;
        index = 1;
      });

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final pages = [
      HomeScreen(onOpenCatalog: openCatalog),
      CatalogScreen(key: ValueKey('cat-$catalogCategory-$catalogQuery'), initialCategory: catalogCategory, initialQuery: catalogQuery),
      CartScreen(onShop: () => setState(() => index = 1)),
      const TrackScreen(),
      const SellerHome(),
    ];
    return Scaffold(
      body: IndexedStack(index: index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (i) => setState(() => index = i),
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        destinations: [
          NavigationDestination(icon: const Icon(Icons.home_outlined), selectedIcon: const Icon(Icons.home), label: app.t('home')),
          NavigationDestination(icon: const Icon(Icons.grid_view_outlined), selectedIcon: const Icon(Icons.grid_view), label: app.t('catalog')),
          NavigationDestination(
            icon: Badge(isLabelVisible: app.cartCount > 0, label: Text('${app.cartCount}'), child: const Icon(Icons.shopping_cart_outlined)),
            selectedIcon: const Icon(Icons.shopping_cart),
            label: app.t('cart'),
          ),
          NavigationDestination(icon: const Icon(Icons.local_shipping_outlined), label: app.t('nav_track')),
          NavigationDestination(icon: const Icon(Icons.storefront_outlined), selectedIcon: const Icon(Icons.storefront), label: app.t('nav_cabinet')),
        ],
      ),
    );
  }
}
