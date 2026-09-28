import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/state.dart';
import 'widgets.dart';

/// Xaridor ma'lumotlari (B2C / B2B), to'lov usuli, yetkazish, shartnoma tili.
class BuyerData {
  String type = 'b2c';
  String payment = 'payme';
  bool delivery = false;
  String lang = 'uz';
  final c = <String, TextEditingController>{
    for (final k in [
      'buyer_name', 'buyer_pinfl', 'buyer_passport', 'buyer_inn', 'buyer_director', 'buyer_phone', 'buyer_email',
      'buyer_address', 'buyer_bank_name', 'buyer_bank_account', 'buyer_bank_mfo', 'delivery_address', 'comment',
    ])
      k: TextEditingController(),
  };

  BuyerData() {
    c['buyer_phone']!.text = '+998 ';
  }

  String v(String k) => c[k]!.text.trim();

  Set<String> validate() {
    final e = <String>{};
    if (v('buyer_name').isEmpty) e.add('buyer_name');
    if (v('buyer_phone').replaceAll(RegExp(r'\D'), '').length < 9) e.add('buyer_phone');
    if (type == 'b2b' && !RegExp(r'^\d{9}$').hasMatch(v('buyer_inn'))) e.add('buyer_inn');
    if (type == 'b2c' && !RegExp(r'^\d{14}$').hasMatch(v('buyer_pinfl'))) e.add('buyer_pinfl');
    if (delivery && v('delivery_address').isEmpty) e.add('delivery_address');
    return e;
  }

  Map<String, dynamic> toJson() => {
        for (final e in c.entries) e.key: e.value.text.trim(),
        'buyer_phone': v('buyer_phone').replaceAll(RegExp(r'[^\d+]'), ''),
        'buyer_type': type,
        'payment_method': payment,
        'delivery_required': delivery,
        'lang': lang,
      };
}

class BuyerForm extends StatefulWidget {
  final BuyerData data;
  final Set<String> errors;
  const BuyerForm({super.key, required this.data, required this.errors});

  @override
  State<BuyerForm> createState() => _BuyerFormState();
}

class _BuyerFormState extends State<BuyerForm> {
  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final d = widget.data;
    Widget field(String k, String label, {TextInputType? kb, int? max, bool req = false}) => Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: TextField(
            controller: d.c[k],
            keyboardType: kb,
            maxLength: max,
            decoration: InputDecoration(
              labelText: req ? '$label *' : label,
              counterText: '',
              errorText: widget.errors.contains(k) ? app.t('required') : null,
            ),
          ),
        );
    Widget choice(String label, bool on, IconData icon, VoidCallback tap, {Widget? badge}) => Expanded(
          child: InkWell(
            onTap: () => setState(tap),
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: on ? const Color(0xFFEEF5FF) : Colors.white,
                border: Border.all(color: on ? brand : const Color(0xFFE2E8F0), width: on ? 2 : 1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(children: [
                Icon(icon, color: on ? brand : ink500),
                const SizedBox(height: 4),
                Text(label, textAlign: TextAlign.center, style: TextStyle(fontWeight: FontWeight.w600, fontSize: 12.5, color: on ? brand : ink)),
                if (badge != null) badge,
              ]),
            ),
          ),
        );

    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text(app.t('buyer_type'), style: const TextStyle(fontWeight: FontWeight.w700)),
      const SizedBox(height: 8),
      Row(children: [
        choice(app.t('individual'), d.type == 'b2c', Icons.person_outline, () => d.type = 'b2c'),
        const SizedBox(width: 8),
        choice(app.t('company'), d.type == 'b2b', Icons.apartment, () {
          d.type = 'b2b';
          d.payment = 'bank';
        }),
      ]),
      const SizedBox(height: 16),
      if (d.type == 'b2c') ...[
        field('buyer_name', app.t('full_name'), req: true),
        field('buyer_pinfl', app.t('pinfl'), kb: TextInputType.number, max: 14, req: true),
        field('buyer_passport', app.t('passport'), max: 12),
      ] else ...[
        field('buyer_name', app.t('company_name'), req: true),
        field('buyer_inn', app.t('inn'), kb: TextInputType.number, max: 9, req: true),
        field('buyer_director', app.t('director')),
        field('buyer_bank_name', app.t('bank_name')),
        field('buyer_bank_account', app.t('bank_account'), kb: TextInputType.number, max: 20),
        field('buyer_bank_mfo', app.t('mfo'), kb: TextInputType.number, max: 5),
      ],
      field('buyer_phone', app.t('phone'), kb: TextInputType.phone, req: true),
      field('buyer_email', app.t('email'), kb: TextInputType.emailAddress),
      field('buyer_address', app.t('address')),
      const SizedBox(height: 4),
      Text(app.t('payment_method'), style: const TextStyle(fontWeight: FontWeight.w700)),
      const SizedBox(height: 8),
      Row(children: [
        choice('Payme', d.payment == 'payme', Icons.credit_card, () => d.payment = 'payme', badge: app.demo('payme') ? const DemoBadge() : null),
        const SizedBox(width: 8),
        choice('Click', d.payment == 'click', Icons.credit_card, () => d.payment = 'click', badge: app.demo('click') ? const DemoBadge() : null),
        const SizedBox(width: 8),
        choice(app.t('pay_bank'), d.payment == 'bank', Icons.account_balance, () => d.payment = 'bank'),
      ]),
      const SizedBox(height: 6),
      Text(d.payment == 'bank' ? app.t('pay_bank_note') : app.t('pay_online_note'), style: const TextStyle(color: ink500, fontSize: 12)),
      const SizedBox(height: 16),
      Text(app.t('delivery'), style: const TextStyle(fontWeight: FontWeight.w700)),
      const SizedBox(height: 8),
      Row(children: [
        choice(app.t('pickup'), !d.delivery, Icons.warehouse_outlined, () => d.delivery = false),
        const SizedBox(width: 8),
        choice(app.t('delivery_to'), d.delivery, Icons.local_shipping_outlined, () => d.delivery = true),
      ]),
      const SizedBox(height: 12),
      if (d.delivery) field('delivery_address', app.t('delivery_address'), req: true),
      DropdownButtonFormField<String>(
        value: d.lang,
        decoration: InputDecoration(labelText: app.t('contract_lang')),
        items: langs.entries.map((e) => DropdownMenuItem(value: e.key, child: Text(e.value))).toList(),
        onChanged: (v) => setState(() => d.lang = v ?? 'uz'),
      ),
      const SizedBox(height: 12),
      TextField(controller: d.c['comment'], maxLines: 3, decoration: InputDecoration(labelText: app.t('comment'))),
    ]);
  }
}
