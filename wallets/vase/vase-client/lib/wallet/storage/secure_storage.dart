import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Keep the original wallet namespace/keychain identity while migrating through
/// the v10 bridge. Never erase keys when decryption or migration fails.
const walletSecureStorage = FlutterSecureStorage(
  aOptions: AndroidOptions(
    resetOnError: false,
    migrateOnAlgorithmChange: true,
    migrateWithBackup: true,
  ),
  iOptions: IOSOptions(
    accountName: 'flutter_secure_storage_service',
    accessibility: KeychainAccessibility.unlocked,
    synchronizable: false,
  ),
  mOptions: MacOsOptions(
    accountName: 'flutter_secure_storage_service',
    accessibility: KeychainAccessibility.unlocked,
    synchronizable: false,
    usesDataProtectionKeychain: true,
  ),
  wOptions: WindowsOptions(useBackwardCompatibility: true),
);
