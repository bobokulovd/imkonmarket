import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/state.dart';
import '../screens/shop/product_screen.dart';

const brand = Color(0xFF1D54F0);
const brandDark = Color(0xFF1A3288);
const accent = Color(0xFFFF9A1F);
const ink = Color(0xFF0F172A);
const ink500 = Color(0xFF64748B);
const bg = Color(0xFFF5F7FB);

ThemeData buildTheme() {
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(seedColor: brand, primary: brand, secondary: accent, surface: Colors.white),
    scaffoldBackgroundColor: bg,
  );
  return base.copyWith(
    appBarTheme: const AppBarTheme(backgroundColor: Colors.white, foregroundColor: ink, elevation: 0, scrolledUnderElevation: 0.5, centerTitle: false),
    cardTheme: CardThemeData(color: Colors.white, elevation: 0, margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: Color(0xFFEFF2F6)))),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      isDense: true,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFFCBD5E1))),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFFCBD5E1))),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: brand, width: 2)),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(minimumSize: const Size(0, 48), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(minimumSize: const Size(0, 48), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
    ),
  );
}

const catIcons = <String, IconData>{
  'brick': Icons.grid_view_rounded,
  'blocks': Icons.view_module_rounded,
  'sofa': Icons.weekend_rounded,
  'school': Icons.school_rounded,
  'door': Icons.door_front_door_rounded,
  'wrench': Icons.build_rounded,
  'bed': Icons.bed_rounded,
  'shirt': Icons.checkroom_rounded,
  'gift': Icons.card_giftcard_rounded,
  'tree': Icons.park_rounded,
  'target': Icons.gps_fixed_rounded,
  'shield': Icons.shield_rounded,
  'basket': Icons.shopping_basket_rounded,
  'tools': Icons.handyman_rounded,
};

const catTone = <String, List<int>>{
  'qurilish': [0xFFFFF1E6, 0xFFFFD9BD, 0xFFC2410C],
  'temir-beton': [0xFFEEF2F6, 0xFFD5DDE7, 0xFF475569],
  'mebel': [0xFFFDF2E9, 0xFFF5DCC3, 0xFF9A5B22],
  'talim-mebeli': [0xFFEAF3FF, 0xFFCFE2FF, 0xFF1D4ED8],
  'rom-eshik': [0xFFE8F7F6, 0xFFC7ECE8, 0xFF0F766E],
  'metall': [0xFFF1F1F4, 0xFFDADAE3, 0xFF3F3F55],
  'toqimachilik': [0xFFFDF0F6, 0xFFF8D6E7, 0xFFBE185D],
  'kiyim': [0xFFEEF0FF, 0xFFD7DCFF, 0xFF4338CA],
  'suvenir': [0xFFFBF3E3, 0xFFF3E0B5, 0xFFA16207],
  'obodonlashtirish': [0xFFECF8EE, 0xFFCDEED3, 0xFF15803D],
  'oquv-jihozlar': [0xFFF0F4EA, 0xFFD9E5C9, 0xFF4D6B1F],
  'xavfsizlik': [0xFFFDEEEE, 0xFFF7D2D2, 0xFFB91C1C],
  'xojalik': [0xFFFFF8E1, 0xFFFFEAB0, 0xFFB45309],
  'xizmatlar': [0xFFF3EEFE, 0xFFE0D4FB, 0xFF6D28D9],
};

class ProductImage extends StatelessWidget {
  final String? src;
  final String? category;
  final double iconSize;
  const ProductImage({super.key, this.src, this.category, this.iconSize = 40});

  @override
  Widget build(BuildContext context) {
    if (src != null && src!.isNotEmpty) {
      return Image.network(src!, fit: BoxFit.cover, width: double.infinity, height: double.infinity,
          errorBuilder: (_, __, ___) => _placeholder(context));
    }
    return _placeholder(context);
  }

  Widget _placeholder(BuildContext context) {
    final app = context.read<AppState>();
    final tone = catTone[category] ?? [0xFFF1F5F9, 0xFFE2E8F0, 0xFF64748B];
    final icon = catIcons[app.category(category ?? '')?['icon']] ?? Icons.inventory_2_rounded;
    return Container(
      decoration: BoxDecoration(gradient: LinearGradient(colors: [Color(tone[0]), Color(tone[1])], begin: Alignment.topLeft, end: Alignment.bottomRight)),
      alignment: Alignment.center,
      child: Icon(icon, size: iconSize, color: Color(tone[2])),
    );
  }
}

