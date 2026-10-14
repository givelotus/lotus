import 'package:flutter/services.dart';
import 'package:flutter_contacts/flutter_contacts.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lotus_dart/lotus.dart' as lotus;
import 'package:vase/features/contacts/device_contacts.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const channel = MethodChannel('flutter_contacts');
  final calls = <MethodCall>[];
  var status = 'notDetermined';
  final address = lotus.Address.fromHex(
    '0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798',
    lotus.NetworkType.MAIN,
  ).toXAddress();
  setUp(() {
    calls.clear();
    status = 'notDetermined';
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
          calls.add(call);
          switch (call.method) {
            case 'permissions.check':
              return status;
            case 'permissions.request':
              return status = 'limited';
            case 'crud.getAll':
              return [
                Contact(
                  id: 'a',
                  displayName: 'Alice',
                  websites: [
                    const Website(url: 'https://example.com'),
                    Website(url: '$address?amount=100'),
                    Website(url: address),
                  ],
                ).toJson(),
                const Contact(id: 'b', displayName: 'Bob').toJson(),
              ];
            default:
              throw StateError('Unexpected native operation ${call.method}');
          }
        });
  });
  tearDown(
    () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null),
  );

  test(
    'requests read access once, respects limited access and reads only websites',
    () async {
      const device = DeviceContacts();
      final snapshot = await device.read(requestPermission: true);
      expect(snapshot.status, PermissionStatus.limited);
      expect(snapshot.contacts.map((c) => c.name), ['Alice', 'Bob']);
      expect(snapshot.contacts.first.address, address);
      expect(snapshot.contacts.last.address, isNull);
      expect(calls.map((c) => c.method), [
        'permissions.check',
        'permissions.request',
        'crud.getAll',
      ]);
      expect(calls[1].arguments, {'type': 'read'});
      expect(calls.last.arguments['properties'], ['website']);
      calls.clear();
      await device.read(requestPermission: true);
      expect(calls.map((c) => c.method), ['permissions.check', 'crud.getAll']);
    },
  );

  test('denial never enumerates contacts or repeatedly prompts', () async {
    for (final denied in ['denied', 'permanentlyDenied', 'restricted']) {
      status = denied;
      calls.clear();
      final snapshot = await const DeviceContacts().read(
        requestPermission: true,
      );
      expect(snapshot.contacts, isEmpty);
      expect(calls.map((c) => c.method), ['permissions.check']);
    }
  });
}
