import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/state.dart';
import '../../ui/widgets.dart';
import 'checkout_screen.dart';
import 'product_screen.dart';

class CartScreen extends StatelessWidget {
  final VoidCallback onShop;
  const CartScreen({super.key, required this.onShop});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    if (app.cart.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: Text(app.t('cart'))),
        body: Center(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.shopping_cart_outlined, size: 56, color: ink500),
            const SizedBox(height: 12),
            Text(app.t('cart_empty'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            Text(app.t('cart_empty_sub'), style: const TextStyle(color: ink500)),
            const SizedBox(height: 16),
            FilledButton(onPressed: onShop, child: Text(app.t('go_shopping'))),
          ]),
        ),
      );
    }
    final groups = app.cartBySeller;
    return Scaffold(
      appBar: AppBar(title: Text('${app.t('cart')} · ${app.cartCount}')),
      body: ListView(padding: const EdgeInsets.all(12), children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: const Color(0xFFEEF5FF), borderRadius: BorderRadius.circular(12)),
          child: Text(app.t('separate_note'), style: const TextStyle(color: brandDark, fontSize: 13)),
        ),
        if (app.cartNeedsVariant) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: const Color(0xFFFFFBEB), borderRadius: BorderRadius.circular(12)),
            child: Text(app.t('variant_required'), style: const TextStyle(color: Color(0xFFB45309), fontSize: 13)),
          ),
        ],
        const SizedBox(height: 12),
        for (final g in groups.values) ...[
          Card(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 12, 14, 4),
                child: Row(children: [
                  const Icon(Icons.factory_outlined, size: 18),
                  const SizedBox(width: 6),
                  Expanded(child: Text(app.p(g.first.product['seller']['name']), style: const TextStyle(fontWeight: FontWeight.w800))),
                  Text(app.p(g.first.product['seller']['region_i18n']), style: const TextStyle(color: ink500, fontSize: 12)),
                ]),
              ),
              for (final l in g)
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    GestureDetector(
                      onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ProductScreen(id: l.productId))),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(10),
                        child: SizedBox(width: 72, height: 72, child: ProductImage(src: l.image, category: l.product['category'], iconSize: 28)),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(app.p(l.product['name']), maxLines: 2, style: const TextStyle(fontWeight: FontWeight.w600)),
                        if (l.variant != null && app.p(l.variant!['label']).isNotEmpty)
                          Text(app.p(l.variant!['label']), style: const TextStyle(color: brandDark, fontSize: 13, fontWeight: FontWeight.w600)),
                        if (l.needsVariant)
                          GestureDetector(
                            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ProductScreen(id: l.productId))),
                            child: Text(app.t('choose_variant'),
                                style: const TextStyle(color: Color(0xFFB45309), fontSize: 13, fontWeight: FontWeight.w700, decoration: TextDecoration.underline)),
                          ),
                        if (app.p(l.product['spec']).isNotEmpty) Text(app.p(l.product['spec']), style: const TextStyle(color: ink500, fontSize: 12)),
                        StockText({...l.product, 'available': l.available}),
                        const SizedBox(height: 6),
                        Row(children: [
                          QtyStepper(
                            value: l.qty,
                            min: l.minOrder,
                            max: l.available,
                            onChanged: (v) => app.setQty(l, v),
                          ),
                          const Spacer(),
                          IconButton(onPressed: () => app.removeFromCart(l), icon: const Icon(Icons.delete_outline)),
                        ]),
                        Text(
                          l.price != null
                              ? app.money((double.tryParse('${l.price}') ?? 0) * l.qty)
                              : app.t('price_on_request'),
                          style: const TextStyle(fontWeight: FontWeight.w800),
                        ),
                      ]),
                    ),
                  ]),
                ),
            ]),
          ),
          const SizedBox(height: 12),
        ],
        if (app.cart.any((l) => l.price == null))
          Text(app.t('priced_later'), style: const TextStyle(color: Color(0xFFB45309), fontSize: 12)),
      ]),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(children: [
            Expanded(
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(app.t('total'), style: const TextStyle(color: ink500)),
                Text(app.money(app.cartTotal), style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
              ]),
            ),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: accent, padding: const EdgeInsets.symmetric(horizontal: 28)),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const CheckoutScreen())),
              child: Text(app.t('checkout')),
            ),
          ]),
        ),
      ),
    );
  }
}