class StockText extends StatelessWidget {
  final Map<String, dynamic> p;
  const StockText(this.p, {super.key});
  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final av = p['available'] as int?;
    if (av == null) return Text(app.t('made_to_order'), style: const TextStyle(color: Color(0xFF6D28D9), fontSize: 12, fontWeight: FontWeight.w600));
    if (av <= 0) return Text(app.t('out_of_stock'), style: const TextStyle(color: Colors.red, fontSize: 12, fontWeight: FontWeight.w600));
    return Text(app.t('in_stock', {'n': av, 'unit': app.unit(p['unit'])}),
        style: const TextStyle(color: Color(0xFF047857), fontSize: 12, fontWeight: FontWeight.w600));
  }
}

class PriceText extends StatelessWidget {
  final Map<String, dynamic> p;
  final bool big;
  const PriceText(this.p, {super.key, this.big = false});
  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    if (p['price'] == null) {
      return Text(app.t('price_on_request'), style: TextStyle(fontWeight: FontWeight.w700, fontSize: big ? 22 : 14, color: const Color(0xFF334155)));
    }
    return Text.rich(TextSpan(children: [
      TextSpan(text: app.money(p['price']), style: TextStyle(fontWeight: FontWeight.w800, fontSize: big ? 26 : 16, color: ink)),
      TextSpan(text: ' / ${app.unit(p['unit'])}', style: TextStyle(fontSize: big ? 14 : 11, color: ink500)),
    ]));
  }
}

class ProductCard extends StatelessWidget {
  final Map<String, dynamic> p;
  const ProductCard(this.p, {super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final inCart = app.inCart(p['id'] as int);
    final av = p['available'] as int?;
    final soldOut = av != null && av <= 0;
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ProductScreen(id: p['id'] as int))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          AspectRatio(aspectRatio: 4 / 3, child: ProductImage(src: p['image'], category: p['category'])),
          Padding(
            padding: const EdgeInsets.fromLTRB(10, 8, 10, 0),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              PriceText(p),
              const SizedBox(height: 2),
              Text(app.p(p['name']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w600, height: 1.2)),
              if (app.p(p['spec']).isNotEmpty)
                Text(app.p(p['spec']), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: ink500, fontSize: 12)),
              const SizedBox(height: 2),
              Text('${app.p(p['seller']['name'])} · ${app.p(p['seller']['region_i18n'])}',
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: ink500, fontSize: 11)),
              StockText(p),
            ]),
          ),
          const Spacer(),
          Padding(
            padding: const EdgeInsets.all(8),
            child: SizedBox(
              width: double.infinity,
              height: 38,
              child: FilledButton.icon(
                style: FilledButton.styleFrom(minimumSize: const Size(0, 38), padding: EdgeInsets.zero,
                    backgroundColor: inCart ? const Color(0xFFECFDF5) : brand, foregroundColor: inCart ? const Color(0xFF047857) : Colors.white),
                onPressed: soldOut || inCart ? null : () => app.addToCart(p, (p['min_order'] as int?) ?? 1),
                icon: Icon(inCart ? Icons.check : Icons.add_shopping_cart, size: 18),
                label: Text(inCart ? app.t('in_cart') : app.t('add_to_cart'), style: const TextStyle(fontSize: 13)),
              ),
            ),
          ),
        ]),
      ),
    );
  }
}

SliverGridDelegate productGridDelegate(BuildContext context) {
  final w = MediaQuery.of(context).size.width;
  final cols = w > 900 ? 4 : w > 600 ? 3 : 2;
  return SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: cols, mainAxisSpacing: 10, crossAxisSpacing: 10, mainAxisExtent: 330);
}

class QtyStepper extends StatelessWidget {
  final int value;
  final int min;
  final int? max;
  final ValueChanged<int> onChanged;
  const QtyStepper({super.key, required this.value, required this.onChanged, this.min = 1, this.max});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 40,
      decoration: BoxDecoration(border: Border.all(color: const Color(0xFFCBD5E1)), borderRadius: BorderRadius.circular(12), color: Colors.white),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        IconButton(visualDensity: VisualDensity.compact, onPressed: value > min ? () => onChanged(value - 1) : null, icon: const Icon(Icons.remove, size: 18)),
        SizedBox(width: 44, child: Text('$value', textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w700))),
        IconButton(visualDensity: VisualDensity.compact, onPressed: max == null || value < max! ? () => onChanged(value + 1) : null, icon: const Icon(Icons.add, size: 18)),
      ]),
    );
  }
}

