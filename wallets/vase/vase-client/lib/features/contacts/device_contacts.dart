import 'package:flutter/foundation.dart';
import 'package:flutter_contacts/flutter_contacts.dart';
import 'contacts_model.dart';

class DeviceContactLink {
  const DeviceContactLink(this.id, this.name, this.address);
  final String id, name;
  final String? address;
}

class DeviceContactsSnapshot {
  const DeviceContactsSnapshot(this.status, this.contacts);
  final PermissionStatus status;
  final List<DeviceContactLink> contacts;
}

class DeviceContacts {
  const DeviceContacts();
  bool get supported =>
      !kIsWeb &&
      (defaultTargetPlatform == TargetPlatform.iOS ||
          defaultTargetPlatform == TargetPlatform.android);

  Stream<void> get changes => FlutterContacts.onDatabaseChange;
  Future<void> openSettings() => FlutterContacts.permissions.openSettings();

  Future<DeviceContactsSnapshot> read({bool requestPermission = false}) async {
    var status = await FlutterContacts.permissions.check(PermissionType.read);
    if (requestPermission && status == PermissionStatus.notDetermined) {
      status = await FlutterContacts.permissions.request(PermissionType.read);
    }
    if (status != PermissionStatus.granted &&
        status != PermissionStatus.limited) {
      return DeviceContactsSnapshot(status, const []);
    }
    final contacts = await FlutterContacts.getAll(
      properties: {ContactProperty.website},
    );
    final result = <DeviceContactLink>[];
    for (final contact in contacts) {
      if (contact.id == null) continue;
      String? address;
      for (final website in contact.websites) {
        try {
          address = contactAddress(website.url);
          break;
        } catch (_) {
          /* Other websites are not payment destinations. */
        }
      }
      result.add(
        DeviceContactLink(contact.id!, contact.displayName ?? '', address),
      );
    }
    return DeviceContactsSnapshot(status, result);
  }

  Future<DeviceContactLink?> pick() async {
    // Keep the picker for explicitly linking a saved Vase contact.
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
    // Replace only our explicitly labelled fields; preserve all other websites.
    final websites = current.websites
        .where((w) => w.label.customLabel != 'Lotus XPI')
        .toList();
    websites.insert(
      0,
      Website(
        url: contact.address,
        label: const Label(WebsiteLabel.custom, 'Lotus XPI'),
      ),
    );
    if (listEquals(current.websites, websites)) return;
    await FlutterContacts.update(current.copyWith(websites: websites));
  }
}
