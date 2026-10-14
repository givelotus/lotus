import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:lotus_dart/nakamoto.dart' as chain;
import 'package:vase/wallet/storage/secure_storage.dart';

const contactsStorageKey = 'vase_contacts_v1';

String contactAddress(String text) {
  final value = text.trim();
  // Store destinations only, never an amount carried by an imported payment URI.
  final uri = Uri.tryParse(value);
  if (uri == null || uri.hasQuery || uri.hasFragment) {
    throw const FormatException(
      'Enter a Lotus mainnet address without an amount',
    );
  }
  return chain.Address.parse(
    value,
    chain: chain.getChain('xpi-mainnet'),
  ).encode();
}

class WalletContact {
  const WalletContact({
    required this.id,
    required this.name,
    required this.address,
    this.deviceContactId,
  });
  final String id, name, address;
  final String? deviceContactId;

  Map<String, Object?> toJson() => {
    'id': id,
    'name': name,
    'addresses': [
      {'chain': 'XPI', 'network': 'mainnet', 'address': address},
    ],
    if (deviceContactId != null) 'deviceContactId': deviceContactId,
  };

  factory WalletContact.fromJson(Object? value) {
    if (value is! Map<String, dynamic> ||
        value['id'] is! String ||
        value['name'] is! String ||
        value['addresses'] is! List ||
        value['deviceContactId'] != null &&
            value['deviceContactId'] is! String) {
      throw const FormatException('Invalid contact record');
    }
    final addresses = value['addresses'] as List;
    if (addresses.length != 1 ||
        addresses.first is! Map ||
        addresses.first['chain'] != 'XPI' ||
        addresses.first['network'] != 'mainnet') {
      throw const FormatException('Unsupported contact address');
    }
    final id = value['id'] as String, name = value['name'] as String;
    if (id.isEmpty || name.trim().isEmpty || name.length > 120) {
      throw const FormatException('Invalid contact identity');
    }
    return WalletContact(
      id: id,
      name: name,
      address: contactAddress(addresses.first['address'] as String),
      deviceContactId: value['deviceContactId'] as String?,
    );
  }
}

/// App-owned identities; phone links are optional, never wallet/key identifiers.
class ContactsModel extends ChangeNotifier {
  ContactsModel({FlutterSecureStorage storage = walletSecureStorage})
    : _storage = storage; // Public injection preserves the shared namespace.
  final FlutterSecureStorage _storage;
  List<WalletContact> _contacts = [];
  List<WalletContact> get contacts => List.unmodifiable(_contacts);
  bool loaded = false, unavailable = false, busy = false;
  bool _disposed = false;
  Future<void>? _loading;

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  Future<void> load() => _loading ??= _load();
  Future<void> _load() async {
    try {
      final raw = await _storage.read(key: contactsStorageKey);
      final parsed = raw == null ? <WalletContact>[] : _decode(raw);
      _contacts = parsed;
      unavailable = false;
      loaded = true;
    } catch (_) {
      // A read/format failure must never overwrite the existing address book.
      unavailable = true;
      loaded = false;
    } finally {
      _loading = null;
      _notify();
    }
  }

  List<WalletContact> _decode(String raw) {
    final value = jsonDecode(raw);
    if (value is! Map ||
        value['version'] != 1 ||
        value['contacts'] is! List ||
        (value['contacts'] as List).length > 10000) {
      throw const FormatException('Invalid contacts');
    }
    final records = (value['contacts'] as List)
        .map(WalletContact.fromJson)
        .toList();
    if (records.map((c) => c.id).toSet().length != records.length) {
      throw const FormatException('Duplicate contact identity');
    }
    return records;
  }

  Future<void> save({
    String? id,
    required String name,
    required String address,
    String? deviceContactId,
  }) async {
    final cleanName = name.trim();
    if (cleanName.isEmpty || cleanName.length > 120) {
      throw const FormatException('Enter a name of up to 120 characters');
    }
    final cleanAddress = contactAddress(address);
    final random = Random.secure();
    final contactId =
        id ??
        List.generate(
          16,
          (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0'),
        ).join();
    if (id != null && !_contacts.any((c) => c.id == id)) {
      throw StateError('Contact missing');
    }
    final updated = WalletContact(
      id: contactId,
      name: cleanName,
      address: cleanAddress,
      deviceContactId: deviceContactId,
    );
    await _write([..._contacts.where((c) => c.id != contactId), updated]);
  }

  Future<void> remove(String id) =>
      _write(_contacts.where((c) => c.id != id).toList());
  Future<void> _write(List<WalletContact> records) async {
    if (!loaded || unavailable || busy || _disposed) {
      throw StateError('Contacts unavailable');
    }
    if (records.length > 10000) throw StateError('Contact capacity reached');
    busy = true;
    _notify();
    try {
      records.sort(
        (a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()),
      );
      await _storage.write(
        key: contactsStorageKey,
        value: jsonEncode({
          'version': 1,
          'contacts': records.map((c) => c.toJson()).toList(),
        }),
      );
      _contacts = records;
    } finally {
      busy = false;
      _notify();
    }
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