const statusColors = <String, Color>{
  'new': Color(0xFF1D4ED8), 'review': Color(0xFFB45309), 'contract': Color(0xFF047857), 'rejected': Color(0xFFB91C1C),
  'cancelled': Color(0xFF64748B), 'active': Color(0xFFB45309), 'paid': Color(0xFF047857), 'shipped': Color(0xFF6D28D9), 'done': Color(0xFF64748B),
};

class StatusChip extends StatelessWidget {
  final String status;
  final String label;
  const StatusChip(this.status, this.label, {super.key});
  @override
  Widget build(BuildContext context) {
    final c = statusColors[status] ?? ink500;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(99)),
      child: Text(label, style: TextStyle(color: c, fontWeight: FontWeight.w700, fontSize: 12)),
    );
  }
}

class DemoBadge extends StatelessWidget {
  const DemoBadge({super.key});
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(color: const Color(0xFFFFFBEB), borderRadius: BorderRadius.circular(6)),
        child: Text(context.read<AppState>().t('demo'), style: const TextStyle(color: Color(0xFFB45309), fontSize: 11, fontWeight: FontWeight.w700)),
      );
}

void toast(BuildContext context, String msg) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg), behavior: SnackBarBehavior.floating));
}

class LangButton extends StatelessWidget {
  const LangButton({super.key});
  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return PopupMenuButton<String>(
      icon: const Icon(Icons.language),
      initialValue: app.lang,
      onSelected: app.setLang,
      itemBuilder: (_) => langs.entries.map((e) => PopupMenuItem(value: e.key, child: Text(e.value))).toList(),
    );
  }
}

class SectionTitle extends StatelessWidget {
  final String text;
  final VoidCallback? onMore;
  const SectionTitle(this.text, {super.key, this.onMore});
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 20, 8, 8),
        child: Row(children: [
          Expanded(child: Text(text, style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w800))),
          if (onMore != null) TextButton(onPressed: onMore, child: Text(context.read<AppState>().t('see_all'))),
        ]),
      );
}

/// ImkonMarket belgisi (saytdagi SVG logotip bilan bir xil).
class LogoMark extends StatelessWidget {
  final double size;
  const LogoMark({super.key, this.size = 36});
  @override
  Widget build(BuildContext context) => SizedBox(width: size, height: size, child: CustomPaint(painter: _LogoPainter()));
}

class _LogoPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final k = size.width / 40;
    canvas.scale(k);
    final bgRect = RRect.fromRectAndRadius(const Rect.fromLTWH(0, 0, 40, 40), const Radius.circular(11));
    canvas.drawRRect(
        bgRect,
        Paint()
          ..shader = const LinearGradient(colors: [Color(0xFF3372FB), Color(0xFF1936AD)], begin: Alignment.topLeft, end: Alignment.bottomRight)
              .createShader(const Rect.fromLTWH(0, 0, 40, 40)));
    final white = Paint()..color = Colors.white;
    final bag = Path()
      ..moveTo(9.5, 15)
      ..lineTo(30.5, 15)
      ..lineTo(28.9, 30.2)
      ..quadraticBezierTo(28.6, 32.3, 26.5, 32.3)
      ..lineTo(13.5, 32.3)
      ..quadraticBezierTo(11.4, 32.3, 11.1, 30.2)
      ..close();
    canvas.drawPath(bag, white);
    final handle = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(const Rect.fromLTWH(15, 8.8, 10, 10), 3.1416, 3.1416, false, handle);
    final arrow = Paint()
      ..color = accent
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.4
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    canvas.drawPath(Path()..moveTo(14.5, 27.5)..lineTo(18.5, 23.5)..lineTo(21.1, 26.1)..lineTo(25.5, 21.5), arrow);
    canvas.drawPath(Path()..moveTo(22.6, 21.3)..lineTo(25.7, 21.3)..lineTo(25.7, 24.4), arrow);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class BrandTitle extends StatelessWidget {
  final bool light;
  const BrandTitle({super.key, this.light = false});
  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: [
        const LogoMark(size: 30),
        const SizedBox(width: 8),
        Text.rich(TextSpan(children: [
          TextSpan(text: 'Imkon', style: TextStyle(color: light ? Colors.white : ink)),
          TextSpan(text: 'Market', style: TextStyle(color: light ? accent : brand)),
        ]), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 20)),
      ]);
}
