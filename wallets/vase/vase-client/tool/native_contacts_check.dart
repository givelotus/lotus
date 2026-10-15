// Developer-only: install on a disposable simulator, never an existing wallet.
// Creates and removes one fixture phone contact; never opens wallet storage.
import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_contacts/flutter_contacts.dart';
import 'package:vase/features/contacts/contacts_model.dart';
import 'package:vase/features/contacts/device_contacts.dart';

void main() {
  runApp(const MaterialApp(home: _CheckPage()));
}

class _CheckPage extends StatefulWidget {
  const _CheckPage();
  @override
  State<_CheckPage> createState() => _CheckState();
}

class _CheckState extends State<_CheckPage> {
  String result =
      'Disposable simulator only. Creates one fixture contact, '
      'checks Vase write-back, then deletes only that fixture.';
  bool running = false;

  void report(String message) {
    debugPrint('VASE_CONTACT_CHECK: $message');
    if (mounted) setState(() => result = message);
  }

  Future<void> run() async {
    setState(() => running = true);
    String? fixtureId;
    StreamSubscription<void>? subscription;
    try {
      const device = DeviceContacts();
      final snapshot = await device.read(requestPermission: true);
      report('Read permission: ${snapshot.status.name}');
      if (snapshot.status != PermissionStatus.granted &&
          snapshot.status != PermissionStatus.limited) {
        if (snapshot.contacts.isNotEmpty) {
          throw StateError('Denied read leaked contacts');
        }
        report('PASS: ${snapshot.status.name} returns an empty directory');
        return;
      }
      var events = 0;
      subscription = device.changes.listen((_) => events++);
      Future<void> changed(int previous) async {
        for (var i = 0; i < 100 && events <= previous; i++) {
          await Future<void>.delayed(const Duration(milliseconds: 100));
        }
        if (events <= previous) throw StateError('Missing native change event');
      }

      var beforeEvents = events;
      fixtureId = await FlutterContacts.create(
        const Contact(
          name: Name(first: 'Vase', last: 'Native Fixture'),
          phones: [Phone(number: '+12025550123')],
          emails: [Email(address: 'vase-fixture@example.invalid')],
          websites: [Website(url: 'https://example.invalid/fixture')],
        ),
      );
      await changed(beforeEvents);
      const properties = {
        ContactProperty.name,
        ContactProperty.phone,
        ContactProperty.email,
        ContactProperty.website,
      };
      final before = (await FlutterContacts.get(
        fixtureId,
        properties: properties,
      ))!;
      const address = 'lotus_16PSJLxxKyuh8ZtQP8cuXwuHpFmJgPH6sE12Rdhgh';
      final recipient = WalletContact(
        id: 'native-fixture',
        name: 'Vase Native Fixture',
        address: address,
        deviceContactId: fixtureId,
      );
      beforeEvents = events;
      await device.writeAddress(recipient);
      await changed(beforeEvents);
      // Idempotence: repeated explicit write-back must not duplicate the field.
      await device.writeAddress(recipient);
      final after = (await FlutterContacts.get(
        fixtureId,
        properties: properties,
      ))!;
      if (after.name != before.name ||
          !listEquals(after.phones, before.phones) ||
          !listEquals(after.emails, before.emails) ||
          after.websites.where((w) => w.url == address).length != 1 ||
          !after.websites.contains(before.websites.single)) {
        throw StateError('Contact fields changed or Lotus field duplicated');
      }
      var directory = await device.read();
      if (directory.contacts.singleWhere((c) => c.id == fixtureId).address !=
          address) {
        throw StateError('Written Lotus address missing from live directory');
      }
      beforeEvents = events;
      await FlutterContacts.update(
        after.copyWith(
          name: const Name(first: 'Vase', last: 'Edited Fixture'),
          websites: before.websites,
        ),
      );
      await changed(beforeEvents);
      directory = await device.read();
      final edited = directory.contacts.singleWhere((c) => c.id == fixtureId);
      if (!edited.name.contains('Edited') || edited.address != null) {
        throw StateError('Native edit/address removal not reflected');
      }
      beforeEvents = events;
      await FlutterContacts.delete(fixtureId);
      final deletedId = fixtureId;
      fixtureId = null;
      await changed(beforeEvents);
      directory = await device.read();
      if (directory.contacts.any((c) => c.id == deletedId)) {
        throw StateError('Deleted fixture remains in live directory');
      }
      report(
        'PASS (${snapshot.status.name}): native write-back; name, phone, '
        'email and existing website preserved; no duplicate Lotus field; '
        'change events; edit/address removal; deletion. Fixture removed.',
      );
    } catch (error) {
      report('FAIL: $error');
    } finally {
      if (fixtureId != null) {
        try {
          await FlutterContacts.delete(fixtureId);
        } catch (_) {
          report('$result\nFixture cleanup failed: $fixtureId');
        }
      }
      await subscription?.cancel();
      if (mounted) setState(() => running = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Native contacts check')),
    body: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          Text(result),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: running ? null : run,
            child: const Text('Run fixture check'),
          ),
        ],
      ),
    ),
  );
}
