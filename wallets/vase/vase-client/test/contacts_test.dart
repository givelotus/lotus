import 'dart:convert';
import 'dart:async';
import 'package:flutter_contacts/flutter_contacts.dart' show PermissionStatus;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:go_router/go_router.dart';
import 'package:lotus_dart/lotus.dart';
import 'package:provider/provider.dart';
import 'package:vase/config/theme.dart';
import 'package:vase/features/contacts/contacts_model.dart';
import 'package:vase/features/contacts/contacts_page.dart';
import 'package:vase/features/contacts/device_contacts.dart';
import 'package:vase/features/send/send_model.dart';
import 'secure_storage_test.dart' show MemoryStorage;

class _Storage extends MemoryStorage {
  _Storage(super.values, {super.failKey});
  bool failWrite = false;
  @override
  Future<void> write({
    required String key,
    required String? value,
    AndroidOptions? aOptions,
    AppleOptions? iOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (failWrite) throw PlatformException(code: 'fixture_write_failure');
    writes.add(key);
    values[key] = value!;
  }
}

class _DeviceContacts extends DeviceContacts {
  @override
  bool get supported => false;
}

class _SyncDeviceContacts extends DeviceContacts {
  final events = StreamController<void>.broadcast();
  DeviceContactsSnapshot snapshot = const DeviceContactsSnapshot(
    PermissionStatus.granted,
    [DeviceContactLink('phone-a', 'Phone Alice', null)],
  );
  final requests = <bool>[];
  bool fail = false;
  @override
  bool get supported => true;
  @override
  Stream<void> get changes => events.stream;
  @override
  Future<DeviceContactsSnapshot> read({bool requestPermission = false}) async {
    requests.add(requestPermission);
    if (fail) throw StateError('test read failed');
    return snapshot;
  }
}

void main() {
  final address = Address.fromHex(
    '0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798',
    NetworkType.MAIN,
  ).toXAddress();
  late _Storage storage;
  late ContactsModel model;
  setUp(() {
    storage = _Storage({'seed': 'untouched wallet fixture'});
    model = ContactsModel(storage: storage);
  });
  tearDown(() => model.dispose());

  test(
    'saved contacts survive restart with independent stable identity and phone link',
    () async {
      await model.load();
      await model.save(
        name: ' Alice ',
        address: address,
        deviceContactId: 'phone-1',
      );
      final first = model.contacts.single;
      await model.save(
        id: first.id,
        name: 'Alice Smith',
        address: address,
        deviceContactId: first.deviceContactId,
      );
      final restarted = ContactsModel(storage: storage);
      addTearDown(restarted.dispose);
      await restarted.load();
      expect(restarted.contacts.single.id, first.id);
      expect(restarted.contacts.single.name, 'Alice Smith');
      expect(restarted.contacts.single.deviceContactId, 'phone-1');
      expect(storage.writes.toSet(), {contactsStorageKey});
      expect(storage.values['seed'], 'untouched wallet fixture');
      await restarted.remove(first.id);
      expect(restarted.contacts, isEmpty);
    },
  );
  test('read failure cannot overwrite an existing contact book', () async {
    final failed = ContactsModel(
      storage: _Storage({
        contactsStorageKey: 'retained',
      }, failKey: contactsStorageKey),
    );
    addTearDown(failed.dispose);
    await failed.load();
    expect(failed.unavailable, isTrue);
    await expectLater(
      failed.save(name: 'Alice', address: address),
      throwsStateError,
    );
  });
  test('corrupt and unknown-version contact books fail closed', () async {
    for (final raw in [
      'not-json',
      '{"version":2,"contacts":[]}',
      '{"version":1,"contacts":[{}]}',
    ]) {
      storage.values[contactsStorageKey] = raw;
      final failed = ContactsModel(storage: storage);
      await failed.load();
      expect(failed.unavailable, isTrue);
      await expectLater(failed.remove('id'), throwsStateError);
      expect(storage.values[contactsStorageKey], raw);
      failed.dispose();
    }
    expect(storage.writes, isEmpty);
  });
  test(
    'failed edit keeps both persisted and active contacts unchanged',
    () async {
      await model.load();
      await model.save(name: 'Alice', address: address);
      final original = storage.values[contactsStorageKey];
      storage.failWrite = true;
      await expectLater(
        model.save(id: model.contacts.single.id, name: 'Bob', address: address),
        throwsA(isA<PlatformException>()),
      );
      expect(model.contacts.single.name, 'Alice');
      expect(storage.values[contactsStorageKey], original);
    },
  );
  test(
    'reject malformed, other-chain, and amount-bearing addresses before storing',
    () async {
      await model.load();
      for (final bad in [
        'wrong',
        '$address?amount=10',
        '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
      ]) {
        await expectLater(
          model.save(name: 'Alice', address: bad),
          throwsFormatException,
        );
      }
      expect(storage.writes, isEmpty);
    },
  );

  testWidgets(
    'phone access starts on visibility and refreshes changes, resume and revocation',
    (tester) async {
      final phone = _SyncDeviceContacts();
      addTearDown(phone.events.close);
      Future<void> render(bool active) async {
        await tester.pumpWidget(
          MaterialApp(
            home: ContactsPage(
              model: model,
              deviceContacts: phone,
              active: active,
            ),
          ),
        );
        await tester.pumpAndSettle();
      }

      await render(false);
      expect(phone.requests, isEmpty);
      await render(true);
      expect(phone.requests, [true]);
      expect(find.text('Phone Alice'), findsOneWidget);
      expect(find.text('Add Lotus address'), findsOneWidget);
      expect(storage.writes, isEmpty);
      phone.snapshot = DeviceContactsSnapshot(PermissionStatus.limited, [
        DeviceContactLink('phone-a', 'Alice renamed', address),
      ]);
      phone.events.add(null);
      await tester.pumpAndSettle();
      expect(find.text('Phone Alice'), findsNothing);
      expect(find.text('Alice renamed'), findsOneWidget);
      expect(find.text('Showing selected phone contacts'), findsOneWidget);
      phone.fail = true;
      phone.events.add(null);
      await tester.pumpAndSettle();
      expect(find.text('Phone contacts could not refresh.'), findsOneWidget);
      expect(find.text('Alice renamed'), findsOneWidget);
      phone.fail = false;
      phone.snapshot = const DeviceContactsSnapshot(
        PermissionStatus.permanentlyDenied,
        [],
      );
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pumpAndSettle();
      expect(find.text('Alice renamed'), findsNothing);
      expect(phone.requests.skip(1).every((request) => !request), isTrue);
      expect(storage.writes, isEmpty);
      await tester.pumpWidget(const SizedBox());
      expect(phone.events.hasListener, isFalse);
    },
  );

  testWidgets(
    'linked names refresh without changing saved destinations or deleting local contacts',
    (tester) async {
      await model.load();
      await model.save(
        name: 'Saved Alice',
        address: address,
        deviceContactId: 'phone-a',
      );
      final saved = storage.values[contactsStorageKey];
      final identity = model.contacts.single.id;
      final phone = _SyncDeviceContacts();
      addTearDown(phone.events.close);
      await tester.pumpWidget(
        MaterialApp(
          home: ContactsPage(model: model, deviceContacts: phone),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('Phone Alice'), findsOneWidget);
      expect(find.text('Saved Alice'), findsOneWidget);
      expect(find.text(address), findsNWidgets(2));
      phone.snapshot = const DeviceContactsSnapshot(
        PermissionStatus.granted,
        [],
      );
      phone.events.add(null);
      await tester.pumpAndSettle();
      expect(find.text('Saved Alice'), findsOneWidget);
      expect(model.contacts.single.id, identity);
      expect(storage.values[contactsStorageKey], saved);
      await tester.pumpWidget(const SizedBox());
    },
  );

  testWidgets(
    'compact editor keeps focused input visible above keyboard and Next moves focus',
    (tester) async {
      tester.view.physicalSize = const Size(390, 640);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lotusTheme,
          home: ContactsPage(model: model, deviceContacts: _DeviceContacts()),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('Add contact'));
      await tester.pumpAndSettle();
      expect(tester.testTextInput.isVisible, isTrue);
      await tester.enterText(
        find.widgetWithText(TextField, 'Name'),
        'Keyboard Alice',
      );
      await tester.testTextInput.receiveAction(TextInputAction.next);
      await tester.pumpAndSettle();
      tester.testTextInput.enterText(address);
      await tester.pump();
      expect(
        tester
            .widget<TextField>(find.widgetWithText(TextField, 'Lotus address'))
            .controller!
            .text,
        address,
      );
      tester.view.viewInsets = const FakeViewPadding(bottom: 290);
      addTearDown(tester.view.resetViewInsets);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await tester.ensureVisible(find.widgetWithText(TextButton, 'Save'));
      await tester.tap(find.widgetWithText(TextButton, 'Save'));
      await tester.pumpAndSettle();
      expect(model.contacts.single.name, 'Keyboard Alice');
      expect(model.contacts.single.address, address);
    },
  );

  testWidgets(
    'add, search and select a contact opens Send with a fresh amount',
    (tester) async {
      await model.load();
      final send = SendModel()..setPayment('old', BigInt.from(999));
      final router = GoRouter(
        initialLocation: '/contacts',
        routes: [
          GoRoute(
            path: '/contacts',
            builder: (_, _) =>
                ContactsPage(model: model, deviceContacts: _DeviceContacts()),
          ),
          GoRoute(
            path: '/send',
            builder: (_, _) => const Scaffold(body: Text('Payment details')),
          ),
        ],
      );
      addTearDown(() {
        router.dispose();
        send.dispose();
      });
      await tester.pumpWidget(
        ChangeNotifierProvider<SendModel>.value(
          value: send,
          child: MaterialApp.router(
            routerConfig: router,
            theme: AppTheme.lotusTheme,
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('Add contact'));
      await tester.pumpAndSettle();
      await tester.enterText(find.widgetWithText(TextField, 'Name'), 'Alice');
      await tester.enterText(
        find.widgetWithText(TextField, 'Lotus address'),
        address,
      );
      await tester.tap(find.widgetWithText(TextButton, 'Save'));
      await tester.pumpAndSettle();
      expect(find.text('Alice'), findsOneWidget);
      expect(find.byTooltip('Import phone contact'), findsNothing);
      await tester.enterText(
        find.widgetWithText(TextField, 'Search contacts'),
        'Nobody',
      );
      await tester.pumpAndSettle();
      expect(find.text('No matching contacts'), findsOneWidget);
      await tester.enterText(
        find.widgetWithText(TextField, 'Search contacts'),
        'Ali',
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Alice'));
      await tester.pumpAndSettle();
      expect(find.text('Payment details'), findsOneWidget);
      expect(send.address, address);
      expect(send.amount, BigInt.zero);
      expect(
        jsonDecode(storage.values[contactsStorageKey]!)['contacts'],
        hasLength(1),
      );
    },
  );
}
