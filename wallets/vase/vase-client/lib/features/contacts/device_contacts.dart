import 'package:flutter/foundation.dart';
import 'package:flutter_contacts/flutter_contacts.dart';
import 'contacts_model.dart';

class DeviceContactLink {
  const DeviceContactLink(this.id, this.name, this.address);
  final String id, name;
  final String? address;
}

class DeviceContacts {
  const DeviceContacts();
  bool get supported =>
      !kIsWeb &&
      (defaultTargetPlatform == TargetPlatform.iOS ||
          defaultTargetPlatform == TargetPlatform.android);

  Future<DeviceContactLink?> pick() async {
    // Native picker returns only the selected identity; never enumerate/upload
    // the user's address book or request permission when opening Contacts.
    final chosen = await FlutterContacts.native.showPicker();
    if (chosen?.id == null) return null;
    String? address;
    if (await FlutterContacts.permissions.has(PermissionType.read)) {
      final full = await FlutterContacts.get(
        chosen!.id!,
        properties: {ContactProperty.website},
      );
      for (final website in full?.websites ?? <Website>[]) {
        try {
          address = contactAddress(website.url);
          break;
        } catch (_) {}
      }
    }
    return DeviceContactLink(chosen!.id!, chosen.displayName ?? '', address);
  }

  Future<void> writeAddress(WalletContact contact) async {
    if (contact.deviceContactId == null) {
      throw StateError('Link a phone contact first');
    }
    final status = await FlutterContacts.permissions.request(
      PermissionType.readWrite,
    );
    if (status != PermissionStatus.granted &&
        status != PermissionStatus.limited) {
      throw StateError('Contacts permission unavailable');
    }
    // Fetch immediately before updating and alter websites only. The plugin
    // tracks fetched fields so unfetched photos/phones/etc are left untouched.
    final current = await FlutterContacts.get(
      contact.deviceContactId!,
      properties: {ContactProperty.website},
    );
    if (current == null) {
      throw StateError('Linked phone contact no longer exists');
    }
    final websites = [...current.websites];
    if (websites.any((w) => w.url == contact.address)) return;
    websites.add(
      Website(
        url: contact.address,
        label: const Label(WebsiteLabel.custom, 'Lotus XPI'),
      ),
    );
    await FlutterContacts.update(current.copyWith(websites: websites));
  }
}
